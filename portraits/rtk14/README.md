# RTK14 장수 초상 (portraits/rtk14)

opensamguk 장수 초상 에셋. 삼국지14(RTK14) 인물 일러스트를 원본으로, 게임 UI용
축소판을 함께 보관한다.

> **전량 완결 — 1000종.** 원본·전체프레임·얼굴크롭·얼굴아이콘 각 1000장으로
> 마감됐다. 정본 목록은 `manifest/rtk14-name-file-map.tsv`(1000행), id 조인키는
> `officer-id-registry.tsv`(id 10001-11000)이다. 이중 모드 중복본·reading-파생
> 폐기본은 제외됐다(李衡 판정: `manifest/mismatch-judgment.txt`).

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
- **`face-crop-148x210/`** — **얼굴 크롭** 148×210 PNG(YuNet 얼굴 검출, FALLBACK 0).
  세로 방향 크롭 파라미터 확정치 **얼굴 높이 ×2.1 · face_y 37%**(v3). 파일명은
  full-frame과 동일한 `<sha16>.png`. `report.tsv`(confidence·얼굴폭·수직중심·판정)와
  검수 증적 `qc/`(qc-v3-worst12-vertical·qc-v3-worst12-icon)를 함께 보관한다.
- **`face-icon-96/`** — **얼굴 아이콘** 96×96 PNG. 확정치 **얼굴 높이 ×2.0 · y 50%**.
  파일명은 얼굴 크롭과 동일한 `<sha16>.png`. `report.tsv` 포함.
- **`serving/`** — id 키 서빙 사본(`officer-id-registry.tsv`의 id↔face_crop_file 조인).
  - `serving/portrait/<id>.png` — face-crop-148x210(v3) 사본
  - `serving/icon/<id>.png` — face-icon-96 사본
  - id 범위 **10001-11000**(레거시 0-9xxx 아이콘 풀과 분리). 라이브 컷오버 시 고정.
- **`officer-id-registry.tsv`** — id ↔ name_kanji ↔ reading ↔ face_crop/full_frame/original
  파일 조인키(파생 문서, 원천층 아님). id는 name_kanji 유니코드 코드포인트 정렬로 10001부터 부여.
- **`manifest/`** — 인물명 ↔ 파일 ↔ 취득 URL 매핑.
  - `rtk14-name-file-map.tsv` — 정본 1000행(name·mode·verify·source_url·
    cache_path·output_path·…). 각 디렉터리 파일의 기준 목록.
  - `mismatch-judgment.txt` — reading↔page 모드 충돌본 판정(李衡 등)
  - `famous20.manifest.tsv` / `famous20.json` — famous-20 샘플 매핑·상세
  - `famous20-paths.txt` / `famous20-final-paths.txt` / `famous3-pagemode.json`
    / `smoke.json` — 파이프라인 리포트

## 향후

- CDN 태깅(`v<YYYY.MM.DD>`)은 활성화 시점에 별도로 부여한다.
