# OpenSamguk asset exports

이 저장소가 다음 자작 아이콘의 정본이다.

- 생성기: `tools/assets/build_city_icons.py`, `tools/assets/build_status_icons.py`, `tools/assets/build_ui_icons.py`, `tools/assets/build_ui_illustrations.py`
- preview: `assets/brand/{city-icons,status-icons,ui-icons,ui-illustrations}/preview.png`
- export: `web/{game,gateway}/public/{city,status,icons,illustrations}/`

UI 아이콘(`icons/`)은 손으로 그린 `assets/ui-icons/source/*.svg`(20×20, `currentColor` 선 1.5px)가 원본이고,
빌더가 개별 SVG 와 sprite `icons.svg`(`<symbol id="ico-<name>">`), `assets/ui-icons/manifest.json` 을 결정적으로 만든다.
`--check` 로 드리프트를 검사하며 CI 에서 돈다.

생성기는 저장소 루트에서 실행한다. `opensamguk`에는 `web/` 아래 export만 같은
상대 경로로 전달한다. 생성기와 preview를 `opensamguk`에 복제하지 않는다.

빈 상태 일러스트(`illustrations/`)는 `assets/ui-illustrations/source/*.svg`(96×96, 청동·이끼 2색 고정)가 원본이고 빌더가 개별 SVG 와
`assets/ui-illustrations/manifest.json` 을 결정적으로 만든다. `<img>` 로 소비하므로 고정색이다. `--check` 가 CI 에서 돈다.

## AI 2D 아이소메트릭 에셋

- 원본·프롬프트·큐레이션: `originals/iso2d/` (제작 규약은 해당 README)
- 추출·검증·내보내기: `tools/assets/*iso2d*.py`
- 조립 검증 이미지: `previews/iso2d/`
- 배포 export: `web/game/public/sprites/iso2d/`
- 고정 태그: `v2026.09.08-iso2d-v1`

108 PNG는 sprite-gen의 `curated/`에서만 복사한다. 원본 시트나 `frames/`를
직접 설치하지 않는다. `export_iso2d_assets.py --check`로 명세와 바이트 동일성을
검사한다. 지도 높이 데이터와 게임 렌더러 구현은 이 에셋 export에 포함되지 않는다.
