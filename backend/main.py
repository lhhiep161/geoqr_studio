from __future__ import annotations

import logging
from pathlib import Path
from typing import List, Literal, Optional

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from backend.core.coordinate_converter import CoordinateConverter, InputMode
from backend.core.distance_calculator import haversine_distance_meters
from backend.core.google_maps_resolver import resolve_google_maps_short_link, validate_google_maps_url
from backend.core.google_maps_url import build_google_maps_url
from backend.core.maps_parser import (
    SOURCE_VIEWPORT_FALLBACK,
    is_google_maps_short_link,
    parse_lat_lng_from_google_maps_url_with_source,
    parse_lat_lng_with_source,
)
from backend.core.plus_code_parser import parse_plus_code
from backend.core.vn2000_config import VN2000ConfigError, VN2000ConfigLoader
from backend.services.ocr_service import (
    OCRError,
    extract_coordinate_candidates_with_warnings,
    get_ocr_status,
    run_ocr_with_diagnostics,
)
from backend.services.qr_service import build_qr_png_base64


ROOT_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT_DIR / "config" / "vn2000_local_crs.csv"
FRONTEND_DIR = ROOT_DIR / "frontend"
ASSETS_DIR = ROOT_DIR / "assets"

app = FastAPI(
    title="GeoQR Studio API",
    version="0.1.0",
    description="Công cụ chuyển đổi tọa độ, OCR tọa độ, định vị bản đồ và tạo QR vị trí.",
)
config_loader = VN2000ConfigLoader(CONFIG_PATH)
logger = logging.getLogger(__name__)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConvertRequest(BaseModel):
    province: str = Field(min_length=1)
    value1: float
    value2: float
    input_mode: Literal["auto", "easting_northing", "northing_easting"] = "auto"
    current_lat: Optional[float] = None
    current_lng: Optional[float] = None


class ConvertResponse(BaseModel):
    province: str
    latitude: float
    longitude: float
    google_maps_url: str
    qr_png_base64: str
    distance_meters: Optional[float]
    used_order: str
    warnings: List[str]


class ProvincesResponse(BaseModel):
    provinces: List[str]


class OCRCandidateResponse(BaseModel):
    point_label: str
    raw_value1: str
    raw_value2: str
    value1: float
    value2: float
    corrections: List[str]
    confidence_note: str


class OCRCoordinatesResponse(BaseModel):
    ok: bool = True
    ocr_mode: str
    raw_text: str
    preprocessing_method: str
    ocr_config: str
    ocr_language: str
    elapsed_seconds: float
    candidate_count: int
    candidates: List[OCRCandidateResponse]
    warnings: List[str]


class OCRErrorResponse(BaseModel):
    ok: bool = False
    stage: str
    error_code: str
    message: str
    detail: str
    suggestion: str


class OCRStatusResponse(BaseModel):
    python_packages_ok: bool
    tesseract_available: bool
    tesseract_version: str
    tesseract_cmd: str
    error: Optional[str]


class GoogleMapsQRRequest(BaseModel):
    input_text: str = Field(min_length=1)


class GoogleMapsQRSuccessResponse(BaseModel):
    ok: bool = True
    latitude: float
    longitude: float
    coordinate_source: str
    google_maps_url: str
    source_url: Optional[str]
    resolved_url: Optional[str]
    qr_png_base64: str
    warnings: List[str]


class GoogleMapsQRErrorResponse(BaseModel):
    ok: bool = False
    message: str
    suggestion: str


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/health")
def api_health() -> dict:
    return {"status": "ok"}


@app.get("/api/provinces", response_model=ProvincesResponse)
def list_provinces() -> ProvincesResponse:
    return ProvincesResponse(provinces=config_loader.list_province_names())


@app.get("/api/ocr-status", response_model=OCRStatusResponse)
def ocr_status() -> OCRStatusResponse:
    status = get_ocr_status()
    return OCRStatusResponse(
        python_packages_ok=status.python_packages_ok,
        tesseract_available=status.tesseract_available,
        tesseract_version=status.tesseract_version,
        tesseract_cmd=status.tesseract_cmd,
        error=status.error,
    )


