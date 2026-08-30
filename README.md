# opensamguk-images

Image assets for the opensamguk project, served via jsDelivr CDN.

## CDN Base URL

```
https://cdn.jsdelivr.net/gh/peppone-choi/opensamguk-images@<tag>/
```

## Usage

Reference assets using the jsDelivr immutable URL pattern:

```
https://cdn.jsdelivr.net/gh/peppone-choi/opensamguk-images@<tag>/web/game/public/city/cast_5.png
```

## Versioning

Assets are tagged with `v<YYYY.MM.DD>` for immutable CDN caching.

## Structure

- `assets/brand/` — opensamguk 아이콘 preview 정본
- `tools/assets/` — 자작 아이콘 생성기 정본
- `web/{game,gateway}/public/` — opensamguk에 전달하는 배포용 export
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

새 자작 아이콘의 정본과 생성기는 이 저장소에만 둔다. `opensamguk`에는
실제 프런트 런타임이 소비하는 export만 복사한다. 자세한 전달 경계는
[`ASSET-EXPORTS.md`](./ASSET-EXPORTS.md)를 따른다.

## License

The repository's own work — documentation, metadata, `assets/`, `web/`, and
the tooling under `tools/` and `.github/` — is MIT licensed; see
[`LICENSE`](./LICENSE).


**The asset directory `portraits/` is NOT covered by that license.** It contains third-party derived material or
material of unrecorded origin. This repository claims no copyright in it and
grants no license to it — see [`THIRD-PARTY-NOTICES.md`](./THIRD-PARTY-NOTICES.md)
and its `LICENSE-NOTICE.md` file.

The boundary is declared in [`.license-boundaries.json`](./.license-boundaries.json)
and enforced by `tools/check-license-boundaries.py` (run in CI). Any new
top-level entry must be classified there or the check fails.
