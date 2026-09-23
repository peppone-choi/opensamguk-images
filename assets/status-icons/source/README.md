# 상태 아이콘 원화

정본 원화는 OpenAI ImageGen 이미지 편집 모드(`images/edits`)로 만든 픽셀아트 시트다.
결정적 후처리는 `tools/assets/build_status_icons.py`가, ImageGen 호출 기록은
`tools/assets/gen_status_icons_imagegen.py`가 맡는다. 호출 후보는 `raw/`(gitignore)에
떨어지고, 사람이 고른 한 장만 이 폴더로 승격한다.

| 파일 | 격자 | 셀 |
| --- | --- | --- |
| `status-master-imagegen.png` | 4×4 | 1–12 = 상태 코드 `1,2,3,4,5,6,7,8,9,32,34,43`, 13 = 수도 별, 14–16 빈 셀 |
| `status-hwiha-imagegen.png` | 2×2 | 1 고립 · 2 포위 · 3 전투 · 4 공사 |
| `imperial-residence-imagegen.png` | 1장 | 황제 거처(2026-09 이전 판 그대로) |

## 2026-09-23 재작성 (v2)

사용자 결정: 상태 세트 전체를 같은 화풍으로 다시 그리고, 휘하(HWIHA) 신규 상태 4종을
더한다. 배지는 건물 좌상단에 약 15–64 CSS px 로 붙으므로 16px 1x 가독성을 우선한다.

- 모델 `gpt-image-2`, `size=1024x1024`, `quality=high`, 입력 1장(편집 모드).
- 호출 3회: `states` 1회(입력 = v1 `status-master-imagegen.png`) → 채택,
  `hwiha` 2회(입력 = 새 `status-master-imagegen.png`) → 2번째 채택.
  1번째 `hwiha` 후보는 고립(엎어진 수레)이 파편·부스러기로 흩어져 32px 이하에서
  읽히지 않고, 칼이 서양식 곡선 코등이였다.
- 배경은 흰색 단색으로 받고 빌더가 가장자리 flood fill + 둘러싸인 큰 흰 덩어리
  (≥1000 원화 px — 비계 틀 안쪽·목책 사이) 제거로 투명화한다.

### 공통 화풍 (두 시트 프롬프트 끝에 붙는다)

> Commercial-quality 16-bit isometric strategy-game pixel art icons, matching the attached
> reference sheet's art direction: light from the top-left, a dark brown-black 1-pixel outline
> around every shape, 3-step shading (highlight, base, shadow), a limited muted palette, chunky
> visible square pixels. Each icon must read as a STRONG SIMPLE SILHOUETTE that is still
> recognisable when shrunk to a 16x16 sprite: few large shapes, thick forms, no thin lines, no
> tiny details, no scenery, no ground shadow. Every icon centred in its own equal cell with
> generous empty margin; icons never touch or overlap each other. Pure flat white background
> everywhere, no checkerboard, no grid lines, no cell borders, no frames, no text, no numbers,
> no labels, no letters.

### `states` (채택 → `status-master-imagegen.png`)

> Redraw the attached reference as a NEW 4x4 sheet of 16 equal cells, read left-to-right,
> top-to-bottom. Cells 1-13 each hold exactly one icon; cells 14, 15 and 16 stay completely
> empty white.
> 1: a tied sheaf of ripe golden grain (bumper harvest).
> 2: three stacked round bronze Han coins with square holes (prosperity).
> 3: a large pale ice-blue snowflake (severe cold).
> 4: a bone-white skull wrapped in a purple cloud of miasma (plague).
> 5: a broken earth slab split by a deep zigzag crack with two rocks jumping up (earthquake).
> 6: a teal whirling typhoon spiral (typhoon).
> 7: a small tiled-roof house half sunk in dark blue waves (flood).
> 8: a cracked empty wooden bowl with a withered drooping grain stalk and one large green
> locust sitting on the rim (famine and locusts).
> 9: a snapped wooden government signboard with a burning torch and a farmer's hoe crossed
> behind it (popular revolt; NO yellow turban, NO masked bandit).
> 10: a city gate tower engulfed in orange flames (arson and agitation).
> 11: a tied brown loot sack spilling bronze coins (plunder).
> 12: a spear crossed with a red war banner and a bold red arrow pointing right (army
> marching to this city).
> 13: a bold golden five-pointed star with no pedestal (capital).

### `hwiha` 2번째 호출 (채택 → `status-hwiha-imagegen.png`)

> Using the attached sheet only as the style reference (same palette, outline, shading and
> pixel size), draw a NEW 2x2 sheet of 4 equal cells, read left-to-right, top-to-bottom, one
> icon per cell, each icon about half the cell wide, ONE compact solid group per icon with no
> scattered debris, crumbs or loose particles.
> 1: a fat tied grain sack with a thick dark iron chain in front of it snapped in two, the two
> broken chain ends clearly apart (isolated: supply line cut).
> 2: a small stone city gate completely encircled by a ring of sharpened wooden palisade
> stakes and spear points aimed inward (besieged).
> 3: two crossed straight double-edged Han-dynasty jian swords with simple flat bronze guards
> and round pommels, and a small bright spark where the blades meet (battle).
> 4: a builder's hammer crossed with a mason's trowel in front of a small square bamboo
> scaffold frame (construction works).

`hwiha` 1번째(기각) 호출은 위와 같되 "ONE compact solid group…" 문장이 없고, 1번이
"a wooden two-wheeled supply cart tipped over with one broken wheel and a spilled grain sack,
beside a short road that is snapped in two by a gap", 3번이 "two crossed steel swords with
bronze guards and a small bright spark where the blades meet"였다.

## v1 (2026-08) 기록

`status-master-imagegen.png` v1(이 저장소 git 이력)은 같은 4×4 배치였고, 수도 별은
받침대 위에 있었다. 최종 프롬프트의 핵심 조건:

- 상업 게임 수준의 16비트 아이소메트릭 전략게임 픽셀아트
- 4×4 동일 셀, 투명 배경, 글자·라벨·구분선 없음
- 좌상단 광원, 어두운 갈흑색 외곽선, 3단 명암, 제한 팔레트
- 24×24 축소에서도 구분되는 강한 실루엣
- 9번은 황건·도적 세력과 겹치지 않는 민란: 부러진 관아 명패, 횃불, 농기구
- 황제 거처는 검은 면류관, 작은 얼굴, 어두운 자주색 예복을 24×24에서 분리

`imperial-residence-imagegen.png`는 황제 거처 표식의 별도 원화다. 삼국지 7 전국지도의
`献帝` 필터에 쓰인 16×16 황제 흉상을 구도 참조로 삼고, 상태 세트의 팔레트·갈흑색
외곽선·픽셀 밀도에 맞게 ImageGen으로 재작성했다. 추출한 구도 참조는
`reference/rtk7-emperor-filter-icon.png`이며 웹 산출물에는 직접 내보내지 않는다.
