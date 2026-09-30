#!/usr/bin/env python3
"""Source-free invariants for the committed Waryong strategic-map derivatives."""

import gzip
import hashlib
import json
import os
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
BASE = ROOT / "waryong" / "map"


def load(name):
    return np.array(Image.open(BASE / name))


def kit_cell(packed, index, columns):
    row, col = divmod(index, columns)
    return packed[row * 16 : (row + 1) * 16, col * 16 : (col + 1) * 16]


class WaryongMapAssetsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.catalog = json.loads((BASE / "catalog.json").read_text())

    def test_images_match_catalog_pixels(self):
        images = self.catalog["images"]
        committed = sorted(p.name for p in BASE.glob("*.png"))
        self.assertEqual(sorted(images), committed)
        for name, meta in images.items():
            pixels = load(name)
            self.assertEqual(meta["size"], [pixels.shape[1], pixels.shape[0]], name)
            self.assertEqual(meta["pixelSha256"], hashlib.sha256(np.ascontiguousarray(pixels).tobytes()).hexdigest(), name)

    def test_kit_encoding_and_roles(self):
        kit = self.catalog["kit"]
        columns = self.catalog["atlasColumns"]
        packed = load("kit-index.png")
        self.assertEqual(788, kit["count"])
        self.assertEqual(list(range(kit["count"])), [entry["id"] for entry in kit["entries"]])
        self.assertTrue(((packed >> 4) <= 2).all())  # 역할은 0 · 1 · 2뿐
        roofs = set(kit["lookup"]["roofTiles"])
        self.assertEqual({0xCD, 0xD0, 0xD3}, roofs)
        for entry in kit["entries"]:
            cell = kit_cell(packed, entry["id"], columns)
            roles = set(np.unique(cell >> 4).tolist())
            if entry["id"] in roofs:
                self.assertIn(1, roles, entry)  # 주색은 늘 있다. 0xD3 문루는 그늘 칸이 없다
                self.assertTrue(roles <= {0, 1, 2}, entry)
            else:
                self.assertEqual({0}, roles, entry)
        for entry in kit["entries"][:256]:
            self.assertEqual({"op": "original", "tile": entry["id"]}, entry["recipe"])
        for mip in kit["mips"]:
            pixels = load(f"kit-mip{mip}.png")
            self.assertEqual(columns * mip, pixels.shape[1])

    def test_lookup_points_into_kit(self):
        kit = self.catalog["kit"]
        lookup = kit["lookup"]
        for group in ("river", "road"):
            for mask, index in lookup[group].items():
                self.assertLess(index, kit["count"], (group, mask))
        self.assertEqual(set("NES NSW NEW ESW NESW NS EW NE NW ES SW E W S N".split()), set(lookup["river"]))
        for name, table in lookup["variants"].items():
            for base, index in table.items():
                recipe = kit["entries"][index]["recipe"]
                self.assertEqual({"op": "palette", "base": int(base), "table": name}, recipe)
                self.assertNotIn(int(base), lookup["roofTiles"])

    def test_statistics_content(self):
        stats_meta = self.catalog["statistics"]
        raw = gzip.decompress((BASE / stats_meta["file"]).read_bytes())
        self.assertEqual(stats_meta["contentSha256"], hashlib.sha256(raw).hexdigest())
        stats = json.loads(raw)
        self.assertEqual(["full", "n4", "c", "cls8", "c4", "c1"], stats["order"])
        for group in ("terrain", "facet"):
            for name in stats["order"]:
                table = stats[group][name]
                self.assertTrue(table, (group, name))
                for key, counts in table.items():
                    self.assertTrue(all(0 <= tile < 256 and n > 0 for tile, n in counts), (group, name, key))
        self.assertEqual(256, len(stats["tileClass"]))
        self.assertEqual({"T", "S", "E", "P"}, {facet for _, facet in stats["tileFacet"]})

    def test_sprites(self):
        markers = load("markers.png")
        self.assertEqual((17 * 16, 16 * 16, 4), markers.shape)
        roles = load("markers-roles.png")
        self.assertTrue(set(np.unique(roles).tolist()) <= {0, 1, 3})
        flags, flag_roles = load("flags.png"), load("flags-roles.png")
        self.assertEqual((16, 32, 4), flags.shape)
        self.assertTrue((flag_roles[flags[..., 3] == 0] == 0).all())
        sites, site_roles = load("sites.png"), load("sites-roles.png")
        self.assertEqual(["county", "ferry", "fort", "tribe"], self.catalog["sites"]["order"])
        self.assertEqual((16, 64, 4), sites.shape)
        for n in range(4):
            cell_roles = site_roles[:, n * 16 : (n + 1) * 16]
            self.assertTrue((cell_roles == 1).any(), f"site {n} has no nation colour")
            self.assertTrue((cell_roles[sites[:, n * 16 : (n + 1) * 16, 3] == 0] == 0).all())

    def test_original_boundary(self):
        originals = {"MMAP.MDL", "MMAP.MAP", "MMAP.MCH", "GAMEPAL.BRG"}
        for directory, subdirs, files in os.walk(ROOT):
            subdirs[:] = [name for name in subdirs if name != ".git"]
            self.assertFalse(originals.intersection(name.upper() for name in files), directory)
        boundaries = json.loads((ROOT / ".license-boundaries.json").read_text())
        waryong = next(entry for entry in boundaries["entries"] if entry["path"] == "waryong")
        self.assertEqual("owner-accepted", waryong["classification"])
        self.assertFalse(list((ROOT / "previews").glob("**/*waryong*")))


if __name__ == "__main__":
    unittest.main()
