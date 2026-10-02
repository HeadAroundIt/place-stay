"""Saved-layout edits. No Windows calls, so the rules can be tested on their own."""

from __future__ import annotations

import uuid
from datetime import datetime

from place_stay.geom import monitor_for_point
from place_stay.match import pair_rules
from place_stay.names import app_name


def new_id() -> str:
    return uuid.uuid4().hex


def now_stamp() -> str:
    return datetime.now().isoformat(timespec="minutes")


def saved_label(stamp: str) -> str:
    try:
        when = datetime.fromisoformat(stamp)
    except ValueError:
        return "Saved"
    days = (datetime.now() - when).days
    if days <= 0:
        return "Saved today"
    if days == 1:
        return "Saved yesterday"
    return f"Saved {when.strftime('%b')} {when.day}"


def rule_from_window(win: dict, monitors: list[dict]) -> dict:
    cx = win["x"] + win["width"] / 2
    cy = win["y"] + win["height"] / 2
    mon = monitor_for_point(cx, cy, monitors)
    if mon is None and monitors:
        mon = monitors[0]
    if mon is None:
        rel_x, rel_y = int(win["x"]), int(win["y"])
        device, left, top, width, height = "", 0, 0, 0, 0
    else:
        rel_x = int(win["x"] - mon["left"])
        rel_y = int(win["y"] - mon["top"])
        device = mon["device"]
        left, top = int(mon["left"]), int(mon["top"])
        width, height = int(mon["width"]), int(mon["height"])
    process = win.get("process") or ""
    title = win.get("title") or ""
    return {
        "id": win.get("keepId") or new_id(),
        "process": process,
        "appName": win.get("appName") or app_name(process, title),
        "title": title,
        "className": win.get("className") or "",
        "monitorDevice": device,
        "monitorLeft": left,
        "monitorTop": top,
        "monitorWidth": width,
        "monitorHeight": height,
        "relX": rel_x,
        "relY": rel_y,
        "width": int(win["width"]),
        "height": int(win["height"]),
        "maximized": bool(win.get("maximized")),
        "minimized": bool(win.get("minimized")),
    }


def apply_edit(rules: list[dict], live_by_hwnd: dict[str, dict], monitors: list[dict], edit: dict) -> list[dict]:
    by_id = {rule["id"]: rule for rule in rules}
    forget = {str(item) for item in (edit.get("forget") or [])}
    keep = {str(item) for item in (edit.get("keep") or [])}
    updates = edit.get("update") or []
    out: list[dict] = []
    seen: set[str] = set()

    for item in updates:
        rule_id = str(item.get("ruleId") or "")
        hwnd = str(item.get("hwnd") or "")
        win = live_by_hwnd.get(hwnd)
        if not rule_id or not win or rule_id in forget:
            continue
        fresh = rule_from_window(win, monitors)
        fresh["id"] = rule_id
        out.append(fresh)
        seen.add(rule_id)

    for rule_id in keep:
        if rule_id in by_id and rule_id not in forget and rule_id not in seen:
            out.append(by_id[rule_id])
            seen.add(rule_id)

    for hwnd in edit.get("add") or []:
        win = live_by_hwnd.get(str(hwnd))
        if not win:
            continue
        out.append(rule_from_window(win, monitors))

    for rule in rules:
        if rule["id"] not in seen and rule["id"] not in forget:
            out.append(rule)
            seen.add(rule["id"])
    return out


def new_rules_for_hwnds(rules: list[dict], live_by_hwnd: dict[str, dict], monitors: list[dict], hwnds: list) -> list[dict]:
    """Windows that are open and not already matched to a saved spot."""
    lives = list(live_by_hwnd.values())
    pairs, _unmatched = pair_rules(rules, lives)
    matched = {str(win["hwnd"]) for _rule, win in pairs if win}
    added: list[dict] = []
    for hwnd in hwnds:
        win = live_by_hwnd.get(str(hwnd))
        if not win or str(win["hwnd"]) in matched:
            continue
        added.append(rule_from_window(win, monitors))
        matched.add(str(win["hwnd"]))
    return added


def unique_name(name: str, existing: list[str]) -> str:
    cleaned = " ".join((name or "").split())[:40] or "My desktop"
    taken = {item.casefold() for item in existing}
    if cleaned.casefold() not in taken:
        return cleaned
    number = 2
    while f"{cleaned} {number}".casefold() in taken:
        number += 1
    return f"{cleaned} {number}"
