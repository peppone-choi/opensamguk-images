#!/usr/bin/env python3
"""Build owner-accepted Waryong strategic-map derivatives; never copy original game binaries.

Reads MMAP.MDL (terrain tiles), MMAP.MAP (map layout, used only to learn synthesis statistics),
MMAP.MCH (map markers) and GAMEPAL.BRG (palettes) from a read-only local folder and writes
`waryong/map/`: the tile kit (original tiles, joins assembled from original tiles, desert/plateau
palette variants), kit mips, sprite sheets (markers, flag cloths, one-cell site icons), synthesis
statistics and a catalog. `--check` rebuilds in memory and compares decoded pixels and content.
"""

from __future__ import annotations

import argparse
import colorsys
import gzip
import hashlib
import io
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "waryong" / "map"
PREVIEW = ROOT / "waryong" / "previews" / "map"  # 파생 그림이라 MIT 경계(previews/) 밖에 둔다
SOURCE_FILES = ("MMAP.MDL", "MMAP.MAP", "MMAP.MCH", "GAMEPAL.BRG")
TILE = 16
ATLAS_COLUMNS = 32
SPRITE_COLUMNS = 16
DAY_BANK = 1  # GAMEPAL.BRG 세트 0의 둘째 벌 = 전략 지도 낮 색(KI.EXE 해독)
MIP_SIZES = (8, 4, 2, 1)

# 이웃 순서: 북 · 북동 · 동 · 남동 · 남 · 남서 · 서 · 북서
NEIGHBOURS = ((-1, 0), (-1, 1), (0, 1), (1, 1), (1, 0), (1, -1), (0, -1), (-1, -1))

RIVER = {"EW": 0x5E, "NE": 0x68, "NW": 0x69, "ES": 0x58, "SW": 0x59, "E": 0x5C, "W": 0x6C, "S": 0x5D, "N": 0x6D}
RIVER_JOINS = {"NES": ("NS", "NE", "ES"), "NSW": ("NS", "NW", "SW"), "NEW": ("EW", "NE", "NW"),
               "ESW": ("EW", "ES", "SW"), "NESW": ("EW", "NS")}
RIVER_PIXELS = (3, 8)
ROAD = {"EW": 0xC8, "NS": 0xC9, "NE": 0xC4, "NW": 0xC5, "ES": 0xC6, "SW": 0xC7}
ROAD_JOINS = {"NES": ("NS", "ES"), "NSW": ("NS", "SW"), "NEW": ("EW", "NE"), "ESW": ("EW", "SW"), "NESW": ("NS", "EW")}
ROAD_PIXELS = (9, 12, 15)
DESERT = {14: 9, 5: 7, 13: 9, 4: 6, 11: 7}
PLATEAU = {14: 13, 5: 13, 4: 5, 11: 12}
ROOF_TILES = {0xCD: 0xCB, 0xD0: 0xCE, 0xD3: 0xD1}  # 주황(주인 없음) 지붕 → 같은 자리 빨강 지붕

# 성 부품(원작 타일 번호). 조립 규칙은 opensamguk 굽기 도구가 이 표로 한다.
CASTLE_PARTS = {
    "small": dict(tl=0xE2, tr=0xE3, bl=0xE4, br=0xE5, wn=0xF4, ws=0xF5, ww=0xF2, we=0xF3, gn=0xD8, gs=0xD9, gw=0xDA, ge=0xDB),
    "big": dict(tl=0xDE, tr=0xDF, bl=0xE0, br=0xE1, wn=0xE7, ws=0xF7, ww=0xE6, we=0xF6, gn=0xDC, gs=0xDC, gw=0xDD, ge=0xDD),
    "keep": 0xCD, "house": 0xFF, "street": 0xFE, "garden": 0xB1, "infield": [0x06, 0xB6],
}
PASS_PARTS = {
    "NS": dict(gate=[0xD4, 0xD0, 0xD5], wall=0xE7, endWest=0xF8, endEast=0xF9),
    "EW": dict(gate=[0xD6, 0xD3, 0xD7], wall=0xE6, endNorth=0xFB, endSouth=0xFA),
}
BRIDGE_PARTS = {"narrowNS": 0xB8, "narrowEW": 0xB9, "wideN": 0xBA, "wideS": 0xBB, "wideW": 0xBC, "wideE": 0xBD, "wideMid": 0xBF,
                "ferryW": 0xC0, "ferryS": 0xC1, "ferryE": 0xC2, "ferryN": 0xC3}

