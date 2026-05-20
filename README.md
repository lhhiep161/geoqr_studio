# GeoQR Studio

Cong cu chuyen doi toa do, OCR toa do, dinh vi ban do va tao QR vi tri.

Tac gia: Hoang Hiep

## Backend MVP (FastAPI)

### 1) Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

OCR requires the Tesseract system binary in addition to Python packages.

macOS Homebrew:

```bash
brew install tesseract tesseract-lang
export TESSERACT_CMD=/opt/homebrew/bin/tesseract
```

Windows:

1. Install Tesseract OCR for Windows.
2. Set `TESSERACT_CMD` to the installed executable path, usually:

```text
C:\Program Files\Tesseract-OCR\tesseract.exe
```

### 2) Run API + Frontend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

Health check:

```bash
GET http://localhost:8000/health
GET http://localhost:8000/api/health
```

Frontend served by FastAPI:

```bash
http://localhost:8000/
```

API endpoints:

```bash
POST http://localhost:8000/api/convert
GET  http://localhost:8000/api/provinces
GET  http://localhost:8000/api/ocr-status
POST http://localhost:8000/api/ocr-coordinates
```

### 3) Run tests

```bash
python -m pytest -q
```

## Frontend local static mode (optional)

Desktop:
1. Start backend:
   - `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
2. Serve frontend:
   - `python -m http.server 5500`
3. Open:
   - `http://localhost:5500/frontend/index.html`

Phone LAN:
1. Start backend:
   - `uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000`
2. Serve frontend:
   - `python -m http.server 5500 --bind 0.0.0.0`
3. Open on phone:
   - `http://<computer-ip>:5500/frontend/index.html`

## OCR (Experimental)

- OCR is experimental. User must verify OCR values before conversion.
- Uploaded images are not stored permanently.
- Recommended: crop only coordinate-table area from GCN.

## Render deployment (Docker)

1. Ensure repository contains root `Dockerfile`.
2. In Render, create a new **Web Service** from this repo.
3. Select **Docker** runtime.
4. Build/deploy with root `Dockerfile`.
5. Start command in Docker image:
   - `uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}`
6. After deploy, verify:
   - `GET /api/health`
   - `GET /api/provinces`
   - Open `/` to confirm frontend is served.

Docker image installs OCR system packages:
- `tesseract-ocr`
- `tesseract-ocr-eng`
- `tesseract-ocr-vie` (best-effort install)
- `libglib2.0-0`
- `libgl1`

## Notes

- Runtime conversion logic reads `config/vn2000_local_crs.csv`.
- Reference Excel files under `data/reference_excel` are only for extraction/testing.
- Google Maps integration is URL-based only; no Google Maps API in MVP.

## Capacitor (Android/iOS wrapper)

This project keeps the same frontend/backend logic and adds Capacitor for mobile packaging.

### 1) Build web assets for Capacitor

```bash
npm run build:web
```

Output directory:

```text
dist/web
```

Mobile build (requires absolute backend URL, avoids localhost fallback):

```bash
set GEOQR_API_BASE_URL=https://your-backend-domain
npm run build:web:mobile
```

### 2) Sync Capacitor platforms

```bash
npx cap sync android
npx cap sync ios
```

### 3) Open native projects

```bash
npx cap open android
npx cap open ios
```

Notes:
- Android build/open requires Android Studio + Android SDK.
- iOS build/open requires macOS + Xcode.
- Backend CORS can be configured using `CORS_ALLOW_ORIGINS` (comma-separated).
