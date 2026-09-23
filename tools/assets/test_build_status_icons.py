from __future__ import annotations

import unittest

from tools.assets import build_status_icons as status_icons


def _gold_run(image, y: int, xs: range) -> int:
    return sum(
        1
        for x in xs
        if (
            image.getpixel((x, y))[3] == 255
            and image.getpixel((x, y))[0] >= 150
            and image.getpixel((x, y))[1] >= 100
            and image.getpixel((x, y))[2] < 100
        )
    )


class StatusIconPipelineTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.icons = status_icons.build_all()

    def test_every_state_has_a_distinct_binary_alpha_silhouette_at_every_scale(self) -> None:
        keys = [str(code) for code in status_icons.STATE_CODES] + list(status_icons.HWIHA_STATES)
        self.assertEqual(16, len(keys))
        for scale in status_icons.SCALES:
            silhouettes: set[bytes] = set()
            for key in keys:
                icon = self.icons[key][scale]
                self.assertEqual((16 * scale, 16 * scale), icon.size, (key, scale))
                alpha = icon.getchannel("A").tobytes()
                self.assertLessEqual(set(alpha), {0, 255}, (key, scale))
                self.assertNotIn(alpha, silhouettes, (key, scale))
                silhouettes.add(alpha)

    def test_large_variants_are_rendered_from_source_not_upscaled(self) -> None:
        # 8x 가 4x 의 최근접 2배 확대라면 2×2 블록이 전부 같은 색이다. 원화에서 독립 축소해야 한다.
        for key in ("1", "battle"):
            big = self.icons[key][8]
            upscaled = self.icons[key][4].resize(big.size)
            self.assertNotEqual(big.tobytes(), upscaled.tobytes(), key)

    def test_badges_fill_their_canvas_with_proportional_margin(self) -> None:
        for key in ("1", "43", "isolated", "works"):
            for scale in status_icons.SCALES:
                bbox = self.icons[key][scale].getchannel("A").getbbox()
                self.assertIsNotNone(bbox)
                self.assertEqual(16 * scale, bbox[3], (key, scale))  # 하단 정렬
                longest = max(bbox[2] - bbox[0], bbox[3] - bbox[1])
                self.assertGreaterEqual(longest, 16 * scale - 2 * scale - 1, (key, scale))

    def test_capital_star_is_compact_and_binary(self) -> None:
        for scale in status_icons.SCALES:
            star = self.icons["capital"][scale]
            self.assertEqual((16 * scale, 16 * scale), star.size)
            self.assertLessEqual(set(star.getchannel("A").tobytes()), {0, 255})

    def test_imperial_residence_keeps_its_24px_contract_and_crown_front(self) -> None:
        variants = self.icons["imperial"]
        self.assertEqual({1: (24, 24), 2: (48, 48), 4: (96, 96)}, {s: v.size for s, v in variants.items()})
        imperial = variants[1]
        alpha = imperial.getchannel("A").tobytes()
        self.assertLessEqual(set(alpha), {0, 255})
        self.assertNotEqual(self.icons["1"][1].getchannel("A").tobytes(), alpha)
        self.assertGreaterEqual(_gold_run(imperial, 8, range(7, 18)), 5)

    def test_imperial_npc_badge_has_a_crisp_compact_crown_front(self) -> None:
        variants = self.icons["imperialNpc"]
        self.assertEqual({1: (16, 16), 2: (32, 32)}, {s: v.size for s, v in variants.items()})
        badge = variants[1]
        self.assertLessEqual(set(badge.getchannel("A").tobytes()), {0, 255})
        self.assertGreaterEqual(_gold_run(badge, 5, range(4, 12)), 4)

    def test_targets_export_every_scale_to_both_apps_and_keep_legacy_flat_files(self) -> None:
        targets = {path.relative_to(status_icons.ROOT).as_posix() for path in status_icons.targets(self.icons)}

        # (12 상태 + 4 휘하 + 별) × 4배율 + 황제 거처 3 + NPC 2 = 73, 평면 15, 앱 2개, preview 1
        self.assertEqual((73 + 15) * 2 + 1, len(targets))
        for app in status_icons.APPS:
            base = f"web/{app}/public/status"
            for flat in ("star-capital.png", "imperial-residence.png", "imperial-npc.png", "state-9.png"):
                self.assertIn(f"{base}/{flat}", targets)
            for name in status_icons.HWIHA_STATES:
                self.assertNotIn(f"{base}/state-{name}.png", targets)
            for scale in (1, 2, 4, 8):
                self.assertIn(f"{base}/{scale}x/star-capital.png", targets)
                for code in status_icons.STATE_CODES:
                    self.assertIn(f"{base}/{scale}x/state-{code}.png", targets)
                for name in status_icons.HWIHA_STATES:
                    self.assertIn(f"{base}/{scale}x/state-{name}.png", targets)
            self.assertIn(f"{base}/4x/imperial-residence.png", targets)
            self.assertIn(f"{base}/2x/imperial-npc.png", targets)


if __name__ == "__main__":
    unittest.main()
