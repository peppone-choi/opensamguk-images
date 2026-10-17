# 3D 굽기 도구 (BAKE-0)

단순 도형으로 조립한 3D 모델을 고정 정사영 카메라·고정 광원으로 방향마다 렌더해 투명 PNG와 manifest를 만든다. 이 저장소에는 생성기·시험용 fixture·시험만 둔다. 렌더 의존성(`three` 0.171.0, `@playwright/test` Chromium·SwiftShader WebGL)은 새로 설치하지 않고 **opensamguk 앱의 고정 commit `web/game`** 을 그 lockfile 그대로 설치해 빌려 쓴다.

**상태: PROVISIONAL.** 카메라 각도·광원 방향·타일 배율·칸 크기는 동작 확인용 임시값이다. 아트 일관성 가이드(`originals/aoe2-20261016/docs/art-consistency-guide.md`)의 기준 화면 승인 전에는 정본이 아니다. `fixtures/`의 모델은 `kind: "test-fixture"` 단순 도형이며 제품 그림이 아니다.

## 경로

| 무엇 | 위치 |
| --- | --- |
| 생성기·시험·시험용 fixture | `tools/assets/bake3d/` |
| 실제 3D 원본 모델(아직 없음) | `originals/<세트>/models/` |
| 검수 시트 | `previews/bake3d/` (fixture 시트는 `previews/bake3d/fixtures/`) |
| 앱 배포 export | 아직 없음. 승인 뒤 `ASSET-EXPORTS.md` 규칙으로 별도 작업 |

## 실행

opensamguk 앱 checkout에서 `web`에서 `corepack pnpm install --frozen-lockfile --filter "@opensamguk/web-game..."`, `web/game`에서 `corepack pnpm exec playwright install chromium`을 마친 뒤 이 저장소 루트에서:

```sh
export BAKE3D_DEPS_ROOT=/path/to/opensamguk/web/game
node tools/assets/bake3d/bake.mjs \
  --config tools/assets/bake3d/config.provisional.json \
  --model tools/assets/bake3d/fixtures/primitive-building.json \
  --out ./bake-out
node --test tools/assets/bake3d/test/*.test.mjs
node tools/assets/bake3d/preview.mjs --check   # 인자 없이 실행하면 시트를 다시 쓴다
```

`--deps`가 `BAKE3D_DEPS_ROOT` 대신 쓰인다. `--chromium <실행파일>` 또는 `BAKE3D_CHROMIUM_PATH`로 다른 Chromium을 지정할 수 있다. 렌더 시험은 의존성·Chromium을 찾지 못하면 이유를 적고 건너뛴다. 실제 검증에는 `BAKE3D_REQUIRE_RENDER=1`을 지정하여 누락을 실패로 처리한다. `BAKE3D_EVIDENCE_DIR`를 주면 출력·대조 시트·결정성 통계(`render-evidence.json`)를 남긴다.

자동 CI는 2026-10-17 사용자 지시에 따라 중지되어 있다. 검증 담당자가 앱 commit과 Node·Chromium 버전을 고정하고, 그 앱의 `web/game` 의존성을 `BAKE3D_DEPS_ROOT`로 지정해 로컬에서 실행한다.

```sh
BAKE3D_REQUIRE_RENDER=1 node --test tools/assets/bake3d/test/*.test.mjs
node tools/assets/bake3d/preview.mjs --check
```

명령·앱 commit·브라우저 버전·실제 시험 결과를 함께 보존한다. 앱 commit이나 Chromium 빌드를 바꾸면 preview 해시를 다시 확인한다. 자동 검증이 수행됐다고 가정하지 않는다.

## 입력

- 설정(`opensamguk-bake3d-config/0`): `status`(`PROVISIONAL` 또는 `approvalRef`가 있는 `APPROVED`), `cell`, `anchor`(세계 원점 = 발 기준점이 놓일 픽셀), `camera`(`orthographic`, `elevationDeg`, `yawDeg`, `tileDiamondWidthPx`), `light`(`directionCamera` = 화면 기준 광원 쪽 벡터 x 오른쪽·y 위·z 보는 쪽, 세기 2개), `directions`, `ramp`. 숨은 기본값은 없다. 고도 30°에서 바닥 타일은 2:1 마름모가 된다.
- 모델(`opensamguk-bake3d-model/0`): `materials`(`#rrggbb`, `team: true`는 진영색 영역)와 `parts`(`box`·`cylinder`·`cone`·`sphere`, 위치·회전·재질). 1 단위 = 타일 한 변, 원점 = 발, 앞쪽 = +Z.

## 처리

- 방향(`s`부터 화면 시계 방향 8개)마다 **모델만** Y축으로 돌린다. 카메라와 광원은 고정이라 좌우 반전 없이 방향마다 따로 렌더한다.
- 패스 2개: 조명 색(`MeshLambertMaterial`, flat), 재질 id(빨강 채널 = 재질 번호, 0 = 배경). 안티앨리어싱 없음.
- alpha bbox로 자르고, 발 기준점은 칸 기준점 − bbox 원점이다. 다음은 실패로 멈추고 출력하지 않는다: 빈 렌더 `EMPTY`, 칸 가장자리에 닿음 `CLIPPED`, 두 패스 범위 불일치 `PASS_MISMATCH`, 기준점이 프레임 밖 `ANCHOR_OUTSIDE_FRAME`, 기존 출력 폴더 `OUTPUT_EXISTS`. 임시 폴더에서 모두 통과한 뒤에만 게시한다.
- 진영색 마스크: team 재질 픽셀만 조명 색의 밝기를 같은 회색으로, alpha 255.
- 팔레트·재질 램프·색 줄이기·바닥 그림자는 하지 않는다(manifest `postprocess`에 `NOT_RUN`). `ramp`가 null이 아니면 `RAMP_NOT_APPROVED`로 거부한다.

## 출력

- `frames/<방향>.{color,mask,matid}.png`: 잘린 RGBA PNG. 메타데이터 없음, 고정 deflate.
- `manifest.json`(`opensamguk-bake3d-manifest/0`): 상태, 도구·three·브라우저·GL 렌더러, 모델·설정 파일 SHA256, 카메라·광원, 방향별 yaw·bbox·프레임 크기·발 기준점·파일 SHA256. 시각·절대 경로는 넣지 않는다.
- `artpack-units-fragment.json`: 앱 `tools/assets/artpack`(PR #1639) 입력 spec의 `units` 부분 형식. A2 계약 방향(sw·nw·ne·se)만 담는다. 지형·그림자 선언이 없어 완성 spec이 아니며 `artpack check`는 아직 돌리지 않았다.

## 결정성

같은 설정·모델·도구·Chromium/SwiftShader 빌드에서 같은 바이트를 낸다. 렌더 시험이 새 브라우저로 두 번 구워 모든 파일을 바이트 비교하고, 픽셀 차이 수·최대 채널 차이도 기록한다. `preview.mjs --check`는 저장된 시트와 바이트 비교한다. 다른 Chromium·러너 이미지 사이의 바이트 일치는 보장하지 않는다.