# 산 면 분류(facets.py 판정 그대로): 이음 타일은 생김새로 정했다
FACET_FIXED = {0x83: "T", 0x84: "T", 0x70: "T", 0x71: "T", 0x7B: "T", 0x7C: "T", 0x7D: "T", 0x76: "T", 0x77: "T", 0x8A: "T", 0x74: "T",
               0x80: "S", 0x95: "S", 0x86: "S", 0x87: "S", 0x88: "S", 0x72: "S", 0x73: "S", 0x7E: "S", 0x78: "S", 0x79: "S", 0x75: "S", 0x89: "S",
               0x81: "E", 0x94: "E", 0x7A: "E", 0x7F: "E", 0x8B: "E", 0x82: "P", 0x85: "P"}
FACETS = ("T", "S", "E", "P")

FLAG_SOURCE_MARKER = 94  # 원작 부대 깃발(빨강 천) — 원작 글자를 지우고 우리 글자를 얹는다
FLAG_CLOTH_ROWS = range(3, 12)
FLAG_CLOTH_COLS = range(5, 14)
SWALLOW_CUT = {5: 14, 6: 12, 7: 11, 8: 11, 9: 12, 10: 13}  # 행 → 새 테두리 열(그 오른쪽은 비움)


def decode_planes(block: bytes) -> np.ndarray:
    tile = np.zeros((TILE, TILE), np.uint8)
    for plane in range(4):
        rows = np.frombuffer(block[plane * 32 : (plane + 1) * 32], np.uint8).reshape(TILE, 2)
        tile |= (np.unpackbits(rows, axis=1) << plane).astype(np.uint8)
    return tile


def decode_tiles(mdl: bytes) -> np.ndarray:
    if len(mdl) != 256 * 128:
        raise ValueError("MMAP.MDL size does not match 256 four-plane 16x16 tiles")
    return np.stack([decode_planes(mdl[n * 128 : (n + 1) * 128]) for n in range(256)])


def decode_map(raw: bytes) -> np.ndarray:
    size = int.from_bytes(raw[:4], "little")
    if size != 384 * 256:
        raise ValueError(f"MMAP.MAP header {size} is not 384x256")
    out = bytearray()
    at, previous = 4, None
    while len(out) < size:
        value = raw[at]
        at += 1
        out.append(value)
        if value == previous:  # 같은 바이트 두 번 → 다음 바이트가 추가 반복 수
            out.extend([value] * raw[at])
            at += 1
            previous = None
        else:
            previous = value
    if at != len(raw) or len(out) < size:
        raise ValueError("MMAP.MAP run-length stream does not end at the file end")
    return np.frombuffer(bytes(out[:size]), np.uint8).reshape(256, 384)


def decode_markers(mch: bytes) -> np.ndarray:
    count = len(mch) // 160
    if count != 269:
        raise ValueError(f"MMAP.MCH holds {count} markers, expected 269")
    markers = np.full((count, TILE, TILE), -1, np.int16)
    for n in range(count):
        block = mch[n * 160 : (n + 1) * 160]
        mask = np.unpackbits(np.frombuffer(block[:32], np.uint8).reshape(TILE, 2), axis=1).astype(bool)
        # NumPy 2 keeps uint8 here; cast before selecting the signed transparent sentinel.
        markers[n] = np.where(mask, decode_planes(block[32:]).astype(np.int16), -1)
    return markers


def decode_palettes(brg: bytes) -> np.ndarray:
    if len(brg) != 8 * 16 * 3:
        raise ValueError("GAMEPAL.BRG is not 8 banks of 16 BRG colours")
    bank = np.frombuffer(brg, np.uint8).reshape(8, 16, 3)  # [B, R, G], 4비트
    return (np.stack([bank[..., 1], bank[..., 2], bank[..., 0]], axis=-1) * 17).astype(np.uint8)


# ── 합성 통계: 원작 배치에서 「왼쪽 · 위 타일 + 이웃 분류 → 타일」 빈도를 배운다


