#!/usr/bin/env python3
"""Build deployable full, bust, and face variants from original portrait sheets."""
from __future__ import annotations

import json
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parents[1]
PORTRAIT_ROOT = ROOT / "portraits-original/han-archetypes"
MANIFEST = PORTRAIT_ROOT / "manifest.json"
CELL_INSET = 3


def _resample() -> Image.Resampling:
    return Image.Resampling.LANCZOS


def _contain(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    fitted = ImageOps.contain(image, size, method=_resample())
    canvas = Image.new("RGB", size, (18, 18, 18))
    canvas.paste(fitted, ((size[0] - fitted.width) // 2, (size[1] - fitted.height) // 2))
    return canvas


def _cover(image: Image.Image, size: tuple[int, int], crop: tuple[float, float, float, float]) -> Image.Image:
    width, height = image.size
    left, top, right, bottom = crop
    region = image.crop((round(width * left), round(height * top), round(width * right), round(height * bottom)))
    return ImageOps.fit(region, size, method=_resample(), centering=(0.5, 0.42))


def build(manifest_path: Path = MANIFEST) -> list[Path]:
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    sheet_info = manifest["sheet"]
    sheet_path = manifest_path.parent / sheet_info["source"]
    with Image.open(sheet_path) as source:
        sheet = source.convert("RGB")

    columns = int(sheet_info["columns"])
    rows = int(sheet_info["rows"])
    if len(manifest["portraits"]) != columns * rows:
        raise ValueError("manifest must bind exactly one portrait to every sheet cell")
    if sheet.width % columns or sheet.height % rows:
        raise ValueError(f"sheet dimensions must divide cleanly: {sheet.size} / {columns}x{rows}")

    cell_width = sheet.width // columns
    cell_height = sheet.height // rows
    outputs: list[Path] = []
    for variant in ("full", "bust", "face"):
        (manifest_path.parent / variant).mkdir(parents=True, exist_ok=True)

    for item in manifest["portraits"]:
        cell_index = int(item["cell"])
        column, row = cell_index % columns, cell_index // columns
        box = (
            column * cell_width + CELL_INSET,
            row * cell_height + CELL_INSET,
            (column + 1) * cell_width - CELL_INSET,
            (row + 1) * cell_height - CELL_INSET,
        )
        cell = sheet.crop(box)
        variants = {
            "full": _contain(cell, (148, 210)),
            "bust": _cover(cell, (148, 210), (0.10, 0.00, 0.90, 1.00)),
            "face": _cover(cell, (96, 96), (0.23, 0.04, 0.77, 0.58)),
        }
        for variant, image in variants.items():
            output = manifest_path.parent / variant / f"{item['id']}.png"
            image.save(output, format="PNG", optimize=True)
            outputs.append(output)
    return outputs


if __name__ == "__main__":
    built = build()
    print(f"built {len(built)} portrait variants")
