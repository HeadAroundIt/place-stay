"""Place. Stay. control panel."""

from __future__ import annotations

import os
import sys
import threading
import traceback
from pathlib import Path


def main() -> None:
    from place_stay.store import log
    from place_stay.winapi import enable_dpi_awareness, set_app_id

    if getattr(sys, "frozen", False):
        os.chdir(str(Path(sys.executable).resolve().parent))
    enable_dpi_awareness()
    set_app_id()
    if "--list" in sys.argv:
        _print_windows()
        return
    try:
        _run()
    except Exception as exc:
        log(traceback.format_exc())
        ctypes_message(str(exc))
        raise


def ctypes_message(text: str) -> None:
    import ctypes

    ctypes.windll.user32.MessageBoxW(0, text[:900], "Place. Stay.", 0x10)


def _print_windows() -> None:
    from place_stay.geom import label_monitors
    from place_stay.winapi import list_monitors, list_windows

    for mon in label_monitors(list_monitors()):
        print(f"{mon['label']} {mon['device']} {mon['width']}x{mon['height']} @ {mon['left']},{mon['top']}")
    for win in list_windows():
        print(f"{win['process']} | {win['title'][:70]} | {win['x']},{win['y']} {win['width']}x{win['height']}")


def _run() -> None:
    import webview

    from place_stay.engine import Engine
    from place_stay.geom import label_monitors
    from place_stay.iconimg import icon_file, save_icon
    from place_stay.shortcuts import ensure_startup, refresh_shortcut_icons, write_folder_launcher
    from place_stay.store import log
    from place_stay.winapi import claim_single_instance, list_monitors

    if not claim_single_instance("Place. Stay."):
        return
    background = "--background" in sys.argv
    engine = Engine()
    if not background:
        engine._restore_pending = False
    try:
        write_folder_launcher()
        ensure_startup(bool(engine.data["settings"].get("runAtStartup")))
    except Exception as exc:
        log(f"launcher setup failed: {exc}")

    icon_path = icon_file()
    save_icon(icon_path)
    try:
        refresh_shortcut_icons()
    except Exception as exc:
        log(f"shortcut icon refresh failed: {exc}")

    monitors = label_monitors(list_monitors())
    primary = next((mon for mon in monitors if mon.get("primary")), monitors[0] if monitors else None)
    width, height = 1180, 860
    if primary:
        avail_w = primary["workRight"] - primary["workLeft"]
        avail_h = primary["workBottom"] - primary["workTop"]
        width = min(1180, max(980, avail_w - 80))
        height = min(900, max(680, avail_h - 80))
    saved = engine.data["settings"].get("window") or {}
    try:
        saved_w = int(saved.get("width") or 0)
        saved_h = int(saved.get("height") or 0)
    except (TypeError, ValueError):
        saved_w = saved_h = 0
    if saved_w >= 980 and saved_h >= 680:
        width, height = saved_w, saved_h
        if primary:
            width = min(width, max(980, avail_w - 40))
            height = min(height, max(680, avail_h - 40))
    theme = engine.data["settings"].get("theme") or "ink"
    hidden = background and bool(engine.data["layouts"])

    api = Api(engine)
    window = webview.create_window(
        "Place. Stay.",
        url=str(Path(__file__).resolve().parent / "ui" / "index.html"),
        js_api=api,
        width=width,
        height=height,
        min_size=(980, 680),
        background_color="#121110" if theme == "ink" else "#e6e0d6",
        text_select=False,
        hidden=hidden,
    )
    api.attach(window, str(icon_path))
    window.events.closing += api.on_closing
    window.events.shown += api.on_shown
    webview.start(api.on_started, gui="edgechromium", http_server=True, icon=str(icon_path))


