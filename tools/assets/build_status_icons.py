#!/usr/bin/env python3
"""도시 상태/수도별 아이콘 빌더 (ImageGen 원화 · 결정적 후처리).

`web/{gateway,game}/public/status/{1x,2x,4x,8x}/` 아래
`state-<code>.png`(12장) · `state-<hwiha>.png`(휘하 신규 4장) · `star-capital.png`와
`imperial-residence.png`(1x/2x/4x) · `imperial-npc.png`(1x/2x),
검수 시트 `assets/brand/status-icons/preview.png`를 생성한다.
기존 평면 경로 `status/<name>.png`는 옛 이름에 한해 1x 사본으로 유지한다.

정본 원화는 `assets/status-icons/source/` 의 ImageGen 시트다(생성 기록:
`tools/assets/gen_status_icons_imagegen.py`, 프롬프트: 같은 폴더 README).

  - `status-master-imagegen.png` — 4×4, 1–12번 셀 = 상태 코드 1,2,3,4,5,6,7,8,9,32,34,43,
    13번 셀 = 수도 별, 14–16번 빈 셀.
  - `status-hwiha-imagegen.png` — 2×2, 고립·포위·전투·공사.
  - `imperial-residence-imagegen.png` — 황제 거처(1장).

각 셀의 배경 제거·분리·축소·팔레트 제한을 코드로 재현한다.

    python3 tools/assets/build_status_icons.py
    python3 tools/assets/build_status_icons.py --check   # 손편집 드리프트 검사, 불일치면 비0 종료

## 크기 규약

배지는 지도에서 성 건물 좌상단에 붙는다. 건물이 발자국을 채우도록 커지면서 배지가
약 15–64 CSS px 로 그려지므로, 한 변 16px 을 1x 로 두고 2x=32 · 4x=64 · 8x=128 을
원화에서 각각 독립 축소·픽셀 힌트한다(최근접 확대본이 아니다). 알파는 이진이고
팔레트는 `_pixel_hint`(build_city_icons)의 48색 양자화를 따른다. 황제 거처는 기존
24px 1x 규약(2x=48, 4x=96), 황제 NPC 이름 배지는 16px 1x(2x=32) 그대로다.

## state 코드 조사 (추측 아님, 코드 근거)

`city.state` 는 `func_map.php` 가 원값 그대로 클라이언트에 넘기는 raw DB 컬럼이다.
이 저장소에 실제 이식된 쓰기 지점을 전수 조사한 값만 아이콘화한다:

  - `RaiseDisaster.kt`: 1 풍작 · 2 호황 · 3 혹한 · 4 역병 · 5 지진 · 6 태풍 · 7 홍수 ·
    8 흉년/메뚜기 · 9 민란(황건·도적 세력과 겹치지 않게 일반화)
  - `CheHwagye.kt`/`CheSeondong.kt` — 화계·선동 성공 시 `state=32`.
  - `CheTalchwi.kt` — 탈취 성공 시 `state=34`.
  - `CheChulbyeong.kt` — 출병 목적지 도시에 `state=43`.

휘하(HWIHA) 신규 상태 4종은 숫자 코드가 아니라 이름으로 내보낸다:
고립(보급 끊김) · 포위 · 전투 · 공사.

작게 렌더되므로 색만으로 구분하지 않는다 — 모든 배지는 서로 다른 알파 실루엣이다.
"""

from __future__ import annotations

import argparse
import io
import sys
from collections import deque
from functools import lru_cache
from pathlib import Path

from PIL import Image, ImageDraw

try:
    from tools.assets.build_city_icons import _pixel_hint, remove_checkerboard_background
except ModuleNotFoundError:  # `python tools/assets/build_status_icons.py`
    from build_city_icons import _pixel_hint, remove_checkerboard_background

