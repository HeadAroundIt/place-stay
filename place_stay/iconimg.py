from __future__ import annotations

import io
import struct
import sys
from pathlib import Path

from PIL import Image, ImageDraw

INK = (18, 17, 16, 255)
PAPER = (243, 239, 232, 255)
WOOD = (215, 176, 122, 255)
SIZES = (16, 20, 24, 32, 48, 256)


def icon_file() -> Path:
    bundled = Path(__file__).resolve().parent / "assets" / "icon.ico"
    if getattr(sys, "frozen", False) and not bundled.exists():
        from place_stay.store import data_dir

        return data_dir() / "icon.ico"
    return bundled


def draw(size: int) -> Image.Image:
    """Draw large, then shrink, so the taskbar sizes stay sharp."""
    factor = 4 if size < 128 else 2
    canvas = size * factor
    image = Image.new("RGBA", (canvas, canvas), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)
    pad = max(factor, int(canvas * 0.06))
    radius = max(factor * 2, int(canvas * 0.22))
    rim = max(factor, canvas // 28)
    pen.rounded_rectangle(
        (pad, pad, canvas - pad - 1, canvas - pad - 1),
        radius=radius,
        fill=INK,
        outline=PAPER,
        width=rim,
    )

    def box(fx0: float, fy0: float, fx1: float, fy1: float, fill: tuple[int, int, int, int]) -> None:
        pen.rounded_rectangle(
            (int(canvas * fx0), int(canvas * fy0), int(canvas * fx1), int(canvas * fy1)),
            radius=max(1, int(canvas * 0.06)),
            fill=fill,
        )

    box(0.22, 0.24, 0.46, 0.76, PAPER)
    box(0.54, 0.34, 0.80, 0.76, WOOD)
    return image.resize((size, size), Image.Resampling.LANCZOS)


def save_icon(path) -> None:
    dest = Path(path)
    if getattr(sys, "frozen", False) and dest.exists():
        return
    _write_ico(dest, [draw(size) for size in SIZES])


def tray_image() -> Image.Image:
    return draw(64)


def _write_ico(path: Path, frames: list[Image.Image]) -> None:
    blobs: list[bytes] = []
    for frame in frames:
        buf = io.BytesIO()
        frame.save(buf, format="PNG")
        blobs.append(buf.getvalue())
    offset = 6 + 16 * len(frames)
    parts = [struct.pack("<HHH", 0, 1, len(frames))]
    for frame, blob in zip(frames, blobs, strict=True):
        width = 0 if frame.width >= 256 else frame.width
        height = 0 if frame.height >= 256 else frame.height
        parts.append(struct.pack("<BBBBHHII", width, height, 0, 0, 1, 32, len(blob), offset))
        offset += len(blob)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"".join(parts) + b"".join(blobs))
