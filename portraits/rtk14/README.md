# RTK14 장수 초상 (portraits/rtk14)

opensamguk 장수 초상 에셋. 삼국지14(RTK14) 인물 일러스트를 원본으로, 게임 UI용
축소판을 함께 보관한다.

> **생산 진행 중 — 1차 배치.** 초상 취득/가공은 계속 진행되며, 이 디렉터리는
> 배치 단위로 파일이 추가된다. 아래 파일 수는 1차 스냅샷 기준이다.

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
- **`manifest/`** — 인물명 ↔ 파일 ↔ 취득 URL 매핑.
  - `famous20.manifest.tsv` — `이름<TAB>이미지_URL` (famous-20 샘플)
  - `famous20.json` — 인물별 원본/산출물 fingerprint·크기·상태 상세
  - `famous20-paths.txt`, `famous20-final-paths.txt` — 산출물 경로 목록
  - `famous3-pagemode.json`, `smoke.json` — 파이프라인 리포트

## 향후

- `face-crop-148x210/` — 전체 프레임이 아닌 **얼굴 크롭** 변형이 추가될 수 있다.
- CDN 태깅(`v<YYYY.MM.DD>`)은 생산 완료·활성화 시점에 별도로 부여한다.
