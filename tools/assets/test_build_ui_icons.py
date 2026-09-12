from __future__ import annotations

import json
import unittest

from tools.assets import build_ui_icons as ui_icons

REQUIRED = {
    "dept-ops", "dept-nation", "dept-military", "dept-info", "dept-plaza", "dept-records",
    "hub-best-generals", "hub-emperor", "hub-generals", "hub-kingdoms", "hub-npcs", "hub-hall-of-fame", "hub-traffic",
    "cmd-ok", "cmd-need", "cmd-no", "cmd-sealed",
    "res-gold", "res-rice", "res-troops", "res-provisions",
    "search", "refresh", "close", "arrow-left", "arrow-right", "arrow-up", "arrow-down", "external", "filter",
    "auction", "dice", "diplomacy", "mail", "tools", "members",
}


class UiIconBuilderTest(unittest.TestCase):
    def test_every_required_icon_exists_with_a_distinct_path(self) -> None:
        icons = ui_icons.load_sources()
        names = {i["name"] for i in icons}
        self.assertTrue(REQUIRED <= names, REQUIRED - names)
        paths = [i["d"] for i in icons]
        self.assertEqual(len(paths), len(set(paths)), "같은 실루엣의 아이콘이 있다")

    def test_outputs_are_deterministic_and_currentcolor_only(self) -> None:
        icons = ui_icons.load_sources()
        first = ui_icons.outputs(icons)
        second = ui_icons.outputs(icons)
        self.assertEqual(first, second)
        sprite = first[ui_icons.EXPORT_DIRS[0] / "icons.svg"]
        for icon in icons:
            self.assertIn(f'id="ico-{icon["name"]}"', sprite)
        self.assertNotIn('fill="#', sprite)
        self.assertNotIn('stroke="#', sprite)
        manifest = json.loads(first[ui_icons.MANIFEST])
        self.assertEqual(len(icons), len(manifest["icons"]))
        self.assertEqual("0 0 20 20", manifest["viewBox"])

    def test_check_mode_passes_after_a_build(self) -> None:
        self.assertEqual(0, ui_icons.main([]))
        self.assertEqual(0, ui_icons.main(["--check"]))


if __name__ == "__main__":
    unittest.main()
