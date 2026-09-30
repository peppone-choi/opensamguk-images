#!/usr/bin/env python3
"""Source-free invariants for the committed Waryong battle board kit."""

import gzip
import hashlib
import json
import runpy
import unittest
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "waryong" / "battle" / "kit"


def load(name, shape):
    raw = (BASE / name).read_bytes()
    data = gzip.decompress(raw) if name.endswith(".gz") else raw
    return data, np.frombuffer(data, np.uint8).reshape(shape)


class WaryongBattleKitTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.kit = json.loads((BASE / "kit.json").read_text())
        cls.tool = runpy.run_path(str(ROOT / "tools" / "build-waryong-battle-kit.py"))

    def test_files_match_recorded_content(self):
        for name, meta in self.kit["files"].items():
            data, array = load(name, meta["shape"])
            self.assertEqual(meta["contentSha256"], hashlib.sha256(data).hexdigest(), name)

    def test_records_point_at_pieces(self):
        _, records = load("records.bin", [3, 256, 8])
        _, pieces = load("pieces.bin.gz", [3, 256, 16, 32])
        _, boards = load("boards.bin.gz", [214, 64, 64])
        self.assertTrue((pieces[:, 0] == 255).all())  # 조각 0은 비어 있다
        for board in self.kit["boards"]:
            ts = board["tileset"]
            used = np.unique(boards[board["id"]])
            self.assertTrue((records[ts, used, 0] > 0).all(), board["id"])
            layout = hashlib.sha256(bytes([ts]) + boards[board["id"]].tobytes()).hexdigest()
            self.assertEqual(board["layoutSha256"], layout, board["id"])

    def test_composed_boards_match_recorded_hash(self):
        _, records = load("records.bin", [3, 256, 8])
        _, pieces = load("pieces.bin.gz", [3, 256, 16, 32])
        _, boards = load("boards.bin.gz", [214, 64, 64])
        for board_id in (0, 40, 192, 209):  # 타일셋 3벌 · 성새 · 배
            board = self.kit["boards"][board_id]
            canvas = self.tool["compose"](records, pieces, board["tileset"], boards[board_id])
            self.assertEqual(list(canvas.shape[::-1]), self.kit["layout"]["canvas"])
            self.assertEqual(board["composedSha256"], hashlib.sha256(canvas.tobytes()).hexdigest(), board_id)

    def test_record_classes_match_server_catalog(self):
        catalog = json.loads((ROOT / "waryong" / "battle" / "catalog-v1.json").read_text())
        _, boards = load("boards.bin.gz", [214, 64, 64])
        classes = self.kit["recordClass"]
        self.assertEqual([256] * 3, [len(c) for c in classes])
        for board in catalog["boards"]:
            ts = board["tileset"]
            rows = "".join(classes[ts][rid] for rid in boards[board["id"]].ravel().tolist())
            self.assertEqual("".join(board["terrainRows"]), rows, board["id"])
            self.assertEqual(self.kit["boards"][board["id"]]["terrainSha256"], hashlib.sha256(rows.encode("ascii")).hexdigest())

    def test_unit_roles_only_on_template_pixels(self):
        _, units = load("units.bin.gz", [360, 16, 32])
        _, roles = load("unit-roles.bin.gz", [180, 16, 32])
        self.assertTrue(set(np.unique(roles).tolist()) <= {0, 1, 2, 3, 4})
        self.assertTrue((roles[units[:180] == 255] == 0).all())
        self.assertTrue((roles[:152] == 1).sum() > 0)

    def test_structures_are_marked_unknown(self):
        self.assertEqual("UNKNOWN", self.kit["structures"]["status"])


if __name__ == "__main__":
    unittest.main()
