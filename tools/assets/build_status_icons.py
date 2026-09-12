#!/usr/bin/env python3
"""도시 상태/수도별 아이콘 빌더 (ImageGen 원화 · 결정적 후처리).

`web/{gateway,game}/public/status/state-<code>.png`(12장) + `star-capital.png`(1장) +
`imperial-residence.png`(1장) + `imperial-npc.png`(1장)과
검수 시트 `assets/brand/status-icons/preview.png`를 생성한다. 정본 원화는
`assets/status-icons/source/status-master-imagegen.png`이며, 각 셀의 배경 제거·분리·축소·
팔레트 제한을 코드로 재현한다.

    python3 tools/assets/build_status_icons.py
    python3 tools/assets/build_status_icons.py --check   # 손편집 드리프트 검사, 불일치면 비0 종료

이 스크립트가 존재하는 이유: `MapViewer.tsx`의 도시 재해/사건 배지와 수도 별이
출처와 배포 권리를 확정할 수 없는 구형 CDN 자산을 참조하던 구조를 자작 자산으로 바꾼다.
구형 자산에는 LICENSE가 없어 권리가 UNKNOWN이다
(`docs/superpowers/research/2026-08-17-asset-license-audit.md` §1-2) — 도시 아이콘·깃발과
같은 판단으로 자작 전환한다.

## state 코드 조사 (추측 아님, 코드 근거)

`MapPreviewController.kt:108-109` 주석: "재해/사건 코드(city.state) — func_map.php:145-147
tuple state자리". `city.state` 는 `func_map.php` 가 원값 그대로 클라이언트에 넘기는
raw DB 컬럼이고, 값의 의미는 그걸 쓰는 로직 쪽에서만 확인된다. 이 저장소에 실제 이식된
쓰기 지점을 전수 조사한 값만 아이콘화한다 — 그 외 코드값은 UNKNOWN 으로 남긴다:

  - `RaiseDisaster.kt` (분기별 재해/풍작 이벤트, `state<=10` 은 매 분기 0으로 리셋):
      1  풍작(호황, 7월) · 2  호황(4월) · 3  혹한/한파/폭설(1·10월)
      4  역병(1월) · 5  지진(전분기) · 6  태풍(4월) · 7  홍수(4월)
      8  흉년/메뚜기(7월) · 9  민란(1·10월, 구형 황건 출현 문구를 일반화)
  - `CheHwagye.kt:262`/`CheSeondong.kt:257` — 화계(방화)·선동(소요) 성공 시 `state=32`
    (둘 다 같은 코드를 공유 — PHP 원본이 두 명령에 같은 표시를 쓴다).
  - `CheTalchwi.kt:294,301` — 탈취(약탈) 성공 시 `state=34`("탈취 상태").
  - `CheChulbyeong.kt:216` — 출병(진군) 목적지 도시에 `state=43, term=3`.

  51 은 상태 코드가 아니라 수도 배지(`event51.gif`, 위 조사 범위 밖 — 이 빌더가 별도로
  `star-capital.png` 로 만든다).

작게 렌더되므로(성 아이콘 우상단 배지) 색만으로 구분하지 않는다 — 실루엣 자체를 다르게
그린다: 곡물단(풍작) / 동전(호황) / 눈송이(혹한) / 해골과 독기(역병) / 균열(지진) /
소용돌이(태풍) / 잠긴 집(홍수) / 빈 그릇과 시든 이삭(흉년) / 부러진 관아 명패·
횃불·농기구(민란) / 불타는 성문(화계·선동) / 자루(탈취) / 군기·창·화살표(출병).
수도 별은 5각 별로 별도다.
"""

from __future__ import annotations

import argparse
import io
import math
import sys
from pathlib import Path
from functools import lru_cache

from PIL import Image

try:
    from tools.assets.build_city_icons import _pixel_hint, remove_checkerboard_background
except ModuleNotFoundError:  # `python tools/assets/build_status_icons.py`
    from build_city_icons import _pixel_hint, remove_checkerboard_background

