"""Match saved windows to the ones currently open.

Same app, even when the title changed (a browser tab, for example). Extra
windows of that app are left alone, so opening something new does not steal a
saved spot.
"""

from __future__ import annotations


def _norm(value: str) -> str:
    return " ".join((value or "").casefold().split())


def _title_points(saved: str, live: str) -> int:
    a = _norm(saved)
    b = _norm(live)
    if not a or not b:
        return 0
    if a == b:
        return 100
    if a in b or b in a:
        return 55
    aw = {word for word in a.split() if len(word) > 2}
    bw = {word for word in b.split() if len(word) > 2}
    if not aw or not bw:
        return 0
    return int(40 * len(aw & bw) / max(len(aw), len(bw)))


def _position_points(rule: dict, live: dict) -> int:
    if "x" not in live or "y" not in live:
        return 0
    left = int(rule.get("monitorLeft", 0)) + int(rule.get("relX", 0))
    top = int(rule.get("monitorTop", 0)) + int(rule.get("relY", 0))
    dist = abs(int(live["x"]) - left) + abs(int(live["y"]) - top)
    return max(0, 36 - dist // 100)


def score_pair(rule: dict, live: dict) -> int:
    score = _title_points(rule.get("title", ""), live.get("title", ""))
    score += _position_points(rule, live)
    saved_class = rule.get("className") or ""
    live_class = live.get("className") or ""
    if saved_class and saved_class == live_class:
        score += 8
    return score


def pair_rules(rules: list[dict], lives: list[dict]) -> tuple[list[tuple[dict, dict | None]], list[dict]]:
    grouped_rules: dict[str, list[tuple[int, dict]]] = {}
    grouped_lives: dict[str, list[tuple[int, dict]]] = {}
    for index, rule in enumerate(rules):
        grouped_rules.setdefault((rule.get("process") or "").casefold(), []).append((index, rule))
    for index, live in enumerate(lives):
        grouped_lives.setdefault((live.get("process") or "").casefold(), []).append((index, live))

    assigned: dict[int, dict] = {}
    used_lives: set[int] = set()

    for process, rule_items in grouped_rules.items():
        live_items = grouped_lives.get(process, [])
        candidates: list[tuple[int, int, int]] = []
        for rule_index, rule in rule_items:
            for live_index, live in live_items:
                candidates.append((score_pair(rule, live), rule_index, live_index))
        candidates.sort(key=lambda item: (-item[0], item[1], item[2]))
        taken_rules: set[int] = set()
        taken_lives: set[int] = set()
        for _score, rule_index, live_index in candidates:
            if rule_index in taken_rules or live_index in taken_lives:
                continue
            assigned[rule_index] = lives[live_index]
            taken_rules.add(rule_index)
            taken_lives.add(live_index)
            used_lives.add(live_index)

    pairs = [(rule, assigned.get(index)) for index, rule in enumerate(rules)]
    unmatched = [live for index, live in enumerate(lives) if index not in used_lives]
    return pairs, unmatched
