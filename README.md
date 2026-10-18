# opensamguk-images

오픈삼국(opensamguk) 이미지의 **정본 저장소**다. 원화 · 생성기 · 검수 시트는 여기에만 두고, 앱 저장소에는 실제로 화면이 쓰는 **export 사본**만 보낸다.

- 문서 색인: [docs/index.md](docs/index.md)
- 지금 무엇이 쓰이고 무엇이 폐기·미사용인지: [docs/asset-status.md](docs/asset-status.md)
- export 를 앱에 보내는 규칙(파일 · 크기 · 해시): [ASSET-EXPORTS.md](ASSET-EXPORTS.md)

## 앱에 가는 길

앱이 이 저장소의 이미지를 받는 길은 둘이다.

| 길 | 무엇 | 앱 쪽 근거 |
| --- | --- | --- |
| **바이트 사본** | UI 아이콘 · 빈 상태 그림 · 워드마크 · 앱 아이콘 · 황제 NPC 표지 · 계책 카드 · 와룡전 지도 키트 · 와룡전 전장 키트 · 전장 `catalog-v1.json` | 앱 `web/{game,gateway}/public/`, `data/map/waryong/<kitId>/export.json`(원본 경로와 commit 기록) |
| **jsDelivr CDN** | RTK14 장수 초상 `portraits/rtk14/serving/{original,portrait,icon}/<id>` | 앱 `web/shared/src/portraitResolver.ts` |

CDN 기본값은 태그 없이 이 저장소의 기본 브랜치를 가리킨다.

```
https://cdn.jsdelivr.net/gh/peppone-choi/opensamguk-images/portraits/rtk14/serving/portrait/10001.png
```

그래서 **`portraits/rtk14/serving/` 의 경로나 파일명을 바꾸면 운영 초상이 바로 깨진다.** 고정 URL 이 필요하면 `@<tag>` 를 붙인다. 태그 형식은 `v<YYYY.MM.DD>`(예: `v2026.09.06`)다.

바이트 사본은 앱 저장소에 들어간 순간 앱이 이 저장소를 다시 읽지 않는다. 새 판을 보내려면 [ASSET-EXPORTS.md](ASSET-EXPORTS.md)의 절차로 앱에 다시 복사한다.

## 폴더 지도

| 폴더 | 무엇 | 상태 |
| --- | --- | --- |
| `waryong/map/` | 와룡전 전략 지도 타일 키트 · 표지 · 깃발 천 · 1칸 거점 · 합성 통계(원작 추출 그대로, U3) | 정본 · 앱 사용 |
| `waryong/battle/kit/` · `catalog-v1.json` | 와룡전 전장 214판 조각 키트 · 지형 목록 | 정본 · 앱 사용 |
| `waryong/battle/maps/` · `units/` | 미리 그린 214판 PNG · 유닛 PNG(키트의 원천 파생) | 보관 · 앱 미사용 |
| `waryong/previews/` | 지도 키트 검수 시트 | 검수 |
| `portraits/rtk14/serving/` | 장수 ID 키 초상 3종(CDN) | 운영 · 앱 사용 |
| `portraits/rtk14/` 나머지 | 원본 · 축소 · 얼굴 자르기 · 목록 · 조사 기록 | 원천 |
| `assets/` | 자작 아이콘 · 그림 · 워드마크의 원화와 preview | 정본 |
| `web/{game,gateway}/` | 앱으로 보내는 export(같은 상대 경로) | export · 일부 미사용 |
| `exports/` | 계책 카드 export | export · 일부 미사용 |
| `originals/` | 사람이 쓴 명세 · 프롬프트 · 원본 | 원천 · 일부 폐기 |
| `previews/` | 생성 결과 검수 시트 | 검수 · 일부 폐기 |
| `portraits-original/` | 자작 한대 인물 원형 초상 | 앱 미사용 |
| `tools/` | 생성기 · 점검 도구 | 도구 |
| `docs/` | 저장소 문서 | 문서 |

폐기 · 미사용 판정과 근거는 [docs/asset-status.md](docs/asset-status.md)에 있다. 아이소 지도는 폐기됐다(지도는 와룡전 탑다운 타일). 와룡전 거점으로 대체된 도시 아이콘 · 자작 城 표지는 2026-10-18 D175 로 지웠다.

## 로컬 점검

CI 는 2026-10-17 에 은퇴했다([docs/development/ci-retirement-2026-10-17.md](docs/development/ci-retirement-2026-10-17.md)). 변경하면 닿는 점검을 저장소 루트에서 직접 돌린다.

```bash
python3 tools/check-license-boundaries.py
python3 -m unittest tools.test_waryong_map_assets tools.test_waryong_battle_assets tools.test_waryong_battle_kit
python3 -m unittest tools.assets.test_build_ui_icons tools.assets.test_build_ui_illustrations tools.assets.test_build_status_icons tools.assets.test_build_seal_icons tools.assets.test_build_wordmark
python3 tools/cards/build_card_display.py --check
(cd tools && python3 test_build_original_portraits.py)
node --test tools/assets/bake3d/test/*.test.mjs
```

- 생성기 대부분은 `--check` 로 드리프트를 검사한다(예: `python3 tools/assets/build_ui_icons.py --check`).
- 와룡전 키트를 다시 만들려면 원작 추출본(`~/.cache/waryongjeon/extract/Src`)이 필요하다. 원작 바이너리는 Git 에 넣지 않는다.
- bake3d 렌더 시험은 `BAKE3D_DEPS_ROOT`(앱 고정 commit 의 `web/game` 의존성)가 없으면 건너뛴다([tools/assets/bake3d/README.md](tools/assets/bake3d/README.md)). 저장소가 한글 같은 비ASCII 경로에 있으면 `render.test.mjs` 가 ENOENT 로 실패한다(20행이 `URL.pathname` 을 그대로 쓴다). 영문 경로의 사본에서 돌린다.

## License

The repository's own work — documentation, metadata, `assets/`, `web/`, and
the tooling under `tools/` and `.github/` — is MIT licensed; see
[`LICENSE`](./LICENSE).


**The asset directory `portraits/` is NOT covered by that license.** It contains third-party derived material
(RTK14 character illustrations) or material of unrecorded origin. This repository claims no copyright in it and
grants no license to third parties. Since 2026-09-06 it is classified `owner-accepted`: the repository owner
uses it in the OpenSamguk product on their own responsibility — see [`THIRD-PARTY-NOTICES.md`](./THIRD-PARTY-NOTICES.md)
and `portraits/LICENSE-NOTICE.md`.

The boundary is declared in [`.license-boundaries.json`](./.license-boundaries.json)
and enforced by `tools/check-license-boundaries.py` (run locally; CI was retired on 2026-10-17). Any new
top-level entry must be classified there or the check fails.

`waryong/` 도 `.license-boundaries.json` 에서 `owner-accepted` 로 분류돼 있다(권리자 UNKNOWN, 2026-09-26 수락). 고지는 `waryong/LICENSE-NOTICE.md` 와 [`THIRD-PARTY-NOTICES.md`](./THIRD-PARTY-NOTICES.md)를 따른다.
