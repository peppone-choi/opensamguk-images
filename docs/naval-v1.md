# naval-v1: original Blender asset delivery

## Boundary and provenance

Task `t_390c6b46`, independent author review `t_7218795b`, downstream UI `t_468312b7`. Approval: [Q40–41 source](https://github.com/peppone-choi/opensamguk/blob/e7d0309b2af307bb6d3cf08c6a32c01ea67a2ed9/docs/planning/owner-delegated-design-proposed-20261019.md). This is an asset delivery only, never a naval engine/UI/product acceptance claim.

Start-time remote main pins (not a three-repository integrated product tree):

| Repository | Observed remote main |
| --- | --- |
| app | `f6c6c4028b3a9bba708444ba99e7804e20afaeea` |
| Docker | `9b7f436db09ea5caf6fc7a76c479f3f4ed89ccf2` |
| images / asset source base | `049091911d954feee54862bea6ddcc70a3ff4e84` |

Only `originals/naval-v1`, `assets/naval-v1`, `exports/naval-v1`, `tools/naval-v1` and this document are owned by this task. App, land boards (including the 214 originals), portraits, existing exports and existing tools remain unchanged. All naval assets are original GAME_TERM art; no claim of historical ship/shore reconstruction. MIT grant and full export notice: `exports/naval-v1/NOTICE.txt`; original provenance: `originals/naval-v1/LICENSE-NOTICE.md`. Existing `.license-boundaries.json` already classifies the four parent directories MIT; no top-level entry or third-party exception is added.

## Actual source pipeline

Each ship and water board has its own native `.blend` source. Meshes include closed hull/deck, gunwales/planks, rudder, mast, curved UV-mapped batten sail, oars, class-specific tower/cargo/canopy, fire/smoke and tow-line geometry. Two newly authored texture PNGs are preserved beside the blends; Blender paths are relative `//textures/…`, so the source directory can be moved without access to this worker's home. Camera, sunlight, world light and state meshes are stored in the blend, not reconstructed from a screenshot.

`--build` authors sources; `--render` reloads the `.blend` files and uses CPU Cycles, 8 samples, 1 render thread, fixed orthographic camera, Standard view transform and transparent RGBA8 PNGs. `--audit` independently reopens all seven native scenes and checks actual camera/light/render values against render metadata, 4096 board tile faces, preserved ship/state meshes, relative existing textures and absence of external linked libraries. The Blender version used is 4.0.2. Even same-version raw PNG byte identity is NOT promised: Blender embeds Date/RenderTime/timing metadata. Compare decoded RGBA pixels for source replay, then rerun pack.py to pin the new raw PNG bytes. The committed exported SHA-256s bind this delivery, not any future re-render. A byte-hash check before repacking correctly fails on new PNG metadata; do not suppress that check or declare the bytes identical.

From the images repository root, with free existing Blender and Python/Pillow:

    python3 tools/naval-v1/run_render.py --build --evidence /absolute/evidence/build --lock-wait 300
    python3 tools/naval-v1/run_render.py --evidence /absolute/evidence/replay --lock-wait 300
    python3 tools/naval-v1/run_render.py --audit --evidence /absolute/evidence/audit --lock-wait 300
    python3 tools/naval-v1/pack.py
    python3 tools/naval-v1/pack.py --check
    python3 -m unittest discover -s tools/naval-v1 -p test_naval_assets.py -v
    python3 tools/check-license-boundaries.py

For an individual source/replay, add `--asset scout` (or another exact ID). To compare reproducibility, snapshot decoded frame hashes before replay; do not run `--build` when testing whether the preserved blend renders. The supervisor records the actual Blender command, UTC, exit code, user-999.slice/host budgets and sampled owned RSS in `render-run.json`, with unmodified Blender stdout in `blender.log`.

The supervisor holds `/srv/hermes-workspace/projects/opensamguk/locks/host-heavy.lock` through child-tree cleanup. It measures real user-999.slice headroom after obtaining the lock, requires at least 384 MiB for these small scenes, limits Blender/OMP/OpenBLAS threads, inherits the existing cgroup, and never changes service/host budgets. It stops its owned child if live measured headroom falls below 96 MiB. Insufficient admission budget or an occupied lock is NOT_RUN, not a bypass; a started render that later fails is FAIL. Blender is placed in a new owned process group and only that group is terminated/reaped on failure, exception, cancellation, timeout or success. No browser, Windows, paid resource, GCP, public port, game initialization or production service is used.

## Inventory and visual state contract

| ID | Shape | Export |
| --- | --- | --- |
| scout | narrow low green canopy, small working hull | 8 directions × 4 states × 2 phases, 160×160 |
| warship | longer red fighting tower, bow spar | same |
| transport | broad blue cargo hold and lashed bundles | same |
| river-narrow | winding banks, narrow water/shallow corridor | 64×64 original visual layout, 768×768 |
| estuary | widening river mouth and banks | same |
| lake | enclosed lake and an off-center island | same |
| coastal-port | coastal bank, two piers/piles, warehouse | same |

Ship states are `idle`, `drifting`, `burning`, `towed`, two 100 ms phases at 10 fps. Drifting/towed sources remove deployed sail/oars; towed adds a distinct bow rope. Fire/smoke is animated geometry, not a painted UI icon. Tow geometry only marks an attachment; the actual line to the real other ship must be drawn from reviewed backend tow endpoints. A visual state never fabricates crew counts, motion, ownership, damage or legal eligibility. The renderer must select the state from authorized backend projection; if burning and drifting/towed coexist, it must preserve both pieces of information (for example burning atlas plus an explicit drift/tow label and backend tow line), not silently drop fire or declare the ship operational. The sprite contains no national ownership assertion; runtime team markers must use legal projection, not class colors.

Total expected raw transparent frames: 196 (192 ships, 4 boards); seven atlases. Ship atlas is 1280×1280, direction columns in the fixed order, state/phase rows: idle0,idle1,drifting0,drifting1,burning0,burning1,towed0,towed1. Board atlas is its one original frame. Frames are pasted without resampling or alpha masks; every RGBA byte must match the corresponding atlas crop. Preview sheets under `assets/naval-v1` are clearly labeled ASSET PREVIEW ONLY, not Docker/game/browser evidence. Game PNG count remains 0 here.

## Manifest v1 — downstream immutable interface

`exports/naval-v1/manifest.json` contains `{version:1, coordinateSystem, assets:[…]}` with exactly seven ordered IDs. Each entry preserves the fixed required fields:

- `id`, `kind` (`ship` / `board`), `sourceBlend` (repository-relative native source).
- `texturePaths` (preserved original textures), `camera`, `lighting` (actual native scene values), `renderScript`.
- `directions`, `animations` (`frameCount`, `fps`, `loop`), `frames` (ordered repository-relative PNG path array).
- `atlas` (repository-relative PNG), `frameRects` (frame path → `{x,y,w,h}` integers, top-left origin).
- `pivot:{x,y}` (pixel coordinates from frame top-left of projected world origin / waterline, not a normalized fraction).
- `sha256` (repository-relative file path → lowercase byte SHA-256; includes blend, textures, render script, render metadata, individual frames, atlas and both license notices).
- `license:{spdx:"MIT", notice:"exports/naval-v1/NOTICE.txt", thirdPartyInputs:[]}`.

Each board additionally has `grid:{rows:64, cols:64, order:"row-major", worldCellCenter, origin, colStep, rowStep, visualRows, authority}`. These metadata values are part of the reviewed v1 art interface. Asset paths are resolved relative to the pinned images checkout, never relative to the manifest file's directory. Export consumers copy only reviewed `exports/naval-v1/**` (plus this notice), pin the exact images commit and manifest byte hash, and remap that common prefix to the local public asset root. They must not fetch `.blend`, scripts, originals or repository main/CDN dynamically at runtime. Keep provenance fields in the manifest even when originals are not shipped.

Grid contract: row increases toward world −Y, col increases toward world +X, N=row−1, E=col+1. Cell center `(col−31.5,31.5−row,0)`. Direction order is N,NE,E,SE,S,SW,W,NW; positive mesh +Y is the bow at N and rotates −45° per direction. The fixed board camera is at `(70,−70,70)`, aimed at zero, orthographic scale100. Ground-cell pixel center = `grid.origin + col*grid.colStep + row*grid.rowStep`. These row/col values are integer cell indices; if consuming continuous backend cell-space positions whose centers are `(row+0.5,col+0.5)` (existing TacticalV2SpaceGrid.centre), subtract 0.5 before applying the basis. Do not transpose row and col or double-add the center offset. Both increasing col/row descend on screen; col projects right and row projects left. Render scale multiplies the frame size, all rect/pivot coordinates and grid vectors equally. Runtime ship scale is a UI responsibility and must be chosen consistently with authoritative footprint; art pixels do not determine collision size. Ships use the same true-isometric camera orientation as the boards: relative `(7,−7,7)`, aimed at `(0,0,0.8)` from `(7,−7,7.8)`.

`visualRows` describes this original visual artwork only. It is NOT a campaign topology, depth, source-pin verification or legal navigation authority. N3 owns the actual tactical fixed template. N4/NUI must verify/match its reviewed template/source pin and row/col layout to the art; if mismatched, fail closed and request an explicit reviewed reconciliation, not quietly reuse a wrong board. Labels `water/shallow/land/sand/port` are visual art roles, not invented exact legal water depths. No board is derived from or replaces any of the old 214 land maps.

## Validation and raw evidence

Execution result, exact source/head/tree and raw SHA inventory are handed off on the native task alongside this document; this file does not invent an eventual PR/head. Final results below are updated only from real tool output.

Actual asset execution result: PASS for source production, 7 native blends, 196 transparent RGBA frames and 7 atlases. Build/render exit0; native-source audit exit0 (all7 reopened); build-free source replay exit0 and decoded RGBA196/196 identical. Raw PNG bytes0/196 identical due Date/RenderTime metadata, so the initial strict byte replay test and pre-repack hash test failed as expected; those failure logs are retained, not relabeled as byte PASS. Repack and final manifest check exit0; final artifact-contract tests29 PASS, fail/error/skip0. License boundary and git diff checks exit0. The sampled build-render child RSS maximum was226124 KiB (sampled, not an exact peak); user slice remained within its measured4539912192-byte maximum. All successful Blender runs confirm their owned process group gone.

An extra owned-timeout probe and repeat audit attempted after the successful audit/replay were NOT_RUN because the shared heavy1 lock did not become free within180s. No Blender was launched by those attempts. They do not prove cancellation/timeout cleanup; that implemented branch remains unexercised and must be independently reviewed. The successful native-source audit used the same render-script SHA256 `1611020e84dcb62ce0a1a2baaa73f0bfdb4efa48a78bfd3f0182ea212c9d82db` as the final preserved script. Raw commands, exits, successes/failures and resource samples are packaged in `assets/naval-v1/validation/raw-evidence.zip`; its inventory is adjacent.

Game/Docker/UI product QA NOT_RUN; whole product NOT_ACCEPTED; score delta0; milestone screenshots0. Independent asset review must pass before the UI consumes this export. Actual tactical-template/depth/source-pin reconciliation and combined state rendering remain downstream N3/N4/NUI work, not completed here.

## Proposed ASSET-EXPORTS registration hunk (review only)

Existing ASSET-EXPORTS.md is deliberately not edited by this owner. After independent review, its owner may append this exact new section without changing existing exports:

    ## Original naval-v1 Blender assets

    `exports/naval-v1/manifest.json` version1 is the provenance-pinned source for the
    separate 3-ship/4-water-board naval renderer. Original `.blend`, textures and
    rendering tools remain in images `originals/naval-v1` and `tools/naval-v1`.
    Copy only reviewed `exports/naval-v1/**` with `NOTICE.txt` to the downstream
    naval public boundary, preserving PNG/manifest bytes and recording images
    commit + manifest SHA-256. See `docs/naval-v1.md` for fields, pivots, atlas
    coordinates, source replay and visual-template versus server-authority limits.
    The preview sheets are not game QA; assets alone do not complete Q40–41.