ROOT = Path(__file__).resolve().parents[2]
APPS = ("gateway", "game")
PREVIEW = ROOT / "assets" / "brand" / "status-icons" / "preview.png"
SOURCE_SHEET = ROOT / "assets" / "status-icons" / "source" / "status-master-imagegen.png"
IMPERIAL_SOURCE = ROOT / "assets" / "status-icons" / "source" / "imperial-residence-imagegen.png"
PREVIEW_SCALE = 8
PREVIEW_GAP = 4

SIZE = 24
STAR_SIZE = 16
IMPERIAL_NPC_SIZE = 16

OUTLINE = (18, 16, 14, 255)


class Canvas:
    """알파 포함 픽셀 격자. 범위 밖 쓰기는 조용히 버린다."""

    def __init__(self, w: int, h: int) -> None:
        self.w, self.h = w, h
        self.px: dict[tuple[int, int], tuple[int, int, int, int]] = {}

    def set(self, x: int, y: int, color) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            self.px[(x, y)] = color

    def rect(self, x0: int, y0: int, x1: int, y1: int, color) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.set(x, y, color)

    def clear_rect(self, x0: int, y0: int, x1: int, y1: int) -> None:
        for y in range(y0, y1 + 1):
            for x in range(x0, x1 + 1):
                self.px.pop((x, y), None)

    def line(self, x0: int, y0: int, x1: int, y1: int, color) -> None:
        """Bresenham."""
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        err = dx + dy
        x, y = x0, y0
        while True:
            self.set(x, y, color)
            if x == x1 and y == y1:
                break
            e2 = 2 * err
            if e2 >= dy:
                err += dy
                x += sx
            if e2 <= dx:
                err += dx
                y += sy

    def circle(self, cx: int, cy: int, r: int, color, fill=True) -> None:
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                d = math.hypot(x - cx, y - cy)
                if fill and d <= r + 0.3:
                    self.set(x, y, color)
                elif not fill and r - 0.8 <= d <= r + 0.3:
                    self.set(x, y, color)

    def outline(self) -> None:
        """채워진 픽셀에 4-이웃한 빈 픽셀을 외곽선으로 만든다."""
        edge = set()
        for (x, y) in self.px:
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                p = (x + dx, y + dy)
                if p not in self.px and 0 <= p[0] < self.w and 0 <= p[1] < self.h:
                    edge.add(p)
        for p in edge:
            self.px[p] = OUTLINE

    def to_image(self) -> Image.Image:
        img = Image.new("RGBA", (self.w, self.h), (0, 0, 0, 0))
        for (x, y), color in self.px.items():
            img.putpixel((x, y), color)
        return img


# 팔레트.
GREEN, GREEN_D = (150, 186, 66, 255), (98, 128, 38, 255)
GOLD, GOLD_D = (232, 190, 74, 255), (168, 128, 36, 255)
ICE, ICE_D = (168, 220, 240, 255), (110, 170, 208, 255)
PLAGUE, PLAGUE_D = (150, 92, 168, 255), (98, 52, 116, 255)
ROCK, ROCK_D = (150, 116, 78, 255), (98, 72, 46, 255)
TEAL, TEAL_D = (78, 168, 168, 255), (44, 116, 116, 255)
WAVE, WAVE_D = (86, 138, 196, 255), (48, 92, 148, 255)
WILT, WILT_D = (168, 140, 62, 255), (110, 88, 34, 255)
TURBAN, TURBAN_D = (214, 172, 40, 255), (176, 52, 40, 255)
FIRE, FIRE_D = (232, 128, 40, 255), (176, 60, 24, 255)
SACK, SACK_D = (150, 108, 62, 255), (98, 68, 36, 255)
SPEAR, SPEAR_D = (200, 200, 208, 255), (120, 40, 36, 255)
STAR_GOLD, STAR_GOLD_D = (250, 214, 96, 255), (188, 138, 30, 255)


