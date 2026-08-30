from __future__ import annotations

import unittest

from tools.assets import build_status_icons as status_icons


class StatusIconPipelineTest(unittest.TestCase):
    def test_every_known_state_has_a_distinct_binary_alpha_silhouette(self) -> None:
        silhouettes: set[bytes] = set()
        for code in status_icons.STATE_BUILDERS:
            icon = status_icons.build_state(code)
            self.assertEqual((24, 24), icon.size)
            alpha = icon.getchannel("A").tobytes()
            self.assertLessEqual(set(alpha), {0, 255})
            self.assertNotIn(alpha, silhouettes)
            silhouettes.add(alpha)

    def test_capital_star_uses_its_own_compact_footprint(self) -> None:
        star = status_icons.build_capital_star()

        self.assertEqual((16, 16), star.size)
        self.assertLessEqual(set(star.getchannel("A").tobytes()), {0, 255})

    def test_imperial_residence_is_a_distinct_full_emperor_portrait(self) -> None:
        imperial = status_icons.build_imperial_residence()

        self.assertEqual((24, 24), imperial.size)
        alpha = imperial.getchannel("A").tobytes()
        self.assertLessEqual(set(alpha), {0, 255})
        self.assertNotEqual(status_icons.build_state(1).getchannel("A").tobytes(), alpha)
        front_gold = [
            imperial.getpixel((x, 8))
            for x in range(7, 18)
            if (
                imperial.getpixel((x, 8))[3] == 255
                and imperial.getpixel((x, 8))[0] >= 150
                and imperial.getpixel((x, 8))[1] >= 100
                and imperial.getpixel((x, 8))[2] < 100
            )
        ]
        self.assertGreaterEqual(len(front_gold), 5)

    def test_imperial_npc_badge_has_a_crisp_compact_crown_front(self) -> None:
        badge = status_icons.build_imperial_npc_badge()

        self.assertEqual((16, 16), badge.size)
        self.assertLessEqual(set(badge.getchannel("A").tobytes()), {0, 255})
        front_gold = [
            badge.getpixel((x, 5))
            for x in range(4, 12)
            if (
                badge.getpixel((x, 5))[3] == 255
                and badge.getpixel((x, 5))[0] >= 150
                and badge.getpixel((x, 5))[1] >= 100
                and badge.getpixel((x, 5))[2] < 100
            )
        ]
        self.assertGreaterEqual(len(front_gold), 4)

    def test_targets_export_all_states_capital_and_emperor_to_both_apps(self) -> None:
        icons = {str(code): status_icons.build_state(code) for code in status_icons.STATE_BUILDERS}
        icons["capital"] = status_icons.build_capital_star()
        icons["imperial"] = status_icons.build_imperial_residence()
        icons["imperialNpc"] = status_icons.build_imperial_npc_badge()
        targets = {path.relative_to(status_icons.ROOT).as_posix() for path in status_icons.targets(icons)}

        self.assertEqual(91, len(targets))
        for app in status_icons.APPS:
            self.assertIn(f"web/{app}/public/status/star-capital.png", targets)
            self.assertIn(f"web/{app}/public/status/2x/star-capital.png", targets)
            self.assertIn(f"web/{app}/public/status/imperial-residence.png", targets)
            self.assertIn(f"web/{app}/public/status/1x/imperial-residence.png", targets)
            self.assertIn(f"web/{app}/public/status/2x/imperial-residence.png", targets)
            self.assertIn(f"web/{app}/public/status/imperial-npc.png", targets)
            self.assertIn(f"web/{app}/public/status/1x/imperial-npc.png", targets)
            self.assertIn(f"web/{app}/public/status/2x/imperial-npc.png", targets)
            for code in status_icons.STATE_BUILDERS:
                self.assertIn(f"web/{app}/public/status/state-{code}.png", targets)
                self.assertIn(f"web/{app}/public/status/1x/state-{code}.png", targets)
                self.assertIn(f"web/{app}/public/status/2x/state-{code}.png", targets)


if __name__ == "__main__":
    unittest.main()
