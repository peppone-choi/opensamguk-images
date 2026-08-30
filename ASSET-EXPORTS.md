# OpenSamguk asset exports

이 저장소가 다음 자작 아이콘의 정본이다.

- 생성기: `tools/assets/build_city_icons.py`, `tools/assets/build_status_icons.py`
- preview: `assets/brand/{city-icons,status-icons}/preview.png`
- export: `web/{game,gateway}/public/{city,status}/`

생성기는 저장소 루트에서 실행한다. `opensamguk`에는 `web/` 아래 export만 같은
상대 경로로 전달한다. 생성기와 preview를 `opensamguk`에 복제하지 않는다.

