import unittest
import numpy as np
from PIL import Image
from prepare_iso2d_tiles import normalize_alpha, footprint
from export_iso2d_assets import BUILDINGS, OUT, UNITS, spill
from prepare_iso2d_objects import seat_on_tile


class GeometryTests(unittest.TestCase):
    def sample(self):
        mask = footprint(6)
        a = np.zeros((160, 256, 4), dtype=np.uint8)
        a[mask] = [110, 130, 90, 255]
        return a, mask

    def test_preserves_source_interior_and_repairs_one_pixel_edge(self):
        a, mask = self.sample()
        ys, xs = np.where(mask)
        y, x = int(ys[0]), int(xs[0])
        a[y, x] = 0
        out, count = normalize_alpha(Image.fromarray(a), 6)
        b = np.array(out)
        self.assertEqual(count, 1)
        self.assertTrue(np.array_equal(b[a[:, :, 3] == 255], a[a[:, :, 3] == 255]))
        self.assertTrue(np.all(b[mask, 3] == 255))
        self.assertTrue(np.all(b[~mask, 3] == 0))

    def test_rejects_missing_interior_instead_of_painting_it(self):
        a, _ = self.sample()
        a[70:85, 120:135] = 0
        with self.assertRaises(ValueError):
            normalize_alpha(Image.fromarray(a), 6)

    def test_rejects_missing_asset(self):
        with self.assertRaises(ValueError):
            normalize_alpha(Image.new('RGBA', (256, 160)), 6)

    def test_rejects_even_single_missing_interior_pixel(self):
        a, _ = self.sample()
        a[80, 128] = 0
        with self.assertRaises(ValueError):
            normalize_alpha(Image.fromarray(a), 6)

    def test_rejects_opaque_rectangle_instead_of_cutting_a_slope(self):
        with self.assertRaises(ValueError):
            normalize_alpha(Image.new('RGBA',(256,160),(110,130,90,255)),6)

    def test_rejects_wrong_authored_slope(self):
        a,_=self.sample()
        with self.assertRaises(ValueError):
            normalize_alpha(Image.fromarray(a),0)

    def test_reference_occlusion_is_order_independent_with_crossing_depths(self):
        from preview_iso2d_integration import raster_triangle
        points=np.array([[0,0],[20,0],[0,20]])
        # Offset the second face so no sample lies exactly on the intersection.
        surfaces=[(np.array([-2.,2.,2.]),(255,0,0,255)),(np.full(3,.03),(0,0,255,255))]
        results=[]
        for order in [surfaces,list(reversed(surfaces))]:
            pixels=np.zeros((24,24,4),dtype=np.uint8);depth=np.full((24,24),-np.inf)
            for z,color in order:raster_triangle(pixels,depth,points,z,color)
            results.append(pixels)
        self.assertTrue(np.array_equal(*results))
        self.assertEqual(results[0][1,1].tolist(),[0,0,255,255])
        self.assertEqual(results[0][2,14].tolist(),[255,0,0,255])


class TileFitTests(unittest.TestCase):
    """A ground object must stand inside the tile diamond it is placed on.

    Nothing checked this before. prepare_iso2d_objects.py cropped each painted compound to its
    alpha bbox and fitted it into an arbitrary (max_w, max_h) box, so the city icons came out at
    different scales, off the diamond centre, hanging 10-31px onto the tile in front of them.
    That, and not the painting, is what made them look inconsistent on the map.
    """

    def probe(self):
        """A sprite that sits correctly, and the same sprite dropped 12px. If the second one
        passes, the assertion below is measuring nothing."""
        good = np.zeros((256, 256, 4), dtype=np.uint8)
        for y in range(112, 241):
            reach = int(128 * (1 - abs(y - 176) / 64)) if y >= 176 else 128
            good[y, 128 - reach:128 + reach] = [160, 140, 110, 255]
        bad = np.zeros_like(good)
        bad[12:] = good[:-12]
        return good, bad

    def test_probe_separates_a_fitting_sprite_from_a_spilling_one(self):
        good, bad = self.probe()
        self.assertLessEqual(spill(good), 0)
        self.assertGreater(spill(bad), 0)

    def test_every_shipped_ground_object_stands_on_its_own_tile(self):
        """All 20, not just the 11 tiers. The 9 unit and prop sprites were bottom-aligned at the
        ground anchor and hung 4.5-48px over the diamond's falling edge; nothing measured them."""
        names = sorted(file.stem for file in (OUT / 'objects').glob('*.png'))
        # 11 tiers + 6 units + gate + two mountains. Named, so a dropped export fails here.
        self.assertEqual(names, sorted(list(BUILDINGS) + list(UNITS.values())
                                       + ['gate', 'mountain-rock', 'mountain-snow']))
        worst = {}
        for name in names:
            file = OUT / 'objects' / f'{name}.png'
            self.assertTrue(file.is_file(), f'{name} is not exported')
            with Image.open(file) as image:
                self.assertEqual(image.size, (256, 256))
                worst[name] = spill(np.array(image.convert('RGBA')))
        over = {k: round(float(v), 1) for k, v in worst.items() if v > 0}
        self.assertEqual(over, {}, f'ground objects hanging below their tile: {over}')

    def test_seat_on_tile_shrinks_a_wide_sprite_that_bottom_aligning_would_spill(self):
        """The red probe for the fix. A wide flat slab bottom-aligned at the ground anchor hangs
        far over the diamond's falling edge; seat_on_tile must bring it back onto the tile
        without sliding it off the tile centre."""
        slab = Image.new('RGBA', (240, 40), (160, 140, 110, 255))
        naive = Image.new('RGBA', (256, 256))
        naive.alpha_composite(slab, (8, 200))  # what the old code did: bottom at y=240
        self.assertGreater(spill(np.array(naive)), 40)

        seated = seat_on_tile(slab, 240, 40)
        self.assertEqual(seated.size, (256, 256))
        self.assertLessEqual(spill(np.array(seated)), 0)
        ys, xs = np.nonzero(np.array(seated)[:, :, 3] >= 8)
        self.assertAlmostEqual((int(xs.min()) + int(xs.max())) / 2, 127.5, delta=1.5)

    def test_seat_on_tile_leaves_a_sprite_that_already_fits_alone(self):
        """If it shrank everything the gate would pass for the wrong reason."""
        good, _ = self.probe()
        crop = Image.fromarray(good).crop(Image.fromarray(good[:, :, 3]).getbbox())
        seated = seat_on_tile(crop, crop.width, crop.height)
        self.assertLessEqual(spill(np.array(seated)), 0)
        self.assertGreaterEqual(int(np.array(seated)[:, :, 3].astype(bool).sum()),
                                int(good[:, :, 3].astype(bool).sum()) * 0.9)

    def test_one_tier_per_city_level_with_no_level_left_unmapped(self):
        self.assertEqual(sorted(BUILDINGS.values()), list(range(1, 12)))
        self.assertEqual(len(set(BUILDINGS)), len(BUILDINGS))


if __name__ == '__main__':
    unittest.main()