ROOT = Path(__file__).resolve().parents[2]
APPS = ("gateway", "game")
SOURCE_DIR = ROOT / "assets" / "status-icons" / "source"
PREVIEW = ROOT / "assets" / "brand" / "status-icons" / "preview.png"
SOURCE_SHEET = SOURCE_DIR / "status-master-imagegen.png"
HWIHA_SHEET = SOURCE_DIR / "status-hwiha-imagegen.png"
IMPERIAL_SOURCE = SOURCE_DIR / "imperial-residence-imagegen.png"

BASE_SIZE = 16            # 상태 배지·수도 별 1x
SCALES = (1, 2, 4, 8)     # 1x=16 · 2x=32 · 4x=64 · 8x=128
IMPERIAL_SIZE = 24        # 황제 거처 1x (기존 규약 유지)
IMPERIAL_SCALES = (1, 2, 4)
IMPERIAL_NPC_SIZE = 16    # 황제 NPC 이름 배지 1x (기존 규약 유지)
IMPERIAL_NPC_SCALES = (1, 2)

STAR_GOLD, STAR_GOLD_D = (250, 214, 96, 255), (188, 138, 30, 255)

STATE_CODES = (1, 2, 3, 4, 5, 6, 7, 8, 9, 32, 34, 43)
HWIHA_STATES = ("isolated", "besieged", "battle", "works")

# (시트, 격자 한 변, 셀 번호) — 셀 번호는 좌→우, 위→아래.
CELLS: dict[str, tuple[Path, int, int]] = {
    **{str(code): (SOURCE_SHEET, 4, index) for index, code in enumerate(STATE_CODES)},
    "capital": (SOURCE_SHEET, 4, 12),
    **{name: (HWIHA_SHEET, 2, index) for index, name in enumerate(HWIHA_STATES)},
}

# 평면 경로(`status/<name>.png`)는 앱이 쓰던 옛 이름만 1x 사본으로 남긴다.
LEGACY_FLAT = {*(str(code) for code in STATE_CODES), "capital", "imperial", "imperialNpc"}


def file_name(key: str) -> str:
    if key == "capital":
        return "star-capital.png"
    if key == "imperial":
        return "imperial-residence.png"
    if key == "imperialNpc":
        return "imperial-npc.png"
    return f"state-{key}.png"


# 가장자리와 이어지지 않은 배경 주머니(비계 틀 안쪽, 목책 사이)를 지우는 최소 면적(원화 px).
# 눈송이·칼날의 흰 하이라이트는 한 덩어리가 700px 미만이라 남는다.
ENCLOSED_BACKGROUND_MIN_AREA = 1000


def _enclosed_background_candidate(pixel: tuple[int, int, int, int]) -> bool:
    return pixel[3] == 255 and min(pixel[:3]) >= 236 and max(pixel[:3]) - min(pixel[:3]) <= 14


def clear_enclosed_background(image: Image.Image, min_area: int = ENCLOSED_BACKGROUND_MIN_AREA) -> Image.Image:
    """flood fill 이 닿지 못한, 외곽선으로 둘러싸인 큰 흰 배경 덩어리를 투명하게 만든다."""
    out = image.copy()
    width, height = out.size
    px = out.load()
    seen = bytearray(width * height)
    for y0 in range(height):
        for x0 in range(width):
            if seen[y0 * width + x0] or not _enclosed_background_candidate(px[x0, y0]):
                continue
            seen[y0 * width + x0] = 1
            queue, component = deque([(x0, y0)]), []
            while queue:
                x, y = queue.popleft()
                component.append((x, y))
                for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if (
                        0 <= nx < width and 0 <= ny < height
                        and not seen[ny * width + nx]
                        and _enclosed_background_candidate(px[nx, ny])
                    ):
                        seen[ny * width + nx] = 1
                        queue.append((nx, ny))
            if len(component) >= min_area:
                for x, y in component:
                    px[x, y] = (0, 0, 0, 0)
    return out


@lru_cache(maxsize=None)
def _sheet(path: Path) -> Image.Image:
    return clear_enclosed_background(remove_checkerboard_background(Image.open(path)))


