"""Where layouts live: %APPDATA%\\PlaceStay\\state.json"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path

from place_stay.brand import DATA_FOLDER, LEGACY_DATA_FOLDER, LOG_NAME

_LOCK = threading.Lock()

DEFAULT = {
    "version": 1,
    "settings": {
        "placeOnOpen": True,
        "runAtStartup": False,
        "theme": "ink",
        "activeLayoutId": None,
        "window": None,
    },
    "layouts": [],
}


def data_dir() -> Path:
    override = os.environ.get("PLACE_STAY_HOME") or os.environ.get("STICKY_DESKTOP_HOME")
    if override:
        root = Path(override)
    else:
        appdata = Path(os.environ.get("APPDATA", "."))
        root = appdata / DATA_FOLDER
        legacy = appdata / LEGACY_DATA_FOLDER
        if not root.exists() and legacy.exists():
            try:
                legacy.rename(root)
            except OSError:
                root = legacy
    root.mkdir(parents=True, exist_ok=True)
    return root


def _path() -> Path:
    return data_dir() / "state.json"


def load() -> dict:
    path = _path()
    if not path.exists():
        return json.loads(json.dumps(DEFAULT))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return json.loads(json.dumps(DEFAULT))
    settings = dict(DEFAULT["settings"])
    settings.update(data.get("settings") or {})
    if settings.get("theme") not in {"ink", "paper"}:
        settings["theme"] = "ink"
    return {
        "version": 1,
        "settings": settings,
        "layouts": list(data.get("layouts") or []),
    }


def save(data: dict) -> None:
    path = _path()
    payload = json.dumps(data, indent=2)
    with _LOCK:
        temp = path.with_suffix(".json.tmp")
        temp.write_text(payload, encoding="utf-8")
        temp.replace(path)


def log(message: str) -> None:
    try:
        from datetime import datetime

        line = f"{datetime.now().isoformat(timespec='seconds')} {message}\n"
        with (data_dir() / LOG_NAME).open("a", encoding="utf-8") as handle:
            handle.write(line)
    except OSError:
        pass
