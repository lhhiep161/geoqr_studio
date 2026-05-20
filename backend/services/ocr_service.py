from __future__ import annotations

import logging
import os
import re
import statistics
import time
from collections import Counter
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import List, Optional, Tuple


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OCRCandidate:
    point_label: str
    raw_value1: str
    raw_value2: str
    value1: float
    value2: float
    corrections: List[str]
    confidence_note: str


@dataclass(frozen=True)
class OCRStatusInfo:
    python_packages_ok: bool
    tesseract_available: bool
    tesseract_version: str
    tesseract_cmd: str
    error: Optional[str]


@dataclass(frozen=True)
class OCRRunResult:
    ocr_mode: str
    raw_text: str
    preprocessing_method: str
    ocr_config: str
    language: str
    elapsed_seconds: float
    warnings: List[str]


class OCRError(Exception):
    def __init__(
        self,
        stage: str,
        error_code: str,
        message: str,
        detail: str,
        suggestion: str,
        status_code: int = 503,
    ) -> None:
        super().__init__(message)
        self.stage = stage
        self.error_code = error_code
        self.message = message
        self.detail = detail
        self.suggestion = suggestion
        self.status_code = status_code

    def to_dict(self) -> dict:
        return {
            "ok": False,
            "stage": self.stage,
            "error_code": self.error_code,
            "message": self.message,
            "detail": self.detail,
            "suggestion": self.suggestion,
        }


@dataclass(frozen=True)
class _ColumnContext:
    median: float
    int_len: int
    prefix: str


def _is_plausible_coordinate_pair(value1: float, value2: float) -> bool:
    big_min, big_max = 1_000_000.0, 2_500_000.0
    small_min, small_max = 300_000.0, 800_000.0
    return (
        (big_min <= value1 <= big_max and small_min <= value2 <= small_max)
        or (big_min <= value2 <= big_max and small_min <= value1 <= small_max)
    )


def _normalize_number_token(token: str) -> str:
    value = token.strip().replace(" ", "")
    if "." in value and "," in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        value = value.replace(",", ".")
    return value


def _extract_numeric_parts(raw: str) -> Optional[Tuple[str, str]]:
    match = re.search(r"(-?)(\d+)(?:[.,](\d+))?", raw.strip())
    if not match:
        return None
    sign = "-" if match.group(1) else ""
    int_part = sign + match.group(2)
    frac = match.group(3) or ""
    return int_part, frac


def _parse_float_strict(raw: str) -> Optional[float]:
    cleaned = raw.strip()
    if not cleaned:
        return None
    if not re.match(r"^-?\d+(?:[.,]\d+)?$", cleaned):
        return None
    try:
        return float(_normalize_number_token(cleaned))
    except ValueError:
        return None


def _build_column_context(values: List[float]) -> Optional[_ColumnContext]:
    if len(values) < 2:
        return None
    int_parts = [str(int(abs(v))) for v in values]
    int_lens = [len(p) for p in int_parts]
    int_len = Counter(int_lens).most_common(1)[0][0]
    prefixes = [p[: min(4, len(p))] for p in int_parts if len(p) == int_len]
    if not prefixes:
        return None
    prefix = Counter(prefixes).most_common(1)[0][0]
    return _ColumnContext(median=float(statistics.median(values)), int_len=int_len, prefix=prefix)


def _proximity_ok(value: float, context: _ColumnContext) -> bool:
    threshold = max(20_000.0, abs(context.median) * 0.2)
    return abs(value - context.median) <= threshold


def _strict_pattern_proximity_ok(value: float, context: _ColumnContext) -> bool:
    threshold = max(5_000.0, abs(context.median) * 0.02)
    return abs(value - context.median) <= threshold


def _correct_by_column_context(
    raw: str,
    context: Optional[_ColumnContext],
    field_name: str,
) -> Tuple[Optional[float], Optional[str], Optional[str]]:
    direct = _parse_float_strict(raw)
    if direct is not None:
        return direct, None, None

    if context is None:
        return None, None, f"{field_name}: not enough valid column context for correction ({raw})"

    parts = _extract_numeric_parts(raw)
    if not parts:
        return None, None, f"{field_name}: cannot parse numeric token ({raw})"

    int_part, frac = parts
    is_negative = int_part.startswith("-")
    unsigned = int_part[1:] if is_negative else int_part
    if len(unsigned) != context.int_len - 1:
        return None, None, f"{field_name}: token length does not match one-missing-digit pattern ({raw})"

    lead = context.prefix[0]
    corrected_int = f"{lead}{unsigned}"
    corrected = f"-{corrected_int}" if is_negative else corrected_int
    if frac:
        corrected = f"{corrected}.{frac}"

    try:
        corrected_value = float(corrected)
    except ValueError:
        return None, None, f"{field_name}: failed to build corrected value from {raw}"

    if not _proximity_ok(corrected_value, context):
        return None, None, f"{field_name}: corrected value still far from column median ({raw} -> {corrected_value})"

    note = f"{field_name}: {raw} -> {corrected_value} using column prefix {context.prefix}"
    return corrected_value, note, None


