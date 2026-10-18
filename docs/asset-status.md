# 자산 상태 — 앱 사용 · 미사용 · 삭제됨

기준: 2026-10-18, 이 저장소 main `4b74765` · 앱 main `2ebffe8f2`. 앱 저장소의 `git ls-tree` 와 `git grep` 으로 대조했다. 화면 실행으로 확인한 표는 아니다.

**지운 자산은 아래 「삭제됨」 절에 복원법과 함께 적는다.** 그 밖의 삭제 · 이동은 따로 승인받아 별도 변경으로 한다(2026-10-18 D175 범위 밖은 보존).

## 상태 뜻

| 상태 | 뜻 |
| --- | --- |
| 사용 | 앱 main 에 바이트 사본이 있거나 CDN 으로 부른다 |
| 원천 | 앱이 직접 쓰지 않지만 사용 중인 export 를 다시 만드는 출발점이다 |
| 미사용 | 쓸 수 있는 상태지만 앱 참조가 0이다 |
| 삭제됨 | 지웠다. 표의 방법으로 되돌릴 수 있다 |

## 사용

| 자산 | 정본 · export | 앱이 받는 길 |
| --- | --- | --- |
| 와룡전 전략 지도 키트 | `waryong/map/` | 바이트 사본 `public/map/waryong/<kitId>/`, `data/map/waryong/<kitId>/` |
| 와룡전 전장 조각 키트 | `waryong/battle/kit/` | 바이트 사본 `public/battle/waryong/<kitId>/` |
| 전장 지형 목록 | `waryong/battle/catalog-v1.json` | 서버 바이트 사본(해시 고정, [ASSET-EXPORTS.md](../ASSET-EXPORTS.md)) |
| RTK14 장수 초상 | `portraits/rtk14/serving/` | jsDelivr CDN. **경로 · 파일명을 바꾸면 운영 초상이 깨진다** |
| UI 아이콘 sprite | `assets/ui-icons/` → `web/*/public/icons/` | 바이트 사본. 73종 가운데 약 25종은 아직 화면이 부르지 않는다(명령 상태 `cmd-*` · 자원 `res-*` · 부서 `dept-*` · `hub-*` 등) |
| 빈 상태 그림 | `assets/ui-illustrations/` → `web/*/public/illustrations/` | 바이트 사본 |
| 워드마크 · 인장 앱 아이콘 | `assets/brand/` → `web/*/public/logo-wordmark*`, `web/*/app/` | 바이트 사본 |
| 황제 NPC 표지 | `assets/status-icons/` → `web/*/public/status/imperial-npc.png` | 바이트 사본 |
| 계책 카드 그림 | `exports/stratagem-cards/display/` | 32장 가운데 2장(`gyeonbyeok` · `ganpa`) 사본. 서버가 두 종류만 준다 |

## 원천

| 자산 | 무엇 |
| --- | --- |
| `portraits/rtk14/{original,full-frame-148x210,face-crop-148x210,face-icon-96}/` | `serving/` 의 출처(원본과 가공 단계) |
| `waryong/battle/maps/` · `units/` | 미리 그린 214판 · 유닛 PNG. 앱은 키트로 조립하지만 `tools/test_waryong_battle_assets.py` 가 목록을 본다 |
| `originals/stratagem-cards/` · `previews/stratagem-cards/` | 카드 명세 · 후보 검수 시트 |

## 미사용

| 자산 | 크기 | 근거 |
| --- | ---: | --- |
| 상태 아이콘 `state-*` · `star-capital` · `imperial-residence` | 약 0.8 MB | 앱 참조 0(같은 폴더의 `imperial-npc` 는 사용) |
| 자작 원형 초상 `portraits-original/han-archetypes/` | 3.3 MB | 앱 참조 0 |
| 전투 말 시안 `originals/battle-tokens/` · `previews/battle-tokens/` | 0.3 MB | 채택되지 않았다. 앱 참조 0 |
| 3D 굽기 `tools/assets/bake3d/` · `previews/bake3d/` | 0.1 MB | PROVISIONAL, 앱 export 없음 |

## 삭제됨

| 자산 | 지운 날 · 근거 | 되돌리는 법 |
| --- | --- | --- |
| 도시 아이콘 `assets/city-icons/` · `assets/brand/city-icons/` · `web/{game,gateway}/public/city/` · `tools/assets/{build,test_build}_city_icons.py` · `{build,test_build}_regional_city_icons.py` | 2026-10-18 D175(앱 사본 · 참조 0, 와룡전 거점으로 대체). 황제 NPC 표지가 쓰던 도우미는 `build_status_icons.py` 로 옮겼다 | 삭제 커밋을 `git revert` 하거나 그 부모에서 `git restore --source=<부모> -- <경로>` |
| 자작 城 표지 `exports/map/markers/` · `originals/map-city-markers/` · `tools/{build,test}-map-city-markers.py` · `tools/requirements-map-markers.txt` | 2026-10-18 D175(와룡전 `sites.png` 로 대체) | 같음 |
| 아이소 2D `originals/iso2d/` · `previews/iso2d/` · `web/game/public/sprites/iso2d/` · `tools/assets/*iso2d*`(시험 포함 9) | 2026-10-18 D175(아이소 지도 폐기, 앱 참조 0) | 태그 `v2026.09.10-iso2d-v2`(export 판) 또는 삭제 커밋 부모에서 `git restore --source` |

## 앱이 부르지만 이 저장소에 없는 경로

앱 코드에 아래 CDN 경로가 남아 있지만 이 저장소에는 그 폴더가 없다. 항상 404 이고 앱은 그림을 숨기거나 기본 초상으로 바꾼다. 이 저장소에서 고칠 일이 아니라 앱에서 지울 일이다.

- `${CDN}/game/*` — 앱 `web/game/lib/constants.ts` 의 `ICON_CDN`(병종 아이콘 · 진행 막대 배경)
- `${CDN}/icons/<picture>` — 옛 초상 풀(`portraitResolver.ts` 의 `PORTRAIT_CDN`)
