#!/usr/bin/env python3
"""한나라 지도 도시 아이콘 빌더.

ImageGen 원화에서 가짜 체크무늬 배경을 제거하고, 64px 공통 캔버스에 각 거점의
시각적 위계를 적용한다. 원화와 빌더의 정본은 opensamguk-images에만 두고,
opensamguk에는 ``web/`` 아래 배포본만 전달한다.

    python3 tools/assets/build_city_icons.py
    python3 tools/assets/build_city_icons.py --check
"""

from __future__ import annotations

import argparse
import io
import sys
from collections import deque
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw, ImageEnhance, ImageFilter


ROOT = Path(__file__).resolve().parents[2]
LEVELS = tuple(range(1, 12))
APPS = ("gateway", "game")
CANVAS_SIZE = 64
SOURCE_DIR = ROOT / "assets" / "city-icons" / "source" / "central-plains"
PROCESSED_DIR = ROOT / "assets" / "city-icons" / "processed" / "central-plains"
PREVIEW = ROOT / "assets" / "brand" / "city-icons" / "preview.png"

# 실루엣의 최대 변 길이. 소(군치)는 영현보다, 영현은 장현보다 반드시 크다.
VISUAL_EXTENT = {
    1: 42,
    2: 40,
    3: 44,
    4: 40,
    5: 48,
    6: 52,
    7: 56,
    8: 60,
    9: 62,
    10: 34,
    11: 27,
}


def source_path(level: int) -> Path:
    return SOURCE_DIR / f"cast_{level}.png"


def _background_candidate(pixel: tuple[int, int, int]) -> bool:
    """ImageGen이 구운 흰색/회색 체크무늬 한 픽셀인지 판별한다."""
    lo, hi = min(pixel), max(pixel)
    return lo >= 226 and hi - lo <= 22


def remove_checkerboard_background(source: Image.Image) -> Image.Image:
    """가장자리와 이어진 밝은 무채색 배경만 투명하게 만든다.

    단순 색상 키가 아니라 flood fill을 쓰므로, 검은 외곽선 안쪽의 밝은 석벽과
    흰 돛은 보존된다. 이 입력은 픽셀아트 원화이므로 이진 알파가 가장 선명하다.
    """
    if source.mode == "RGBA" and source.getchannel("A").getextrema()[0] == 0:
        return source.copy()

    rgb = source.convert("RGB")
    width, height = rgb.size
    pixels = rgb.load()
    background = bytearray(width * height)
    queue: deque[tuple[int, int]] = deque()

    def add(x: int, y: int) -> None:
        idx = y * width + x
        if background[idx] or not _background_candidate(pixels[x, y]):
            return
        background[idx] = 1
        queue.append((x, y))

    for x in range(width):
        add(x, 0)
        add(x, height - 1)
    for y in range(height):
        add(0, y)
        add(width - 1, y)

    while queue:
        x, y = queue.popleft()
        if x:
            add(x - 1, y)
        if x + 1 < width:
            add(x + 1, y)
        if y:
            add(x, y - 1)
        if y + 1 < height:
            add(x, y + 1)

    out = rgb.convert("RGBA")
    alpha = Image.new("L", (width, height), 255)
    alpha.putdata([0 if flag else 255 for flag in background])
    out.putalpha(alpha)
    return out


def _pixel_hint(image: Image.Image) -> Image.Image:
    """작은 크기에서 고전 전략게임식 계단과 명암을 남긴다."""
    alpha = image.getchannel("A").point(lambda value: 255 if value >= 96 else 0)
    rgb = Image.new("RGB", image.size, (20, 18, 16))
    rgb.paste(image.convert("RGB"), mask=alpha)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.08)
    rgb = ImageEnhance.Color(rgb).enhance(1.06)
    rgb = rgb.filter(ImageFilter.UnsharpMask(radius=0.7, percent=190, threshold=2))
    rgb = rgb.quantize(colors=48, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE).convert("RGBA")
    rgb.putalpha(alpha)

    outline_alpha = ImageChops.subtract(alpha.filter(ImageFilter.MaxFilter(3)), alpha)
    outlined = Image.new("RGBA", image.size, (20, 17, 14, 0))
    outlined.putalpha(outline_alpha)
    outlined.alpha_composite(rgb)
    return outlined


