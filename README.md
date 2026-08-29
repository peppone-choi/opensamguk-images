# opensamguk-images

Image assets for the opensamguk project, served via jsDelivr CDN.

## CDN Base URL

```
https://cdn.jsdelivr.net/gh/peppone-choi/opensamguk-images@<tag>/
```

## Usage

Reference assets using the jsDelivr immutable URL pattern:

```
https://cdn.jsdelivr.net/gh/peppone-choi/opensamguk-images@v2026.05.21/icons/0.jpg
```

## Versioning

Assets are tagged with `v<YYYY.MM.DD>` for immutable CDN caching.

## Structure

- `game/` — game assets
- `icons/` — icon images
- `hook/` — hook assets
- `originals/` — project-authored source specifications
- `exports/` — generated, deployment-ready project assets
- `previews/` — generated visual QA sheets

### Han map city markers

The county, commandery-seat, and capital map markers are generated from
`originals/map-city-markers/design.json`:

```bash
python3 tools/build-map-city-markers.py
python3 tools/build-map-city-markers.py --check
python3 tools/test-map-city-markers.py
```

## License

The repository's own work — documentation, metadata, and the tooling under
`tools/` and `.github/` — is MIT licensed; see [`LICENSE`](./LICENSE).

**The asset directories `game/`, `hook/`, `icons/`, and `portraits/` are NOT
covered by that license.** They contain third-party derived material or
material of unrecorded origin. This repository claims no copyright in it and
grants no license to it — see [`THIRD-PARTY-NOTICES.md`](./THIRD-PARTY-NOTICES.md)
and the `LICENSE-NOTICE.md` file in each of those directories.

The boundary is declared in [`.license-boundaries.json`](./.license-boundaries.json)
and enforced by `tools/check-license-boundaries.py` (run in CI). Any new
top-level entry must be classified there or the check fails.