def draw_1_bumper(c: Canvas) -> None:
    """풍작 — 두 줄기와 낟알이 보이는 풍성한 곡물단."""
    for x0, tip in ((10, (7, 3)), (13, (15, 2)), (12, (11, 4))):
        c.line(12, 21, x0, 7, GREEN_D)
        c.line(13, 21, tip[0], tip[1] + 3, GREEN)
    for x, y in ((6, 4), (8, 5), (5, 7), (9, 8), (16, 3), (14, 5), (17, 7), (13, 8)):
        c.rect(x, y, x + 2, y + 2, GREEN)
        c.set(x + 1, y, GREEN_D)
    c.rect(8, 16, 16, 18, GOLD_D)


def draw_2_boom(c: Canvas) -> None:
    """호황 — 네모 구멍이 난 한나라 동전 세 닢."""
    for cx, cy in ((8, 15), (16, 15), (12, 8)):
        c.circle(cx, cy, 6, GOLD)
        c.circle(cx, cy, 6, GOLD_D, fill=False)
        c.clear_rect(cx - 1, cy - 1, cx + 1, cy + 1)


def draw_3_cold(c: Canvas) -> None:
    """혹한 — 6방향 눈송이."""
    cx, cy, r = 12, 12, 9
    for k in range(6):
        a = k * math.pi / 3
        x1, y1 = round(cx + r * math.cos(a)), round(cy + r * math.sin(a))
        c.line(cx, cy, x1, y1, ICE)
        mx, my = round(cx + r * 0.62 * math.cos(a)), round(cy + r * 0.62 * math.sin(a))
        for sa in (a + 0.7, a - 0.7):
            sx, sy = round(mx + 3 * math.cos(sa)), round(my + 3 * math.sin(sa))
            c.line(mx, my, sx, sy, ICE_D)
    c.set(cx, cy, ICE)


def draw_4_plague(c: Canvas) -> None:
    """역병 — 해골과 위로 피어오르는 독기."""
    c.circle(12, 12, 7, PLAGUE)
    c.rect(8, 16, 16, 20, PLAGUE)
    c.clear_rect(8, 10, 10, 12)
    c.clear_rect(14, 10, 16, 12)
    c.clear_rect(11, 14, 13, 15)
    c.rect(10, 18, 11, 20, PLAGUE_D)
    c.rect(13, 18, 14, 20, PLAGUE_D)
    c.line(8, 6, 6, 2, PLAGUE_D)
    c.line(14, 5, 16, 1, PLAGUE_D)


def draw_5_quake(c: Canvas) -> None:
    """지진 — 갈라진 대지."""
    c.rect(2, 14, 21, 21, ROCK)
    zig = [(3, 14), (7, 8), (10, 14), (14, 6), (17, 13), (21, 9)]
    for (x0, y0), (x1, y1) in zip(zig, zig[1:]):
        c.line(x0, y0, x1, y1, ROCK_D)
        c.line(x0, y0 + 1, x1, y1 + 1, ROCK_D)
    c.rect(3, 5, 6, 8, ROCK_D)
    c.rect(18, 3, 21, 7, ROCK_D)


def draw_6_typhoon(c: Canvas) -> None:
    """태풍 — 소용돌이."""
    cx, cy = 12, 12
    prev = None
    for i in range(110):
        t = i * 0.22
        r = 0.5 + t * 0.48
        x, y = round(cx + r * math.cos(t)), round(cy + r * math.sin(t))
        if r > 10:
            break
        if prev and prev != (x, y):
            c.line(prev[0], prev[1], x, y, TEAL if i % 6 < 3 else TEAL_D)
        prev = (x, y)


def draw_7_flood(c: Canvas) -> None:
    """홍수 — 처마까지 잠긴 집과 파도."""
    c.line(7, 9, 12, 4, ROCK_D)
    c.line(12, 4, 17, 9, ROCK_D)
    c.rect(8, 9, 16, 15, ROCK)
    c.clear_rect(11, 11, 13, 15)
    for row, y0 in enumerate((13, 17, 20)):
        for x in range(2, 22):
            up = math.sin(x * 0.9 + row) > 0
            c.set(x, y0 + (0 if up else 1), WAVE if row < 2 else WAVE_D)
    c.rect(2, 21, 21, 22, WAVE_D)


