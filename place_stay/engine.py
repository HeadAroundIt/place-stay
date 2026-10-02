"""Capture the desktop, remember layouts, and put windows back once."""

from __future__ import annotations

import copy
import os
import threading
import time

from place_stay import winapi
from place_stay.geom import (
    clamp_rect,
    label_monitors,
    monitor_for_point,
    resolve_monitor,
    same_place,
    staging_rect,
)
from place_stay.layouts import (
    apply_edit,
    new_id,
    new_rules_for_hwnds,
    now_stamp,
    rule_from_window,
    saved_label,
    unique_name,
)
from place_stay.names import app_name
from place_stay.store import load, log, save

_STATUS_ORDER = {"moved": 0, "new": 1, "in_place": 2, "closed": 3}


class Engine:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._attempts: dict[int, int] = {}
        self.data = load()
        self._bound: dict[int, str] = {}
        self._seen: dict[int, tuple] = {}
        self._restore_pending = bool(self.data["settings"].get("placeOnOpen"))
        self.activity = ""
        self.activity_at = 0.0

    def tick(self) -> None:
        if winapi.mouse_left_down():
            return
        with self._lock:
            if not self.data["settings"].get("placeOnOpen"):
                return
            layout = self._active_locked()
            if not layout:
                return
            layout = copy.deepcopy(layout)
            first = self._restore_pending
            if first:
                self._restore_pending = False
        self._sync(layout, move=True, require_stable=not first, honor_minimized=False)

    def ui_state(self) -> dict:
        monitors = label_monitors(winapi.list_monitors())
        live = self._decorate(winapi.list_windows(), monitors)
        with self._lock:
            snapshot = copy.deepcopy(self.data)
            activity = self.activity
            activity_at = self.activity_at
        return _compose(snapshot, monitors, live, activity, activity_at)

    def create_layout(self, name: str, hwnds: list) -> dict:
        monitors = label_monitors(winapi.list_monitors())
        live = {str(item["hwnd"]): item for item in self._decorate(winapi.list_windows(), monitors)}
        chosen = [live[str(hwnd)] for hwnd in hwnds if str(hwnd) in live]
        if not chosen:
            return {"ok": False, "error": "Choose at least one open window.", "state": self.ui_state()}
        with self._lock:
            layout_name = unique_name(str(name or ""), [item["name"] for item in self.data["layouts"]])
            layout = {
                "id": new_id(),
                "name": layout_name,
                "savedAt": now_stamp(),
                "windows": [rule_from_window(item, monitors) for item in chosen],
            }
            self.data["layouts"].insert(0, layout)
            self.data["settings"]["activeLayoutId"] = layout["id"]
            save(self.data)
        self._rebind_active()
        return {"ok": True, "toast": f"Saved {layout_name}.", "state": self.ui_state()}

    def update_layout(self, layout_id: str, edit: dict) -> dict:
        monitors = label_monitors(winapi.list_monitors())
        live = {str(item["hwnd"]): item for item in self._decorate(winapi.list_windows(), monitors)}
        with self._lock:
            layout = self._find_locked(layout_id)
            if layout is None:
                missing = True
                name = ""
                updated = []
            else:
                missing = False
                updated = apply_edit(layout["windows"], live, monitors, edit or {})
                name = layout["name"]
                if updated:
                    layout["windows"] = updated
                    layout["savedAt"] = now_stamp()
                    save(self.data)
        if missing:
            return {"ok": False, "error": "That layout is gone.", "state": self.ui_state()}
        if not updated:
            return {"ok": False, "error": "Leave at least one window in the layout.", "state": self.ui_state()}
        self._rebind_active()
        return {"ok": True, "toast": f"Updated {name}.", "state": self.ui_state()}

    def add_open(self, hwnds: list) -> dict:
        monitors = label_monitors(winapi.list_monitors())
        live = {str(item["hwnd"]): item for item in self._decorate(winapi.list_windows(), monitors)}
        with self._lock:
            layout = self._active_locked()
            rules = list(layout["windows"]) if layout else []
            added = new_rules_for_hwnds(rules, live, monitors, hwnds or [])
            if not added:
                missing = not any(str(hwnd) in live for hwnd in (hwnds or []))
            else:
                missing = False
                if layout is None:
                    layout = {
                        "id": new_id(),
                        "name": "My desktop",
                        "savedAt": now_stamp(),
                        "windows": [],
                    }
                    self.data["layouts"].insert(0, layout)
                    self.data["settings"]["activeLayoutId"] = layout["id"]
                layout["windows"].extend(added)
                layout["savedAt"] = now_stamp()
                save(self.data)
                names = [rule["appName"] for rule in added]
        if not added:
            if missing:
                return {"ok": False, "error": "That window isn't open anymore. Open it, then add it.", "state": self.ui_state()}
            return {"ok": False, "error": "That app is already in this layout.", "state": self.ui_state()}
        self._rebind_active()
        if len(names) == 1:
            toast = f"Added {names[0]} where it is now."
        else:
            toast = f"Added {len(names)} apps where they are now."
        return {"ok": True, "toast": toast, "state": self.ui_state()}

    def rename_layout(self, layout_id: str, name: str) -> dict:
        with self._lock:
            layout = self._find_locked(layout_id)
            if layout is None:
                return {"ok": False, "error": "That layout is gone.", "state": self.ui_state()}
            others = [item["name"] for item in self.data["layouts"] if item["id"] != layout_id]
            layout["name"] = unique_name(str(name or ""), others)
            save(self.data)
        return {"ok": True, "toast": "Renamed.", "state": self.ui_state()}

    def delete_layout(self, layout_id: str) -> dict:
        with self._lock:
            before = len(self.data["layouts"])
            self.data["layouts"] = [item for item in self.data["layouts"] if item["id"] != layout_id]
            if len(self.data["layouts"]) == before:
                return {"ok": False, "error": "That layout is gone.", "state": self.ui_state()}
            if self.data["settings"].get("activeLayoutId") == layout_id:
                self.data["settings"]["activeLayoutId"] = self.data["layouts"][0]["id"] if self.data["layouts"] else None
            save(self.data)
            self._bound.clear()
            self._seen.clear()
        self._rebind_active()
        return {"ok": True, "toast": "Layout deleted. Your windows were left where they are.", "state": self.ui_state()}

    def select_layout(self, layout_id: str) -> dict:
        with self._lock:
            if self._find_locked(layout_id) is None:
                return {"ok": False, "error": "That layout is gone.", "state": self.ui_state()}
            self.data["settings"]["activeLayoutId"] = layout_id
            save(self.data)
            self._bound.clear()
            self._seen.clear()
            self._restore_pending = False
        self._rebind_active()
        return {"ok": True, "state": self.ui_state()}

    def apply_layout(self, layout_id: str | None = None) -> dict:
        with self._lock:
            layout = self._find_locked(layout_id) if layout_id else self._active_locked()
            if layout is None:
                return {"ok": False, "error": "Save a layout first.", "state": self.ui_state()}
            layout = copy.deepcopy(layout)
            self._bound.clear()
            self._seen.clear()
            self._attempts.clear()
            self._restore_pending = False
        moved, failed, already, missing, warnings = self._sync(
            layout, move=True, require_stable=False, honor_minimized=True, report=True
        )
        toast = _toast(moved, failed, already, missing, warnings)
        self._set_activity(moved)
        return {"ok": not failed, "toast": toast, "state": self.ui_state()}

    def update_settings(self, patch: dict) -> dict:
        patch = patch or {}
        arm = False
        startup_flag = None
        with self._lock:
            settings = self.data["settings"]
            if "placeOnOpen" in patch:
                settings["placeOnOpen"] = bool(patch["placeOnOpen"])
                self._restore_pending = False
                arm = settings["placeOnOpen"]
            if "theme" in patch and patch["theme"] in {"ink", "paper"}:
                settings["theme"] = patch["theme"]
            if "runAtStartup" in patch:
                settings["runAtStartup"] = bool(patch["runAtStartup"])
                startup_flag = settings["runAtStartup"]
            if "window" in patch and isinstance(patch["window"], dict):
                settings["window"] = {
                    "x": int(patch["window"].get("x", 0)),
                    "y": int(patch["window"].get("y", 0)),
                    "width": int(patch["window"].get("width", 0)),
                    "height": int(patch["window"].get("height", 0)),
                }
            save(self.data)
        if startup_flag is not None:
            from place_stay import shortcuts

            try:
                shortcuts.ensure_startup(startup_flag)
            except Exception as exc:
                log(f"startup shortcut failed: {exc}")
                with self._lock:
                    self.data["settings"]["runAtStartup"] = False
                    save(self.data)
                return {
                    "ok": False,
                    "error": "Couldn't add Place. Stay. to startup. You can still open it yourself.",
                    "state": self.ui_state(),
                }
        if arm:
            layout = self._active_copy()
            if layout:
                self._sync(layout, move=False, require_stable=False, honor_minimized=False)
        return {"ok": True, "state": self.ui_state()}

    def remember_window_bounds(self, bounds: dict) -> None:
        with self._lock:
            self.data["settings"]["window"] = bounds
            save(self.data)

    def _active_copy(self) -> dict | None:
        with self._lock:
            layout = self._active_locked()
            return copy.deepcopy(layout) if layout else None

    def _active_locked(self) -> dict | None:
        return self._find_locked(self.data["settings"].get("activeLayoutId"))

    def _find_locked(self, layout_id: str | None) -> dict | None:
        if not layout_id:
            return None
        return next((item for item in self.data["layouts"] if item["id"] == layout_id), None)

    def _decorate(self, windows: list[dict], monitors: list[dict]) -> list[dict]:
        decorated = []
        for win in windows:
            item = dict(win)
            item["appName"] = app_name(item.get("process", ""), item.get("title", ""))
            mon = monitor_for_point(item["x"] + item["width"] / 2, item["y"] + item["height"] / 2, monitors)
            item["monitorLabel"] = mon["label"] if mon else "Off screen"
            item["monitorDevice"] = mon["device"] if mon else ""
            decorated.append(item)
        return decorated

    def _rebind_active(self) -> None:
        layout = self._active_copy()
        with self._lock:
            self._bound.clear()
            self._seen.clear()
            self._attempts.clear()
        if layout:
            self._sync(layout, move=False, require_stable=False, honor_minimized=False)

    def _sync(
        self,
        layout: dict,
        *,
        move: bool,
        require_stable: bool,
        honor_minimized: bool,
        report: bool = False,
    ):
        live = self._decorate(winapi.list_windows(), label_monitors(winapi.list_monitors()))
        live_ids = {item["hwnd"] for item in live}
        with self._lock:
            self._bound = {hwnd: rule_id for hwnd, rule_id in self._bound.items() if hwnd in live_ids}
            self._seen = {hwnd: sig for hwnd, sig in self._seen.items() if hwnd in live_ids}
            self._attempts = {hwnd: count for hwnd, count in self._attempts.items() if hwnd in live_ids}
            bound_rules = set(self._bound.values())
            bound_hwnds = set(self._bound)
        free_rules = [rule for rule in layout.get("windows", []) if rule["id"] not in bound_rules]
        free_live = [item for item in live if item["hwnd"] not in bound_hwnds]
        from place_stay.match import pair_rules

        pairs, _unmatched = pair_rules(free_rules, free_live)
        monitors = label_monitors(winapi.list_monitors())
        moved: list[str] = []
        failed: list[str] = []
        already = 0
        missing = 0
        warnings: list[str] = []
        matched = 0
        for rule, win in pairs:
            if win is None:
                missing += 1
                continue
            matched += 1
            hwnd = int(win["hwnd"])
            sig = (win["x"], win["y"], win["width"], win["height"], win["maximized"], win["minimized"])
            with self._lock:
                prev = self._seen.get(hwnd)
                count = prev[1] + 1 if prev and prev[0] == sig else 1
                self._seen[hwnd] = (sig, count)
            if require_stable and count < 2:
                continue
            placed = True
            if move:
                did_move, message, warning = self._move_one(rule, win, monitors, honor_minimized)
                if message:
                    failed.append(message)
                    with self._lock:
                        tries = self._attempts.get(hwnd, 0) + 1
                        self._attempts[hwnd] = tries
                    if tries < 3:
                        placed = False
                elif did_move:
                    moved.append(rule.get("appName") or "A window")
                else:
                    already += 1
                if warning:
                    warnings.append(warning)
            if placed:
                with self._lock:
                    self._bound[hwnd] = rule["id"]
        if moved and not report:
            self._set_activity(moved)
        if report:
            return moved, failed, already, missing if matched or missing else missing, warnings
        return None

    def _move_one(self, rule: dict, win: dict, monitors: list[dict], honor_minimized: bool) -> tuple[bool, str, str]:
        mon, exact = resolve_monitor(rule, monitors)
        if mon is None:
            return False, f"Couldn't find a screen for {rule.get('appName', 'a window')}.", ""
        warning = ""
        if not exact:
            warning = f"{mon['label']} is standing in for a screen that isn't connected."
        if same_place(rule, win, mon):
            return False, "", warning
        if rule.get("maximized"):
            x, y, w, h = staging_rect(mon)
        else:
            x, y, w, h = clamp_rect(
                mon["left"] + int(rule.get("relX", 0)),
                mon["top"] + int(rule.get("relY", 0)),
                int(rule.get("width", 800)),
                int(rule.get("height", 600)),
                mon,
            )
        ok, message = winapi.place_window(
            int(win["hwnd"]),
            x,
            y,
            w,
            h,
            maximized=bool(rule.get("maximized")),
            minimize=bool(honor_minimized and rule.get("minimized")),
        )
        if not ok:
            name = rule.get("appName") or "A window"
            return False, f"{name}: {message}", warning
        log(f"placed {rule.get('appName')} on {mon['label']} at {x},{y} {w}x{h}")
        return True, "", warning

    def _set_activity(self, names: list[str]) -> None:
        if not names:
            return
        if len(names) == 1:
            text = f"Put {names[0]} back in place."
        else:
            text = f"Put {len(names)} windows back in place."
        with self._lock:
            self.activity = text
            self.activity_at = time.time()