def _repair_pair_by_decimal_scale(
    raw1: str,
    raw2: str,
    value1: float,
    value2: float,
) -> Tuple[float, float, List[str]]:
    if _is_plausible_coordinate_pair(value1, value2):
        return value1, value2, []

    raw_values = [raw1.strip(), raw2.strip()]
    base_values = [value1, value2]
    scale_candidates: List[List[float]] = []

    for raw, value in zip(raw_values, base_values):
        if "." in raw or "," in raw:
            scale_candidates.append([value])
            continue

        candidates = [value]
        for divisor in (10.0, 100.0, 1000.0):
            scaled = value / divisor
            if scaled not in candidates:
                candidates.append(scaled)
        scale_candidates.append(candidates)

    best_pair: Optional[Tuple[float, float]] = None
    best_penalty = float("inf")
    for candidate1 in scale_candidates[0]:
        for candidate2 in scale_candidates[1]:
            if not _is_plausible_coordinate_pair(candidate1, candidate2):
                continue
            penalty = abs(candidate1 - value1) + abs(candidate2 - value2)
            if penalty < best_penalty:
                best_penalty = penalty
                best_pair = (candidate1, candidate2)

    if best_pair is None:
        return value1, value2, []

    notes: List[str] = []
    if best_pair[0] != value1:
        notes.append(f"value1: inferred decimal scale from {raw1} -> {best_pair[0]}")
    if best_pair[1] != value2:
        notes.append(f"value2: inferred decimal scale from {raw2} -> {best_pair[1]}")
    return best_pair[0], best_pair[1], notes


def _fraction_digit_count(raw: str) -> int:
    parts = _extract_numeric_parts(raw)
    if not parts:
        return 0
    return len(parts[1])


def _apply_coordinate_pattern_validation(candidates: List[OCRCandidate]) -> Tuple[List[OCRCandidate], List[str]]:
    if len(candidates) < 2:
        return candidates, []

    warnings: List[str] = []
    ctx1 = _build_column_context([item.value1 for item in candidates])
    ctx2 = _build_column_context([item.value2 for item in candidates])
    col1_int_lens = [len(str(int(abs(item.value1)))) for item in candidates]
    col2_int_lens = [len(str(int(abs(item.value2)))) for item in candidates]
    col1_frac_lens = [_fraction_digit_count(item.raw_value1) for item in candidates if _fraction_digit_count(item.raw_value1) > 0]
    col2_frac_lens = [_fraction_digit_count(item.raw_value2) for item in candidates if _fraction_digit_count(item.raw_value2) > 0]

    dominant_int1 = Counter(col1_int_lens).most_common(1)[0][0] if col1_int_lens else 0
    dominant_int2 = Counter(col2_int_lens).most_common(1)[0][0] if col2_int_lens else 0
    dominant_frac1 = Counter(col1_frac_lens).most_common(1)[0][0] if col1_frac_lens else 0
    dominant_frac2 = Counter(col2_frac_lens).most_common(1)[0][0] if col2_frac_lens else 0

    filtered: List[OCRCandidate] = []
    for item in candidates:
        int_len1 = len(str(int(abs(item.value1))))
        int_len2 = len(str(int(abs(item.value2))))
        frac_len1 = _fraction_digit_count(item.raw_value1)
        frac_len2 = _fraction_digit_count(item.raw_value2)

        int_ok = abs(int_len1 - dominant_int1) <= 1 and abs(int_len2 - dominant_int2) <= 1
        frac_ok = True
        proximity_ok = (
            (ctx1 is None or _strict_pattern_proximity_ok(item.value1, ctx1))
            and (ctx2 is None or _strict_pattern_proximity_ok(item.value2, ctx2))
        )
        if dominant_frac1:
            frac_ok = frac_ok and (frac_len1 == 0 or abs(frac_len1 - dominant_frac1) <= 1)
        if dominant_frac2:
            frac_ok = frac_ok and (frac_len2 == 0 or abs(frac_len2 - dominant_frac2) <= 1)

        if int_ok and frac_ok and proximity_ok:
            filtered.append(item)
            continue

        warnings.append(
            f"Skipped row {item.point_label} due to inconsistent coordinate pattern ({item.raw_value1} | {item.raw_value2})."
        )

    return (filtered if filtered else candidates), warnings


