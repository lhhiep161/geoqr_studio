from __future__ import annotations

from pathlib import Path

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
LOGO_PATH = ROOT / "assets" / "brand" / "logo.png"
ANDROID_RES = ROOT / "android" / "app" / "src" / "main" / "res"
IOS_ICON_PATH = ROOT / "ios" / "App" / "App" / "Assets.xcassets" / "AppIcon.appiconset" / "AppIcon-512@2x.png"


ANDROID_ICON_SIZES = {
    "mipmap-mdpi": 48,
    "mipmap-hdpi": 72,
    "mipmap-xhdpi": 96,
    "mipmap-xxhdpi": 144,
    "mipmap-xxxhdpi": 192,
}


def ensure_logo() -> Image.Image:
    if not LOGO_PATH.exists():
        raise FileNotFoundError(f"Logo not found: {LOGO_PATH}")
    return Image.open(LOGO_PATH).convert("RGBA")


def build_square_icon(logo: Image.Image, size: int, inset_ratio: float = 0.82) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (255, 255, 255, 255))
    target = max(1, int(size * inset_ratio))
    resized = logo.resize((target, target), Image.Resampling.LANCZOS)
    offset = ((size - target) // 2, (size - target) // 2)
    canvas.alpha_composite(resized, offset)
    return canvas


def build_adaptive_foreground(logo: Image.Image, size: int, inset_ratio: float = 0.72) -> Image.Image:
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    target = max(1, int(size * inset_ratio))
    resized = logo.resize((target, target), Image.Resampling.LANCZOS)
    offset = ((size - target) // 2, (size - target) // 2)
    canvas.alpha_composite(resized, offset)
    return canvas


def generate_android_icons(logo: Image.Image) -> None:
    for folder, size in ANDROID_ICON_SIZES.items():
        out_dir = ANDROID_RES / folder
        out_dir.mkdir(parents=True, exist_ok=True)
        build_square_icon(logo, size).save(out_dir / "ic_launcher.png")
        build_square_icon(logo, size).save(out_dir / "ic_launcher_round.png")
        build_adaptive_foreground(logo, size).save(out_dir / "ic_launcher_foreground.png")


def generate_ios_icon(logo: Image.Image) -> None:
    IOS_ICON_PATH.parent.mkdir(parents=True, exist_ok=True)
    build_square_icon(logo, 1024, inset_ratio=0.84).save(IOS_ICON_PATH)


def main() -> None:
    logo = ensure_logo()
    generate_android_icons(logo)
    generate_ios_icon(logo)
    print("Generated Android/iOS launcher icons from assets/brand/logo.png")


if __name__ == "__main__":
    main()
