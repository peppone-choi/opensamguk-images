# Third-Party Notices

This repository contains material that is **not** the work of the repository
owner and is **not** covered by the root [`LICENSE`](./LICENSE) (MIT).

For every path listed below, this repository:

- **does not claim copyright**;
- **grants no license of any kind** (no use, copy, modification, redistribution,
  sublicensing, or commercial-use permission);
- makes **no representation** that redistribution or use is permitted.

Rights remain with the respective original rights holders. Anyone wishing to use
these files must obtain permission from those rights holders directly.

The authoritative machine-readable boundary is
[`.license-boundaries.json`](./.license-boundaries.json), verified by
`tools/check-license-boundaries.py`.

Origin is recorded as observed in this repository. Where the origin could not be
established from repository evidence it is marked **UNKNOWN**, and UNKNOWN is
treated the same as third-party: no license is granted.

---

## `portraits/` — RTK14 character illustrations and derivatives

| Item | Detail |
| --- | --- |
| Paths | `portraits/rtk14/original/`, `full-frame-148x210/`, `face-crop-148x210/`, `face-icon-96/`, `serving/` |
| Original rights holder | Koei Tecmo Games Co., Ltd. — character illustrations from *Romance of the Three Kingdoms XIV* (三國志14 / RTK14) |
| Acquisition source | Attachment images on the RTK14 wikiwiki, `https://wikiwiki.jp/sangokushi14/` (`cdn.wikiwiki.jp/.../::attach/*.jpg`). Per-file source URLs are recorded in `portraits/rtk14/manifest/rtk14-name-file-map.tsv`. |
| Current state | 1000 acquired originals (stored byte-preserved as `<sha256>.bin`) plus mechanically derived resizes/crops (148×210 full-frame, 148×210 face crop, 96×96 face icon) and id-keyed serving copies. Derivative processing does not create a new independent work here; the derivatives carry the same status as the originals. |
| Status | Third-party derived. No license granted by this repository. |

`portraits/rtk14/README.md`, `manifest/*`, `officer-id-registry.tsv` and
`*/report.tsv` are pipeline metadata authored for this project, but they describe
and index the third-party material and are kept inside the third-party boundary
for clarity.

## `icons/` — character icon pool

The `icons/` tree is third-party derived or UNKNOWN throughout. No license is
granted for any path under `icons/`.

| Path | Origin as observed | Status |
| --- | --- | --- |
| `icons/*.jpg` (1842 numbered files at the top of `icons/`) | Legacy 삼국지 모의전투 (devsam / HiDCHe) general-portrait pool inherited with the game. Individual provenance is not recorded in this repository; portraits in this pool are widely Koei Tecmo *Romance of the Three Kingdoms* series derived. | UNKNOWN → treated as third-party |
| `icons/삼국지6/` | *Romance of the Three Kingdoms VI* (Koei Tecmo Games Co., Ltd.) character art | Third-party |
| `icons/포켓몬스터/` | *Pokémon* — The Pokémon Company / Nintendo / Game Freak / Creatures Inc. | Third-party |
| `icons/롤시나리오/` | *League of Legends* champion art and esports player photographs — Riot Games, Inc.; photograph rights holders unidentified | Third-party |
| `icons/쿠키런킹덤/` | *Cookie Run: Kingdom* — Devsisters Corp. | Third-party |
| `icons/환상향/` | *Touhou Project* (東方Project) — Team Shanghai Alice (ZUN) and fan-artwork derivatives; individual artists unidentified | Third-party |
| `icons/걸그룹/` | Photographs of real, identifiable K-pop performers. Photographers and rights holders unidentified; publicity/personality rights of the depicted individuals also apply. | Third-party |
| `icons/스타1프로게이머/` | Photographs of real, identifiable StarCraft professional players. Photographers and rights holders unidentified; publicity/personality rights of the depicted individuals also apply. | Third-party |
| `icons/루드라사움/` | Community scenario icon set; original authorship not recorded in this repository | UNKNOWN → treated as third-party |
| `icons/강서유서월드/` | Community scenario icon set; original authorship not recorded in this repository | UNKNOWN → treated as third-party |
| `icons/삼모시네마틱유니버스/` | Community scenario icon set; original authorship not recorded in this repository | UNKNOWN → treated as third-party |

## `game/` — game UI, map, and unit assets

| Item | Detail |
| --- | --- |
| Paths | `game/*` (backgrounds, banners, color chips, GIFs), `game/map/*`, `game/src/*` |
| Origin as observed | Assets inherited from the legacy 삼국지 모의전투 (devsam / HiDCHe) PHP game. `game/src/*.jpg` are unit-type illustrations (보병, 궁병, 기병, 충차 …) of the kind used by the Koei Tecmo *Romance of the Three Kingdoms* series; `game/map/` holds scenario map art for che / chess / cr / ludo_rathowm / pokemon_v1. Original authorship is not recorded in this repository. |
| Current state | Served unchanged as game assets. `game/src/코드.txt` is a unit-code table (text). |
| Status | UNKNOWN → treated as third-party. No license granted by this repository. |

## `hook/` — legacy image-service deploy scripts

| Item | Detail |
| --- | --- |
| Paths | `hook/hook.php`, `hook/git_pull.php`, `hook/InstallKey.php`, `hook/HashKey.orig.php`, `hook/gogs_key.orig.php` |
| Origin as observed | PHP sources in namespace `sammo\img_service` — the legacy 삼국지 모의전투 (devsam / HiDCHe) image-service deploy hooks, inherited rather than authored here. Upstream license not recorded in this repository. |
| Current state | Retained as-is; not part of CDN asset serving. |
| Status | UNKNOWN → treated as third-party. No license granted by this repository. |

---

## Reporting

If you are a rights holder for any of the above and want a path removed or its
entry corrected, open an issue on this repository.
