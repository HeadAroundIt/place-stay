import struct
import tempfile
import unittest
from pathlib import Path

from place_stay.iconimg import SIZES, draw, save_icon
from place_stay.paths import frozen, launch_args
from place_stay.geom import (
    clamp_rect,
    label_monitors,
    monitor_for_point,
    resolve_monitor,
    same_place,
)
from place_stay.layouts import apply_edit, new_rules_for_hwnds, rule_from_window, unique_name
from place_stay.match import pair_rules


LEFT = {
    "device": r"\\.\DISPLAY1",
    "left": -1080,
    "top": -123,
    "width": 1080,
    "height": 1920,
    "workLeft": -1080,
    "workTop": -123,
    "workRight": 0,
    "workBottom": 1757,
    "primary": False,
}
MAIN = {
    "device": r"\\.\DISPLAY2",
    "left": 0,
    "top": 0,
    "width": 2560,
    "height": 1440,
    "workLeft": 0,
    "workTop": 0,
    "workRight": 2560,
    "workBottom": 1400,
    "primary": True,
}


class GeomTests(unittest.TestCase):
    def test_labels_match_this_desk(self):
        labeled = label_monitors([LEFT, MAIN])
        by_device = {mon["device"]: mon["label"] for mon in labeled}
        self.assertEqual(by_device[LEFT["device"]], "Left screen")
        self.assertEqual(by_device[MAIN["device"]], "Main screen")

    def test_discord_sits_on_the_left_screen(self):
        labeled = label_monitors([dict(LEFT), dict(MAIN)])
        mon = monitor_for_point(-1059 + 521, 949 + 364, labeled)
        self.assertEqual(mon["label"], "Left screen")

    def test_missing_screen_falls_back_by_overlap(self):
        rule = {
            "monitorDevice": r"\\.\DISPLAY9",
            "monitorLeft": 0,
            "monitorTop": 0,
            "monitorWidth": 2560,
            "monitorHeight": 1440,
        }
        mon, exact = resolve_monitor(rule, [LEFT, MAIN])
        self.assertFalse(exact)
        self.assertEqual(mon["device"], MAIN["device"])

    def test_same_place_allows_a_little_jitter(self):
        rule = {"relX": 100, "relY": 80, "width": 800, "height": 600, "maximized": False, "minimized": False}
        live = {"x": 120, "y": 90, "width": 810, "height": 590, "maximized": False, "minimized": False}
        self.assertTrue(same_place(rule, live, MAIN))
        live["x"] = 400
        self.assertFalse(same_place(rule, live, MAIN))

    def test_clamp_keeps_a_window_on_the_left_screen(self):
        x, y, w, h = clamp_rect(-4000, -4000, 700, 500, LEFT)
        self.assertGreaterEqual(x + w, LEFT["left"] + 80)
        self.assertLess(x, LEFT["left"] + LEFT["width"])
        self.assertEqual((w, h), (700, 500))


class MatchTests(unittest.TestCase):
    def test_titles_keep_two_windows_from_swapping(self):
        rules = [
            {"process": "chrome.exe", "title": "Mail", "className": "Chrome", "monitorLeft": 0, "monitorTop": 0, "relX": 10, "relY": 10},
            {"process": "chrome.exe", "title": "Maps", "className": "Chrome", "monitorLeft": 0, "monitorTop": 0, "relX": 900, "relY": 10},
        ]
        lives = [
            {"process": "chrome.exe", "title": "Maps - today", "className": "Chrome", "x": 20, "y": 20},
            {"process": "chrome.exe", "title": "Mail - Inbox", "className": "Chrome", "x": 880, "y": 30},
        ]
        pairs, unmatched = pair_rules(rules, lives)
        self.assertEqual(pairs[0][1]["title"], "Mail - Inbox")
        self.assertEqual(pairs[1][1]["title"], "Maps - today")
        self.assertEqual(unmatched, [])

    def test_extra_window_is_left_alone(self):
        rules = [{"process": "brave.exe", "title": "Docs", "className": "Chrome", "monitorLeft": 0, "monitorTop": 0, "relX": 0, "relY": 0}]
        lives = [
            {"process": "brave.exe", "title": "Docs", "className": "Chrome", "x": 0, "y": 0},
            {"process": "brave.exe", "title": "Video", "className": "Chrome", "x": 400, "y": 0},
        ]
        pairs, unmatched = pair_rules(rules, lives)
        self.assertEqual(pairs[0][1]["title"], "Docs")
        self.assertEqual([item["title"] for item in unmatched], ["Video"])

    def test_changed_title_still_pairs_the_only_window(self):
        rules = [{"process": "discord.exe", "title": "Old server", "className": "Chrome", "monitorLeft": -1080, "monitorTop": -123, "relX": 20, "relY": 40}]
        lives = [{"process": "discord.exe", "title": "A brand new title", "className": "Chrome", "x": -1000, "y": 80}]
        pairs, _unmatched = pair_rules(rules, lives)
        self.assertIs(pairs[0][1], lives[0])

    def test_different_apps_never_pair(self):
        rules = [{"process": "chrome.exe", "title": "Hello", "className": "A", "monitorLeft": 0, "monitorTop": 0, "relX": 0, "relY": 0}]
        lives = [{"process": "notepad.exe", "title": "Hello", "className": "A", "x": 0, "y": 0}]
        pairs, unmatched = pair_rules(rules, lives)
        self.assertIsNone(pairs[0][1])
        self.assertEqual(unmatched, lives)