def tile_class(t: int, tiles: np.ndarray) -> str:
    tile = tiles[t]
    water = np.isin(tile, RIVER_PIXELS).mean()
    dark = np.isin(tile, (0, 4, 1)).mean()
    if 0xC4 <= t <= 0xC9:
        return "R"
    if 0xB8 <= t <= 0xC3:
        return "B"
    if t >= 0xCB and t not in (0xF8, 0xF9, 0xFA, 0xFB):
        return "C"
    if 0xB1 <= t <= 0xB3:
        return "F"
    if 0xB4 <= t <= 0xB7:
        return "A"
    if water >= 0.5 or t == 0xCA:
        return "W"
    if 0x70 <= t <= 0xAF or 0xF8 <= t <= 0xFB:
        return "M" if dark >= 0.30 else "h"
    return "L"


def facet_of(t: int, tiles: np.ndarray) -> str:
    if t in FACET_FIXED:
        return FACET_FIXED[t]
    tile = tiles[t].ravel()
    if (tile == 0).sum() >= 70:
        return "S"
    if (tile == 6).sum() >= 15:
        return "E"
    if ((tile == 14) | (tile == 2)).sum() >= 90:
        return "T"
    return "P"


def neighbours(grid: np.ndarray, y: int, x: int, fill: str) -> tuple[str, ...]:
    h, w = grid.shape
    return tuple(grid[y + dy, x + dx] if 0 <= y + dy < h and 0 <= x + dx < w else fill for dy, dx in NEIGHBOURS)


def learn_statistics(tiles: np.ndarray, layout: np.ndarray) -> dict:
    classes = [tile_class(t, tiles) for t in range(256)]
    water = np.array([np.isin(tiles[t], RIVER_PIXELS).mean() for t in range(256)])
    coarse = {"h": "M", "R": "L", "B": "L", "C": "L", "A": "L", "F": "L"}
    base = np.vectorize(lambda t: coarse.get(classes[t], classes[t]))(layout)
    h, w = layout.shape
    is_water = base == "W"
    near_water = is_water.copy()
    for dy, dx in NEIGHBOURS:
        shifted = np.zeros_like(is_water)
        shifted[max(0, -dy) : h - max(0, dy), max(0, -dx) : w - max(0, dx)] = is_water[max(0, dy) : h - max(0, -dy), max(0, dx) : w - max(0, -dx)]
        near_water |= shifted
    cls = base.copy()
    cls[(base == "L") & (water[layout] >= 0.06) & ~near_water] = "r"
    output = np.isin(np.array(classes)[layout], ["W", "L", "M", "h"])
    facet_cls = cls.copy()
    mountain = cls == "M"
    facet_cls[mountain] = np.vectorize(lambda t: facet_of(int(t), tiles))(layout[mountain])

    def learn(grid: np.ndarray) -> dict[str, dict[str, Counter]]:
        tables: dict[str, dict[str, Counter]] = {k: defaultdict(Counter) for k in ("full", "n4", "c", "cls8", "c4", "c1")}
        for y in range(h):
            for x in range(w):
                if not output[y, x]:
                    continue
                t = int(layout[y, x])
                c = str(grid[y, x])
                n = neighbours(grid, y, x, c)
                left = int(layout[y, x - 1]) if x > 0 else -1
                up = int(layout[y - 1, x]) if y > 0 else -1
                ring = c + "".join(n)
                cross = c + n[0] + n[2] + n[4] + n[6]
                tables["full"][f"{left},{up},{ring}"][t] += 1
                tables["n4"][f"{left},{up},{cross}"][t] += 1
                tables["c"][f"{left},{up},{c}"][t] += 1
                tables["cls8"][ring][t] += 1
                tables["c4"][cross][t] += 1
                tables["c1"][c][t] += 1
        return tables

    def encode(tables: dict[str, dict[str, Counter]]) -> dict:
        return {name: {key: [[t, n] for t, n in sorted(counts.items())] for key, counts in sorted(table.items())}
                for name, table in tables.items()}

    tile_facet = sorted({int(t): facet_of(int(t), tiles) for t in np.unique(layout[mountain])}.items())
    return {
        "schemaVersion": 1,
        "keyFormat": {
            "classes": "W water, L land, M mountain, r river line; facet tables split M into T top, S south, E east, P west",
            "full": "left,up,c+N+NE+E+SE+S+SW+W+NW", "n4": "left,up,c+N+E+S+W", "c": "left,up,c",
            "cls8": "c+N+NE+E+SE+S+SW+W+NW", "c4": "c+N+E+S+W", "c1": "c",
            "left_up": "original tile id of the left / upper neighbour, -1 outside the map",
        },
        "order": ["full", "n4", "c", "cls8", "c4", "c1"],
        "terrain": encode(learn(cls)),
        "facet": encode(learn(facet_cls)),
        "tileClass": classes,
        "tileFacet": [[t, f] for t, f in tile_facet],
    }


