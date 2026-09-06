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
