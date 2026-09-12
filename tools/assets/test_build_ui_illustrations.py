from __future__ import annotations

import json
import unittest

from tools.assets import build_ui_illustrations as ill

REQUIRED = {"records-empty", "posts-empty", "map-pending"}


class UiIllustrationBuilderTest(unittest.TestCase):
    def test_required_set_two_colors_and_distinct_bodies(self) -> None:
        items = ill.load_sources()
        self.assertTrue(REQUIRED <= {i["name"] for i in items})
        bodies = [i["body"] for i in items]
        self.assertEqual(len(bodies), len(set(bodies)))
        for i in items:
            colors = {c.lower() for c in ill._COLOR.findall(i["body"])}
            self.assertTrue(colors <= ill.ALLOWED_COLORS, i["name"])
            self.assertEqual(2, len(colors), f"{i['name']} 는 2색이어야 한다")

    def test_outputs_deterministic_and_manifest_complete(self) -> None:
        items = ill.load_sources()
        self.assertEqual(ill.outputs(items), ill.outputs(items))
        manifest = json.loads(ill.outputs(items)[ill.MANIFEST])
        self.assertEqual(len(items), len(manifest["illustrations"]))

    def test_check_passes_after_build(self) -> None:
        self.assertEqual(0, ill.main([]))
        self.assertEqual(0, ill.main(["--check"]))


if __name__ == "__main__":
    unittest.main()
