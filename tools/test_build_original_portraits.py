from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from build_original_portraits import build


class OriginalPortraitBuilderTest(unittest.TestCase):
    def test_builds_all_three_variants_with_exact_dimensions(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            Image.new("RGB", (400, 300), (90, 70, 50)).save(source / "sheet.png")
            manifest = {
                "sheet": {"columns": 4, "rows": 3, "source": "source/sheet.png"},
                "portraits": [{"id": f"p{i:02d}", "name": str(i), "cell": i} for i in range(12)],
            }
            path = root / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")

            outputs = build(path)

            self.assertEqual(len(outputs), 36)
            for variant, size in {"full": (148, 210), "bust": (148, 210), "face": (96, 96)}.items():
                with Image.open(root / variant / "p00.png") as image:
                    self.assertEqual(image.size, size)

    def test_rejects_incomplete_cell_binding(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source"
            source.mkdir()
            Image.new("RGB", (400, 300)).save(source / "sheet.png")
            path = root / "manifest.json"
            path.write_text(json.dumps({
                "sheet": {"columns": 4, "rows": 3, "source": "source/sheet.png"},
                "portraits": [],
            }), encoding="utf-8")

            with self.assertRaisesRegex(ValueError, "exactly one portrait"):
                build(path)


if __name__ == "__main__":
    unittest.main()
