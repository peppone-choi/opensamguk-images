# OpenSamguk terrain masters, first batch

Generated 2026-10-16 using built-in imagegen only. The five separate `*-master.png` files are the selected candidates. The two `terrain-master*.png` atlas attempts are rejected because exterior translucent glow and imprecise geometry survived correction.

## Selected assets

| Asset | Full PNG size | Suggested source crop x,y,width,height | Approximate source center |
|---|---|---|---|
| grass-master.png | 1254x1254 | 3,342,1246,639 | 626,661 |
| forest-master.png | 1774x887 | 97,99,1580,711 | 887,454 |
| mountain-master.png | 1774x887 | 60,24,1650,839 | 885,443 |
| river-master.png | 1774x887 | 63,49,1648,792 | 887,445 |
| deepwater-master.png | 1774x887 | 73,44,1628,819 | 887,453 |

Crops are measured from alpha >=128, not hard guarantees of exact artwork boundaries. `validation.json` includes estimated four diamond tips, alpha statistics, source sizes and SHA-256 hashes. `SHA256SUMS` provides checksums; `provenance.json` contains every exact generation/correction prompt and reference paths.

## Intended integration

One terrain image per file. Ground-center anchor at destination (64,32) in a 128x64 tile. Destination diamond vertices (64,0),(128,32),(64,64),(0,32). Normalize the source crop to destination width/height and use the engine's exact diamond clipping path to ensure the footprint. Source terrain is flat with no raised base. Retain masters unchanged for higher resolution or future art correction.

## Validation and limitations

- All five selected PNGs genuinely contain an alpha channel and hundreds of thousands of completely transparent pixels. No synthetic checkerboard background.
- All five visually inspected: no labels, UI, scenery montage or raised slab; muted palette and fine realistic texture are broadly coherent with the approved concepts.
- Exact 2:1 geometry was not reliably followed: measured ratios are 1.9499, 2.2222, 1.9666, 2.0808 and 1.9878. Forest needs the largest geometric normalization.
- Alpha is mostly near-opaque rather than exactly255 inside the artwork. Small low-alpha speckles can extend beyond the obvious diamond. Raw alpha bounding boxes therefore overestimate usable art. Threshold geometry and engine clipping need review; these are not already pixel-clean production tiles.
- Seamlessness, adjacent-edge continuity, target128x64 readability and in-game color balance have not been validated in a browser. River/deepwater textures have directional highlights and may reveal repetition.
- No 128x64 derivative files were written because this task used imagegen for image modifications and preserved returned image bytes. A renderer can sample the crops and clip to its native diamond geometry without changing the master assets. If deterministic export preprocessing is desired, it should be explicitly authorized as a separate processing step.
- The first atlas included a numerically contradictory intermediate size phrase in its prompt, preserved honestly in the ledger. It is rejected and should not be integrated.

Status: first integration candidates, not production-ready assets or completed browser playthrough.