def render_icon(level: int, canvas_size: int = CANVAS_SIZE) -> Image.Image:
    source = Image.open(source_path(level))
    extracted = remove_checkerboard_background(source)
    bbox = extracted.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"cast_{level}: foreground not found")

    cropped = extracted.crop(bbox)
    extent = round(VISUAL_EXTENT[level] * canvas_size / CANVAS_SIZE)
    scale = min(extent / cropped.width, extent / cropped.height)
    size = (
        max(1, round(cropped.width * scale)),
        max(1, round(cropped.height * scale)),
    )
    resized = _pixel_hint(cropped.resize(size, Image.Resampling.LANCZOS))

    canvas = Image.new("RGBA", (canvas_size, canvas_size), (0, 0, 0, 0))
    x = (canvas_size - resized.width) // 2
    y = canvas_size - resized.height - 1
    canvas.alpha_composite(resized, (x, y))
    return canvas


def render_variants(level: int) -> dict[int, Image.Image]:
    return {1: render_icon(level, 32), 2: render_icon(level, 64)}


def _png_bytes(image: Image.Image) -> bytes:
    buf = io.BytesIO()
    image.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def preview_sheet(icons: dict[int, dict[int, Image.Image]]) -> Image.Image:
    scale = 4
    cell = CANVAS_SIZE * scale
    gap = 8
    width = gap + 11 * (cell + gap)
    height = gap * 2 + cell
    sheet = Image.new("RGBA", (width, height), (27, 31, 35, 255))
    draw = ImageDraw.Draw(sheet)
    for column, level in enumerate(LEVELS):
        x = gap + column * (cell + gap)
        tile = 16
        for yy in range(0, cell, tile):
            for xx in range(0, cell, tile):
                fill = (39, 44, 49, 255) if (xx // tile + yy // tile) % 2 else (49, 55, 61, 255)
                draw.rectangle((x + xx, gap + yy, x + xx + tile - 1, gap + yy + tile - 1), fill=fill)
        enlarged = icons[level][2].resize((cell, cell), Image.Resampling.NEAREST)
        sheet.alpha_composite(enlarged, (x, gap))
        draw.text((x + 5, gap + 5), str(level), fill=(255, 226, 130, 255), stroke_width=1, stroke_fill=(0, 0, 0, 255))
    return sheet


def targets(icons: dict[int, dict[int, Image.Image]]) -> dict[Path, bytes]:
    files: dict[Path, bytes] = {}
    for level, variants in icons.items():
        data = _png_bytes(variants[2])
        files[PROCESSED_DIR / f"cast_{level}.png"] = data
        files[PROCESSED_DIR / "2x" / f"cast_{level}.png"] = data
        files[PROCESSED_DIR / "1x" / f"cast_{level}.png"] = _png_bytes(variants[1])
        for app in APPS:
            files[ROOT / "web" / app / "public" / "city" / f"cast_{level}.png"] = data
            for dpr, icon in variants.items():
                files[ROOT / "web" / app / "public" / "city" / f"{dpr}x" / f"cast_{level}.png"] = _png_bytes(icon)
    files[PREVIEW] = _png_bytes(preview_sheet(icons))
    return files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="기존 산출물과 바이트 비교")
    args = parser.parse_args()

    icons = {level: render_variants(level) for level in LEVELS}
    files = targets(icons)
    if args.check:
        drift = [path for path, data in files.items() if not path.exists() or path.read_bytes() != data]
        for path in drift:
            print(f"DRIFT {path.relative_to(ROOT)}", file=sys.stderr)
        if drift:
            print(f"{len(drift)}개 산출물이 빌더 출력과 다르다.", file=sys.stderr)
            return 1
        print(f"{len(files)}개 산출물 일치.")
        return 0

    for path, data in files.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        print(f"wrote {path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
