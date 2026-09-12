#!/usr/bin/env python3
"""Build compact Han-map administrative markers from the checked-in design spec."""

from __future__ import annotations

import argparse
import hashlib
from io import BytesIO
import json
from pathlib import Path
import sys

from PIL import Image, ImageDraw


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "originals" / "map-city-markers" / "design.json"
EXPORT_DIR = ROOT / "exports" / "map" / "markers"
PREVIEW_PATH = ROOT / "previews" / "map-city-markers.png"
SCALE = 4


def rgba(hex_color: str) -> tuple[int, int, int, int]:
    value = hex_color.removeprefix("#")
    return tuple(int(value[index:index + 2], 16) for index in (0, 2, 4)) + (255,)


def scaled(points: list[tuple[float, float]]) -> list[tuple[int, int]]:
    return [(round(x * SCALE), round(y * SCALE)) for x, y in points]


def marker_png(config: dict, palette: dict[str, str]) -> bytes:
    width = config["width"]
    height = config["height"]
    image = Image.new("RGBA", (width * SCALE, height * SCALE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    outline = rgba(palette["outline"])
    rim = rgba(palette["rim"])
    face = rgba(palette["face"])
    gold = rgba(palette["gold"])
    gate = rgba(palette["gate"])
    center = width / 2
    finial_space = 6 if config.get("finial") else 1

    if config.get("finial"):
        diamond = [(center, 0.5), (center + 3.3, 4), (center, 7.5), (center - 3.3, 4)]
        draw.polygon(scaled(diamond), fill=outline)
        inner = [(center, 1.6), (center + 2.1, 4), (center, 6.4), (center - 2.1, 4)]
        draw.polygon(scaled(inner), fill=gold)

    outer = [
        (center, finial_space), (width - 4, finial_space + 3),
        (width - 1.5, height * 0.50), (width - 5, height * 0.72),
        (center, height - 1), (5, height * 0.72),
        (1.5, height * 0.50), (4, finial_space + 3),
    ]
    draw.polygon(scaled(outer), fill=outline)
    rim_shape = [
        (center, finial_space + 2), (width - 5.4, finial_space + 4.2),
        (width - 3.5, height * 0.50), (width - 6.6, height * 0.69),
        (center, height - 3.4), (6.6, height * 0.69),
        (3.5, height * 0.50), (5.4, finial_space + 4.2),
    ]
    draw.polygon(scaled(rim_shape), fill=gold if config.get("finial") else rim)
    face_shape = [
        (center, finial_space + 4), (width - 7, finial_space + 6),
        (width - 5.5, height * 0.50), (width - 8, height * 0.66),
        (center, height - 6), (8, height * 0.66),
        (5.5, height * 0.50), (7, finial_space + 6),
    ]
    draw.polygon(scaled(face_shape), fill=face)

    tiers = config["roofTiers"]
    roof_width = min(width - 12, 10 + tiers * 3.5)
    roof_top = finial_space + 6
    for tier in range(tiers):
        y = roof_top + tier * 4.2
        half = roof_width / 2 - tier * 0.5
        roof = [
            (center - half, y + 2.5), (center - half * 0.35, y + 1.6),
            (center, y - 0.8), (center + half * 0.35, y + 1.6),
            (center + half, y + 2.5), (center + half - 1, y + 4),
            (center, y + 1.4), (center - half + 1, y + 4),
        ]
        draw.polygon(scaled(roof), fill=outline)
        inset = [(x + (center - x) * 0.16, yy + 0.45) for x, yy in roof[:5]]
        inset += [(center + half - 1.6, y + 3.1), (center, y + 0.7), (center - half + 1.6, y + 3.1)]
        draw.polygon(scaled(inset), fill=gold)

    gate_y = roof_top + tiers * 4.1 + 1.2
    gates = config["gates"]
    total_width = gates * 3.6 + (gates - 1) * 1.1
    start_x = center - total_width / 2
    draw.rectangle(
        scaled([(start_x - 1.4, gate_y - 1), (start_x + total_width + 1.4, gate_y + 5.6)]),
        fill=outline,
    )
    for gate_index in range(gates):
        x0 = start_x + gate_index * 4.7
        draw.rectangle(scaled([(x0, gate_y + 0.4), (x0 + 3.6, gate_y + 4.7)]), fill=gate)
        draw.rectangle(scaled([(x0 + 0.7, gate_y + 1.1), (x0 + 2.9, gate_y + 4.7)]), fill=gold)

    image = image.resize((width, height), Image.Resampling.LANCZOS)
    output = BytesIO()
    image.save(output, format="PNG", optimize=True)
    return output.getvalue()


def preview_png(markers: dict[str, bytes]) -> bytes:
    canvas = Image.new("RGBA", (420, 180), (38, 49, 48, 255))
    draw = ImageDraw.Draw(canvas)
    draw.rounded_rectangle((12, 12, 408, 168), radius=14, fill=(51, 68, 61, 255), outline=(111, 123, 93, 255), width=2)
    positions = {"county": 72, "commandery": 210, "capital": 348}
    for name, x in positions.items():
        icon = Image.open(BytesIO(markers[name])).convert("RGBA")
        canvas.alpha_composite(icon, (x - icon.width // 2, 48 - icon.height // 2))
        large = icon.resize((icon.width * 2, icon.height * 2), Image.Resampling.NEAREST)
        canvas.alpha_composite(large, (x - large.width // 2, 78))
    output = BytesIO()
    canvas.save(output, format="PNG", optimize=True)
    return output.getvalue()


def build_outputs() -> dict[Path, bytes]:
    spec_bytes = SPEC_PATH.read_bytes()
    spec = json.loads(spec_bytes)
    markers = {
        name: marker_png(config, spec["palette"])
        for name, config in spec["markers"].items()
    }
    manifest = {
        "version": 1,
        "pixelRatio": 2,
        "designSha256": hashlib.sha256(spec_bytes).hexdigest(),
        "markers": {
            name: {
                "file": f"{name}.png",
                "width": config["width"],
                "height": config["height"],
                "anchor": [config["width"] // 2, config["height"] - 2],
                "sha256": hashlib.sha256(markers[name]).hexdigest(),
            }
            for name, config in spec["markers"].items()
        },
    }
    outputs = {EXPORT_DIR / f"{name}.png": content for name, content in markers.items()}
    outputs[EXPORT_DIR / "manifest.json"] = (json.dumps(manifest, ensure_ascii=False, indent=2) + "\n").encode()
    outputs[PREVIEW_PATH] = preview_png(markers)
    return outputs


def output_matches(path: Path, content: bytes) -> bool:
    if not path.exists():
        return False
    if path != PREVIEW_PATH:
        return path.read_bytes() == content
    with Image.open(path) as checked_in, Image.open(BytesIO(content)) as generated:
        return checked_in.size == generated.size and checked_in.convert("RGBA").tobytes() == generated.convert("RGBA").tobytes()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail when checked-in outputs drift")
    args = parser.parse_args()
    outputs = build_outputs()
    if args.check:
        drift = [str(path.relative_to(ROOT)) for path, content in outputs.items() if not output_matches(path, content)]
        if drift:
            print("map city marker outputs are stale:", *drift, sep="\n  ", file=sys.stderr)
            return 1
        return 0
    for path, content in outputs.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
