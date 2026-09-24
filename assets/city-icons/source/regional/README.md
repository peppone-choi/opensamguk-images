# 지역별 城 원본

이 디렉터리의 열 장 `*-atlas.png`는 내장 ImageGen으로 만든 투명 배경 원화다. OpenAI API로 만들었던 이전 시안은 폐기했다. 기준 그림은 기존 작전실 城 아이콘의 8x export를 배열한 `../../guides/regional-7.png`와 여백을 늘린 `../../guides/regional-7-roomy.png`다.

각 그림은 좌상단부터 행 우선으로 縣 소(11), 縣(10), 郡 소(5), 郡 중(6), 郡 대(7), 郡 특(8), 수도급(9)을 그린 3×3 판이다. 마지막 수도급 그림은 아래 행 전체를 쓰며, 나머지 두 칸은 비운다. 기존 1–4레벨의 수·관·진·이 그림은 기존 아이콘을 사용한다.

생성 지시는 공통으로 “기존 작전실 2D 성 아이콘의 등각 투영, 일곱 실루엣과 크기 순서 유지, 실제 투명 배경, 각 셀 안 여백, 글자·깃발·국가색 없음, 건물은 지역 건축 특징으로 구분”이었다. 지역 지시는 다음과 같다.

| 양식 | 건축 단서 |
|---|---|
| metropolitan | 사예의 정연한 축선과 검은 기와 |
| central-plain | 예주·연주의 낮고 넓은 황토 성벽 |
| hebei | 기주의 높은 회색 석벽과 탑 |
| east-coast | 청주·서주의 밝은 벽과 해안 잔교 |
| northern-frontier | 유주·병주의 두꺼운 목책과 감시탑 |
| liangzhou | 량주의 건조한 흙벽과 평지붕 |
| jingzhou | 형주의 높은 목조 누각과 남방 지붕 |
| jiangdong | 양주의 흰 회벽과 굽은 기와지붕 |
| sichuan | 익주의 높은 처마와 층진 지붕 |
| lingnan | 교주의 통풍형 전각과 짙은 초목 |

`../../palette.json`은 기존 작전실 아이콘에서 한 번 고정한 96색 팔레트다. 내보내기는 `python3 tools/assets/build_regional_city_icons.py metropolitan central-plain hebei east-coast northern-frontier liangzhou jingzhou jiangdong sichuan lingnan --palette assets/city-icons/palette.json`으로 재생성한다. `--check`는 산출물을 풀어 크기와 RGBA 픽셀이 빌더 출력과 같은지 확인한다(zlib 압축 바이트는 macOS와 Linux에서 다르다). CI(`license-boundaries`)가 이 검사와 `test_build_regional_city_icons`를 돌린다. 추출은 원본 알파를 읽고 셀 경계를 검사한다. 렌더는 32/64/128/256px에서 이웃 셀 그림을 자르지 않고 여백을 확보한다. 각 export는 제 해상도의 픽셀 격자에서 고정 팔레트로 양자화하므로 4x(128px)·8x(256px)도 64px 그림의 확대가 아니라 원본(칸 418px)에서 직접 뽑은 해상도를 가진다. 윤곽선은 64px 기준 굵기를 유지해 1x·2x는 1px, 4x는 2px, 8x는 4px이다. 지도는 모든 배율을 64px 마커 규격(anchor 32/63)으로 맞추므로, 4x·8x를 64px로 환산한 실루엣 폭·가로 중심·바닥선이 2x와 1px 이내여야 한다. 탑 꼭대기처럼 64칸에서는 평균되어 사라지는 가는 부분이 256px에서는 살아나므로 윗변은 조금 높아질 수 있다.