@app.post("/api/ocr-coordinates", response_model=OCRCoordinatesResponse | OCRErrorResponse)
async def ocr_coordinates(mode: str = "fast", image: UploadFile = File(...)):
    normalized_mode = mode.strip().lower() if mode else "fast"
    mode_warning: Optional[str] = None
    if normalized_mode not in {"fast", "enhanced"}:
        mode_warning = f"OCR mode '{mode}' không hợp lệ, hệ thống dùng mặc định 'fast'."
        normalized_mode = "fast"

    if image is None:
        err = OCRError(
            stage="upload_read",
            error_code="UPLOAD_MISSING",
            message="No image upload found.",
            detail="Form field 'image' is missing.",
            suggestion="Select an image file and retry.",
            status_code=400,
        )
        return JSONResponse(status_code=err.status_code, content=err.to_dict())

    if not (image.content_type or "").startswith("image/"):
        err = OCRError(
            stage="upload_read",
            error_code="UPLOAD_NOT_IMAGE",
            message="Uploaded file is not an image.",
            detail=f"content_type={image.content_type or 'unknown'}",
            suggestion="Upload JPG/PNG image file only.",
            status_code=400,
        )
        return JSONResponse(status_code=err.status_code, content=err.to_dict())

    try:
        content = await image.read()
    except Exception as exc:
        logger.exception("Failed reading uploaded OCR image.")
        err = OCRError(
            stage="upload_read",
            error_code="UPLOAD_READ_FAILED",
            message="Failed to read uploaded file.",
            detail=f"{exc.__class__.__name__}: cannot read uploaded bytes",
            suggestion="Retry upload with a smaller/clearer image.",
            status_code=400,
        )
        return JSONResponse(status_code=err.status_code, content=err.to_dict())

    if not content:
        err = OCRError(
            stage="upload_read",
            error_code="UPLOAD_EMPTY",
            message="Uploaded image is empty.",
            detail="File size is 0 bytes.",
            suggestion="Choose a valid JPG/PNG image and retry.",
            status_code=400,
        )
        return JSONResponse(status_code=err.status_code, content=err.to_dict())
    if len(content) > 5 * 1024 * 1024:
        err = OCRError(
            stage="upload_read",
            error_code="UPLOAD_TOO_LARGE",
            message="Ảnh vượt quá giới hạn dung lượng 5MB.",
            detail=f"file_size_bytes={len(content)}",
            suggestion="Vui lòng crop ảnh nhỏ hơn (<=5MB) rồi thử lại.",
            status_code=413,
        )
        return JSONResponse(status_code=err.status_code, content=err.to_dict())

    try:
        ocr_result = run_ocr_with_diagnostics(content, mode=normalized_mode)
    except OCRError as err:
        logger.error("OCR error stage=%s code=%s detail=%s", err.stage, err.error_code, err.detail)
        return JSONResponse(status_code=err.status_code, content=err.to_dict())

    try:
        candidates, parse_warnings = extract_coordinate_candidates_with_warnings(ocr_result.raw_text)
    except Exception as exc:
        logger.exception("Coordinate parse failed after OCR text extraction.")
        err = OCRError(
            stage="coordinate_parse",
            error_code="COORDINATE_PARSE_FAILED",
            message="Failed to parse coordinate candidates from OCR text.",
            detail=f"{exc.__class__.__name__}: parse failed",
            suggestion="Try crop image tighter around coordinate table and retry.",
            status_code=500,
        )
        return JSONResponse(status_code=err.status_code, content=err.to_dict())

    warnings: List[str] = []
    if mode_warning:
        warnings.append(mode_warning)
    warnings.extend(ocr_result.warnings)
    warnings.extend(parse_warnings)
    if not candidates:
        warnings.append("OCR doc duoc anh nhung chua tim thay cap toa do. Hay crop sat vung bang toa do va thu lai.")
    warnings.append("OCR is experimental. Please verify values before conversion.")

    return OCRCoordinatesResponse(
        ok=True,
        ocr_mode=ocr_result.ocr_mode,
        raw_text=ocr_result.raw_text,
        preprocessing_method=ocr_result.preprocessing_method,
        ocr_config=ocr_result.ocr_config,
        ocr_language=ocr_result.language,
        elapsed_seconds=ocr_result.elapsed_seconds,
        candidate_count=len(candidates),
        candidates=[
            OCRCandidateResponse(
                point_label=item.point_label,
                raw_value1=item.raw_value1,
                raw_value2=item.raw_value2,
                value1=item.value1,
                value2=item.value2,
                corrections=item.corrections,
                confidence_note=item.confidence_note,
            )
            for item in candidates
        ],
        warnings=warnings,
    )


@app.post("/api/convert", response_model=ConvertResponse)
def convert_coordinates(payload: ConvertRequest) -> ConvertResponse:
    try:
        local_crs = config_loader.get_by_province(payload.province)
    except VN2000ConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    conversion = CoordinateConverter.convert(
        value1=payload.value1,
        value2=payload.value2,
        local_crs=local_crs,
        input_mode=InputMode(payload.input_mode),
    )

    google_maps_url = build_google_maps_url(conversion.latitude, conversion.longitude)
    qr_png_base64 = build_qr_png_base64(google_maps_url)

    distance_meters: Optional[float] = None
    warnings = list(conversion.warnings)
    if payload.current_lat is not None or payload.current_lng is not None:
        if payload.current_lat is None or payload.current_lng is None:
            warnings.append("Both current_lat and current_lng are required to calculate distance.")
        else:
            distance_meters = haversine_distance_meters(
                payload.current_lat,
                payload.current_lng,
                conversion.latitude,
                conversion.longitude,
            )

    return ConvertResponse(
        province=local_crs.province_name,
        latitude=conversion.latitude,
        longitude=conversion.longitude,
        google_maps_url=google_maps_url,
        qr_png_base64=qr_png_base64,
        distance_meters=distance_meters,
        used_order=conversion.used_order,
        warnings=warnings,
    )


