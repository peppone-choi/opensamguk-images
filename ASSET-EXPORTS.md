# OpenSamguk asset exports

이 저장소가 다음 자작 아이콘의 정본이다.

- 생성기: `tools/assets/build_city_icons.py`, `tools/assets/build_status_icons.py`
- ImageGen 호출 기록(비결정적, 수동): `tools/assets/gen_status_icons_imagegen.py`
- preview: `assets/brand/{city-icons,status-icons}/preview.png`
- export: `web/{game,gateway}/public/{city,status}/`

생성기는 저장소 루트에서 실행한다. `opensamguk`에는 `web/` 아래 export만 같은
상대 경로로 전달한다. 생성기와 preview를 `opensamguk`에 복제하지 않는다.

```bash
python3 tools/assets/build_city_icons.py      # --check 로 드리프트 검사
python3 tools/assets/build_status_icons.py    # --check 로 드리프트 검사
python3 -m unittest tools.assets.test_build_city_icons tools.assets.test_build_status_icons
```

배율 폴더 `<N>x/`는 각 자산의 1x 한 변에 N을 곱한 크기다. 앱은
`/city/${scale}x/…`처럼 배율로 경로를 만든다.

## 도시 아이콘 `web/{game,gateway}/public/city/`

`cast_<level>.png`, level 1–11. 정사각 캔버스, 앵커는 하단 중앙
(64px 규격 anchorX 32/64 · anchorY 63/64 — 하단 여백이 캔버스에 비례: 32·64→1px,
128→2px, 256→4px).

| 경로 | 한 변(px) | 비고 |
| --- | ---: | --- |
| `1x/cast_<level>.png` | 32 | |
| `2x/cast_<level>.png` | 64 | |
| `4x/cast_<level>.png` | 128 | 2026-09-23 추가 — 발자국을 채우는 건물(48–96 CSS px) |
| `8x/cast_<level>.png` | 256 | 2026-09-23 추가 — 경 5×5 근접 확대(최대 약 240 CSS px) |
| `cast_<level>.png` | 64 | 옛 평면 경로(2x 사본) |

배율마다 원화(`assets/city-icons/source/central-plains/`)에서 따로 축소하며,
거점 간 시각 위계(`VISUAL_EXTENT`)는 캔버스에 비례해 유지된다.

## 상태 아이콘 `web/{game,gateway}/public/status/`

| 파일 | 1x | 2x | 4x | 8x |
| --- | ---: | ---: | ---: | ---: |
| `state-{1,2,3,4,5,6,7,8,9,32,34,43}.png` | 16 | 32 | 64 | 128 |
| `state-{isolated,besieged,battle,works}.png` (휘하 신규) | 16 | 32 | 64 | 128 |
| `star-capital.png` | 16 | 32 | 64 | 128 |
| `imperial-residence.png` | 24 | 48 | 96 | — |
| `imperial-npc.png` | 16 | 32 | — | — |

평면 경로 `status/<이름>.png`는 옛 이름(상태 코드 12종·`star-capital`·`imperial-residence`·
`imperial-npc`)에 한해 1x 사본이다. 휘하 신규 4종은 배율 폴더에만 있다.
2026-09-23 재작성으로 `state-*`의 1x 는 24px → 16px, 2x 는 48px → 32px 로 바뀌었다
(`imperial-*`는 바이트 그대로).