# ── 키트: 원작 256장 + 원작 타일끼리 겹친 이음 + 사막 · 고원 팔레트 변형


def overlay(tiles: np.ndarray, first: np.ndarray, rest: list[np.ndarray], pixels: tuple[int, ...]) -> np.ndarray:
    out = first.copy()
    for part in rest:
        mask = np.isin(part, pixels)
        out[mask] = part[mask]
    return out


def river_part(tiles: np.ndarray, key: str) -> np.ndarray:
    if key == "NS":  # 남북 곧은 강: 6D 위 반 + 5D 아래 반
        return np.vstack([tiles[0x6D][:8], tiles[0x5D][8:]])
    return tiles[RIVER[key]].copy()


def build_kit(tiles: np.ndarray) -> tuple[np.ndarray, np.ndarray, list[dict], dict]:
    entries: list[dict] = []
    images: list[np.ndarray] = []
    roles: list[np.ndarray] = []

    def add(image: np.ndarray, recipe: dict, kind: str, role: np.ndarray | None = None) -> int:
        entries.append({"id": len(images), "kind": kind, "recipe": recipe})
        images.append(image.astype(np.uint8))
        roles.append(np.zeros((TILE, TILE), np.uint8) if role is None else role.astype(np.uint8))
        return len(images) - 1

    classes = [tile_class(t, tiles) for t in range(256)]
    for t in range(256):
        role = None
        if t in ROOF_TILES:
            red = tiles[ROOF_TILES[t]]
            role = np.zeros((TILE, TILE), np.uint8)
            role[(tiles[t] == 11) & (red == 10)] = 1
            role[(tiles[t] == 7) & (red == 6)] = 2
        add(tiles[t], {"op": "original", "tile": t}, "roof" if role is not None else f"original:{classes[t]}", role)
    joins: dict[str, dict[str, int]] = {"river": {}, "road": {}}
    joins["river"]["NS"] = add(river_part(tiles, "NS"), {"op": "stack", "top": 0x6D, "bottom": 0x5D}, "river")
    for mask, parts in RIVER_JOINS.items():
        image = overlay(tiles, river_part(tiles, parts[0]), [river_part(tiles, p) for p in parts[1:]], RIVER_PIXELS)
        joins["river"][mask] = add(image, {"op": "overlay", "parts": list(parts), "pixels": list(RIVER_PIXELS)}, "river")
    for mask, parts in ROAD_JOINS.items():
        image = overlay(tiles, tiles[ROAD[parts[0]]], [tiles[ROAD[p]] for p in parts[1:]], ROAD_PIXELS)
        joins["road"][mask] = add(image, {"op": "overlay", "parts": [ROAD[p] for p in parts], "pixels": list(ROAD_PIXELS)}, "road")
    village = tiles[0x02].copy()
    quarter = tiles[0xFE][0:8, 0:8]
    keep = quarter != 9
    village[4:12, 4:12][keep] = quarter[keep]
    village_id = add(village, {"op": "inset", "base": 0x02, "part": 0xFE, "from": [0, 0, 8, 8], "to": [4, 4], "skip": [9]}, "village")
    base_count = len(images)
    variants: dict[str, dict[str, int]] = {"desert": {}, "plateau": {}}
    for name, table in (("desert", DESERT), ("plateau", PLATEAU)):
        remap = np.arange(16, dtype=np.uint8)
        for src, dst in table.items():
            remap[src] = dst
        for base in range(base_count):
            if entries[base]["kind"] == "roof":
                continue  # 지붕 칸(세력색 역할)은 변형을 만들지 않는다. 성 칸에 변형을 쓸지는 굽기가 칸마다 정한다
            image = remap[images[base]]
            if (image == images[base]).all():
                continue
            variants[name][str(base)] = add(image, {"op": "palette", "base": base, "table": name}, f"{name}:{entries[base]['kind']}")
    index = {
        "river": joins["river"] | {k: v for k, v in RIVER.items()},
        "road": joins["road"] | {k: v for k, v in ROAD.items()},
        "village": village_id,
        "variants": variants,
        "castle": CASTLE_PARTS,
        "pass": PASS_PARTS,
        "bridge": BRIDGE_PARTS,
        "roofTiles": sorted(ROOF_TILES),
    }
    return np.stack(images), np.stack(roles), entries, index


