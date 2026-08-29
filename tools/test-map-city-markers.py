#!/usr/bin/env python3
"""Contract tests for the generated Han map city markers."""

from pathlib import Path
import unittest

from PIL import Image


ROOT = Path(__file__).resolve().parents[1]
MARKERS = ROOT / "exports" / "map" / "markers"


class MapCityMarkerTest(unittest.TestCase):
    def test_markers_have_expected_canvas_and_transparency(self) -> None:
        expected = {
            "county.png": (28, 32),
            "commandery.png": (36, 40),
            "capital.png": (44, 48),
        }

        for filename, size in expected.items():
            with self.subTest(filename=filename):
                with Image.open(MARKERS / filename) as image:
                    self.assertEqual(image.mode, "RGBA")
                    self.assertEqual(image.size, size)
                    self.assertEqual(image.getpixel((0, 0))[3], 0)
                    self.assertGreater(image.getbbox()[2] - image.getbbox()[0], size[0] // 2)

    def test_marker_footprints_grow_by_administrative_tier(self) -> None:
        footprints = []
        for filename in ("county.png", "commandery.png", "capital.png"):
            with Image.open(MARKERS / filename) as image:
                alpha = image.getchannel("A")
                footprints.append(sum(alpha.histogram()[1:]))

        self.assertLess(footprints[0], footprints[1])
        self.assertLess(footprints[1], footprints[2])


if __name__ == "__main__":
    unittest.main()
