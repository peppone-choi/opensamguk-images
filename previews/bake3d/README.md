# 3D 굽기 검수 시트

`tools/assets/bake3d/`가 만든 방향별 대조 시트다. 칸 8개는 왼쪽부터 s, sw, w, nw, n, ne, e, se이고 2배로 키웠으며, 자주색 점이 발 기준점이다.

- `fixtures/`: 시험용 단순 도형(`tools/assets/bake3d/fixtures/`)의 시트. **제품 그림이 아니다.** 카메라·광원·배율은 PROVISIONAL 임시값이다. `node tools/assets/bake3d/preview.mjs --check`가 CI에서 바이트 일치를 검사한다.
- `.color.png`는 조명 색, `.mask.png`는 진영색 마스크(진영색 재질이 있는 모델만)다.
