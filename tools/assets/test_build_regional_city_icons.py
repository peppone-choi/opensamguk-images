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

    def test_large_exports_keep_paired_pixel_blocks(self) -> None:
        for style in STYLES:
            for level in LEVELS:
                for scale in (4, 8):
                    rgba = np.asarray(Image.open(BASE / 'processed/regional' / style / f'{scale}x/cast_{level}.png'))
                    block = scale // 2
                    for offset in range(1, block):
                        self.assertTrue(np.array_equal(rgba[::block, ::block], rgba[offset::block, ::block]), f'{style}/{scale}/{level}')
                        self.assertTrue(np.array_equal(rgba[::block, ::block], rgba[::block, offset::block]), f'{style}/{scale}/{level}')

    def test_each_style_keeps_its_own_silhouette(self) -> None:
        for level in LEVELS:
            masks = [Image.open(BASE / 'processed/regional' / style / f'1x/cast_{level}.png').getchannel('A').tobytes()
                     for style in STYLES]
            self.assertEqual(len(set(masks)), len(STYLES), f'cast_{level} uses a shared alpha mask')


if __name__ == '__main__':
    unittest.main()