class LayoutTests(unittest.TestCase):
    def test_update_refreshes_open_windows_and_keeps_closed_ones(self):
        rules = [
            {"id": "a", "process": "notepad.exe", "title": "Notes", "width": 100, "height": 100},
            {"id": "b", "process": "steam.exe", "title": "Steam", "width": 50, "height": 50},
        ]
        live = {
            "9": {
                "hwnd": 9,
                "process": "notepad.exe",
                "title": "Notes",
                "className": "Notepad",
                "appName": "Notepad",
                "x": 200,
                "y": 160,
                "width": 640,
                "height": 480,
                "maximized": False,
                "minimized": False,
            }
        }
        updated = apply_edit(
            rules,
            live,
            [MAIN],
            {"update": [{"ruleId": "a", "hwnd": "9"}], "keep": ["b"], "add": [], "forget": []},
        )
        by_id = {rule["id"]: rule for rule in updated}
        self.assertEqual(by_id["a"]["width"], 640)
        self.assertEqual(by_id["a"]["relX"], 200)
        self.assertEqual(by_id["b"]["title"], "Steam")

    def test_add_and_forget(self):
        live = {
            "4": {
                "process": "notepad.exe",
                "title": "Untitled",
                "className": "Notepad",
                "x": 10,
                "y": 20,
                "width": 300,
                "height": 200,
                "maximized": False,
                "minimized": False,
            }
        }
        updated = apply_edit(
            [{"id": "old", "title": "Gone"}],
            live,
            [MAIN],
            {"update": [], "keep": [], "add": ["4"], "forget": ["old"]},
        )
        self.assertEqual(len(updated), 1)
        self.assertEqual(updated[0]["appName"], "Notepad")

    def test_second_window_of_the_same_app_can_be_added(self):
        rules = [{
            "id": "mail",
            "process": "chrome.exe",
            "title": "Mail",
            "className": "Chrome",
            "monitorLeft": 0,
            "monitorTop": 0,
            "relX": 10,
            "relY": 10,
        }]
        mail = {
            "hwnd": 1,
            "process": "chrome.exe",
            "title": "Mail - Inbox",
            "className": "Chrome",
            "appName": "Chrome",
            "x": 20,
            "y": 20,
            "width": 800,
            "height": 600,
            "maximized": False,
            "minimized": False,
        }
        maps = {
            "hwnd": 2,
            "process": "chrome.exe",
            "title": "Maps",
            "className": "Chrome",
            "appName": "Chrome",
            "x": 900,
            "y": 40,
            "width": 700,
            "height": 500,
            "maximized": False,
            "minimized": False,
        }
        live = {"1": mail, "2": maps}
        self.assertEqual(new_rules_for_hwnds(rules, live, [MAIN], ["1"]), [])
        added = new_rules_for_hwnds(rules, live, [MAIN], ["2"])
        self.assertEqual(len(added), 1)
        self.assertEqual(added[0]["title"], "Maps")
        self.assertEqual(added[0]["relX"], 900)

    def test_rule_uses_the_screen_under_the_window(self):
        rule = rule_from_window(
            {
                "process": "discord.exe",
                "title": "Chat",
                "className": "Chrome",
                "x": -1000,
                "y": 100,
                "width": 800,
                "height": 600,
                "maximized": False,
                "minimized": False,
            },
            label_monitors([dict(LEFT), dict(MAIN)]),
        )
        self.assertEqual(rule["monitorDevice"], LEFT["device"])
        self.assertEqual(rule["relX"], 80)

    def test_unique_names(self):
        self.assertEqual(unique_name("Work", ["Work"]), "Work 2")
        self.assertEqual(unique_name("  ", []), "My desktop")


class IconTests(unittest.TestCase):
    def test_icon_file_has_the_taskbar_sizes(self):
        image = draw(32)
        self.assertEqual(image.size, (32, 32))
        self.assertGreater(image.getextrema()[-1][1], 0)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "icon.ico"
            save_icon(path)
            data = path.read_bytes()
        _reserved, kind, count = struct.unpack_from("<HHH", data)
        self.assertEqual((_reserved, kind), (0, 1))
        self.assertEqual(count, len(SIZES))


class PathTests(unittest.TestCase):
    def test_source_launch_uses_the_module(self):
        self.assertFalse(frozen())
        self.assertEqual(launch_args(background=False), "-m place_stay")
        self.assertEqual(launch_args(background=True), "-m place_stay --background")


if __name__ == "__main__":
    unittest.main()