@lru_cache(maxsize=None)
def _source_cell(key: str) -> Image.Image:
    path, grid, index = CELLS[key]
    source = _sheet(path)
    width, height = source.size
    col, row = index % grid, index // grid
    left, right = round(col * width / grid), round((col + 1) * width / grid)
    top, bottom = round(row * height / grid), round((row + 1) * height / grid)
    cell = source.crop((left, top, right, bottom))
    bbox = cell.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError(f"status source cell {key} is empty")
    return cell.crop(bbox)


def _render(source: Image.Image, size: int, extent: int) -> Image.Image:
    scale = min(extent / source.width, extent / source.height)
    resized = source.resize(
        (max(1, round(source.width * scale)), max(1, round(source.height * scale))),
        Image.Resampling.LANCZOS,
    )
    resized = _pixel_hint(resized)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((size - resized.width) // 2, size - resized.height))
    return canvas


def build_state(key: int | str, size: int = BASE_SIZE) -> Image.Image:
    """상태 배지. 여백은 캔버스에 비례한다(16→14, 32→28, 64→56, 128→112)."""
    return _render(_source_cell(str(key)), size, size - 2 * max(1, size // BASE_SIZE))


def build_capital_star(size: int = BASE_SIZE) -> Image.Image:
    return _render(_source_cell("capital"), size, size - max(1, size // BASE_SIZE))




@lru_cache(maxsize=1)
def _imperial_source() -> Image.Image:
    source = remove_checkerboard_background(Image.open(IMPERIAL_SOURCE))
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("imperial residence source is empty")
    return source.crop(bbox)


def build_imperial_residence(size: int = IMPERIAL_SIZE) -> Image.Image:
    """RTK7 황제 필터 실루엣을 현재 상태 배지 화풍으로 재해석한 황제 거처 표식."""
    source = _imperial_source()
    extent = size - 2
    scale = min(extent / source.width, extent / source.height)
    resized = source.resize(
        (max(1, round(source.width * scale)), max(1, round(source.height * scale))),
        Image.Resampling.LANCZOS,
    )
    resized = _pixel_hint(resized)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((size - resized.width) // 2, size - resized.height - 1))
    # ImageGen 원화의 면류관 앞 유주가 24px LANCZOS 축소에서 한 덩어리로
    # 합쳐지지 않게 논리 픽셀 격자에서 다섯 줄을 복원한다.
    unit = max(1, size // IMPERIAL_SIZE)
    if size == IMPERIAL_SIZE * unit:
        for logical_x in (8, 10, 12, 14, 16):
            color = STAR_GOLD if logical_x == 12 else STAR_GOLD_D
            for y in range(8 * unit, 9 * unit):
                for x in range(logical_x * unit, (logical_x + 1) * unit):
                    canvas.putpixel((x, y), color)
    return canvas


def build_imperial_npc_badge(size: int = IMPERIAL_NPC_SIZE) -> Image.Image:
    """인물명 앞에 붙이는 황제 특별 NPC 배지. 16px용 면류관 앞판을 별도 클린업한다."""
    badge = build_imperial_residence(size)
    unit = max(1, size // IMPERIAL_NPC_SIZE)
    if size == IMPERIAL_NPC_SIZE * unit:
        for logical_x in range(4, 12):
            color = STAR_GOLD if logical_x in (7, 8) else STAR_GOLD_D
            for y in range(5 * unit, 6 * unit):
                for x in range(logical_x * unit, (logical_x + 1) * unit):
                    badge.putpixel((x, y), color)
        for logical_x in (5, 7, 9, 11):
            for y in range(6 * unit, 7 * unit):
                for x in range(logical_x * unit, (logical_x + 1) * unit):
                    badge.putpixel((x, y), STAR_GOLD_D)
    return badge


def build_all() -> dict[str, dict[int, Image.Image]]:
    """{키: {배율: 이미지}}."""
    icons: dict[str, dict[int, Image.Image]] = {}
    for code in STATE_CODES:
        icons[str(code)] = {s: build_state(code, BASE_SIZE * s) for s in SCALES}
    for name in HWIHA_STATES:
        icons[name] = {s: build_state(name, BASE_SIZE * s) for s in SCALES}
    icons["capital"] = {s: build_capital_star(BASE_SIZE * s) for s in SCALES}
    icons["imperial"] = {s: build_imperial_residence(IMPERIAL_SIZE * s) for s in IMPERIAL_SCALES}
    icons["imperialNpc"] = {s: build_imperial_npc_badge(IMPERIAL_NPC_SIZE * s) for s in IMPERIAL_NPC_SCALES}
    return icons


PREVIEW_ORDER = ("capital", *(str(code) for code in STATE_CODES), *HWIHA_STATES, "imperial", "imperialNpc")


def preview_sheet(icons: dict[str, dict[int, Image.Image]]) -> Image.Image:
    """열 = 아이콘(게임 코드 순서 → 휘하 신규 → 황제), 행 = 1x·2x·4x·8x 를 같은 128px 로
    최근접 확대한 것, 마지막 행 = 실제 크기(1x·2x·4x 나란히, 짙은 지도색 위)."""
    cell, gap = 128, 8
    row_bg = (24, 24, 28, 255)
    native_h = BASE_SIZE * 4 + gap
    width = gap + len(PREVIEW_ORDER) * (cell + gap)
    height = gap + len(SCALES) * (cell + gap) + native_h + gap
    sheet = Image.new("RGBA", (width, height), row_bg)
    draw = ImageDraw.Draw(sheet)
    for column, key in enumerate(PREVIEW_ORDER):
        x = gap + column * (cell + gap)
        for row, scale in enumerate(SCALES):
            y = gap + row * (cell + gap)
            draw.rectangle((x, y, x + cell - 1, y + cell - 1), fill=(36, 38, 44, 255))
            image = icons[key].get(scale)
            if image is None:
                continue
            factor = max(1, cell // image.width)
            big = image.resize((image.width * factor, image.height * factor), Image.Resampling.NEAREST)
            sheet.alpha_composite(big, (x + (cell - big.width) // 2, y + (cell - big.height) // 2))
        y = gap + len(SCALES) * (cell + gap)
        draw.rectangle((x, y, x + cell - 1, y + native_h - 1), fill=(78, 92, 64, 255))
        nx = x + 2
        for scale in (1, 2, 4):
            image = icons[key].get(scale)
            if image is None or nx + image.width > x + cell:
                continue
            sheet.alpha_composite(image, (nx, y + native_h - image.height - 2))
            nx += image.width + 2
    return sheet


def png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def targets(icons: dict[str, dict[int, Image.Image]]) -> dict[Path, bytes]:
    out: dict[Path, bytes] = {}
    for key, variants in icons.items():
        name = file_name(key)
        for app in APPS:
            base = ROOT / "web" / app / "public" / "status"
            for scale, image in variants.items():
                out[base / f"{scale}x" / name] = png_bytes(image)
            if key in LEGACY_FLAT:
                out[base / name] = png_bytes(variants[1])
    out[PREVIEW] = png_bytes(preview_sheet(icons))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="쓰지 않고 기존 파일과 바이트 비교")
    args = ap.parse_args()

    files = targets(build_all())

    if args.check:
        bad = [
            p for p, data in files.items()
            if not p.exists() or p.read_bytes() != data
        ]
        for p in bad:
            print(f"DRIFT {p.relative_to(ROOT)}", file=sys.stderr)
        if bad:
            print(f"{len(bad)}개 산출물이 빌더 출력과 다르다.", file=sys.stderr)
            return 1
        print(f"{len(files)}개 산출물 일치.")
        return 0

    for p, data in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
        print(f"wrote {p.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