def draw_8_famine(c: Canvas) -> None:
    """흉년 — 금이 간 빈 그릇과 고개 숙인 이삭."""
    c.line(3, 14, 12, 18, WILT_D)
    c.line(12, 18, 21, 14, WILT_D)
    c.rect(6, 18, 18, 21, WILT)
    c.line(12, 18, 10, 21, OUTLINE)
    c.line(18, 14, 17, 7, WILT_D)
    c.line(17, 7, 14, 4, WILT_D)
    for x, y in ((13, 3), (15, 4), (12, 6), (16, 7)):
        c.rect(x, y, x + 2, y + 1, WILT)


def draw_9_turban(c: Canvas) -> None:
    """황건적 출현 — 매듭과 긴 꼬리가 있는 황색 두건."""
    c.rect(4, 7, 19, 12, TURBAN)
    c.rect(5, 12, 18, 15, TURBAN_D)
    c.rect(6, 15, 9, 21, TURBAN)
    c.rect(15, 15, 18, 22, TURBAN)
    c.rect(10, 8, 13, 11, FIRE_D)


def draw_32_fire(c: Canvas) -> None:
    """화계/선동 — 불타는 성문."""
    c.rect(4, 13, 7, 22, ROCK_D)
    c.rect(17, 13, 20, 22, ROCK_D)
    c.rect(4, 11, 20, 14, ROCK)
    c.rect(9, 16, 15, 22, OUTLINE)
    for cx in (7, 12, 17):
        c.line(cx, 12, cx - 2, 5, FIRE_D)
        c.line(cx - 2, 5, cx, 2, FIRE)
        c.line(cx, 2, cx + 2, 8, FIRE)


def draw_34_plunder(c: Canvas) -> None:
    """탈취 — 묶은 자루."""
    c.line(10, 4, 14, 4, SACK_D)
    for y in range(5, 22):
        half = max(2, min(8, 3 + min(y - 5, 21 - y)))
        c.rect(12 - half, y, 12 + half, y, SACK)
    c.rect(6, 18, 18, 21, SACK_D)
    c.rect(9, 4, 15, 7, SACK_D)
    for cx, cy in ((4, 5), (19, 7)):
        c.circle(cx, cy, 2, GOLD)
        c.clear_rect(cx, cy, cx, cy)


def draw_43_march(c: Canvas) -> None:
    """출병(진군) — 창과 붉은 군기, 진행 화살표."""
    c.line(8, 22, 8, 5, SPEAR_D)
    c.line(8, 2, 5, 7, SPEAR)
    c.line(8, 2, 11, 7, SPEAR)
    c.line(5, 7, 11, 7, SPEAR)
    c.rect(9, 8, 18, 14, (176, 52, 40, 255))
    c.line(14, 19, 21, 19, SPEAR)
    c.line(21, 19, 18, 16, SPEAR)
    c.line(21, 19, 18, 22, SPEAR)


STATE_BUILDERS = {
    1: draw_1_bumper,
    2: draw_2_boom,
    3: draw_3_cold,
    4: draw_4_plague,
    5: draw_5_quake,
    6: draw_6_typhoon,
    7: draw_7_flood,
    8: draw_8_famine,
    9: draw_9_turban,
    32: draw_32_fire,
    34: draw_34_plunder,
    43: draw_43_march,
}


SOURCE_CELL_BY_CODE = {
    1: 0, 2: 1, 3: 2, 4: 3,
    5: 4, 6: 5, 7: 6, 8: 7,
    9: 8, 32: 9, 34: 10, 43: 11,
}


@lru_cache(maxsize=1)
def _source_cells() -> tuple[Image.Image, ...]:
    source = remove_checkerboard_background(Image.open(SOURCE_SHEET))
    width, height = source.size
    cells: list[Image.Image] = []
    for index in range(13):
        col, row = index % 4, index // 4
        left, right = round(col * width / 4), round((col + 1) * width / 4)
        top, bottom = round(row * height / 4), round((row + 1) * height / 4)
        cell = source.crop((left, top, right, bottom))
        bbox = cell.getchannel("A").getbbox()
        if bbox is None:
            raise ValueError(f"status source cell {index} is empty")
        cells.append(cell.crop(bbox))
    return tuple(cells)


