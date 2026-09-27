#!/usr/bin/env python3
"""Source-free invariants for the committed Waryong derivative catalog."""

import json
import os
import runpy
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "waryong" / "battle"


class WaryongBattleAssetsTest(unittest.TestCase):
    def test_export_inventory_rejects_missing_and_stale_files(self):
        builder = runpy.run_path(str(ROOT / "tools" / "build-waryong-battle-assets.py"))
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "source"
            committed = Path(temp) / "committed"
            source.mkdir()
            committed.mkdir()
            with self.assertRaisesRegex(SystemExit, "units are empty"):
                builder["required_unit_names"]("red", source)
            (source / "unit.png").touch()
            expected = builder["required_unit_names"]("red", source)
            with self.assertRaisesRegex(SystemExit, "missing=1"):
                builder["require_names"]("committed red units", builder["png_names"](committed), expected)
            (committed / "unit.png").touch()
            (committed / "stale.png").touch()
            with self.assertRaisesRegex(SystemExit, "extra=1"):
                builder["require_names"]("committed red units", builder["png_names"](committed), expected)

    def test_board_inventory_and_terrain(self):
        catalog = json.loads((BASE / "catalog-v1.json").read_text())
        boards = catalog["boards"]
        self.assertEqual(214, len(boards))
        self.assertEqual(list(range(214)), [board["id"] for board in boards])
        self.assertEqual(188, sum(board["kind"] == "FORTRESS" for board in boards))
        self.assertEqual(26, sum(board["kind"] == "FIELD" for board in boards))
        for board in boards:
            terrain = "".join(board["terrainRows"])
            self.assertEqual(64, len(board["terrainRows"]))
            self.assertTrue(all(len(row) == 64 for row in board["terrainRows"]))
            self.assertEqual(4096, len(terrain))
            self.assertEqual(set(terrain) <= set("PFMRW"), True)
            self.assertEqual(4096, sum(board["terrainCounts"].values()))
            self.assertEqual(board["kind"] == "FORTRESS", "W" in terrain)
            self.assertTrue((BASE / board["image"]).is_file())
        for board_id in (38, 48):  # wooden stockades also count as fortress walls
            self.assertEqual("FORTRESS", boards[board_id]["kind"])
        for board_id in (64, 75, 125, 154, 192):
            self.assertEqual("FIELD", boards[board_id]["kind"])
        for board_id in range(209, 213):
            self.assertFalse(boards[board_id]["landEligible"])

    def test_units_and_original_boundary(self):
        for side in ("red", "blue"):
            self.assertEqual(82, len(list((BASE / "units" / side).glob("*.png"))))
        originals = {"BATTLE.MAP", "BATTLE.MDL", "BATTLE.SCH"}
        for directory, subdirs, files in os.walk(ROOT):
            subdirs[:] = [name for name in subdirs if name != ".git"]
            self.assertFalse(originals.intersection(name.upper() for name in files), directory)


if __name__ == "__main__":
    unittest.main()
