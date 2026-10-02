"""Pure geometry for monitors and saved window rectangles."""

from __future__ import annotations

PLACE_TOLERANCE = 32


def label_monitors(monitors: list[dict]) -> list[dict]:
    mons = [dict(m) for m in monitors]
    if not mons:
        return mons
    if len(mons) == 1:
        mons[0]["label"] = "Main screen"
        return mons

    span_x = max(m["left"] for m in mons) - min(m["left"] for m in mons)
    span_y = max(m["top"] for m in mons) - min(m["top"] for m in mons)
    horizontal = span_x >= span_y
    primary = next((m for m in mons if m.get("primary")), mons[0])

    for mon in mons:
        if mon is primary or mon.get("primary"):
            mon["label"] = "Main screen"
            continue
        if horizontal:
            center = mon["left"] + mon["width"] / 2
            primary_center = primary["left"] + primary["width"] / 2
            side = "Left" if center < primary_center else "Right"
        else:
            center = mon["top"] + mon["height"] / 2
            primary_center = primary["top"] + primary["height"] / 2
            side = "Top" if center < primary_center else "Bottom"
        mon["label"] = f"{side} screen"

    seen: dict[str, list[dict]] = {}
    for mon in mons:
        seen.setdefault(mon["label"], []).append(mon)
    for label, group in seen.items():
        if len(group) > 1:
            for index, mon in enumerate(group, start=1):
                mon["label"] = f"{label} {index}"
    return mons


def overlap(ax: int, ay: int, aw: int, ah: int, bx: int, by: int, bw: int, bh: int) -> int:
    left = max(ax, bx)
    top = max(ay, by)
    right = min(ax + aw, bx + bw)
    bottom = min(ay + ah, by + bh)
    if right <= left or bottom <= top:
        return 0
    return (right - left) * (bottom - top)


def center_on(rect: dict, mon: dict) -> bool:
    cx = rect["x"] + rect["width"] / 2
    cy = rect["y"] + rect["height"] / 2
    return (
        mon["left"] <= cx < mon["left"] + mon["width"]
        and mon["top"] <= cy < mon["top"] + mon["height"]
    )


def monitor_for_point(x: float, y: float, monitors: list[dict]) -> dict | None:
    for mon in monitors:
        if mon["left"] <= x < mon["left"] + mon["width"] and mon["top"] <= y < mon["top"] + mon["height"]:
            return mon
    best = None
    best_dist = None
    for mon in monitors:
        cx = mon["left"] + mon["width"] / 2
        cy = mon["top"] + mon["height"] / 2
        dist = abs(cx - x) + abs(cy - y)
        if best_dist is None or dist < best_dist:
            best = mon
            best_dist = dist
    return best


def resolve_monitor(rule: dict, monitors: list[dict]) -> tuple[dict | None, bool]:
    device = rule.get("monitorDevice") or ""
    for mon in monitors:
        if mon["device"] == device:
            return mon, True
    best = None
    best_area = 0
    for mon in monitors:
        area = overlap(
            int(rule.get("monitorLeft", 0)),
            int(rule.get("monitorTop", 0)),
            int(rule.get("monitorWidth", 0)),
            int(rule.get("monitorHeight", 0)),
            mon["left"],
            mon["top"],
            mon["width"],
            mon["height"],
        )
        if area > best_area:
            best = mon
            best_area = area
    if best is not None:
        return best, False
    primary = next((m for m in monitors if m.get("primary")), None)
    if primary is not None:
        return primary, False
    if monitors:
        return monitors[0], False
    return None, False


def clamp_rect(x: int, y: int, w: int, h: int, mon: dict) -> tuple[int, int, int, int]:
    w = max(240, min(int(w), int(mon["width"])))
    h = max(160, min(int(h), int(mon["height"])))
    min_x = mon["left"] + 80 - w
    max_x = mon["left"] + mon["width"] - 80
    min_y = mon["top"] - 8
    max_y = mon["top"] + mon["height"] - 80
    if min_x > max_x:
        x = mon["left"]
    else:
        x = min(max(int(x), min_x), max_x)
    if min_y > max_y:
        y = mon["top"]
    else:
        y = min(max(int(y), min_y), max_y)
    return x, y, w, h


def staging_rect(mon: dict) -> tuple[int, int, int, int]:
    left = int(mon["workLeft"])
    top = int(mon["workTop"])
    right = int(mon["workRight"])
    bottom = int(mon["workBottom"])
    if right - left < 200 or bottom - top < 200:
        left = int(mon["left"])
        top = int(mon["top"])
        right = int(mon["left"]) + int(mon["width"])
        bottom = int(mon["top"]) + int(mon["height"])
    width = max(240, min(720, right - left - 48))
    height = max(180, min(480, bottom - top - 48))
    return left + 24, top + 24, width, height


def same_place(rule: dict, live: dict, mon: dict) -> bool:
    rule_min = bool(rule.get("minimized"))
    live_min = bool(live.get("minimized"))
    if rule_min or live_min:
        return rule_min and live_min
    if rule.get("maximized") or live.get("maximized"):
        return bool(rule.get("maximized") and live.get("maximized") and center_on(live, mon))
    x = int(mon["left"]) + int(rule.get("relX", 0))
    y = int(mon["top"]) + int(rule.get("relY", 0))
    return (
        abs(int(live["x"]) - x) <= PLACE_TOLERANCE
        and abs(int(live["y"]) - y) <= PLACE_TOLERANCE
        and abs(int(live["width"]) - int(rule.get("width", 0))) <= PLACE_TOLERANCE
        and abs(int(live["height"]) - int(rule.get("height", 0))) <= PLACE_TOLERANCE
    )


def fit_window_bounds(bounds: dict | None, monitors: list[dict], fallback: tuple[int, int, int, int]) -> tuple[int, int, int, int]:
    fx, fy, fw, fh = fallback
    if not bounds or not monitors:
        return fx, fy, fw, fh
    try:
        x = int(bounds["x"])
        y = int(bounds["y"])
        w = int(bounds["width"])
        h = int(bounds["height"])
    except (KeyError, TypeError, ValueError):
        return fx, fy, fw, fh
    if w < 400 or h < 320:
        return fx, fy, fw, fh
    if monitor_for_point(x + w / 2, y + h / 2, monitors) is None:
        return fx, fy, fw, fh
    return x, y, w, h
