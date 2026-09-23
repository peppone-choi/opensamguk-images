#!/usr/bin/env python3
"""Extract regional HanMapCanvas city icons from curated ImageGen atlases.

The existing central-plains art remains the fallback for levels 1-4 and for
regions without a reviewed atlas. This builder never changes the base icons.
"""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter

from build_city_icons import VARIANT_SIZES, VISUAL_EXTENT
from pixelize_iso2d import oklab

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'assets/city-icons'
LEVELS = (11, 10, 5, 6, 7, 8, 9)
STYLES = ('metropolitan', 'central-plain', 'hebei', 'east-coast',
          'northern-frontier', 'liangzhou', 'jingzhou', 'jiangdong', 'sichuan', 'lingnan')


def palette_from_file(path: Path) -> np.ndarray:
    colors = json.loads(path.read_text())['colors']
    palette = np.array([[int(c[i:i + 2], 16) for i in (1, 3, 5)] for c in colors], dtype=np.uint8)
    if palette.shape != (96, 3):
        raise ValueError(f'{path}: expected fixed 96-colour city palette')
    return palette


def extract(atlas: Image.Image, style: str) -> dict[int, Image.Image]:
    atlas = atlas.convert('RGBA')
    if atlas.width != atlas.height or atlas.width % 3:
        raise ValueError(f'{style}: expected square atlas divisible into 3x3 cells')
    cell = atlas.width // 3
    result: dict[int, Image.Image] = {}
    for index, level in enumerate(LEVELS):
        col, row = index % 3, index // 3
        # The capital is alone on the last row. The model may draw its outer
        # curtain wall a little across the first cell boundary into an empty
        # slot. Read the full row so no original pixel is cut off.
        left = 0 if level == 9 else col * cell
        right = atlas.width if level == 9 else (col + 1) * cell
        image = atlas.crop((left, row * cell, right, (row + 1) * cell))
        alpha = np.array(image.getchannel('A'))
        ys, xs = np.nonzero(alpha >= 128)
        if not xs.size:
            raise ValueError(f'{style}/cast_{level}: empty atlas cell')
        margin = min(xs.min(), ys.min(), image.width - 1 - xs.max(), image.height - 1 - ys.max())
        if margin < 4:
            raise ValueError(f'{style}/cast_{level}: touches atlas cell edge (margin={margin})')
        bbox = (int(xs.min()), int(ys.min()), int(xs.max()) + 1, int(ys.max()) + 1)
        cut = image.crop(bbox)
        rgba = np.array(cut)
        rgba[rgba[:, :, 3] < 128] = 0
        result[level] = Image.fromarray(rgba, 'RGBA')
    return result


def quantize(image: Image.Image, palette: np.ndarray, block: int) -> Image.Image:
    source = np.array(image.convert('RGBA'), dtype=np.float64)
    h, w = source.shape[:2]
    cells = source.reshape(h // block, block, w // block, block, 4).transpose(0, 2, 1, 3, 4)
    weight = cells[..., 3] / 255
    total = weight.sum((2, 3))
    rgb = (cells[..., :3] * weight[..., None]).sum((2, 3)) / np.maximum(total[..., None], 1)
    keep = total >= block * block * .5
    lab = oklab(palette.astype(np.float64))
    index = np.argmin(((oklab(rgb).reshape(-1, 1, 3) - lab[None]) ** 2).sum(2), axis=1)
    out = np.zeros((h // block, w // block, 4), dtype=np.uint8)
    out[..., :3] = palette[index].reshape(h // block, w // block, 3)
    out[..., 3] = np.where(keep, 255, 0)
    # Draw the contour on the pixel grid, before expanding its cells. A
    # post-resize one-pixel outline would break the pixel blocks at 4x/8x.
    low_alpha = Image.fromarray(out[..., 3], 'L')
    rim = np.array(low_alpha.filter(ImageFilter.MaxFilter(3)), dtype=np.uint8) > out[..., 3]
    out[rim] = (*palette[0], 255)
    out = np.repeat(np.repeat(out, block, 0), block, 1)
    out[out[:, :, 3] == 0] = 0
    return Image.fromarray(out, 'RGBA')


def render(source: Image.Image, level: int, size: int, palette: np.ndarray) -> Image.Image:
    extent = round(VISUAL_EXTENT[level] * size / 64)
    # Keep the contour and the entire silhouette inside its square at every
    # export size. The bottom gap is part of the sprite's baseline anchor.
    margin = max(2, round(size / 32))
    max_span = size - 2 * margin
    factor = min(extent / source.width, extent / source.height,
                 max_span / source.width, max_span / source.height)
    width, height = max(1, round(source.width * factor)), max(1, round(source.height * factor))
    art = source.resize((width, height), Image.Resampling.LANCZOS)
    canvas = Image.new('RGBA', (size, size))
    canvas.alpha_composite(art, ((size - width) // 2, size - height - margin))
    # A fixed 64-cell pixel grid keeps the 8x asset visibly pixelated when
    # scaled onto the map instead of turning back into a tiny painting.
    return quantize(canvas, palette, max(1, size // 64))


def png_bytes(image: Image.Image) -> bytes:
    out = io.BytesIO()
    image.save(out, 'PNG', optimize=True)
    return out.getvalue()


def build(style: str, palette_path: Path, check: bool) -> None:
    atlas_path = BASE / 'source/regional' / f'{style}-atlas.png'
    if not atlas_path.is_file():
        raise ValueError(f'missing curated ImageGen atlas: {atlas_path}')
    palette = palette_from_file(palette_path)
    sprites = extract(Image.open(atlas_path), style)
    for level, source in sprites.items():
        for factor, size in VARIANT_SIZES.items():
            image = render(source, level, size, palette)
            data = png_bytes(image)
            paths = (BASE / 'processed/regional' / style / f'{factor}x/cast_{level}.png',
                     *(ROOT / 'web' / app / 'public/city/regional' / style / f'{factor}x/cast_{level}.png'
                       for app in ('game', 'gateway')))
            for path in paths:
                if check:
                    if not path.is_file() or path.read_bytes() != data:
                        raise ValueError(f'export drift: {path}')
                else:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_bytes(data)
    print(json.dumps({'style': style, 'levels': list(LEVELS), 'palette': str(palette_path), 'check': check}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('styles', nargs='+', choices=STYLES)
    parser.add_argument('--palette', type=Path, required=True)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    for name in args.styles:
        build(name, args.palette, args.check)
