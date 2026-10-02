from __future__ import annotations

import json
from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"


def test_manifest_defines_installable_app() -> None:
    manifest = json.loads((FRONTEND / "manifest.webmanifest").read_text(encoding="utf-8"))

    assert manifest["name"] == "GeoQR Studio"
    assert manifest["display"] == "standalone"
    assert manifest["start_url"] == "./"
    assert manifest["theme_color"] == "#005993"
    assert {icon["sizes"] for icon in manifest["icons"]} >= {"192x192", "512x512"}
    assert any(icon.get("purpose") == "maskable" for icon in manifest["icons"])


def test_pwa_icons_have_declared_sizes() -> None:
    expected = {
        "icon-192.png": (192, 192),
        "icon-512.png": (512, 512),
        "icon-maskable-512.png": (512, 512),
        "apple-touch-icon.png": (180, 180),
    }

    for filename, size in expected.items():
        with Image.open(ROOT / "assets" / "pwa" / filename) as icon:
            assert icon.size == size


def test_frontend_registers_manifest_and_service_worker() -> None:
    index_html = (FRONTEND / "index.html").read_text(encoding="utf-8-sig")
    app_js = (FRONTEND / "app.js").read_text(encoding="utf-8-sig")
    service_worker = (FRONTEND / "service-worker.js").read_text(encoding="utf-8")

    assert 'rel="manifest"' in index_html
    assert 'rel="apple-touch-icon"' in index_html
    assert 'navigator.serviceWorker.register("./service-worker.js")' in app_js
    assert 'url.pathname.startsWith("/api/")' in service_worker
