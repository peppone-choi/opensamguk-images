#!/usr/bin/env python3
"""Build the Waryong battle board kit (original pieces, records, board layouts, units); never copy original binaries.

The kit lets the app assemble any of the 214 isometric battle boards in the browser instead of shipping
69 MB of pre-rendered board images. Layout rules (KI.EXE 0xdc80 · 0xdd78 · 0xe049 · 0xe0a5):
cell (r, c) → x = (r + c) · 16, y = (r − c) · 8 + 64 · 8 + TOP − L · 16 for layer L; all layer-0 pieces first,
then layer 1, …; inside a layer cells go back (small r − c) to front. `--check` rebuilds and compares content.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
OUTPUT = ROOT / "waryong" / "battle" / "kit"
SOURCE_FILES = ("BATTLE.MAP", "BATTLE.MDL", "BATTLE.SCH", "GAMEPAL.BRG")
BOARDS = 214
SIDE = 64
LAYERS = 7
PIECE_W, PIECE_H = 32, 16
PIECES = 256
TILESETS = 3
TILESET_BYTES = 0xF800
STEP = 16
TOP = LAYERS * STEP + 8
CANVAS_W = 2 * SIDE * 16 + PIECE_W
CANVAS_H = 2 * SIDE * 8 + TOP + PIECE_H
EMPTY = 255
UNIT_PIECES = 360


def piece_bits(block: bytes) -> np.ndarray:
    """64 bytes = four quadrants (TL, TR, BL, BR) × 8 rows × 2 bytes → 16 × 32 bits."""
    quads = np.unpackbits(np.frombuffer(block, np.uint8)).reshape(4, 8, 16)
    out = np.zeros((PIECE_H, PIECE_W), np.uint8)
    out[0:8, 0:16], out[0:8, 16:32], out[8:16, 0:16], out[8:16, 16:32] = quads
    return out


def decode_piece(block: bytes) -> np.ndarray:
    """[mask 64B][plane × 4 of 64B] → palette index, EMPTY where the mask is clear."""
    mask = piece_bits(block[:64]).astype(bool)
    index = sum(piece_bits(block[64 * (k + 1) : 64 * (k + 2)]).astype(np.uint8) << k for k in range(4))
    return np.where(mask, index, EMPTY).astype(np.uint8)


def decode_tilesets(mdl: bytes) -> tuple[np.ndarray, np.ndarray]:
    if len(mdl) < 4096 + TILESETS * TILESET_BYTES:
        raise ValueError("BATTLE.MDL lacks three complete tilesets")
    records = np.zeros((TILESETS, PIECES, 8), np.uint8)
    pieces = np.full((TILESETS, PIECES, PIECE_H, PIECE_W), EMPTY, np.uint8)
    for ts in range(TILESETS):
        base = 4096 + ts * TILESET_BYTES
        records[ts] = np.frombuffer(mdl[base : base + 2048], np.uint8).reshape(PIECES, 8)
        for p in range(1, PIECES):
            at = base + 0x800 + p * 320
            if at + 320 > base + TILESET_BYTES:
                break
            pieces[ts, p] = decode_piece(mdl[at : at + 320])
    return records, pieces


def decode_boards(raw: bytes) -> tuple[np.ndarray, np.ndarray]:
    if len(raw) != 512 + BOARDS * SIDE * SIDE:
        raise ValueError("BATTLE.MAP size does not match 214 original 64x64 boards")
    tilesets = np.frombuffer(raw[: BOARDS * 2], np.uint8)[0::2].copy()
    grids = np.frombuffer(raw[512:], np.uint8).reshape(BOARDS, SIDE, SIDE).copy()
    return tilesets, grids


def decode_units(sch: bytes) -> np.ndarray:
    if len(sch) != UNIT_PIECES * 320:
        raise ValueError("BATTLE.SCH size does not match 360 unit pieces")
    return np.stack([decode_piece(sch[n * 320 : (n + 1) * 320]) for n in range(UNIT_PIECES)])


def unit_roles(units: np.ndarray) -> np.ndarray:
    """Roles from the red side (0–179) against the blue side (180–359): 1 main, 2 shade, 3 light, 4 flag rim."""
    red, blue = units[:180].astype(np.int16), units[180:].astype(np.int16)
    roles = np.zeros(red.shape, np.uint8)
    roles[(red == 10) & (blue == 3)] = 1
    roles[(red == 6) & (blue == 8)] = 2
    roles[(red == 7) & (blue == 1)] = 3
    roles[(red == 0) & (blue == 12)] = 4
    return roles


def compose(records: np.ndarray, pieces: np.ndarray, tileset: int, grid: np.ndarray) -> np.ndarray:
    canvas = np.full((CANVAS_H, CANVAS_W), EMPTY, np.uint8)
    order = sorted(((r - c), (r + c), r, c) for r in range(SIDE) for c in range(SIDE))
    table = records[tileset]
    for layer in range(LAYERS):
        for _, _, r, c in order:
            pid = int(table[grid[r, c]][1 + layer])
            if pid == 0:
                continue
            piece = pieces[tileset, pid]
            x = (r + c) * 16
            y = (r - c) * 8 + SIDE * 8 + TOP - layer * STEP
            region = canvas[y : y + PIECE_H, x : x + PIECE_W]
            opaque = piece != EMPTY
            region[opaque] = piece[opaque]
    return canvas


def gz(data: bytes) -> bytes:
    buffer = io.BytesIO()
    with gzip.GzipFile(fileobj=buffer, mode="wb", compresslevel=9, mtime=0, filename="") as out:
        out.write(data)
    return buffer.getvalue()


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build(sources: dict[str, bytes]) -> dict[str, bytes]:
    records, pieces = decode_tilesets(sources["BATTLE.MDL"])
    tilesets, grids = decode_boards(sources["BATTLE.MAP"])
    units = decode_units(sources["BATTLE.SCH"])
    roles = unit_roles(units)
    palette = np.frombuffer(sources["GAMEPAL.BRG"], np.uint8).reshape(8, 16, 3)
    day = (np.stack([palette[1, :, 1], palette[1, :, 2], palette[1, :, 0]], axis=-1) * 17).astype(int).tolist()
    boards = []
    for n in range(BOARDS):
        ts = int(tilesets[n])
        if ts not in range(TILESETS):
            raise ValueError(f"board {n}: invalid tileset {ts}")
        grid = grids[n]
        if any(records[ts, rid, 0] == 0 for rid in set(grid.ravel().tolist())):
            raise ValueError(f"board {n}: references an empty record")
        boards.append({
            "id": n,
            "tileset": ts,
            "layoutSha256": sha(bytes([ts]) + grid.tobytes()),
            "composedSha256": sha(compose(records, pieces, ts, grid).tobytes()),
        })
    files = {
        "pieces.bin.gz": gz(pieces.tobytes()),
        "records.bin": records.tobytes(),
        "boards.bin.gz": gz(grids.tobytes()),
        "units.bin.gz": gz(units.tobytes()),
        "unit-roles.bin.gz": gz(roles.tobytes()),
    }
    kit = {
        "schemaVersion": 1,
        "artifactId": "waryong-battle-kit",
        "status": "owner-accepted derived kit",
        "source": {
            "game": "제갈공명 와룡전",
            "files": list(SOURCE_FILES),
            "sha256": {name: sha(sources[name]) for name in SOURCE_FILES},
            "originalBinaryCommitted": False,
        },
        "layout": {
            "boards": BOARDS, "side": SIDE, "layers": LAYERS, "tilesets": TILESETS, "piecesPerTileset": PIECES,
            "piece": [PIECE_W, PIECE_H], "step": STEP, "top": TOP, "canvas": [CANVAS_W, CANVAS_H], "empty": EMPTY,
            "project": "x = (r + c) * 16, y = (r - c) * 8 + side * 8 + top - layer * step",
            "order": "layer 0 for every cell, then layer 1, …; within a layer sort by (r - c, r + c)",
            "record": "8 bytes: [layer count, piece id for layers 0..6]; piece 0 = none; layer count is not used for drawing",
        },
        "files": {
            "pieces.bin.gz": {"shape": [TILESETS, PIECES, PIECE_H, PIECE_W], "dtype": "uint8", "meaning": "palette index, 255 transparent", "contentSha256": sha(pieces.tobytes())},
            "records.bin": {"shape": [TILESETS, PIECES, 8], "dtype": "uint8", "contentSha256": sha(records.tobytes())},
            "boards.bin.gz": {"shape": [BOARDS, SIDE, SIDE], "dtype": "uint8", "meaning": "record id per cell [board][r][c]", "contentSha256": sha(grids.tobytes())},
            "units.bin.gz": {"shape": [UNIT_PIECES, PIECE_H, PIECE_W], "dtype": "uint8", "meaning": "palette index, 255 transparent; 0-179 red side, 180-359 blue side; a unit = pieces 2k (top) and 2k+1 (bottom)", "contentSha256": sha(units.tobytes())},
            "unit-roles.bin.gz": {"shape": [180, PIECE_H, PIECE_W], "dtype": "uint8", "meaning": "red template roles: 1 main, 2 shade, 3 light, 4 flag rim", "contentSha256": sha(roles.tobytes())},
        },
        "palette": {"bank": "GAMEPAL.BRG set 0, second bank (day)", "rgb": day},
        "boards": boards,
        "hashes": {
            "layoutSha256": "sha256(tileset byte + 64x64 record ids)",
            "composedSha256": "sha256 of the composed canvas (uint8 palette index, 255 empty, canvas size)",
        },
        "structures": {"status": "UNKNOWN", "note": "gate open/closed/broken, wall durability and ladder record ids are not identified yet"},
    }
    files["kit.json"] = (json.dumps(kit, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    return files


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True, help="read-only folder containing BATTLE.* and GAMEPAL.BRG")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    files = build({name: (args.source_dir / name).read_bytes() for name in SOURCE_FILES})
    if args.check:
        for name, data in sorted(files.items()):
            target = OUTPUT / name
            if not target.is_file():
                raise SystemExit(f"missing export: {name}")
            same = gzip.decompress(target.read_bytes()) == gzip.decompress(data) if name.endswith(".gz") else target.read_bytes() == data
            if not same:
                raise SystemExit(f"content drift: {name}")
        stale = sorted(p.name for p in OUTPUT.iterdir() if p.is_file() and p.name not in files)
        if stale:
            raise SystemExit(f"stale exports: {stale}")
    else:
        OUTPUT.mkdir(parents=True, exist_ok=True)
        for name, data in files.items():
            (OUTPUT / name).write_bytes(data)
    print(f"{BOARDS} boards; files {', '.join(f'{k} {len(v)}' for k, v in sorted(files.items()))}")


if __name__ == "__main__":
    main()