@app.post("/api/google-maps-qr", response_model=GoogleMapsQRSuccessResponse | GoogleMapsQRErrorResponse)
def create_google_maps_qr(payload: GoogleMapsQRRequest):
    value = payload.input_text.strip()
    source_url: Optional[str] = None
    resolved_url: Optional[str] = None
    warnings: List[str] = []

    try:
        parsed = None
        plus_code_result = parse_plus_code(value)
        if plus_code_result is not None:
            parsed = (plus_code_result.latitude, plus_code_result.longitude, plus_code_result.source)
        if parsed is None and value.startswith(("http://", "https://")):
            validate_google_maps_url(value)
            source_url = value
            short_link = is_google_maps_short_link(value)
            if short_link:
                resolved_url = resolve_google_maps_short_link(value, timeout_seconds=8.0)
            else:
                resolved_url = value
            validate_google_maps_url(resolved_url)
            parsed = parse_lat_lng_from_google_maps_url_with_source(resolved_url)
            if parsed is None and short_link:
                return JSONResponse(
                    status_code=400,
                    content=GoogleMapsQRErrorResponse(
                        ok=False,
                        message="Không tìm thấy tọa độ trong link Google Maps rút gọn. Vui lòng mở link trên Google Maps và sao chép tọa độ hoặc link đầy đủ.",
                        suggestion="Mở link rút gọn trên Google Maps, sau đó sao chép link đầy đủ hoặc Lat/Long.",
                    ).model_dump(),
                )
        elif parsed is None:
            parsed = parse_lat_lng_with_source(value)

        if parsed is None:
            return JSONResponse(
                status_code=400,
                content=GoogleMapsQRErrorResponse(
                    ok=False,
                    message="Không đọc được tọa độ từ nội dung đã dán. Vui lòng kiểm tra lại link hoặc nhập theo dạng: 10.7769,106.7009",
                    suggestion="Nếu là link rút gọn, hãy mở link trên Google Maps rồi sao chép link đầy đủ hoặc tọa độ Lat/Long.",
                ).model_dump(),
            )

        latitude, longitude, coordinate_source = parsed
        if not (-90.0 <= latitude <= 90.0 and -180.0 <= longitude <= 180.0):
            return JSONResponse(
                status_code=400,
                content=GoogleMapsQRErrorResponse(
                    ok=False,
                    message="Tọa độ vượt ngoài phạm vi hợp lệ.",
                    suggestion="Vui lòng kiểm tra lại định dạng Lat/Long.",
                ).model_dump(),
            )

        if not (8.0 <= latitude <= 24.0 and 102.0 <= longitude <= 110.0):
            warnings.append("Tọa độ không nằm trong phạm vi Việt Nam, vui lòng kiểm tra lại.")
        if coordinate_source == SOURCE_VIEWPORT_FALLBACK:
            warnings.append("Link Google Maps chỉ có tọa độ tâm màn hình, có thể không phải vị trí chính xác của địa điểm.")

        maps_url = build_google_maps_url(latitude, longitude)
        qr_png_base64 = build_qr_png_base64(maps_url)
        return GoogleMapsQRSuccessResponse(
            ok=True,
            latitude=latitude,
            longitude=longitude,
            coordinate_source=coordinate_source,
            google_maps_url=maps_url,
            source_url=source_url,
            resolved_url=resolved_url,
            qr_png_base64=qr_png_base64,
            warnings=warnings,
        )
    except ValueError as exc:
        return JSONResponse(
            status_code=400,
            content=GoogleMapsQRErrorResponse(
                ok=False,
                message=str(exc),
                suggestion="Vui lòng chỉ dùng link Google Maps hợp lệ hoặc nhập trực tiếp Lat/Long.",
            ).model_dump(),
        )
    except Exception:
        logger.exception("Google Maps QR creation failed.")
        return JSONResponse(
            status_code=500,
            content=GoogleMapsQRErrorResponse(
                ok=False,
                message="Không thể xử lý nội dung đã dán ở thời điểm hiện tại.",
                suggestion="Vui lòng thử lại hoặc dùng link Google Maps đầy đủ.",
            ).model_dump(),
        )


if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")
if FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
