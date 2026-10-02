"""Build the app icon and installer artwork from the same mark used in the UI."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from place_stay import __version__  # noqa: E402
from place_stay.iconimg import draw, save_icon  # noqa: E402

INK = (18, 17, 16, 255)
PAPER = (243, 239, 232, 255)
WOOD = (215, 176, 122, 255)
MUTED = (183, 176, 166, 255)
ASSETS = Path(__file__).resolve().parent / "assets"
WIZARD_SIZES = ((164, 314), (192, 368), (240, 459), (320, 612), (480, 918))
SMALL_SIZES = (55, 64, 92, 110, 128)


def main() -> None:
    ASSETS.mkdir(parents=True, exist_ok=True)
    icon_path = ASSETS / "app.ico"
    save_icon(icon_path)
    package_icon = ROOT / "place_stay" / "assets" / "icon.ico"
    package_icon.parent.mkdir(parents=True, exist_ok=True)
    package_icon.write_bytes(icon_path.read_bytes())

    for width, height in WIZARD_SIZES:
        wizard_panel(width, height).save(ASSETS / f"wizard-side-{width}x{height}.png")
    for size in SMALL_SIZES:
        wizard_badge(size).save(ASSETS / f"wizard-small-{size}.png")

    _write_version_files()
    print(f"Wrote installer assets for Place. Stay. {__version__}")


def wizard_panel(width: int, height: int) -> Image.Image:
    image = Image.new("RGBA", (width, height), INK)
    glow = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    pen = ImageDraw.Draw(glow)
    pen.ellipse(
        (-int(width * 0.35), -int(height * 0.18), int(width * 1.35), int(height * 0.42)),
        fill=(215, 176, 122, 36),
    )
    image = Image.alpha_composite(image, glow.filter(ImageFilter.GaussianBlur(radius=max(8, width // 18))))

    mark_size = max(72, int(width * 0.56))
    mark = draw(mark_size)
    mx = (width - mark_size) // 2
    my = int(height * 0.22)
    image.paste(mark, (mx, my), mark)

    overlay = ImageDraw.Draw(image)
    title_size = max(13, int(width * 0.078))
    lede_size = max(10, int(width * 0.048))
    title_font = _font(title_size, bold=True)
    lede_font = _font(lede_size, bold=False)
    text_y = my + mark_size + max(18, int(height * 0.04))
    overlay.text((width / 2, text_y), "Place. Stay.", font=title_font, fill=PAPER, anchor="ma")
    overlay.text((width / 2, text_y + title_size + max(8, height // 80)), "Screens stay put", font=lede_font, fill=MUTED, anchor="ma")

    bar_w = max(28, int(width * 0.18))
    bar_y = text_y + title_size + lede_size + max(22, int(height * 0.045))
    overlay.rounded_rectangle(
        ((width - bar_w) / 2, bar_y, (width + bar_w) / 2, bar_y + max(3, height // 220)),
        radius=2,
        fill=WOOD,
    )
    return image


def wizard_badge(size: int) -> Image.Image:
    image = Image.new("RGBA", (size, size), INK)
    inner = max(16, int(size * 0.78))
    mark = draw(inner)
    offset = (size - inner) // 2
    image.paste(mark, (offset, offset), mark)
    return image


def _font(size: int, *, bold: bool) -> ImageFont.ImageFont:
    windir = Path(os.environ.get("WINDIR", r"C:\Windows"))
    names = ("segoeuib.ttf", "SegoeUI-Bold.ttf") if bold else ("segoeui.ttf", "segoeui.ttf")
    for name in names:
        path = windir / "Fonts" / name
        if path.exists():
            return ImageFont.truetype(str(path), size)
    return ImageFont.load_default()


def _write_version_files() -> None:
    parts = (__version__.split(".") + ["0", "0", "0"])[:4]
    numeric = tuple(int(part) for part in parts)
    iss = Path(__file__).resolve().parent / "version.iss"
    iss.write_text(f'#define MyAppVersion "{__version__}"\n', encoding="utf-8")
    info = Path(__file__).resolve().parent / "version_info.txt"
    info.write_text(
        "\n".join(
            [
                "VSVersionInfo(",
                "  ffi=FixedFileInfo(",
                f"    filevers={numeric},",
                f"    prodvers={numeric},",
                "    mask=0x3f,",
                "    flags=0x0,",
                "    OS=0x40004,",
                "    fileType=0x1,",
                "    subtype=0x0,",
                "    date=(0, 0)",
                "  ),",
                "  kids=[",
                "    StringFileInfo([",
                "      StringTable(",
                "        '040904B0',",
                "        [",
                "          StringStruct('CompanyName', 'Place. Stay.'),",
                "          StringStruct('FileDescription', 'Place. Stay.'),",
                f"          StringStruct('FileVersion', '{__version__}'),",
                "          StringStruct('InternalName', 'PlaceStay'),",
                "          StringStruct('LegalCopyright', 'Place. Stay.'),",
                "          StringStruct('OriginalFilename', 'PlaceStay.exe'),",
                "          StringStruct('ProductName', 'Place. Stay.'),",
                f"          StringStruct('ProductVersion', '{__version__}')",
                "        ]",
                "      )",
                "    ]),",
                "    VarFileInfo([VarStruct('Translation', [1033, 1200])])",
                "  ]",
                ")",
                "",
            ]
        ),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
