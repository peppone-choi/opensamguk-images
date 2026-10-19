#!/usr/bin/env python3
"""Run after pack.py: real artifacts are required, never manufactured fixtures."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
SPEC=importlib.util.spec_from_file_location('naval_pack',Path(__file__).with_name('pack.py'))
pack=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pack)
RUN_SPEC=importlib.util.spec_from_file_location('naval_run',Path(__file__).with_name('run_render.py'))
runner=importlib.util.module_from_spec(RUN_SPEC)
RUN_SPEC.loader.exec_module(runner)


class ArtifactContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((ROOT/'exports/naval-v1/manifest.json').read_text())

    def changed(self,change):
        manifest=copy.deepcopy(self.manifest)
        change(manifest)
        with self.assertRaises((ValueError,FileNotFoundError,KeyError)):
            pack.verify(ROOT,manifest)

    def test_real_inventory_alpha_atlas_hashes_and_silhouettes(self):
        self.assertEqual(pack.verify(ROOT,self.manifest)['transparentFrames'],196)

    def test_version_fail_closed(self):
        self.changed(lambda m:m.update(version=2))

    def test_boolean_version_rejected(self):
        self.changed(lambda m:m.update(version=True))

    def test_coordinate_axes_rejected(self):
        self.changed(lambda m:m['coordinateSystem'].update(north='row+1'))

    def test_missing_ship(self):
        self.changed(lambda m:m['assets'].pop(0))

    def test_missing_direction_frame(self):
        self.changed(lambda m:m['assets'][0]['frames'].pop())

    def test_duplicate_frame(self):
        self.changed(lambda m:m['assets'][0]['frames'].append(m['assets'][0]['frames'][0]))

    def test_missing_source_hash(self):
        self.changed(lambda m:m['assets'][0]['sha256'].pop(m['assets'][0]['sourceBlend']))

    def test_hash_tamper(self):
        self.changed(lambda m:m['assets'][0]['sha256'].update({m['assets'][0]['sourceBlend']:'0'*64}))

    def test_direction_reorder(self):
        self.changed(lambda m:m['assets'][0]['directions'].reverse())

    def test_rectangle_tamper(self):
        self.changed(lambda m:m['assets'][0]['frameRects'][m['assets'][0]['frames'][0]].update(x=1))

    def test_non_orthographic(self):
        self.changed(lambda m:m['assets'][0]['camera'].update(type='PERSP'))

    def test_camera_metadata_drift(self):
        self.changed(lambda m:m['assets'][0]['camera'].update(orthoScale=99))

    def test_lighting_metadata_drift(self):
        self.changed(lambda m:m['assets'][0]['lighting'].update(samples=1))

    def test_grid_projection_metadata_drift(self):
        self.changed(lambda m:m['assets'][3]['grid'].update(origin=[0,0]))

    def test_source_namespace_boundary(self):
        self.changed(lambda m:m['assets'][0].update(sourceBlend='waryong/source.blend'))

    def test_pivot_off_canvas(self):
        self.changed(lambda m:m['assets'][0]['pivot'].update(x=-1))

    def test_original_license_only(self):
        self.changed(lambda m:m['assets'][0]['license'].update(thirdPartyInputs=['waryong']))

    def test_animation_frame_contract(self):
        self.changed(lambda m:m['assets'][0]['animations']['burning'].update(frameCount=1))

    def test_board_row_count(self):
        self.changed(lambda m:m['assets'][3]['grid']['visualRows'].pop())

    def test_board_col_count(self):
        self.changed(lambda m:m['assets'][3]['grid']['visualRows'][0].pop())

    def test_board_is_not_runtime_authority(self):
        self.changed(lambda m:m['assets'][3]['grid'].update(authority='runtime-navigation-authority'))

    def test_source_scope(self):
        for asset in self.manifest['assets']:
            self.assertTrue(asset['sourceBlend'].startswith('originals/naval-v1/'))
            self.assertTrue(asset['atlas'].startswith('exports/naval-v1/'))
            self.assertTrue(all(f.startswith('exports/naval-v1/frames/') for f in asset['frames']))

    def test_all_four_visual_layouts_distinct(self):
        rows=[json.dumps(a['grid']['visualRows']) for a in self.manifest['assets'] if a['kind']=='board']
        self.assertEqual(len(set(rows)),4)

    def test_grid_basis_not_degenerate(self):
        for asset in self.manifest['assets'][3:]:
            grid=asset['grid']
            a,b=grid['colStep'],grid['rowStep']
            self.assertGreater(abs(a[0]*b[1]-a[1]*b[0]),1)
            self.assertGreater(a[0],0)
            self.assertLess(b[0],0)
            self.assertGreater(a[1],0)
            self.assertGreater(b[1],0)


class PathAndAdmission(unittest.TestCase):
    def test_reject_traversal(self):
        with self.assertRaises(ValueError): pack.safe_path(ROOT,'../outside.png')

    def test_reject_absolute_path(self):
        with self.assertRaises(ValueError): pack.safe_path(ROOT,'/etc/passwd')

    def test_allow_scoped_path(self):
        self.assertEqual(pack.safe_path(ROOT,'exports/naval-v1/manifest.json'),ROOT/'exports/naval-v1/manifest.json')

    def test_live_user_slice_budget_measured(self):
        actual=runner.resources()
        self.assertIsInstance(actual['cgroupMemoryCurrent'],int)
        self.assertIn('user-999.slice',actual['cgroup'])
        self.assertGreater(int(actual['cgroupMemoryMax']),0)
        self.assertGreater(actual['hostMemAvailable'],0)


if __name__=='__main__': unittest.main(verbosity=2)
