"""워드마크 검사: 미세 차이는 허용하고 export 훼손은 거부한다."""
from __future__ import annotations

import contextlib
import io
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from tools.assets import build_wordmark as wordmark


class WordmarkCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        master = Image.open(wordmark.MASTER).convert("RGBA")
        for path, _, _ in wordmark.outputs(master):
            target = self.root / path.relative_to(wordmark.ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(path, target)
        self.small = self.root / "web/game/public/logo-wordmark-sm.png"

    def check(self, expected: int, message: str) -> None:
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(wordmark, "ROOT", self.root), patch.object(sys, "argv", ["wordmark", "--check"]):
            with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
                self.assertEqual(wordmark.main(), expected, stderr.getvalue())
        self.assertIn(message, stdout.getvalue() + stderr.getvalue())

    def test_committed_exports_pass(self) -> None:
        self.check(0, "wordmark check OK: 6 files")

    def test_small_channel_difference_is_allowed(self) -> None:
        image = Image.open(self.small).convert("RGBA")
        r, g, b, a = image.getpixel((86, 32))
        image.putpixel((86, 32), (r + 1 if r < 255 else r - 1, g, b, a))
        image.save(self.small)
        self.check(0, "wordmark check OK")

    def test_replaced_png_is_rejected(self) -> None:
        Image.new("RGBA", (172, 64), (255, 0, 0, 255)).save(self.small)
        self.check(1, "RGBA PSNR")

    def test_lost_transparency_is_rejected(self) -> None:
        image = Image.open(self.small).convert("RGBA")
        image.putalpha(255)
        image.save(self.small)
        self.check(1, "RGBA PSNR")

    def test_replaced_webp_is_rejected(self) -> None:
        path = self.root / "web/game/public/logo-wordmark.webp"
        Image.new("RGB", (840, 314), (12, 15, 14)).save(path, "WEBP")
        self.check(1, "PSNR")

    def test_wrong_dimensions_are_rejected(self) -> None:
        Image.new("RGBA", (171, 64)).save(self.small)
        self.check(1, "크기")

    def test_oversized_export_is_rejected(self) -> None:
        with self.small.open("ab") as output:
            output.write(b"\0" * wordmark.MAX_BYTES)
        self.check(1, "B > 100000 B")

    def test_missing_export_is_rejected(self) -> None:
        self.small.unlink()
        self.check(1, "없음")


if __name__ == "__main__":
    unittest.main()
