#!/usr/bin/env python3
"""Check reproducible, bounded regional city exports at every source scale."""
from __future__ import annotations

import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from build_regional_city_icons import BASE, LEVELS, STYLES, palette_from_file


class RegionalCityIconsTest(unittest.TestCase):
    def test_complete_palette_and_alpha_contract(self) -> None:
        palette = {tuple(rgb) for rgb in palette_from_file(BASE / 'palette.json')}
        for style in STYLES:
            for level in LEVELS:
                for scale in (1, 2, 4, 8):
                    path = BASE / 'processed/regional' / style / f'{scale}x/cast_{level}.png'
                    self.assertTrue(path.is_file(), str(path))
                    image = Image.open(path).convert('RGBA')
                    self.assertEqual(image.size, (32 * scale, 32 * scale), str(path))
                    rgba = np.asarray(image)
                    alpha = rgba[:, :, 3]
                    self.assertTrue(set(np.unique(alpha)).issubset({0, 255}), str(path))
                    self.assertTrue(np.all(rgba[alpha == 0, :3] == 0), str(path))
                    self.assertTrue(set(map(tuple, rgba[alpha == 255, :3].reshape(-1, 3))).issubset(palette), str(path))
                    bounds = image.getchannel('A').getbbox()
                    self.assertIsNotNone(bounds, str(path))
                    left, top, right, bottom = bounds
                    self.assertGreaterEqual(min(left, top, image.width - right, image.height - bottom), 1, str(path))
                    for app in ('game', 'gateway'):
                        exported = BASE.parents[1] / 'web' / app / 'public/city/regional' / style / f'{scale}x/cast_{level}.png'
                        self.assertEqual(path.read_bytes(), exported.read_bytes(), str(exported))

    def test_large_exports_use_their_own_resolution(self) -> None:
        # A 4x/8x export must not be a coarser grid repeated in blocks. Every
        # coarser grid that fits 128/256 is a multiple of 2, so the effective
        # resolution equals the file resolution iff the 2x2 block test fails.
        for style in STYLES:
            for level in LEVELS:
                for scale in (4, 8):
                    rgba = np.asarray(Image.open(BASE / 'processed/regional' / style / f'{scale}x/cast_{level}.png'))
                    upscaled = np.repeat(np.repeat(rgba[::2, ::2], 2, 0), 2, 1)
                    self.assertFalse(np.array_equal(rgba, upscaled),
                                     f'{style}/{scale}x/cast_{level}: nearest upscale of a coarser grid')

    def test_large_exports_keep_the_2x_footprint(self) -> None:
        # HanMapCanvas places every variant with the 64px marker spec (anchor
        # 32/63) and the per-level visual extent. Scaled back to 64, the 4x/8x
        # silhouette width, horizontal centre and baseline must sit within 1px
        # of the 2x export. The top edge is not compared: thin tower tips that
        # average away on the 64 grid survive at 256 and legitimately rise.
        for style in STYLES:
            for level in LEVELS:
                left, _, right, bottom = Image.open(
                    BASE / 'processed/regional' / style / f'2x/cast_{level}.png').getchannel('A').getbbox()
                for scale in (4, 8):
                    box = Image.open(BASE / 'processed/regional' / style / f'{scale}x/cast_{level}.png').getchannel('A').getbbox()
                    l, _, r, b = (edge / (scale / 2) for edge in box)
                    name = f'{style}/{scale}x/cast_{level}'
                    self.assertLessEqual(abs((r - l) - (right - left)), 1, f'{name} width')
                    self.assertLessEqual(abs((r + l) / 2 - (right + left) / 2), 1, f'{name} centre')
                    self.assertLessEqual(abs(b - bottom), 1, f'{name} baseline')

    def test_each_style_keeps_its_own_silhouette(self) -> None:
        for level in LEVELS:
            masks = [Image.open(BASE / 'processed/regional' / style / f'1x/cast_{level}.png').getchannel('A').tobytes()
                     for style in STYLES]
            self.assertEqual(len(set(masks)), len(STYLES), f'cast_{level} uses a shared alpha mask')


if __name__ == '__main__':
    unittest.main()
