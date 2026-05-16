from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from typing import Optional

from openlocationcode import openlocationcode as olc


@dataclass(frozen=True)
class PlusCodeParseResult:
    latitude: float
    longitude: float
    source: str


LOCALITY_REFERENCES = {
    "thới an, hồ chí minh": (10.8831125, 106.6760156),
    "thoi an, ho chi minh": (10.8831125, 106.6760156),
    "thoi an quan 12": (10.8831125, 106.6760156),
}


_PLUS_CODE_TOKEN = re.compile(r"\b[23456789CFGHJMPQRVWX]{2,8}\+[23456789CFGHJMPQRVWX]{2,}\b", re.IGNORECASE)


def _normalize_text(value: str) -> str:
    text = (value or "").strip().lower()
    text = "".join(ch for ch in unicodedata.normalize("NFD", text) if unicodedata.category(ch) != "Mn")
    return re.sub(r"\s+", " ", text).strip()


def _extract_plus_code_token(text: str) -> Optional[str]:
    match = _PLUS_CODE_TOKEN.search(text or "")
    if not match:
        return None
    return match.group(0).upper()


def parse_plus_code(text: str) -> Optional[PlusCodeParseResult]:
    raw = (text or "").strip()
    if not raw:
        return None

    token = _extract_plus_code_token(raw)
    if not token:
        if "+" in raw:
            raise ValueError("Plus Code không hợp lệ. Vui lòng kiểm tra lại nội dung đã dán.")
        return None

    if not olc.isValid(token):
        raise ValueError("Plus Code không hợp lệ. Vui lòng kiểm tra lại nội dung đã dán.")

    if olc.isFull(token):
        area = olc.decode(token)
        return PlusCodeParseResult(latitude=area.latitudeCenter, longitude=area.longitudeCenter, source="plus_code")

    locality_text = raw.replace(token, " ").strip(" ,")
    if not locality_text:
        raise ValueError("Plus Code rút gọn cần thêm khu vực tham chiếu. Vui lòng dán link Google Maps đầy đủ hoặc nhập tọa độ Lat/Long.")

    normalized = _normalize_text(locality_text).replace("viet nam", "").replace("việt nam", "").strip(" ,")
    ref = LOCALITY_REFERENCES.get(normalized)
    if ref is None:
        for key, value in LOCALITY_REFERENCES.items():
            if key in normalized or normalized in key:
                ref = value
                break
    if ref is None and "thoi an" in normalized and "ho chi minh" in normalized:
        ref = LOCALITY_REFERENCES["thoi an, ho chi minh"]
    if ref is None:
        raise ValueError("Plus Code rút gọn cần thêm khu vực tham chiếu. Vui lòng dán link Google Maps đầy đủ hoặc nhập tọa độ Lat/Long.")

    recovered = olc.recoverNearest(token, ref[0], ref[1])
    area = olc.decode(recovered)
    return PlusCodeParseResult(latitude=area.latitudeCenter, longitude=area.longitudeCenter, source="plus_code")