def _size_label(width: int, height: int, maximized: bool, minimized: bool) -> str:
    if minimized:
        return "Minimized"
    if maximized:
        return "Maximized"
    return f"{int(width)} × {int(height)}"


def _compose(data: dict, monitors: list[dict], live: list[dict], activity: str, activity_at: float) -> dict:
    from place_stay.match import pair_rules
    from place_stay.shortcuts import desktop_shortcut_exists

    active_id = data["settings"].get("activeLayoutId")
    layout = next((item for item in data["layouts"] if item["id"] == active_id), None)
    rows: list[dict] = []
    if layout:
        pairs, unmatched = pair_rules(layout.get("windows", []), live)
        for rule, win in pairs:
            mon, _exact = resolve_monitor(rule, monitors)
            saved_name = mon["label"] if mon else "Missing screen"
            if win is None:
                rows.append(
                    {
                        "key": f"saved:{rule['id']}",
                        "hwnd": None,
                        "ruleId": rule["id"],
                        "appName": rule.get("appName") or "Window",
                        "title": rule.get("title") or "",
                        "monitorLabel": saved_name,
                        "sizeLabel": _size_label(rule.get("width", 0), rule.get("height", 0), rule.get("maximized"), rule.get("minimized")),
                        "status": "closed",
                        "suggested": True,
                        "x": None,
                        "y": None,
                        "width": rule.get("width", 0),
                        "height": rule.get("height", 0),
                        "minimized": bool(rule.get("minimized")),
                        "maximized": bool(rule.get("maximized")),
                        "hint": "Still remembered for the next time it opens",
                    }
                )
                continue
            status = "in_place" if mon and same_place(rule, win, mon) else "moved"
            hint = ""
            if status == "moved" and win.get("monitorLabel") != saved_name:
                hint = f"Saved on {saved_name}"
            rows.append(_live_row(win, rule["id"], status, hint))
        for win in unmatched:
            rows.append(_live_row(win, None, "new", ""))
    else:
        for win in live:
            rows.append(_live_row(win, None, "new", ""))

    rows.sort(key=lambda row: (_STATUS_ORDER.get(row["status"], 9), row.get("y") or 0, row.get("x") or 0))
    return {
        "monitors": monitors,
        "rows": rows,
        "layouts": [
            {
                "id": item["id"],
                "name": item["name"],
                "savedLabel": saved_label(item.get("savedAt", "")),
                "count": len(item.get("windows") or []),
                "active": item["id"] == active_id,
            }
            for item in data["layouts"]
        ],
        "activeLayoutId": active_id,
        "settings": {
            "placeOnOpen": bool(data["settings"].get("placeOnOpen")),
            "runAtStartup": bool(data["settings"].get("runAtStartup")),
            "theme": data["settings"].get("theme") or "ink",
            "hasDesktopShortcut": desktop_shortcut_exists(),
        },
        "activity": activity,
        "activityAt": activity_at,
    }


