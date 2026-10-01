# 계책 카드 그림 (채택본 32장)

- 512×768 WebP. 생성: OpenAI Images API `gpt-image-1-mini`, 명세 `originals/stratagem-cards/design.json`(스타일 `bright` + `periodRules`).
- 후보·프롬프트·해시·채택 여부는 `originals/stratagem-cards/provenance.json` 의 `adopted` 에 있다. 채택은 QA 1–4차(명세의 `qaFirstPass`·`qaSecondPass`)를 거친 사람 판단이다.
- 다시 만들 때: `python3 tools/cards/generate_card_art.py --cards <id> --style bright --quality medium` 로 후보를 뽑고 provenance 의 `adopted` 를 갱신한 뒤 이 폴더를 다시 쓴다.

## 표시용 `display/` (308×462)

앱은 카드를 154×231 로 그린다. `display/<id>.webp` 는 채택본을 그 2배(308×462)로 줄인 WebP(손실 q85)다 — 장당 약 20 KB(채택본 40–53 KB), 채택본을 다시 줄인 것과의 PSNR 37 dB 안팎. 앱 `public/stratagem-cards/` 에는 이것을 export 로 둔다.

- 다시 만들 때: `python3 tools/cards/build_card_display.py`, 확인: `--check`(CI). 확인은 바이트가 아니라 푼 그림으로 한다 — 이름 집합 · 크기 · PSNR ≥ 34 dB.
- 채택본을 바꾸면 display 도 다시 만든다(`--check` 가 빨개진다).