class Api:
    def __init__(self, engine) -> None:
        self._engine = engine
        self._window = None
        self._icon_path = ""
        self._quitting = False
        self._stop = threading.Event()
        self._tray = None
        self._tray_failed = False

    def attach(self, window, icon_path: str) -> None:
        self._window = window
        self._icon_path = icon_path

    def on_shown(self) -> None:
        self._style_frame()

    def on_started(self) -> None:
        self._style_frame()
        threading.Thread(target=self._watch, name="place-watch", daemon=True).start()
        threading.Thread(target=self._tray_loop, name="place-tray", daemon=True).start()

    def on_closing(self) -> bool:
        self._remember_bounds()
        if self._quitting or self._tray_failed:
            self._stop.set()
            self._stop_tray()
            return True
        try:
            self._window.hide()
        except Exception:
            return True
        return False

    def get_state(self) -> dict:
        return self._engine.ui_state()

    def create_layout(self, name, hwnds) -> dict:
        return self._engine.create_layout(name, list(hwnds or []))

    def update_layout(self, layout_id, edit) -> dict:
        return self._engine.update_layout(str(layout_id), edit or {})

    def add_open(self, hwnds) -> dict:
        return self._engine.add_open(list(hwnds or []))

    def rename_layout(self, layout_id, name) -> dict:
        return self._engine.rename_layout(str(layout_id), str(name or ""))

    def delete_layout(self, layout_id) -> dict:
        return self._engine.delete_layout(str(layout_id))

    def select_layout(self, layout_id) -> dict:
        return self._engine.select_layout(str(layout_id))

    def apply_layout(self, layout_id=None) -> dict:
        return self._engine.apply_layout(str(layout_id) if layout_id else None)

    def update_settings(self, patch) -> dict:
        result = self._engine.update_settings(patch or {})
        if patch and "theme" in patch:
            self._style_frame()
        return result

    def create_desktop_shortcut(self) -> dict:
        from place_stay.shortcuts import create_desktop_shortcut
        from place_stay.store import log

        try:
            path = create_desktop_shortcut()
        except Exception as exc:
            log(f"desktop shortcut failed: {exc}")
            return {"ok": False, "error": "Couldn't create the desktop shortcut.", "state": self._engine.ui_state()}
        return {"ok": True, "toast": "Shortcut added to your desktop.", "path": path, "state": self._engine.ui_state()}

    def quit_app(self) -> None:
        self._quitting = True
        self._stop.set()
        self._remember_bounds()
        self._stop_tray()
        try:
            self._window.destroy()
        except Exception:
            os._exit(0)

    def _watch(self) -> None:
        from place_stay.store import log

        while not self._stop.is_set():
            try:
                self._engine.tick()
            except Exception:
                log(traceback.format_exc())
            if self._stop.wait(0.8):
                break

    def _style_frame(self) -> None:
        from place_stay.winapi import apply_window_icon, find_titled, style_frame

        dark = (self._engine.data["settings"].get("theme") or "ink") == "ink"
        for _ in range(8):
            hwnd = find_titled("Place. Stay.")
            if hwnd:
                style_frame(hwnd, dark=dark)
                apply_window_icon(hwnd, self._icon_path)
                return
            if self._stop.wait(0.25):
                return

    def _remember_bounds(self) -> None:
        window = self._window
        if window is None:
            return
        try:
            width = int(window.width)
            height = int(window.height)
            if width < 400 or height < 320:
                return
            self._engine.remember_window_bounds(
                {"x": int(window.x), "y": int(window.y), "width": width, "height": height}
            )
        except Exception:
            return

    def _tray_loop(self) -> None:
        from pystray import Icon, Menu, MenuItem

        from place_stay.iconimg import tray_image
        from place_stay.store import log

        def open_window(_icon, _item):
            try:
                self._window.show()
            except Exception:
                log(traceback.format_exc())

        def apply_active(_icon, _item):
            try:
                self._engine.apply_layout(None)
            except Exception:
                log(traceback.format_exc())

        def quit_app(_icon, _item):
            self.quit_app()

        menu = Menu(
            MenuItem("Open Place. Stay.", open_window, default=True),
            MenuItem("Put windows back", apply_active),
            Menu.SEPARATOR,
            MenuItem("Quit", quit_app),
        )
        try:
            self._tray = Icon("Place. Stay.", tray_image(), "Place. Stay.", menu)
            self._tray.run(self._after_tray_ready)
        except Exception:
            self._tray_failed = True
            log(traceback.format_exc())

    def _after_tray_ready(self, icon) -> None:
        from place_stay.store import log
        from place_stay.winapi import watch_shell_events

        try:
            icon.visible = True
        except Exception:
            log(traceback.format_exc())

        def reshow() -> None:
            if self._stop.wait(1.5):
                return
            self._recover_tray()

        threading.Thread(target=reshow, name="place-tray-reshow", daemon=True).start()
        try:
            watch_shell_events(self._recover_tray, self._stop)
        except Exception:
            log(traceback.format_exc())

    def _recover_tray(self) -> None:
        tray = self._tray
        if tray is None or self._quitting:
            return
        try:
            tray.visible = False
            tray.visible = True
        except Exception:
            return

    def _stop_tray(self) -> None:
        from place_stay.winapi import stop_shell_watch

        stop_shell_watch()
        tray = self._tray
        if tray is None:
            return
        try:
            tray.stop()
        except Exception:
            pass
