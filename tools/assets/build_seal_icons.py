#!/usr/bin/env python3
"""오픈삼국 인장 아이콘 export 빌더 — 정본 assets/brand/logo-master.png 의 붉은 三國 낙관에서 두 앱의 아이콘을 만든다.

2026-10-02 오픈삼국 저장소 tools/assets/build_brand_assets.py 에서 옮겨 왔다(판정식 · 상수 · 순서 그대로). 정본은 워드마크와 같은
파일이다(D22, MIT — WORDMARK.md). 새로 그리지 않는다 — 낙관 획만 골라 평탄한 붉은색으로 다시 칠해 어두운 정사각 타일에 올린다.

산출(web/{game,gateway}/app/ 에 같은 파일 — Next App Router 가 자동으로 잇는다):
    icon.png        네이티브 해상도 인장 타일(낙관 104×167 + 패딩 = 241×241). 업스케일하지 않는다
    apple-icon.png  180×180(위 타일을 LANCZOS 로 줄임)
    favicon.ico     16 · 32 · 48 멀티사이즈(16px 에서 조금이라도 더 읽히게 패딩을 줄인 193×193 타일에서)

워드마크 전체를 파비콘 크기로 줄이면 「오픈삼국」 네 글자와 부제가 뭉개지므로 인장을 쓴다. 그래도 16px 에서 三國 두 글자 자체가
읽히지는 않는다.

    python3 tools/assets/build_seal_icons.py           # 다시 굽는다
    python3 tools/assets/build_seal_icons.py --check   # 디스크의 사본이 정본에서 나온 것인지 본다(CI)

--check 는 바이트가 아니라 푼 그림을 본다 — PNG · ICO 는 손실 없는 형식이라 픽셀이 정확히 같아야 하지만, 압축 바이트는 OS · zlib
빌드마다 다를 수 있다(build_wordmark.py 참고). ICO 는 16 · 32 · 48 각 크기를 따로 푼다.
"""
from __future__ import annotations

import io
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, IcoImagePlugin

ROOT = Path(__file__).resolve().parents[2]
MASTER = ROOT / "assets" / "brand" / "logo-master.png"
APPS = ("game", "gateway")

PLATE = (15, 13, 12, 255)  # 인장 타일 배경(거의 검정)
SEAL_RGB = (198, 32, 38)  # 낙관 붉은색 정규화 값
# 이 개수 미만의 붉은 픽셀만 있는 행/열은 잡광으로 버린다. 지금 정본에서 정답 상자(104×167)를 내는 구간은 floor 19–32 다
# (전수 탐색 실측). 24 는 그 구간 안에서 여유가 -5/+8 로 고르다. seal_bounds() 의 자기 검증은 DENSITY_FLOOR+8(=32, 안전 구간의
# 정확한 상한)에서도 같은 상자인지 본다 — 낙관 외곽선이 얇아지면 실제로 상자가 줄기 전에 먼저 죽는다.
DENSITY_FLOOR = 24
PAD_RATIO_ICON = 0.22  # icon.png · apple-icon.png 타일 패딩
PAD_RATIO_FAVICON = 0.08  # favicon.ico 타일 패딩(16px 에서 최대한 읽히도록 최소화)
ICO_SIZES = ((16, 16), (32, 32), (48, 48))
APPLE_SIZE = (180, 180)


def is_seal_pixel(r: int, g: int, b: int) -> bool:
    """붉은 낙관 획인가.

    r-g · r-b 만 보면 금박의 어두운 갈색(대표값 220/160/80)도 통과해 옆 글자 「국」의 ㄱ 획이 같이 들어온다. 낙관 붉은색(대표값
    180/20/20)은 g · b 가 둘 다 낮고 서로 비슷하다는 점이 금박과 다르다. 이 식은 금박만 배제한다 — 정본 가운데의 붉은 해 · 깃발도
    통과한다(실측 33,898px 중 89.6% 가 낙관이 아님). 낙관만 남기는 것은 seal_bounds() 의 오른쪽 30% 탐색 창이다.
    """
    return r > 110 and g < 90 and b < 90 and abs(g - b) < 40 and r - g > 60


