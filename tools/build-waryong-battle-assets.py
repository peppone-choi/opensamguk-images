#!/usr/bin/env python3
"""Build derived Waryong battle exports; never copy original game binaries."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MAP_COUNT = 214
SIDE = 64
HEADER_BYTES = 512
WALL_CAPS = ({125}, {114, 117}, {139, 166})
MOUNTAIN_CAPS = ({165}, {163, 164}, {152})


def piece_colors(mdl: bytes, tileset: int, piece: int) -> Counter[int]:
    offset = 4096 + tileset * 0xF800 + 0x800 + piece * 320
    block = mdl[offset : offset + 320]
    if len(block) != 320:
        raise ValueError(f"missing piece {tileset}:{piece}")
    colors: Counter[int] = Counter()
    for byte_index in range(64):
        for bit in range(8):
            mask = 128 >> bit
            if not block[byte_index] & mask:
                continue
            color = sum(
                (bool(block[64 * (plane + 1) + byte_index] & mask) << plane)
                for plane in range(4)
            )
            colors[color] += 1
    return colors


def terrain_for_record(mdl: bytes, tileset: int, record: bytes) -> str:
    layers = record[0]
    if layers == 0:
        return "P"  # unused MDL record; used records are checked below
    if layers > 7:
        raise ValueError(f"invalid layer count {layers}")
    cap = record[layers]
    if layers >= 3 and cap in WALL_CAPS[tileset]:
        return "W"
    base_colors = piece_colors(mdl, tileset, record[1])
    total = sum(base_colors.values())
    if total and base_colors[3] * 2 >= total:
        return "R"
    if layers >= 4 and cap in MOUNTAIN_CAPS[tileset]:
        return "M"
    if total and (base_colors[4] + base_colors[5]) * 2 >= total:
        return "F"
    return "P"


def catalog(map_bytes: bytes, mdl: bytes, sch: bytes) -> dict:
    if len(map_bytes) != HEADER_BYTES + MAP_COUNT * SIDE * SIDE:
        raise ValueError("BATTLE.MAP size does not match 214 original 64x64 boards")
    if len(mdl) < 4096 + 3 * 0xF800:
        raise ValueError("BATTLE.MDL lacks three complete tilesets")
    if len(sch) != 360 * 320:
        raise ValueError("BATTLE.SCH size does not match 360 original pieces")
    terrain_tables = []
    record_tables = []
    for tileset in range(3):
        table_at = 4096 + tileset * 0xF800
        table = [mdl[table_at + n * 8 : table_at + (n + 1) * 8] for n in range(256)]
        record_tables.append(table)
        terrain_tables.append([terrain_for_record(mdl, tileset, row) for row in table])
    boards = []
    for board_id in range(MAP_COUNT):
        tileset = map_bytes[board_id * 2]
        if tileset not in range(3):
            raise ValueError(f"board {board_id}: invalid tileset {tileset}")
        table = record_tables[tileset]
        terrain_table = terrain_tables[tileset]
        raw = map_bytes[
            HEADER_BYTES + board_id * SIDE * SIDE : HEADER_BYTES + (board_id + 1) * SIDE * SIDE
        ]
        if any(table[record_id][0] == 0 for record_id in set(raw)):
            raise ValueError(f"board {board_id}: references an empty MDL record")
        terrain = "".join(terrain_table[record_id] for record_id in raw)
        counts = Counter(terrain)
        boards.append(
            {
                "id": board_id,
                "tileset": tileset,
                "kind": "FORTRESS" if counts["W"] else "FIELD",
                "landEligible": board_id not in range(209, 213),
                "terrainCounts": {key: counts[key] for key in "PFMRW"},
                "terrainRows": [terrain[row * SIDE : (row + 1) * SIDE] for row in range(SIDE)],
                "image": f"maps/battle_{board_id:03d}_ts{tileset}.png",
            }
        )
    return {
        "schemaVersion": 1,
        "status": "owner-accepted derived catalog",
        "source": {
            "game": "제갈공명 와룡전",
            "files": ["BATTLE.MAP", "BATTLE.MDL", "BATTLE.SCH"],
            "battleMapSha256": hashlib.sha256(map_bytes).hexdigest(),
            "battleMdlSha256": hashlib.sha256(mdl).hexdigest(),
            "battleSchSha256": hashlib.sha256(sch).hexdigest(),
            "originalBinaryCommitted": False,
        },
        "boardSize": SIDE,
        "terrainLegend": {"P": "plain", "F": "forest", "M": "mountain", "R": "river", "W": "wall"},
        "classificationBasis": "MDL record top piece cap + base-piece palette; WALL_CAPS and MOUNTAIN_CAPS in this tool",
        "boards": boards,
    }


def png_names(directory: Path) -> set[str]:
    return {path.name for path in directory.glob("*.png") if path.is_file()}


def required_unit_names(side: str, source_dir: Path) -> set[str]:
    names = png_names(source_dir)
    if not names:
        raise SystemExit(f"rendered {side} units are empty: {source_dir}")
    return names


def require_names(label: str, actual: set[str], expected: set[str]) -> None:
    missing = sorted(expected - actual)
    extra = sorted(actual - expected)
    if missing or extra:
        raise SystemExit(
            f"{label} inventory drift: "
            f"missing={len(missing)} {missing[:5]}, extra={len(extra)} {extra[:5]}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True, help="read-only folder containing BATTLE.MAP/MDL")
    parser.add_argument("--rendered-dir", type=Path, required=True, help="read-only out/battle folder")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    output = ROOT / "waryong" / "battle"
    result = catalog(
        (args.source_dir / "BATTLE.MAP").read_bytes(),
        (args.source_dir / "BATTLE.MDL").read_bytes(),
        (args.source_dir / "BATTLE.SCH").read_bytes(),
    )
    expected_maps = {Path(board["image"]).name for board in result["boards"]}
    source_maps = args.rendered_dir / "maps"
    target_maps = output / "maps"
    require_names("rendered maps", png_names(source_maps), expected_maps)
    units = {}
    for side in ("red", "blue"):
        source_dir = args.rendered_dir / "units" / side / "sprites"
        target_dir = output / "units" / side
        names = required_unit_names(side, source_dir)
        units[side] = (source_dir, target_dir, names)
    if args.check:
        require_names("committed maps", png_names(target_maps), expected_maps)
        for side, (_, target_dir, names) in units.items():
            require_names(f"committed {side} units", png_names(target_dir), names)
    else:
        for target_dir, names in [(target_maps, expected_maps)] + [
            (target_dir, names) for _, target_dir, names in units.values()
        ]:
            for stale in target_dir.glob("*.png"):
                if stale.name not in names:
                    stale.unlink()
    encoded = (json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    manifest = output / "catalog-v1.json"
    if args.check:
        if manifest.read_bytes() != encoded:
            raise SystemExit("catalog drift")
    else:
        output.mkdir(parents=True, exist_ok=True)
        manifest.write_bytes(encoded)
    for board in result["boards"]:
        name = Path(board["image"]).name
        source = source_maps / name
        target = target_maps / name
        if args.check:
            if target.read_bytes() != source.read_bytes():
                raise SystemExit(f"map export drift: {name}")
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    for source_dir, target_dir, names in units.values():
        for name in sorted(names):
            source = source_dir / name
            target = target_dir / name
            if args.check:
                if target.read_bytes() != source.read_bytes():
                    raise SystemExit(f"unit export drift: {target.name}")
            else:
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(source, target)
    print(f"{len(result['boards'])} boards; {Counter(b['kind'] for b in result['boards'])}")


if __name__ == "__main__":
    main()
