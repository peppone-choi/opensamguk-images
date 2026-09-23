from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

from PIL import Image, ImageDraw


MODULE_PATH = Path(__file__).with_name("build_city_icons.py")
SPEC = importlib.util.spec_from_file_location("build_city_icons", MODULE_PATH)
assert SPEC and SPEC.loader
city_icons = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(city_icons)


class CityIconPipelineTest(unittest.TestCase):
    def test_checkerboard_extraction_produces_real_transparency(self) -> None:
        source = Image.new("RGB", (64, 64), (250, 250, 250))
        draw = ImageDraw.Draw(source)
        for y in range(0, 64, 8):
            for x in range(0, 64, 8):
                if (x // 8 + y // 8) % 2:
                    draw.rectangle((x, y, x + 7, y + 7), fill=(242, 244, 242))
        draw.rectangle((20, 18, 43, 47), fill=(42, 35, 28))

        extracted = city_icons.remove_checkerboard_background(source)

        self.assertEqual("RGBA", extracted.mode)
        self.assertEqual(0, extracted.getpixel((0, 0))[3])
        self.assertEqual(255, extracted.getpixel((30, 30))[3])

    def test_all_levels_have_source_and_visual_mass_contract(self) -> None:
        self.assertEqual(tuple(range(1, 12)), city_icons.LEVELS)
        self.assertEqual(
            {5: 48, 10: 34, 11: 27},
            {level: city_icons.VISUAL_EXTENT[level] for level in (5, 10, 11)},
        )
        for level in city_icons.LEVELS:
            self.assertTrue(city_icons.source_path(level).is_file(), level)

    def test_rendered_icons_share_canvas_and_keep_transparent_corners(self) -> None:
        rendered = {level: city_icons.render_icon(level) for level in (5, 10, 11)}

        for icon in rendered.values():
            self.assertEqual((64, 64), icon.size)
            self.assertEqual("RGBA", icon.mode)
            self.assertEqual(0, icon.getpixel((0, 0))[3])

        bboxes = {level: icon.getchannel("A").getbbox() for level, icon in rendered.items()}
        heights = {level: bbox[3] - bbox[1] for level, bbox in bboxes.items() if bbox}
        self.assertGreater(heights[5], heights[10])
        self.assertGreater(heights[10], heights[11])

    def test_dpr_exports_are_independently_pixel_hinted(self) -> None:
        variants = city_icons.render_variants(5)

        self.assertEqual({1: 32, 2: 64, 4: 128, 8: 256}, city_icons.VARIANT_SIZES)
        self.assertEqual({1, 2, 4, 8}, set(variants))
        for dpr, icon in variants.items():
            self.assertEqual((32 * dpr, 32 * dpr), icon.size)
            self.assertEqual({0, 255}, set(icon.getchannel("A").tobytes()))
            self.assertEqual(0, icon.getpixel((0, 0))[3])

    def test_large_variants_keep_hierarchy_and_proportional_bottom_anchor(self) -> None:
        for dpr, size in ((4, 128), (8, 256)):
            bboxes = {level: city_icons.render_variants(level)[dpr].getchannel("A").getbbox() for level in (5, 10, 11)}
            heights = {level: bbox[3] - bbox[1] for level, bbox in bboxes.items()}
            self.assertGreater(heights[5], heights[10])
            self.assertGreater(heights[10], heights[11])
            # 64px 규격 anchorY 63/64 — 하단 여백이 캔버스에 비례한다(128→2px, 256→4px).
            self.assertEqual(size * 63 // 64, bboxes[5][3])
            center = (bboxes[5][0] + bboxes[5][2]) / 2
            self.assertLessEqual(abs(center - size / 2), dpr)

    def test_targets_include_dpr_specific_web_exports(self) -> None:
        icons = {level: city_icons.render_variants(level) for level in city_icons.LEVELS}
        paths = {path.relative_to(city_icons.ROOT).as_posix() for path in city_icons.targets(icons)}

        for app in city_icons.APPS:
            self.assertIn(f"web/{app}/public/city/1x/cast_5.png", paths)
            self.assertIn(f"web/{app}/public/city/2x/cast_5.png", paths)
            self.assertIn(f"web/{app}/public/city/4x/cast_5.png", paths)
            self.assertIn(f"web/{app}/public/city/8x/cast_5.png", paths)
            self.assertIn(f"web/{app}/public/city/cast_5.png", paths)


if __name__ == "__main__":
    unittest.main()
