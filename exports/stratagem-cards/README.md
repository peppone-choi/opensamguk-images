# 계책 카드 그림 (채택본 32장)

- 512×768 WebP. 생성: OpenAI Images API `gpt-image-1-mini`, 명세 `originals/stratagem-cards/design.json`(스타일 `bright` + `periodRules`).
- 후보·프롬프트·해시·채택 여부는 `originals/stratagem-cards/provenance.json` 의 `adopted` 에 있다. 채택은 QA 1–4차(명세의 `qaFirstPass`·`qaSecondPass`)를 거친 사람 판단이다.
- 다시 만들 때: `python3 tools/cards/generate_card_art.py --cards <id> --style bright --quality medium` 로 후보를 뽑고 provenance 의 `adopted` 를 갱신한 뒤 이 폴더를 다시 쓴다.
