# License notice — Waryong derivatives

`waryong/` is outside this repository's MIT license. Everything in it is derived from the original game **제갈공명 와룡전**:

- `waryong/battle/` — battlefield images, unit sprites and a derived terrain catalog from `BATTLE.MAP`, `BATTLE.MDL`, `BATTLE.SCH`.
  `waryong/battle/kit/` holds the same boards as original pieces (palette index + transparency), record tables, board layouts (record id per cell), unit pieces and unit role layers, so the app assembles boards itself instead of shipping pre-rendered images.
- `waryong/map/` — the strategic-map tile kit and sprites from `MMAP.MDL` (terrain tiles), `MMAP.MCH` (map markers) and `GAMEPAL.BRG` (palettes), plus synthesis statistics learned from `MMAP.MAP` (map layout). Joined tiles, palette variants, flag cloths and one-cell site icons are assembled only from original tiles and markers (cropping, overlaying, palette remapping, mode-downscaling); no new artwork is drawn.
- `waryong/previews/` — contact sheets of the above.

The original files are kept outside Git in a read-only local cache and are not included here.

The repository owner peppone-choi accepted responsibility for using these derivatives in OpenSamguk on 2026-09-26 (battle) and extended it to the strategic map on 2026-09-30 (「난 그 이미지 그대로 쓰라고 할려 했는데?」). This `owner-accepted` classification records that product decision; it grants no rights to third parties and does not claim ownership of the original art. The machine-readable boundary is [`.license-boundaries.json`](../.license-boundaries.json).

The catalogs, statistics and the Python conversion tools are project-authored metadata and code, but the catalogs and statistics remain in this conservative third-party directory boundary because they are derived from the original data. The conversion tools themselves live in `tools/` under the repository's MIT boundary.