def _live_row(win: dict, rule_id: str | None, status: str, hint: str) -> dict:
    substantial = win.get("className") != "#32770" and (
        win.get("minimized") or (win["width"] >= 280 and win["height"] >= 180)
    )
    return {
        "key": f"saved:{rule_id}" if rule_id else f"live:{win['hwnd']}",
        "hwnd": str(win["hwnd"]),
        "ruleId": rule_id,
        "appName": win.get("appName") or "Window",
        "title": win.get("title") or "",
        "monitorLabel": win.get("monitorLabel") or "",
        "sizeLabel": _size_label(win["width"], win["height"], win.get("maximized"), win.get("minimized")),
        "status": status,
        "suggested": bool(substantial),
        "x": win["x"],
        "y": win["y"],
        "width": win["width"],
        "height": win["height"],
        "visX": win.get("visX", win["x"]),
        "visY": win.get("visY", win["y"]),
        "visWidth": win.get("visWidth", win["width"]),
        "visHeight": win.get("visHeight", win["height"]),
        "minimized": bool(win.get("minimized")),
        "maximized": bool(win.get("maximized")),
        "hint": hint,
    }


def _toast(moved: list[str], failed: list[str], already: int, missing: int, warnings: list[str]) -> str:
    if failed:
        return failed[0]
    if warnings and moved:
        return warnings[0]
    if len(moved) == 1:
        return f"Put {moved[0]} back."
    if len(moved) == 2:
        return f"Put {moved[0]} and {moved[1]} back."
    if len(moved) > 2:
        return f"Put {len(moved)} windows back."
    if already:
        return "Everything saved is already in place."
    if missing:
        return "Those saved apps aren't open right now."
    return "Nothing to move."