def _segment_text_rows(binary_image) -> List[Tuple[int, int]]:
    import cv2  # type: ignore
    import numpy as np

    if binary_image.ndim != 2:
        return []

    inverted = cv2.bitwise_not(binary_image)
    width = binary_image.shape[1]
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(12, width // 18), 1))
    horizontal_lines = cv2.morphologyEx(inverted, cv2.MORPH_OPEN, horizontal_kernel, iterations=1)
    text_only = cv2.subtract(inverted, horizontal_lines)
    row_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (max(8, width // 36), 5))
    row_mask = cv2.dilate(text_only, row_kernel, iterations=1)

    contours, _ = cv2.findContours(row_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes: List[Tuple[int, int]] = []
    min_width = max(30, int(width * 0.18))
    min_height = max(12, binary_image.shape[0] // 30)
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        if w < min_width or h < min_height:
            continue
        boxes.append((y, y + h))

    if not boxes:
        return []

    boxes.sort()
    merged: List[Tuple[int, int]] = []
    for top, bottom in boxes:
        if not merged or top > merged[-1][1] + 8:
            merged.append((top, bottom))
            continue
        merged[-1] = (merged[-1][0], max(merged[-1][1], bottom))

    output: List[Tuple[int, int]] = []
    height = binary_image.shape[0]
    for top, bottom in merged:
        pad = 6
        output.append((max(0, top - pad), min(height, bottom + pad)))
    return output


def _detect_main_vertical_split(binary_image) -> Optional[int]:
    import cv2  # type: ignore
    import numpy as np

    if binary_image.ndim != 2:
        return None

    inverted = cv2.bitwise_not(binary_image)
    height, width = binary_image.shape
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(18, height // 6)))
    vertical_lines = cv2.morphologyEx(inverted, cv2.MORPH_OPEN, vertical_kernel, iterations=1)
    projection = vertical_lines.sum(axis=0)
    if projection.size == 0:
        return None

    center_start = int(width * 0.3)
    center_end = int(width * 0.7)
    if center_end <= center_start:
        return None
    center_projection = projection[center_start:center_end]
    if center_projection.size == 0 or center_projection.max() <= 0:
        return None

    return int(center_start + center_projection.argmax())


def _score_numeric_token(raw: str) -> int:
    cleaned = raw.strip()
    if not cleaned:
        return -100

    score = 0
    if re.fullmatch(r"\d+[.,]\d{2}", cleaned):
        score += 12
    elif re.fullmatch(r"\d+[.,]\d{1,3}", cleaned):
        score += 8
    elif re.fullmatch(r"\d{6,8}", cleaned):
        score += 3
    elif re.fullmatch(r"\d{5,10}", cleaned):
        score += 1
    else:
        score -= 4

    parsed = _parse_float_strict(cleaned)
    if parsed is None:
        score -= 10
    elif parsed > 0:
        score += 2
    return score


def _ocr_numeric_cell(
    gray_cell,
    pytesseract_module,
    lang: str,
    timeout_seconds: int,
) -> str:
    import cv2  # type: ignore
    from PIL import Image

    cell = cv2.copyMakeBorder(gray_cell, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=255)
    upscaled = cv2.resize(cell, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
    variants = []
    variants.append(("gray", Image.fromarray(upscaled)))

    blur = cv2.GaussianBlur(upscaled, (3, 3), 0)
    _, otsu = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    variants.append(("otsu", Image.fromarray(otsu)))

    adaptive = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        7,
    )
    variants.append(("adaptive", Image.fromarray(adaptive)))

    sharpen = cv2.addWeighted(upscaled, 1.4, blur, -0.4, 0)
    variants.append(("sharpen", Image.fromarray(sharpen)))

    configs = [
        '--oem 3 --psm 7 -c preserve_interword_spaces=1 -c tessedit_char_whitelist="0123456789.,"',
        '--oem 3 --psm 13 -c preserve_interword_spaces=1 -c tessedit_char_whitelist="0123456789.,"',
    ]

    best_text = ""
    best_score = -10_000
    for _variant_name, variant in variants:
        for config in configs:
            try:
                text = pytesseract_module.image_to_string(
                    variant,
                    lang=lang,
                    config=config,
                    timeout=timeout_seconds,
                ) or ""
            except Exception:
                continue
            cleaned = re.sub(r"[^0-9.,]", "", " ".join(text.split()))
            score = _score_numeric_token(cleaned)
            if score > best_score:
                best_score = score
                best_text = cleaned

    return best_text


def _ocr_segmented_cells(
    image_variant,
    binary_variant,
    pytesseract_module,
    lang: str,
    timeout_seconds: int,
) -> Tuple[str, List[str]]:
    import cv2  # type: ignore
    import numpy as np

    gray = np.array(image_variant.convert("L"))
    binary = np.array(binary_variant.convert("L"))
    rows = _segment_text_rows(binary)
    if not rows:
        return "", ["No row segments detected for cell OCR."]

    split_x = _detect_main_vertical_split(binary)
    if split_x is None:
        return "", ["No vertical split detected for X/Y columns."]

    width = gray.shape[1]
    left_margin = max(0, int(width * 0.04))
    right_margin = min(width, int(width * 0.96))
    cell_texts: List[str] = []
    warnings: List[str] = []

    for idx, (top, bottom) in enumerate(rows, start=1):
        row_gray = gray[top:bottom, :]
        if row_gray.size == 0:
            continue

        left_end = max(left_margin + 20, split_x - 10)
        right_start = min(right_margin - 20, split_x + 10)
        if right_start <= left_end:
            continue

        left_cell = row_gray[:, left_margin:left_end]
        right_cell = row_gray[:, right_start:right_margin]
        left_text = _ocr_numeric_cell(left_cell, pytesseract_module, lang, timeout_seconds)
        right_text = _ocr_numeric_cell(right_cell, pytesseract_module, lang, timeout_seconds)
        if not left_text and not right_text:
            warnings.append(f"Cell OCR produced empty row {idx}.")
            continue
        if not left_text or not right_text:
            warnings.append(
                f"Cell OCR detected row {idx} but could not read both X/Y cells completely (left='{left_text or '-'}', right='{right_text or '-'}')."
            )
        cell_texts.append(f"{idx} {left_text} {right_text}".strip())

    if rows and len(cell_texts) < len(rows):
        warnings.append(f"Detected {len(rows)} row segments but parsed only {len(cell_texts)} rows from cell OCR.")

    return "\n".join(cell_texts), warnings


def _ocr_segmented_rows(
    image_variant,
    binary_variant,
    pytesseract_module,
    lang: str,
    timeout_seconds: int,
    whitelist: str,
) -> Tuple[str, List[str]]:
    import cv2  # type: ignore
    import numpy as np
    from PIL import Image

    gray = np.array(image_variant.convert("L"))
    binary = np.array(binary_variant.convert("L"))
    rows = _segment_text_rows(binary)
    if not rows:
        return "", ["No row segments detected from cropped image."]

    row_texts: List[str] = []
    warnings: List[str] = []
    for idx, (top, bottom) in enumerate(rows, start=1):
        row_gray = gray[top:bottom, :]
        if row_gray.size == 0:
            continue
        row_upscaled = cv2.resize(row_gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        row_binary = cv2.adaptiveThreshold(
            row_upscaled,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            31,
            5,
        )
        row_image = Image.fromarray(row_binary)
        row_config = f'--oem 3 --psm 7 -c preserve_interword_spaces=1 -c tessedit_char_whitelist="{whitelist}"'
        try:
            row_text = pytesseract_module.image_to_string(
                row_image,
                lang=lang,
                config=row_config,
                timeout=timeout_seconds,
            ) or ""
        except Exception as exc:
            warnings.append(f"Row OCR failed for row {idx}: {exc.__class__.__name__}")
            continue

        cleaned = " ".join(row_text.split())
        if cleaned:
            row_texts.append(f"{idx} {cleaned}")
        else:
            warnings.append(f"Row OCR detected row {idx} but returned empty text.")

    if rows and len(row_texts) < len(rows):
        warnings.append(f"Detected {len(rows)} row segments but parsed only {len(row_texts)} rows from row OCR.")

    return "\n".join(row_texts), warnings


def extract_coordinate_candidates_with_warnings(raw_text: str) -> Tuple[List[OCRCandidate], List[str]]:
    text = raw_text or ""
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    warnings: List[str] = []

    def token_int_len(token: str) -> int:
        parts = _extract_numeric_parts(token)
        if not parts:
            return 0
        int_part = parts[0]
        int_unsigned = int_part[1:] if int_part.startswith("-") else int_part
        return len(int_unsigned)

    def coord_tokens_from_segment(segment: str) -> List[str]:
        raw_tokens = re.findall(r"[^\s]+", segment)
        out: List[str] = []
        for tk in raw_tokens:
            if not re.search(r"\d", tk):
                continue
            if token_int_len(tk) < 5:
                continue
            out.append(tk)
        return out

    raw_rows: List[Tuple[str, str, str]] = []
    for line in lines:
        if "|" in line:
            raw_parts = [p.strip() for p in line.split("|")]
            if len(raw_parts) < 2:
                if re.search(r"\d", line):
                    warnings.append(f"Skipped OCR line with digits but insufficient pipe-separated segments: {line}")
                continue
            left_tokens = coord_tokens_from_segment(raw_parts[0])
            right_tokens = coord_tokens_from_segment(raw_parts[1])
            left = left_tokens[0] if left_tokens else None
            right = right_tokens[0] if right_tokens else None
            if not left or not right:
                warnings.append(f"Skipped OCR row because one side of the pair could not be read: {line}")
                continue
            label = str(len(raw_rows) + 1)
            raw_rows.append((label, left, right))
            continue

        coord_tokens = coord_tokens_from_segment(line)
        if len(coord_tokens) < 2:
            if re.search(r"\d", line):
                warnings.append(f"Skipped OCR line with digits but not enough coordinate tokens: {line}")
            continue
        label_match = re.match(r"^\s*(\w+)\s+", line)
        label = (label_match.group(1) if label_match else str(len(raw_rows) + 1)).strip()
        raw_rows.append((label, coord_tokens[0], coord_tokens[1]))

    if raw_rows:
        col1_valid = [v for _, raw1, _ in raw_rows if (v := _parse_float_strict(raw1)) is not None]
        col2_valid = [v for _, _, raw2 in raw_rows if (v := _parse_float_strict(raw2)) is not None]
        ctx1 = _build_column_context(col1_valid)
        ctx2 = _build_column_context(col2_valid)

        candidates: List[OCRCandidate] = []
        for label, raw1, raw2 in raw_rows:
            v1, corr1, warn1 = _correct_by_column_context(raw1, ctx1, "value1")
            v2, corr2, warn2 = _correct_by_column_context(raw2, ctx2, "value2")

            if warn1:
                warnings.append(warn1)
            if warn2:
                warnings.append(warn2)
            if v1 is None or v2 is None:
                warnings.append(
                    f"Skipped OCR row {label} because parsed tokens could not be normalized into a coordinate pair ({raw1} | {raw2})."
                )
                continue

            v1, v2, scale_notes = _repair_pair_by_decimal_scale(raw1, raw2, v1, v2)
            plausible = _is_plausible_coordinate_pair(v1, v2)
            if not plausible:
                warnings.append(
                    f"Skipped suspicious row {label}: {v1} | {v2} (possible missing leading digit or OCR noise)."
                )
                continue

            corrections: List[str] = []
            if corr1:
                corrections.append(corr1)
            if corr2:
                corrections.append(corr2)
            corrections.extend(scale_notes)
            confidence_note = "detected from same OCR row"
            if corrections:
                confidence_note += "; corrected by column context"

            candidates.append(
                OCRCandidate(
                    point_label=label,
                    raw_value1=raw1,
                    raw_value2=raw2,
                    value1=v1,
                    value2=v2,
                    corrections=corrections,
                    confidence_note=confidence_note,
                )
            )

        if candidates:
            filtered_candidates, pattern_warnings = _apply_coordinate_pattern_validation(candidates)
            warnings.extend(pattern_warnings)
            return filtered_candidates[:50], warnings

    if raw_rows:
        warnings.append("OCR detected row-like content but no valid coordinate pairs were parsed from it.")
        return [], warnings

    token_pattern = re.compile(r"(?<!\d)(\d{5,10}(?:[.,]\d+)?)(?!\d)")
    tokens = token_pattern.findall(text)
    values: List[float] = []
    for token in tokens:
        parsed = _parse_float_strict(token)
        if parsed is not None:
            values.append(parsed)

    fallback: List[OCRCandidate] = []
    for i in range(len(values) - 1):
        v1, v2 = values[i], values[i + 1]
        fallback.append(
            OCRCandidate(
                point_label=str(i + 1),
                raw_value1=str(v1),
                raw_value2=str(v2),
                value1=v1,
                value2=v2,
                corrections=[],
                confidence_note="detected from nearby OCR numbers (low confidence)",
            )
        )
        if len(fallback) >= 20:
            break
    if fallback:
        warnings.append("Using low-confidence fallback pairing from nearby numbers.")
    return fallback, warnings


def extract_coordinate_candidates_from_text(raw_text: str) -> List[OCRCandidate]:
    candidates, _ = extract_coordinate_candidates_with_warnings(raw_text)
    return candidates


def _resolve_tesseract_cmd() -> str:
    env_cmd = os.getenv("TESSERACT_CMD", "").strip()
    if env_cmd:
        return env_cmd
    common_paths = [
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path("/opt/homebrew/bin/tesseract"),
        Path("/usr/local/bin/tesseract"),
        Path("/usr/bin/tesseract"),
    ]
    for path in common_paths:
        if path.exists():
            return str(path)
    return "tesseract"


def get_ocr_status() -> OCRStatusInfo:
    try:
        import pytesseract
        from PIL import Image  # noqa: F401
        import cv2  # noqa: F401
        import numpy as np  # noqa: F401
    except Exception as exc:
        return OCRStatusInfo(False, False, "", "", f"Missing OCR dependency: {exc.__class__.__name__}")

    tesseract_cmd = _resolve_tesseract_cmd()
    pytesseract.pytesseract.tesseract_cmd = tesseract_cmd
    try:
        version = str(pytesseract.get_tesseract_version())
        logger.info("OCR status - tesseract_cmd=%s version=%s", tesseract_cmd, version)
        return OCRStatusInfo(True, True, version, tesseract_cmd, None)
    except Exception as exc:
        logger.exception("Failed to detect Tesseract command/version.")
        return OCRStatusInfo(True, False, "", tesseract_cmd, f"Tesseract unavailable: {exc.__class__.__name__}")


def _score_ocr_candidates(candidates: List[OCRCandidate]) -> int:
    if not candidates:
        return 0

    score = 0
    for item in candidates:
        confidence = (item.confidence_note or "").casefold()
        if "nearby ocr numbers" in confidence:
            score += 1
        elif "corrected by column context" in confidence:
            score += 8
        else:
            score += 10

        frac1 = _fraction_digit_count(item.raw_value1)
        frac2 = _fraction_digit_count(item.raw_value2)
        if frac1 == 2:
            score += 2
        if frac2 == 2:
            score += 2

    col1_int_lens = [len(str(int(abs(item.value1)))) for item in candidates]
    col2_int_lens = [len(str(int(abs(item.value2)))) for item in candidates]
    if len(set(col1_int_lens)) == 1:
        score += 4
    if len(set(col2_int_lens)) == 1:
        score += 4

    if len(candidates) >= 3:
        score += 3
    return score


def run_ocr_with_diagnostics(image_bytes: bytes, mode: str = "fast", is_cropped: bool = False) -> OCRRunResult:
    status = get_ocr_status()
    if not status.python_packages_ok:
        raise OCRError(
            stage="dependency_check",
            error_code="OCR_DEPENDENCY_MISSING",
            message="OCR dependencies are not installed.",
            detail=status.error or "Missing python OCR packages.",
            suggestion="Install pytesseract, Pillow, OpenCV, numpy and restart backend.",
            status_code=503,
        )
    if not status.tesseract_available:
        raise OCRError(
            stage="dependency_check",
            error_code="TESSERACT_UNAVAILABLE",
            message="Tesseract OCR binary is not available.",
            detail=status.error or "Cannot run tesseract command.",
            suggestion="Chua cau hinh duoc Tesseract OCR. Kiem tra TESSERACT_CMD/PATH.",
            status_code=503,
        )

    try:
        from PIL import Image, ImageFilter
        import cv2  # type: ignore
        import numpy as np
        import pytesseract
    except Exception as exc:
        logger.exception("Unexpected dependency import failure during OCR.")
        raise OCRError(
            stage="dependency_check",
            error_code="OCR_IMPORT_FAILED",
            message="Cannot import OCR dependencies.",
            detail=f"{exc.__class__.__name__}: import failed",
            suggestion="Reinstall OCR dependencies and restart backend.",
            status_code=503,
        ) from exc

    normalized_mode = mode if mode in {"fast", "enhanced"} else "fast"
    started = time.perf_counter()

    try:
        probe = Image.open(BytesIO(image_bytes))
        probe.verify()
    except Exception as exc:
        logger.exception("Image verify failed in OCR pipeline.")
        raise OCRError(
            stage="image_open",
            error_code="IMAGE_INVALID",
            message="Cannot read uploaded image.",
            detail="Unsupported/corrupt image or invalid file bytes.",
            suggestion="Khong doc duoc file anh. Hay dung JPG/PNG ro net va thu lai.",
            status_code=400,
        ) from exc

    try:
        img = Image.open(BytesIO(image_bytes)).convert("RGB")
    except Exception as exc:
        logger.exception("Image reopen/convert failed after verify.")
        raise OCRError(
            stage="image_open",
            error_code="IMAGE_REOPEN_FAILED",
            message="Cannot reopen image for OCR.",
            detail="Image verify passed but reopen/convert failed.",
            suggestion="Khong doc duoc file anh. Hay dung JPG/PNG ro net va thu lai.",
            status_code=400,
        ) from exc

    try:
        max_side = 1800 if normalized_mode == "fast" else 2600
        width, height = img.size
        longest = max(width, height)
        if longest > max_side:
            scale = max_side / float(longest)
            img = img.resize((max(1, int(width * scale)), max(1, int(height * scale))), Image.Resampling.LANCZOS)

        arr = np.array(img)
        gray = cv2.cvtColor(arr, cv2.COLOR_RGB2GRAY)

        gray_2x = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        denoise_2x = cv2.fastNlMeansDenoising(gray_2x, None, 8, 7, 21)
        contrast_2x = cv2.convertScaleAbs(denoise_2x, alpha=1.20, beta=8)
        _, otsu_2x = cv2.threshold(contrast_2x, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

        preprocess_variants = [
            ("fast_gray_2x_otsu", Image.fromarray(otsu_2x), Image.fromarray(otsu_2x)),
            ("fast_original_rgb", img, Image.fromarray(otsu_2x)),
        ]

        if is_cropped:
            crop_contrast = cv2.convertScaleAbs(denoise_2x, alpha=1.28, beta=10)
            crop_adaptive = cv2.adaptiveThreshold(
                crop_contrast,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                29,
                5,
            )
            preprocess_variants.extend(
                [
                    ("crop_gray_2x_contrast", Image.fromarray(crop_contrast), Image.fromarray(crop_adaptive)),
                    ("crop_gray_2x_adaptive", Image.fromarray(crop_adaptive), Image.fromarray(crop_adaptive)),
                ]
            )

        if normalized_mode == "enhanced" and not is_cropped:
            gray_3x = cv2.resize(gray, None, fx=3, fy=3, interpolation=cv2.INTER_CUBIC)
            denoise_3x = cv2.fastNlMeansDenoising(gray_3x, None, 10, 7, 21)
            contrast_3x = cv2.convertScaleAbs(denoise_3x, alpha=1.30, beta=12)
            adaptive_3x = cv2.adaptiveThreshold(
                contrast_3x,
                255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                31,
                7,
            )
            sharpen_kernel = np.array([[0, -1, 0], [-1, 5, -1], [0, -1, 0]])
            sharp_3x = cv2.filter2D(adaptive_3x, -1, sharpen_kernel)
            preprocess_variants.extend(
                [
                    (
                        "enhanced_gray_3x_adaptive_sharpen",
                        Image.fromarray(sharp_3x).filter(ImageFilter.SHARPEN),
                        Image.fromarray(adaptive_3x),
                    ),
                    ("enhanced_gray_3x_contrast", Image.fromarray(contrast_3x), Image.fromarray(adaptive_3x)),
                ]
            )
    except Exception as exc:
        logger.exception("Image preprocessing failed for OCR.")
        raise OCRError(
            stage="image_preprocess",
            error_code="IMAGE_PREPROCESS_FAILED",
            message="Image preprocessing failed.",
            detail=f"{exc.__class__.__name__}: preprocessing failed",
            suggestion="Try a clearer crop around coordinate table and upload again.",
            status_code=422,
        ) from exc

    ocr_warnings: List[str] = []
    preferred_lang = "eng+vie"
    lang_to_use = "eng"
    try:
        available_langs = set(pytesseract.get_languages(config=""))
        if {"eng", "vie"}.issubset(available_langs):
            lang_to_use = preferred_lang
        else:
            ocr_warnings.append("Không tìm thấy đủ dữ liệu ngôn ngữ eng+vie, hệ thống dùng eng.")
    except Exception:
        ocr_warnings.append("Không kiểm tra được danh sách ngôn ngữ Tesseract, hệ thống dùng eng.")

    whitelist = "0123456789.,|/-:;()[]{} XYxyABCDDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyzÀÁÂÃÈÉÊÌÍÒÓÔÕÙÚĂĐĨŨƠƯàáâãèéêìíòóôõùúăđĩũơưẠ-ỹ"
    ocr_configs = [("table_block", f'--oem 3 --psm 6 -c preserve_interword_spaces=1 -c tessedit_char_whitelist="{whitelist}"')]
    timeout_seconds = 8
    max_attempts = 2
    if normalized_mode == "enhanced" and not is_cropped:
        ocr_configs.append(("line_mode", f'--oem 3 --psm 7 -c preserve_interword_spaces=1 -c tessedit_char_whitelist="{whitelist}"'))
        timeout_seconds = 15
        max_attempts = 6
    if is_cropped:
        ocr_configs.extend(
            [
                ("single_column", f'--oem 3 --psm 4 -c preserve_interword_spaces=1 -c tessedit_char_whitelist="{whitelist}"'),
                ("sparse_text", f'--oem 3 --psm 11 -c preserve_interword_spaces=1 -c tessedit_char_whitelist="{whitelist}"'),
            ]
        )
        timeout_seconds = 10 if normalized_mode == "fast" else 12
        max_attempts = min(8, len(preprocess_variants) * len(ocr_configs) + len(preprocess_variants))
        ocr_warnings.append("Ảnh đã được khoanh vùng trước khi OCR; hệ thống dùng tiền xử lý nhẹ.")

    best_text = ""
    best_method = ""
    best_cfg = ""
    best_score = -1
    run_error: Optional[Exception] = None
    attempts = 0

    for method_name, image_variant, binary_variant in preprocess_variants:
        if is_cropped and attempts < max_attempts:
            cell_text, cell_warnings = _ocr_segmented_cells(
                image_variant=image_variant,
                binary_variant=binary_variant,
                pytesseract_module=pytesseract,
                lang=lang_to_use,
                timeout_seconds=timeout_seconds,
            )
            attempts += 1
            ocr_warnings.extend(cell_warnings)
            cell_candidates, _ = extract_coordinate_candidates_with_warnings(cell_text)
            cell_score = _score_ocr_candidates(cell_candidates)
            if len(cell_candidates) >= 2:
                cell_score += 10
            if cell_score > best_score:
                best_score = cell_score
                best_text = cell_text
                best_method = f"{method_name}_segmented_cells"
                best_cfg = "cell_mode_psm7_psm13"

        if is_cropped and attempts < max_attempts:
            segmented_text, segmented_warnings = _ocr_segmented_rows(
                image_variant=image_variant,
                binary_variant=binary_variant,
                pytesseract_module=pytesseract,
                lang=lang_to_use,
                timeout_seconds=timeout_seconds,
                whitelist=whitelist,
            )
            attempts += 1
            ocr_warnings.extend(segmented_warnings)
            segmented_candidates, _ = extract_coordinate_candidates_with_warnings(segmented_text)
            segmented_score = _score_ocr_candidates(segmented_candidates)
            if segmented_score > best_score:
                best_score = segmented_score
                best_text = segmented_text
                best_method = f"{method_name}_segmented_rows"
                best_cfg = "row_mode_psm7"

        for cfg_name, cfg_value in ocr_configs:
            if attempts >= max_attempts:
                break
            attempts += 1
            try:
                text = pytesseract.image_to_string(
                    image_variant,
                    lang=lang_to_use,
                    config=cfg_value,
                    timeout=timeout_seconds,
                ) or ""
            except Exception as exc:
                if lang_to_use == preferred_lang:
                    try:
                        text = pytesseract.image_to_string(
                            image_variant,
                            lang="eng",
                            config=cfg_value,
                            timeout=timeout_seconds,
                        ) or ""
                        ocr_warnings.append("eng+vie không khả dụng ở lần chạy OCR này, hệ thống đã fallback sang eng.")
                        lang_to_use = "eng"
                    except Exception as exc2:
                        run_error = exc2
                        continue
                else:
                    run_error = exc
                    continue

            candidates, _ = extract_coordinate_candidates_with_warnings(text)
            score = _score_ocr_candidates(candidates)
            if score > best_score:
                best_score = score
                best_text = text
                best_method = method_name
                best_cfg = cfg_name
        if attempts >= max_attempts:
            break

    if best_score < 0:
        logger.exception("Tesseract OCR execution failed.", exc_info=run_error)
        is_timeout = isinstance(run_error, RuntimeError)
        raise OCRError(
            stage="tesseract_run",
            error_code="TESSERACT_RUN_TIMEOUT" if is_timeout else "TESSERACT_RUN_FAILED",
            message="Tesseract OCR timeout." if is_timeout else "Tesseract OCR run failed.",
            detail=f"{(run_error.__class__.__name__ if run_error else 'UnknownError')}: tesseract execution error",
            suggestion="OCR mất quá nhiều thời gian hoặc lỗi khi xử lý ảnh. Hãy crop ảnh nhỏ hơn và thử lại.",
            status_code=504 if is_timeout else 503,
        ) from run_error

    elapsed_seconds = round(time.perf_counter() - started, 3)
    return OCRRunResult(
        ocr_mode=normalized_mode,
        raw_text=best_text,
        preprocessing_method=best_method,
        ocr_config=best_cfg,
        language=lang_to_use,
        elapsed_seconds=elapsed_seconds,
        warnings=list(ocr_warnings),
    )
