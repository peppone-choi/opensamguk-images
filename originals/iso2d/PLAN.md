# 2D isometric asset production

Goal: AI-authored Han China map assets, paired with the existing iso3d palette.

User decisions: hand-painted non-pixel art; 256×128 flat footprint; no tile borders or baked sidewalls; AI-generated directional slope variants, not warped flat textures. The handoff is preserved in `handoff.txt`.

## Production order and gates

- [x] Call the built-in image generator for one flat PLAIN pilot. Preserve raw output.
- [x] Create `work/opensamguk-images/iso2d-assets` through the metarepo start-task command (reference pull + exported environment + graph query).
- [x] Extract the pilot with sprite-gen's chroma-removal and static-sheet pipeline. Validate geometry and an 8×8 repeated field before accepting.
- [x] Generate geometry-guided PLAIN slope samples. Four corner heights N/E/S/W share grid vertices. Basic masks 0..14 encode a 0/1 corner height; mask 15 is mask 0 at base+1. Trial height step: 32 screen pixels. This is not a claim about physical elevation.
- [x] Verify slope joins on a hill, basin, ridge, saddle and cliff scene. Reject wrong silhouettes, gaps, edge bands and baked sidewalls; regenerate rather than draw replacement art.
- [x] Expand accepted terrain pipeline to SEA, PLAIN, MOUNTAIN, RIVER, LAKE, DESERT, PLATEAU, BASIN, HILL. Six land materials use directional slopes; water remains level with separate banks. Cliff and raised land props are separate.
- [x] Generate hamlet/county/commandery/capital and six armType assets, then count strategic features from actual map sources.
- [x] Import extracted PNGs with unpack_atlas_run.py, curate, export through export_curated_pngs.py. Only curated outputs can become deliverables.
- [x] Mixed-terrain 8×8 QA and side-by-side iso3d palette QA. Only passed assets can be tagged or exported to opensamguk.
- [x] Record raw/prompt provenance, validation and risks. Commit/tag and deployment-copy closeout are recorded in the metarepo task reports. Rejected attempts are explicitly marked and not installed.

## Height-data limitation

The current han-tiles.json has terrain classes but no vertex elevation grid. build_terrain_grid.py explicitly uses named geographic regions instead of an elevation raster. The v2 contracts have elevation fields and demo fixtures, but these are not a map-wide height source. Production height reconstruction and DEM selection are outside an asset-generation claim; QA uses explicit synthetic fixtures.

## Geometry acceptance

Flat footprint corners are (128,0), (256,64), (128,128), (0,64). Padded slope cell is 256×160 with baseline corners (128,32), (256,96), (128,160), (0,96); raised corners subtract 32px. A slope sprite must depict its actual shape. Shared corners alone do not define saddle triangulation: its diagonal must be recorded consistently, with no crack at shared edges. Cliff edges are explicitly discontinuous and cannot be inferred merely from differing tile-center heights.

No generated raw file is a production result. Geometry guides and QA composition code are allowed; locally drawn terrain replacements are not.
