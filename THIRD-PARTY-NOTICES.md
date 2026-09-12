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

An `owner-accepted` entry is third-party material that the repository owner has
explicitly decided to use in the OpenSamguk product, taking the responsibility
for that use. It stays outside the root MIT license; the label records the
decision, it does not grant anyone else a license.

---

## `portraits/` — RTK14 character illustrations and derivatives

| Item | Detail |
| --- | --- |
| Paths | `portraits/rtk14/original/`, `full-frame-148x210/`, `face-crop-148x210/`, `face-icon-96/`, `serving/` |
| Original rights holder | Koei Tecmo Games Co., Ltd. — character illustrations from *Romance of the Three Kingdoms XIV* (三國志14 / RTK14) |
| Acquisition source | Attachment images on the RTK14 wikiwiki, `https://wikiwiki.jp/sangokushi14/` (`cdn.wikiwiki.jp/.../::attach/*.jpg`). Per-file source URLs are recorded in `portraits/rtk14/manifest/rtk14-name-file-map.tsv`. |
| Current state | 1000 acquired originals (stored byte-preserved as `<sha256>.bin`) plus mechanically derived resizes/crops (148×210 full-frame, 148×210 face crop, 96×96 face icon) and id-keyed serving copies. Derivative processing does not create a new independent work here; the derivatives carry the same status as the originals. |
| Status | Third-party derived. No license granted by this repository to third parties. **Owner-accepted for use in the OpenSamguk product** (`.license-boundaries.json` classification `owner-accepted`, accepted 2026-09-06 by the repository owner, who takes the responsibility; see `portraits/LICENSE-NOTICE.md` and opensamguk ADR-LITE-048). |

`portraits/rtk14/README.md`, `manifest/*`, `officer-id-registry.tsv` and
`*/report.tsv` are pipeline metadata authored for this project, but they describe
and index the third-party material and are kept inside the third-party boundary
for clarity.

## Reporting

If you are a rights holder for any of the above and want a path removed or its
entry corrected, open an issue on this repository.

### 2026-08-17 — 선택 시나리오 아이콘 세트 전량 제거

아래 10개 세트(총 2,335장)와 그에 딸린 `game/map/pokemon_v1/`을 **히스토리까지** 제거했다
(`git filter-repo` + force push). 이 리포는 공개 저장소이고, 해당 세트는 실존 인물의 사진
또는 제3자가 권리를 보유한 캐릭터 아트였다.

| 제거된 경로 | 장수 | 제거 사유 |
| --- | --- | --- |
| `icons/걸그룹/` | 530 | 실존 인물 사진 — 사진 저작권 + 초상권(퍼블리시티권) |
| `icons/스타1프로게이머/` | 297 | 실존 인물 사진 — 동일 |
| `icons/롤시나리오/` | 439 | Riot Games 캐릭터 아트 + 실존 프로선수 사진 |
| `icons/루드라사움/` | 464 | 출처 미확인 (UNKNOWN) |
| `icons/포켓몬스터/` | 291 | The Pokémon Company / Nintendo / Game Freak |
| `icons/환상향/` | 176 | 東方Project (上海アリス幻樂団) 및 2차 창작 |
| `icons/강서유서월드/` | 108 | 출처 미확인 (UNKNOWN) |
| `icons/쿠키런킹덤/` | 22 | Devsisters Corp. |
| `icons/삼모시네마틱유니버스/` | 7 | 출처 미확인 (UNKNOWN) |
| `icons/삼국지6/` | 1 | 코에이 테크모 (삼국지6) |
| `game/map/pokemon_v1/` | 1 | 위 포켓몬 시나리오 전용 맵 — 참조 시나리오 제거로 고아가 됨 |

전부 삼국지 시나리오와 무관한 선택 시나리오 전용 자산이며, 메인 레포에서 이들을 참조하던
비-삼국지 시나리오 데이터도 함께 제거된다.

**주의 — jsDelivr 캐시.** 히스토리 재작성으로 이전 커밋 SHA는 사라지지만, jsDelivr가
이미 캐싱한 SHA 고정 URL은 캐시가 만료될 때까지 잠시 더 응답할 수 있다. GitHub 쪽 객체는
재작성 시점에 접근 불가가 된다.

`game/map/ludo_rathowm/`은 **남긴다** — 아이콘 세트는 제거됐지만 시나리오 2180이 여전히 그 맵을 쓴다.
