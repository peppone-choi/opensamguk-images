from __future__ import annotations

import unittest

from tools.assets import build_status_icons as status_icons


class StatusIconPipelineTest(unittest.TestCase):
    def test_every_known_state_has_a_distinct_binary_alpha_silhouette(self) -> None:
        silhouettes: set[bytes] = set()
        for code in status_icons.STATE_BUILDERS:
            icon = status_icons.build_state(code)
            self.assertEqual((15, 15), icon.size)
            alpha = icon.getchannel("A").tobytes()
            self.assertLessEqual(set(alpha), {0, 255})
            self.assertNotIn(alpha, silhouettes)
            silhouettes.add(alpha)

    def test_capital_star_uses_its_own_compact_footprint(self) -> None:
        star = status_icons.build_capital_star()

        self.assertEqual((10, 10), star.size)
        self.assertLessEqual(set(star.getchannel("A").tobytes()), {0, 255})

    def test_targets_export_all_states_and_capital_to_both_apps(self) -> None:
        icons = {str(code): status_icons.build_state(code) for code in status_icons.STATE_BUILDERS}
        icons["capital"] = status_icons.build_capital_star()
        targets = {path.relative_to(status_icons.ROOT).as_posix() for path in status_icons.targets(icons)}

        self.assertEqual(27, len(targets))
        for app in status_icons.APPS:
            self.assertIn(f"web/{app}/public/status/star-capital.png", targets)
            for code in status_icons.STATE_BUILDERS:
                self.assertIn(f"web/{app}/public/status/state-{code}.png", targets)


if __name__ == "__main__":
    unittest.main()
