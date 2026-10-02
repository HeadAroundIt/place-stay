"""Where the app lives when running from source versus a frozen install."""

from __future__ import annotations

import sys
from pathlib import Path


def frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def package_dir() -> Path:
    return Path(__file__).resolve().parent


def app_home() -> Path:
    if frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def launch_exe() -> Path:
    if frozen():
        return Path(sys.executable).resolve()
    exe = Path(sys.executable)
    candidate = exe.with_name("pythonw.exe")
    return candidate if candidate.exists() else exe


def launch_args(*, background: bool = False) -> str:
    parts: list[str] = []
    if not frozen():
        parts.append("-m place_stay")
    if background:
        parts.append("--background")
    return " ".join(parts)