# ── 스프라이트: 표지 269장, 깃발 천 2종, 1칸 거점 4종(원작 부품으로만 조립)


def flag_cloths(markers: np.ndarray) -> dict[str, np.ndarray]:
    fringe = markers[FLAG_SOURCE_MARKER].copy()
    rows, cols = np.meshgrid(FLAG_CLOTH_ROWS, FLAG_CLOTH_COLS, indexing="ij")
    glyph = fringe[rows, cols] == 15
    fringe[rows[glyph], cols[glyph]] = 10  # 원작 글자를 천 색으로 지운다
    swallow = fringe.copy()
    for row, cut in SWALLOW_CUT.items():
        swallow[row, cut] = 0  # 원작 테두리 색 0
        swallow[row, cut + 1 :] = -1
    return {"fringe": fringe, "swallow": swallow}


def shrink_mode(image: np.ndarray, role: np.ndarray, factor: int) -> tuple[np.ndarray, np.ndarray]:
    n = image.shape[0] // factor
    out = np.zeros((n, n), np.int16)
    out_role = np.zeros((n, n), np.uint8)
    for j in range(n):
        for i in range(n):
            block = image[j * factor : (j + 1) * factor, i * factor : (i + 1) * factor].ravel().tolist()
            out[j, i] = Counter(block).most_common(1)[0][0]
            rb = role[j * factor : (j + 1) * factor, i * factor : (i + 1) * factor].ravel()
            rb = rb[rb > 0]
            if len(rb) * 2 >= factor * factor:
                out_role[j, i] = Counter(rb.tolist()).most_common(1)[0][0]
    return out, out_role


