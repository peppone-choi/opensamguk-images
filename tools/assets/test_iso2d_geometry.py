import unittest
import numpy as np
from PIL import Image
from prepare_iso2d_tiles import normalize_alpha, footprint


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


if __name__ == '__main__':
    unittest.main()
