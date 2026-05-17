# AGENTS.md

## Project

**Name:** GeoQR Studio

This repository is for a mobile-first PWA/web app used as a personal coordinate workflow tool to:

1. Convert VN2000 cadastral coordinates printed on Vietnamese land-use certificates (`GCN QSDD`) into WGS84 latitude/longitude.
2. Compare the converted coordinate with the user's current GPS location.
3. Generate a Google Maps URL for quick viewing.

The product is an **internal support/reference tool only**. It does **not** replace official surveying results or competent authority confirmation.

## Product Intent

The UX should be simple enough for non-GIS specialists. End users should not need to understand projection parameters, EPSG codes, or geodesy terminology. The system must hide CRS complexity behind province/city selection and well-defined configuration.

## Non-Negotiable Product Rules

1. Do **not** ask end users to choose EPSG, central meridian, projection zone, scale factor, false easting, false northing, or datum parameters.
2. End users only select the province/city shown on the `GCN QSDD` and enter or confirm coordinate values.
3. VN2000 cadastral CRS settings must be derived from `config/vn2000_local_crs.csv`.
4. Default cadastral rules:
   - Datum: `VN-2000`
   - Projection: `Transverse Mercator (TM-3)`
   - Zone width: `3 degrees`
   - Scale factor `k0 = 0.9999`
   - False easting: `500000`
   - False northing: `0`
   - Unit: `meter`
5. Do **not** use Excel as the runtime engine.
6. Files in `data/reference_excel/` are reference and test sources only.
7. Google Maps integration must use URL generation only, for example: `https://www.google.com/maps?q=<lat>,<lng>`.
8. Do **not** add Google Maps API unless explicitly requested.
9. Coordinate conversion logic must be isolated from UI code.
10. Add automated tests for coordinate conversion.
11. Do **not** implement OCR unless explicitly requested in a later phase.
12. Do **not** store customer data or `GCN` images in this MVP.
13. Keep debug logging disabled by default.
14. Show warnings when results look suspicious, including likely swapped `X/Y` input.
15. Do **not** introduce paid APIs.
16. Do **not** add map rendering, offline maps, OCR, or native app features unless explicitly requested.

## Preferred Architecture

Use this structure unless there is a strong reason to deviate:

```text
backend/
  core/
    coordinate_converter.py
    vn2000_config.py
    distance_calculator.py
    google_maps_url.py
  services/
    qr_service.py
frontend/
config/
  vn2000_local_crs.csv
tests/
  test_coordinates.csv
```

### Responsibilities

- `backend/core/coordinate_converter.py`
  - Pure coordinate conversion logic.
  - No UI code.
  - No direct dependency on Excel files.
- `backend/core/vn2000_config.py`
  - Load and validate province/city CRS configuration from `config/vn2000_local_crs.csv`.
- `backend/core/distance_calculator.py`
  - Compute distance between converted coordinate and device GPS location.
- `backend/core/google_maps_url.py`
  - Generate Google Maps URLs only.
- `backend/services/qr_service.py`
  - Reserved for QR-related support features if needed later.
- `frontend/`
  - Mobile-first, PWA-friendly UI.
  - Must consume backend/core functionality via clean interfaces.

## UI and Branding

Keep the interface clean, professional, and trustworthy.

- Primary color: `#005993`
- Accent color: `#D71249`
- Light background: `#F4F8FB`
- Main text: `#0F172A`
- Secondary text: `#64748B`

Branding rules:

- If `assets/brand/logo.png` exists, use it in the header/brand area.
- If the logo is unavailable, fall back to a text brand header: `GeoQR Studio`.
- Prefer a calm, trustworthy, mobile-first layout over consumer-style map-heavy UI.

## UX Rules

- Ask the user for the province/city from the `GCN QSDD`.
- Ask the user for coordinate values only.
- Keep inputs and outputs understandable to non-technical bank staff.
- Clearly label converted latitude/longitude.
- Provide a one-tap Google Maps link via URL generation.
- Show a warning when:
  - the result is implausible for the chosen province/city,
  - the coordinate appears malformed,
  - `X/Y` may be swapped,
  - the distance from the current GPS location is unexpectedly large.
- Show a visible disclaimer that results are for internal support/reference only.

## Data and Security

- Treat all user-entered land certificate data as sensitive operational information.
- Do not persist customer data in the MVP unless explicitly approved later.
- Do not store uploaded images or scans.
- Avoid verbose logs that could expose coordinate or document details.
- Keep debug logging off by default.

## Implementation Guidance

- Prefer Python `FastAPI` in `backend/`.
- Keep business logic deterministic and testable.
- Separate:
  - CRS/config loading
  - coordinate transformation
  - validation/suspicion checks
  - distance calculation
  - URL generation
- Build small, reviewable changes.
- Preserve clear boundaries between frontend and backend logic.
- Use reference Excel files only to validate behavior and build test fixtures.

## Testing Expectations

- Add and maintain automated tests for coordinate conversion.
- Prefer fixture-driven tests using known examples in `tests/test_coordinates.csv`.
- Include tests for:
  - valid conversion flows,
  - province/city configuration lookup,
  - suspicious input detection,
  - swapped `X/Y` warning behavior when applicable,
  - Google Maps URL formatting,
  - distance calculation behavior.
- Run tests after every code change.

## Out of Scope Until Requested

- OCR
- Google Maps API
- Interactive embedded map features
- Offline maps
- Native mobile apps
- Paid third-party APIs
- Long-term storage of customer or certificate image data

## Working Agreement For Contributors

When making changes in this repository:

1. Keep changes small and reviewable.
2. Respect the product rules above as hard constraints.
3. Avoid adding hidden GIS complexity to the UI.
4. Do not couple conversion logic to frontend code.
5. Do not rely on Excel at runtime.
6. Run relevant tests after changes.
7. Summarize changed files and assumptions in handoff notes or PR descriptions.

## Current Repository Notes

- `assets/brand/logo.png` is present and should be used when branding is implemented.
- `data/reference_excel/` contains reference spreadsheets only.
- `config/` and `tests/` may be populated as implementation proceeds.