def small_castle(tiles: np.ndarray, kit_roles: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    p = CASTLE_PARTS["small"]
    layout = [[p["tl"], p["wn"], p["tr"]], [p["gw"], CASTLE_PARTS["keep"], p["ge"]], [p["bl"], p["ws"], p["br"]]]
    image = np.block([[tiles[t] for t in row] for row in layout]).astype(np.int16)
    role = np.block([[kit_roles[t] for t in row] for row in layout])
    return image, role


def outlined(image: np.ndarray) -> np.ndarray:
    out = image.copy()
    opaque = image >= 0
    h, w = image.shape
    for y in range(h):
        for x in range(w):
            if opaque[y, x]:
                continue
            if any(0 <= y + dy < h and 0 <= x + dx < w and opaque[y + dy, x + dx] for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                out[y, x] = 0  # 풀밭 위에서 뜨게 원작 검정 0으로 한 줄 테두리
    return out


def site_icons(tiles: np.ndarray, kit_roles: np.ndarray) -> dict[str, tuple[np.ndarray, np.ndarray, dict]]:
    icons: dict[str, tuple[np.ndarray, np.ndarray, dict]] = {}
    # 장현: 원작 민가(FE) 타일 안쪽 14×14, 지붕 색(8 · 1)이 세력색 역할
    house = tiles[0xFE].astype(np.int16)
    image = np.full((TILE, TILE), -1, np.int16)
    image[1:15, 1:15] = house[1:15, 1:15]
    role = np.zeros((TILE, TILE), np.uint8)
    role[image == 8] = 1
    role[image == 1] = 2
    icons["county"] = (outlined(image), role, {"op": "crop", "tile": 0xFE, "rect": [1, 1, 15, 15], "roleColors": {"8": 1, "1": 2}, "outline": 0})
    # 수(나루): 작은 성 3×3을 1/4로 줄인 12×12 + 원작 다리 판자(B9) 아래 네 줄
    castle, castle_role = small_castle(tiles, kit_roles)
    mini, mini_role = shrink_mode(castle, castle_role, 4)
    image = np.full((TILE, TILE), -1, np.int16)
    role = np.zeros((TILE, TILE), np.uint8)
    image[0:12, 2:14] = mini
    role[0:12, 2:14] = mini_role
    plank = tiles[BRIDGE_PARTS["narrowEW"]].astype(np.int16)
    image[12:16, 0:16] = plank[6:10, 0:16]
    icons["ferry"] = (outlined(image), role, {"op": "assemble", "castle": "small", "shrink": 4, "plank": {"tile": BRIDGE_PARTS["narrowEW"], "rows": [6, 10]}})
    # 진(요새): 원작 관문 문루(D0) 그대로, 지붕이 세력색 역할
    image = tiles[0xD0].astype(np.int16)
    icons["fort"] = (image, kit_roles[0xD0].copy(), {"op": "original", "tile": 0xD0})
    # 이(이민족 부락): 원작 숲(B1)과 민가(FE) 네 귀를 엇갈려 놓는다
    forest = tiles[CASTLE_PARTS["garden"]].astype(np.int16)
    image = np.full((TILE, TILE), -1, np.int16)
    image[0:8, 0:8] = house[0:8, 0:8]
    image[8:16, 8:16] = house[8:16, 8:16]
    image[0:8, 8:16] = forest[0:8, 8:16]
    image[8:16, 0:8] = forest[8:16, 0:8]
    role = np.zeros((TILE, TILE), np.uint8)
    houses = np.zeros((TILE, TILE), bool)
    houses[0:8, 0:8] = True
    houses[8:16, 8:16] = True
    role[houses & (image == 8)] = 1
    role[houses & (image == 1)] = 2
    icons["tribe"] = (image, role, {"op": "quarters", "house": 0xFE, "forest": CASTLE_PARTS["garden"], "roleColors": {"8": 1, "1": 2}})
    return icons


# ── 이미지 · 해시


def pixel_sha(array: np.ndarray) -> str:
    return hashlib.sha256(np.ascontiguousarray(array).tobytes()).hexdigest()


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG", optimize=False, compress_level=9)
    return buffer.getvalue()


def sheet(cells: np.ndarray, columns: int, fill: int) -> np.ndarray:
    count = cells.shape[0]
    rows = (count + columns - 1) // columns
    out = np.full((rows * TILE, columns * TILE) + cells.shape[3:], fill, cells.dtype)
    for n, cell in enumerate(cells):
        r, c = divmod(n, columns)
        out[r * TILE : (r + 1) * TILE, c * TILE : (c + 1) * TILE] = cell
    return out


def rgba(indexed: np.ndarray, palette: np.ndarray) -> np.ndarray:
    colours = palette[np.clip(indexed, 0, 15)]
    alpha = np.where(indexed >= 0, 255, 0).astype(np.uint8)
    out = np.dstack([colours, alpha])
    out[indexed < 0] = 0
    return out


def mips(images: np.ndarray, palette: np.ndarray) -> dict[int, np.ndarray]:
    colours = palette[images].astype(np.float64)  # n × 16 × 16 × 3
    out = {}
    for size in MIP_SIZES:
        k = TILE // size
        reduced = colours.reshape(len(images), size, k, size, k, 3).mean(axis=(2, 4))
        out[size] = np.floor(reduced + 0.5).astype(np.uint8)
    return out


def build(sources: dict[str, bytes]) -> tuple[dict[str, bytes], dict]:
    tiles = decode_tiles(sources["MMAP.MDL"])
    layout = decode_map(sources["MMAP.MAP"])
    markers = decode_markers(sources["MMAP.MCH"])
    palettes = decode_palettes(sources["GAMEPAL.BRG"])
    day = palettes[DAY_BANK]
    kit, kit_roles, kit_entries, kit_index = build_kit(tiles)
    stats = learn_statistics(tiles, layout)
    cloths = flag_cloths(markers)
    sites = site_icons(tiles, kit_roles)

    files: dict[str, bytes] = {}
    images: dict[str, np.ndarray] = {}

    def put_image(name: str, array: np.ndarray, mode: str) -> None:
        images[name] = array
        files[name] = png_bytes(Image.fromarray(array, mode))

    put_image("tiles.png", sheet(tiles, SPRITE_COLUMNS, 0), "L")
    packed = kit | (kit_roles << 4)  # 값 = 팔레트 색인 + 16 × 역할(0 없음 · 1 세력 주색 · 2 세력 그늘)
    put_image("kit-index.png", sheet(packed, ATLAS_COLUMNS, 0), "L")
    put_image("kit.png", sheet(day[kit], ATLAS_COLUMNS, 0), "RGB")
    for size, reduced in mips(kit, day).items():
        count = len(reduced)
        rows = (count + ATLAS_COLUMNS - 1) // ATLAS_COLUMNS
        grid = np.zeros((rows * size, ATLAS_COLUMNS * size, 3), np.uint8)
        for n, cell in enumerate(reduced):
            r, c = divmod(n, ATLAS_COLUMNS)
            grid[r * size : (r + 1) * size, c * size : (c + 1) * size] = cell
        put_image(f"kit-mip{size}.png", grid, "RGB")
    put_image("markers.png", rgba(sheet(markers, SPRITE_COLUMNS, -1), day), "RGBA")
    marker_roles = np.zeros(markers.shape, np.uint8)
    marker_roles[:120][markers[:120] == 10] = 1  # 부대 표지: 채움(빨강 10) = 세력 주색
    marker_roles[:120][markers[:120] == 15] = 3  # 테두리(흰 15) = 세력색 밝기에 따라 흰색 · 갈색
    put_image("markers-roles.png", sheet(marker_roles, SPRITE_COLUMNS, 0), "L")
    flag_stack = np.stack([cloths["fringe"], cloths["swallow"]])
    put_image("flags.png", rgba(np.hstack(list(flag_stack)), day), "RGBA")
    put_image("flags-roles.png", np.hstack([(c == 10).astype(np.uint8) for c in flag_stack]), "L")
    site_names = list(sites)
    put_image("sites.png", rgba(np.hstack([sites[n][0] for n in site_names]), day), "RGBA")
    put_image("sites-roles.png", np.hstack([sites[n][1] for n in site_names]), "L")

    stats_json = (json.dumps(stats, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=9, mtime=0, filename="") as gz:
        gz.write(stats_json)
    files["synth-stats.json.gz"] = buffer.getvalue()
    files["palettes.json"] = (json.dumps({
        "schemaVersion": 1,
        "encoding": "GAMEPAL.BRG bytes [B,R,G] 4-bit; RGB = (R, G, B) * 17",
        "dayBank": DAY_BANK,
        "banks": palettes.tolist(),
    }, sort_keys=True, separators=(",", ":")) + "\n").encode()

    catalog = {
        "schemaVersion": 1,
        "status": "owner-accepted derived catalog",
        "source": {
            "game": "제갈공명 와룡전",
            "files": list(SOURCE_FILES),
            "sha256": {name: hashlib.sha256(sources[name]).hexdigest() for name in SOURCE_FILES},
            "originalBinaryCommitted": False,
        },
        "tile": TILE,
        "atlasColumns": ATLAS_COLUMNS,
        "spriteColumns": SPRITE_COLUMNS,
        "kit": {
            "count": len(kit_entries),
            "indexEncoding": "kit-index.png: value = palette index (0-15) + 16 * role; role 0 none, 1 nation main, 2 nation shade (HLS lightness x 0.55)",
            "entries": kit_entries,
            "lookup": kit_index,
            "mips": list(MIP_SIZES),
        },
        "markers": {
            "count": int(markers.shape[0]),
            "roles": "markers-roles.png: 1 nation main (army fill 10), 3 contrast border (army border 15: white, or brown on light nations)",
            "groups": {"army": [0, 119], "dust": [128, 162], "effects": [[153, 156], [180, 183], [237, 239]], "notMarkers": [256, 268]},
            "armyLayout": "index = (shape * 6 + colour) * 5 + frame; shapes A filled, B striped, C rimmed, D fret; colours red, blue, yellow, green, orange, black; frames 0 left, 1 right, 2 up, 3 down, 4 flag (KI.EXE 0x2b28)",
            "armyTemplates": "recolour the red bundles (index (shape * 6) * 5 + frame): role 1 pixels take the nation colour",
        },
        "flags": {
            "order": ["fringe", "swallow"],
            "use": {"fringe": "castle and pass (nation first letter)", "swallow": "army (general first letter)"},
            "source": {"marker": FLAG_SOURCE_MARKER, "glyphErased": {"rows": [FLAG_CLOTH_ROWS.start, FLAG_CLOTH_ROWS.stop], "cols": [FLAG_CLOTH_COLS.start, FLAG_CLOTH_COLS.stop], "from": 15, "to": 10},
                       "swallowCut": {str(k): v for k, v in SWALLOW_CUT.items()}},
            "roles": "flags-roles.png: 1 cloth (nation colour); letters are drawn by the app along the cloth slant",
        },
        "sites": {
            "order": site_names,
            "levels": {"county": 11, "ferry": 1, "fort": 2, "tribe": 4},
            "recipes": {name: sites[name][2] for name in site_names},
            "roles": "sites-roles.png: 1 nation main, 2 nation shade",
        },
        "statistics": {"file": "synth-stats.json.gz", "contentSha256": hashlib.sha256(stats_json).hexdigest(), "bytes": len(stats_json)},
        "images": {name: {"mode": Image.fromarray(array).mode if array.ndim == 2 else {3: "RGB", 4: "RGBA"}[array.shape[2]],
                          "size": [int(array.shape[1]), int(array.shape[0])], "pixelSha256": pixel_sha(array)}
                   for name, array in sorted(images.items())},
    }
    files["catalog.json"] = (json.dumps(catalog, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return files, {"tiles": tiles, "kit": kit, "kitRoles": kit_roles, "day": day, "sites": sites, "cloths": cloths, "markers": markers}


def preview(parts: dict) -> dict[str, bytes]:
    day = parts["day"]
    nations = [np.array(c) for c in ((0x4F, 0x7F, 0xBF), (0xB0, 0x56, 0x9A), (0x3F, 0x8F, 0x3A))]

    def paint(indexed: np.ndarray, role: np.ndarray, colour: np.ndarray | None) -> np.ndarray:
        out = rgba(indexed, day).astype(np.float64)
        if colour is not None:
            hh, l, s = colorsys.rgb_to_hls(*(colour / 255))
            shade = np.round(np.array(colorsys.hls_to_rgb(hh, l * 0.55, s)) * 255)
            out[..., :3][role == 1] = colour
            out[..., :3][role == 2] = shade
        return out.astype(np.uint8)

    kit_rgb = rgba(sheet(parts["kit"].astype(np.int16), ATLAS_COLUMNS, -1), day)
    kit_img = Image.fromarray(kit_rgb, "RGBA").resize((kit_rgb.shape[1] * 2, kit_rgb.shape[0] * 2), Image.NEAREST)
    rows = []
    for colour in [None] + nations:
        cells = [paint(parts["sites"][n][0], parts["sites"][n][1], colour) for n in parts["sites"]]
        cells += [paint(c, (c == 10).astype(np.uint8), colour) for c in parts["cloths"].values()]
        rows.append(np.hstack(cells))
    sprite = np.vstack(rows)
    sprite_img = Image.fromarray(sprite, "RGBA").resize((sprite.shape[1] * 4, sprite.shape[0] * 4), Image.NEAREST)
    return {"kit.png": png_bytes(kit_img), "sites-and-flags.png": png_bytes(sprite_img)}


def decoded_pixels(data: bytes) -> np.ndarray:
    return np.array(Image.open(io.BytesIO(data)))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True, help="read-only folder containing MMAP.MDL/MAP/MCH and GAMEPAL.BRG")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    sources = {name: (args.source_dir / name).read_bytes() for name in SOURCE_FILES}
    files, parts = build(sources)
    previews = preview(parts)
    if args.check:
        for name, data in sorted(files.items()):
            target = OUTPUT / name
            if not target.is_file():
                raise SystemExit(f"missing export: {name}")
            if name.endswith(".png"):
                if not np.array_equal(decoded_pixels(target.read_bytes()), decoded_pixels(data)):
                    raise SystemExit(f"pixel drift: {name}")
            elif name.endswith(".gz"):
                if gzip.decompress(target.read_bytes()) != gzip.decompress(data):
                    raise SystemExit(f"content drift: {name}")
            elif target.read_bytes() != data:
                raise SystemExit(f"content drift: {name}")
        stale = sorted(p.name for p in OUTPUT.iterdir() if p.is_file() and p.name not in files)
        if stale:
            raise SystemExit(f"stale exports: {stale}")
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        PREVIEW.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (OUTPUT / name).write_bytes(data)
        for name, data in previews.items():
            (PREVIEW / name).write_bytes(data)
    catalog = json.loads(files["catalog.json"])
    print(f"kit {catalog['kit']['count']} tiles; markers {catalog['markers']['count']}; sites {len(catalog['sites']['order'])}; "
          f"stats {catalog['statistics']['bytes']} bytes")


if __name__ == "__main__":
    main()