def _render_source_cell(index: int, size: int, extent: int) -> Image.Image:
    source = _source_cells()[index]
    scale = min(extent / source.width, extent / source.height)
    resized = source.resize(
        (max(1, round(source.width * scale)), max(1, round(source.height * scale))),
        Image.Resampling.LANCZOS,
    )
    resized = _pixel_hint(resized)
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas.alpha_composite(resized, ((size - resized.width) // 2, size - resized.height))
    return canvas


def build_state(code: int, size: int = SIZE) -> Image.Image:
    return _render_source_cell(SOURCE_CELL_BY_CODE[code], size, size - 2)


def build_capital_star(size: int = STAR_SIZE) -> Image.Image:
    return _render_source_cell(12, size, size - 1)


@lru_cache(maxsize=1)
def _imperial_source() -> Image.Image:
    source = remove_checkerboard_background(Image.open(IMPERIAL_SOURCE))
    bbox = source.getchannel("A").getbbox()
    if bbox is None:
        raise ValueError("imperial residence source is empty")
    return source.crop(bbox)


def build_imperial_residence(size: int = SIZE) -> Image.Image:
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
    unit = max(1, size // SIZE)
    if size == SIZE * unit:
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


def preview_sheet(icons: dict[str, Image.Image]) -> Image.Image:
    s, gap = PREVIEW_SCALE, PREVIEW_GAP
    w = sum(i.width * s for i in icons.values()) + gap * (len(icons) + 1)
    h = max(i.height * s for i in icons.values()) + gap * 2
    sheet = Image.new("RGBA", (w, h), (24, 24, 28, 255))
    x = gap
    # 게임 상태 코드의 실제 순서로 보여 줘 32/34/43이 3과 4 사이에 끼지 않게 한다.
    for key in ["capital", "imperial", "imperialNpc", *(str(code) for code in STATE_BUILDERS)]:
        img = icons[key]
        img = img.resize((img.width * s, img.height * s), Image.NEAREST)
        sheet.alpha_composite(img, (x, h - gap - img.height))
        x += img.width + gap
    return sheet


def png_bytes(img: Image.Image) -> bytes:
    buf = io.BytesIO()
    img.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def targets(icons: dict[str, Image.Image]) -> dict[Path, bytes]:
    out: dict[Path, bytes] = {}
    for key, img in icons.items():
        data = png_bytes(img)
        if key == "capital":
            name = "star-capital.png"
        elif key == "imperial":
            name = "imperial-residence.png"
        elif key == "imperialNpc":
            name = "imperial-npc.png"
        else:
            name = f"state-{key}.png"
        for app in APPS:
            out[ROOT / "web" / app / "public" / "status" / name] = data
            out[ROOT / "web" / app / "public" / "status" / "1x" / name] = data
            if key == "capital":
                doubled = build_capital_star(STAR_SIZE * 2)
            elif key == "imperial":
                doubled = build_imperial_residence(SIZE * 2)
            elif key == "imperialNpc":
                doubled = build_imperial_npc_badge(IMPERIAL_NPC_SIZE * 2)
            else:
                doubled = build_state(int(key), SIZE * 2)
            out[ROOT / "web" / app / "public" / "status" / "2x" / name] = png_bytes(doubled)
    out[PREVIEW] = png_bytes(preview_sheet(icons))
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="쓰지 않고 기존 파일과 바이트 비교")
    args = ap.parse_args()

    icons: dict[str, Image.Image] = {str(code): build_state(code) for code in STATE_BUILDERS}
    icons["capital"] = build_capital_star()
    icons["imperial"] = build_imperial_residence()
    icons["imperialNpc"] = build_imperial_npc_badge()
    files = targets(icons)

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
