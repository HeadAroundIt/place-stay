"""Capture Place Stay UI photos for the GitHub README.

Same treatment as PasteFlick: serve the real interface, then photograph it
with headless Chrome at 2x.
"""

from __future__ import annotations

import os
import socket
import subprocess
import threading
import time
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UI = ROOT / "place_stay" / "ui"
OUT = ROOT / "readme" / "shots"
CHROME = Path(os.environ.get("PROGRAMFILES", r"C:\Program Files")) / "Google/Chrome/Application/chrome.exe"


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(UI), **kwargs)

    def log_message(self, fmt: str, *args) -> None:
        pass

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def shot(url: str, dest: Path, width: int, height: int) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".tmp.png")
    cmd = [
        str(CHROME),
        "--headless=new",
        "--disable-gpu",
        "--hide-scrollbars",
        "--no-first-run",
        "--force-device-scale-factor=2",
        f"--window-size={width},{height}",
        "--default-background-color=00000000",
        f"--screenshot={tmp}",
        "--virtual-time-budget=4000",
        url,
    ]
    subprocess.run(cmd, check=True, cwd=str(ROOT))
    tmp.replace(dest)
    print(dest.name, dest.stat().st_size)


def main() -> None:
    if not CHROME.is_file():
        raise SystemExit("Chrome not found")
    port = free_port()
    httpd = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    time.sleep(0.2)
    base = f"http://127.0.0.1:{port}/index.html"
    try:
        shot(f"{base}?preview=1&shot=desk", OUT / "desk.png", 1140, 560)
        shot(f"{base}?preview=1&shot=windows", OUT / "windows.png", 980, 470)
        shot(f"{base}?preview=1&shot=putback", OUT / "put-back.png", 1140, 560)
    finally:
        httpd.shutdown()
    print("ok")


if __name__ == "__main__":
    main()