def seal_bounds(master: Image.Image, floor: int = DENSITY_FLOOR) -> tuple[int, int, int, int]:
    """정본에서 붉은 낙관의 경계(x0, y0, x1, y1 — 끝 포함). 오른쪽 30% 탐색 창이 다른 붉은 요소와의 분리를 맡는다."""
    width, height = master.size
    px = master.load()
    search_from = int(width * 0.7)
    cols: Counter[int] = Counter()
    rows: Counter[int] = Counter()
    for y in range(height):
        for x in range(search_from, width):
            r, g, b, a = px[x, y]
            if a > 8 and is_seal_pixel(r, g, b):
                cols[x] += 1
                rows[y] += 1
    xs = [x for x, count in cols.items() if count >= floor]
    ys = [y for y, count in rows.items() if count >= floor]
    if not xs or not ys:
        raise SystemExit("붉은 낙관을 찾지 못했다 — 정본이 바뀌었으면 임계값을 다시 잡아라")
    bounds = (min(xs), min(ys), max(xs), max(ys))
    if floor == DENSITY_FLOOR:
        # 낙관 상자는 작고 세로로 긴 직사각형이어야 한다. 해 · 깃발이 섞이면 색만으로는 안 죽으므로 여기서 죽는다.
        x0, y0, x1, y1 = bounds
        cw, ch = x1 - x0 + 1, y1 - y0 + 1
        area_ratio = (cw * ch) / (width * height)
        assert area_ratio < 0.02, f"낙관 상자가 너무 크다 — 잡광 혼입 의심: {cw}x{ch} ({area_ratio:.4f})"
        assert 0.4 < cw / ch < 0.9, f"낙관 종횡비 이탈: {cw / ch:.2f}"
        assert seal_bounds(master, floor=floor + 8) == bounds, "DENSITY_FLOOR 여유 부족 — 임계값을 다시 잡아라"
    return bounds


def build_seal_tile(master: Image.Image, pad_ratio: float) -> Image.Image:
    """낙관 획만 평탄한 붉은색으로 다시 칠해 어두운 정사각 타일에 올린다(네이티브 해상도 + 패딩, 업스케일 없음)."""
    x0, y0, x1, y1 = seal_bounds(master)
    crop = master.crop((x0, y0, x1 + 1, y1 + 1))
    crop_w, crop_h = crop.size
    pad = round(max(crop_w, crop_h) * pad_ratio)
    side = max(crop_w, crop_h) + pad * 2

    glyph = Image.new("RGBA", (crop_w, crop_h), (0, 0, 0, 0))
    src = crop.load()
    dst = glyph.load()
    for y in range(crop_h):
        for x in range(crop_w):
            r, g, b, a = src[x, y]
            if a <= 8 or not is_seal_pixel(r, g, b):
                continue
            dst[x, y] = (*SEAL_RGB, min(255, round((r - max(g, b)) * 2.2)))

    tile = Image.new("RGBA", (side, side), PLATE)
    tile.alpha_composite(glyph, ((side - crop_w) // 2, (side - crop_h) // 2))
    return tile.convert("RGB")


def outputs(master: Image.Image) -> dict[Path, Image.Image]:
    icon_tile = build_seal_tile(master, PAD_RATIO_ICON)
    favicon_tile = build_seal_tile(master, PAD_RATIO_FAVICON)
    apple_icon = icon_tile.resize(APPLE_SIZE, Image.LANCZOS)
    rows: dict[Path, Image.Image] = {}
    for app in APPS:
        app_dir = ROOT / "web" / app / "app"
        rows[app_dir / "icon.png"] = icon_tile
        rows[app_dir / "apple-icon.png"] = apple_icon
        rows[app_dir / "favicon.ico"] = favicon_tile
    return rows


def encode(path: Path, image: Image.Image) -> bytes:
    buf = io.BytesIO()
    if path.suffix == ".ico":
        image.save(buf, format="ICO", sizes=list(ICO_SIZES))
    else:
        image.save(buf, format="PNG", optimize=True)
    return buf.getvalue()


def frames(data: bytes, suffix: str) -> dict[tuple[int, int], Image.Image]:
    """파일 바이트를 크기별 RGBA 그림으로 푼다(ICO 는 들어 있는 크기마다)."""
    image = Image.open(io.BytesIO(data))
    if suffix == ".ico":
        assert isinstance(image, IcoImagePlugin.IcoImageFile)
        return {size: image.ico.getimage(size).convert("RGBA") for size in sorted(image.ico.sizes())}
    image.load()
    return {image.size: image.convert("RGBA")}


def same_pixels(want: bytes, have: bytes, suffix: str) -> bool:
    # 픽셀 바이트를 그대로 견준다. ImageChops.difference(...).getbbox() 는 RGBA 에서 알파만 보므로(기본 alpha_only) 색 차이를 놓친다.
    a, b = frames(want, suffix), frames(have, suffix)
    return a.keys() == b.keys() and all(a[k].tobytes() == b[k].tobytes() for k in a)


def main(argv: list[str]) -> int:
    check = "--check" in argv
    if not MASTER.exists():
        raise SystemExit(f"정본이 없다: {MASTER}")
    master = Image.open(MASTER).convert("RGBA")
    rows = outputs(master)
    if check:
        drift = [path for path, image in rows.items()
                 if not path.exists() or not same_pixels(encode(path, image), path.read_bytes(), path.suffix)]
        for path in drift:
            print(f"DRIFT: {path.relative_to(ROOT)}", file=sys.stderr)
        if drift:
            return 1
        print(f"seal icons check OK: {len(rows)} files pixel-match")
        return 0
    for path, image in rows.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(encode(path, image))
    print(f"seal icons rebuilt for: {', '.join(APPS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
