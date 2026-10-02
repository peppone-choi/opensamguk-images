"""인장 아이콘 검사: 압축 바이트 차이는 허용하고 픽셀 훼손 · 빠진 파일 · 낙관 상자 변화는 거부한다."""
from __future__ import annotations

import contextlib
import io
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools.assets import build_seal_icons as seal


class SealIconCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        master = Image.open(seal.MASTER).convert("RGBA")
        for path in seal.outputs(master):
            target = self.root / path.relative_to(seal.ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        self.icon = self.root / "web/game/app/icon.png"

    def check(self, expected: int, message: str) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(seal, "ROOT", self.root):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(seal.main(["--check"]), expected, stderr.getvalue())
        self.assertIn(message, stdout.getvalue() + stderr.getvalue())

    def test_committed_exports_pass(self) -> None:
        self.check(0, "seal icons check OK: 6 files pixel-match")

    def test_other_compression_bytes_are_allowed(self) -> None:
        image = Image.open(self.icon)
        image.load()
        before = self.icon.read_bytes()
        image.save(self.icon, format="PNG", compress_level=1)
        self.assertNotEqual(before, self.icon.read_bytes())  # 바이트는 달라졌다
        self.check(0, "seal icons check OK")

    def test_one_changed_pixel_is_rejected(self) -> None:
        image = Image.open(self.icon).convert("RGB")
        r, g, b = image.getpixel((0, 0))
        image.putpixel((0, 0), (r + 1, g, b))
        image.save(self.icon)
        self.check(1, "DRIFT: web/game/app/icon.png")

    def test_replaced_favicon_is_rejected(self) -> None:
        path = self.root / "web/gateway/app/favicon.ico"
        Image.new("RGB", (48, 48), (255, 0, 0)).save(path, format="ICO", sizes=list(seal.ICO_SIZES))
        self.check(1, "DRIFT: web/gateway/app/favicon.ico")

    def test_missing_file_is_rejected(self) -> None:
        (self.root / "web/game/app/apple-icon.png").unlink()
        self.check(1, "DRIFT: web/game/app/apple-icon.png")


class SealBoundsTests(unittest.TestCase):
    def test_seal_box_is_the_native_crop(self) -> None:
        x0, y0, x1, y1 = seal.seal_bounds(Image.open(seal.MASTER).convert("RGBA"))
        self.assertEqual((x1 - x0 + 1, y1 - y0 + 1), (104, 167))

    def test_tile_sizes(self) -> None:
        master = Image.open(seal.MASTER).convert("RGBA")
        self.assertEqual(seal.build_seal_tile(master, seal.PAD_RATIO_ICON).size, (241, 241))
        self.assertEqual(seal.build_seal_tile(master, seal.PAD_RATIO_FAVICON).size, (193, 193))


if __name__ == "__main__":
    unittest.main()
