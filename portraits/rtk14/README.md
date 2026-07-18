# RTK14 장수 초상 (portraits/rtk14)

opensamguk 장수 초상 에셋. 삼국지14(RTK14) 인물 일러스트를 원본으로, 게임 UI용
축소판을 함께 보관한다.

> **전량 완결 — 1000종.** 원본·전체프레임·얼굴크롭 각 1000장으로 마감됐다.
> 정본 목록은 `manifest/rtk14-name-file-map.tsv`(1000행)이며, 각 디렉터리의
> 파일은 이 목록의 `cache_path`/`output_path` 기준으로 정렬된다. 이중 모드
> 중복본·reading-파생 폐기본은 제외됐다(李衡 판정: `manifest/mismatch-judgment.txt`).

## 출처

- 원본: **RTK14 wikiwiki** (`https://wikiwiki.jp/sangokushi14/`) 의 인물 일러스트.
  각 인물 페이지의 첨부 이미지(`cdn.wikiwiki.jp/.../::attach/*.jpg`)를 취득한다.
- 취득 URL은 매니페스트/리포트 파일에 인물명과 함께 기록된다.

## 취득·가공 파이프라인

메인 레포(비공개)의 `tools/rtk-faces/build_rtk14_faces.py`가 다운로드→정규화→
리사이즈를 수행한다. 산출물은 두 형태로 이 레포에 보관된다.

## 디렉터리

- **`original/`** — 취득한 원본 이미지(대부분 JPEG). 파일명은 원본 바이트의
  SHA-256 해시이며 확장자는 `.bin`(컨테이너 무관 원본 보존).
- **`full-frame-148x210/`** — full-frame 비율 축소판. 원본 전체 프레임을
  **148×210 PNG**로 리사이즈한 게임 UI용 초상. 파일명은 대응 원본 SHA-256의
  **앞 16자리 hex**(`<sha16>.png` ↔ `original/<sha256>.bin`).
- **`face-crop-148x210/`** — 전체 프레임이 아닌 **얼굴 크롭** 148×210 PNG(YuNet
  얼굴 검출 기반, FALLBACK 0). 파일명은 full-frame과 동일한 `<sha16>.png`.
  `report.tsv`(인물별 confidence·얼굴폭·수직중심·판정)와 검수 증적 몽타주
  `qc/`(montage-*·_spot_*)를 함께 보관한다.
- **`manifest/`** — 인물명 ↔ 파일 ↔ 취득 URL 매핑.
  - `rtk14-name-file-map.tsv` — 정본 1000행(name·mode·verify·source_url·
    cache_path·output_path·…). 각 디렉터리 파일의 기준 목록.
  - `mismatch-judgment.txt` — reading↔page 모드 충돌본 판정(李衡 등)
  - `famous20.manifest.tsv` / `famous20.json` — famous-20 샘플 매핑·상세
  - `famous20-paths.txt` / `famous20-final-paths.txt` / `famous3-pagemode.json`
    / `smoke.json` — 파이프라인 리포트

## 향후

- CDN 태깅(`v<YYYY.MM.DD>`)은 활성화 시점에 별도로 부여한다.
