"""Extract AI-authored slope shapes without synthesizing slopes from flat art.

Run with the sprite-gen venv. The fixed guide crop replaces character-centric
bbox scaling. Edge extrusion only copies existing source RGB within 2 pixels;
missing interiors or larger geometry errors fail. No texture is drawn here.
"""
import argparse
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from sprite_gen.extract import remove_chroma_background
from sprite_gen.slice_sheet import (
    DEFAULT_KEY_THRESHOLD, DEFAULT_FRINGE_KEY_THRESHOLD, DEFAULT_FRINGE_DELTA,
)


def vertices(mask):
    return [(x, y - 32 * bool(mask & (1 << i)))
            for i, (x, y) in enumerate([(128, 32), (256, 96), (128, 160), (0, 96)])]


def footprint(mask):
    if not 0 <= mask < 15:
        raise ValueError('mask must be 0..14; all-up is flat at base+1')
    image = Image.new('L', (256, 160))
    ImageDraw.Draw(image).polygon(vertices(mask), fill=255)
    return np.array(image) > 0


def shifted(a, dx, dy):
    out = np.zeros_like(a)
    h, w = a.shape[:2]
    xs, xe = max(0, -dx), min(w, w-dx)
    ys, ye = max(0, -dy), min(h, h-dy)
    out[ys+dy:ye+dy, xs+dx:xe+dx] = a[ys:ye, xs:xe]
    return out


def normalize_alpha(image, mask):
    a = np.array(image.convert('RGBA'))
    if a.shape != (160, 256, 4):
        raise ValueError('expected fixed 256x160 guide crop')
    expected = footprint(mask)
    # The AI paints a six-pixel bleed beyond the guide. Allow two additional
    # pixels for resampling, but reject a rectangle or a different slope.
    envelope = np.array(Image.fromarray(expected.astype(np.uint8)*255).filter(ImageFilter.MaxFilter(17)))>0
    if np.any((a[:,:,3]>=240) & ~envelope):
        raise ValueError(f'mask {mask}: authored silhouette exceeds 8px bleed envelope')
    # Do not turn soft chroma-edge pixels opaque: that bakes a magenta hairline.
    # Use already opaque, non-magenta source pixels for the narrow edge bleed.
    rgb = a[:, :, :3].astype(np.int16)
    key_spill = (rgb[:, :, 0] > rgb[:, :, 1]) & (rgb[:, :, 2] > rgb[:, :, 1])
    valid = (a[:, :, 3] >= 240) & ~key_spill & expected
    missing = expected & ~valid
    count = int(missing.sum())
    interior = expected.copy()
    offsets = sorted([(dx, dy) for dx in range(-2, 3) for dy in range(-2, 3)
                      if dx or dy], key=lambda v: (v[0]**2+v[1]**2, v))
    # One rasterization pixel beyond the 2px source-copy radius distinguishes
    # the discrete diagonal boundary from truly missing interior texture.
    for dx in range(-3, 4):
        for dy in range(-3, 4):
            if dx*dx+dy*dy <= 9:
                interior &= shifted(expected, dx, dy)
    if np.any(missing & interior):
        raise ValueError(f'mask {mask}: missing interior; regenerate, do not paint')
    out = a.copy()
    for dx, dy in offsets:
        take = missing & shifted(valid, dx, dy)
        out[take, :3] = shifted(a, dx, dy)[take, :3]
        missing[take] = False
    if missing.any():
        raise ValueError(f'mask {mask}: geometry differs by more than 2px; regenerate')
    out[:, :, 3] = expected.astype(np.uint8) * 255
    out[~expected] = 0
    return Image.fromarray(out), count


def extract(sheet, out_dir, material, bleed=False):
    raw = Image.open(sheet).convert('RGBA')
    clean = remove_chroma_background(raw, (255, 0, 255), DEFAULT_KEY_THRESHOLD,
                                    DEFAULT_FRINGE_KEY_THRESHOLD, DEFAULT_FRINGE_DELTA)
    w, h = clean.size
    records = []
    staged = []
    for mask in range(15):
        col, row = mask % 3, mask // 3
        # Keep the generated slope silhouette. Normalize BOTH bounding dimensions
        # to the numeric asset contract, unlike the standing-character slicer
        # that normalizes height alone and leaves inconsistent widths.
        cell = clean.crop((round(col*w/3), round(row*h/5), round((col+1)*w/3), round((row+1)*h/5)))
        if bleed:
            box = ((col+128/768)*w/3, (row+96/512)*h/5,
                   (col+640/768)*w/3, (row+416/512)*h/5)
            cut = clean.transform((256,160), Image.Transform.EXTENT, box, Image.Resampling.BICUBIC)
        else:
            alpha = np.array(cell)[:, :, 3]
            bbox = Image.fromarray((alpha >= 128).astype(np.uint8)*255).getbbox()
            if bbox is None:
                raise ValueError(f'mask {mask}: empty AI source')
            ys = [y for _, y in vertices(mask)]
            cut = Image.new('RGBA', (256, 160))
            cut.alpha_composite(cell.crop(bbox).resize((256, max(ys)-min(ys)), Image.Resampling.LANCZOS), (0, min(ys)))
        image, repaired = normalize_alpha(cut, mask)
        name = f'{material}-{mask:02d}.png'
        staged.append((name,image))
        records.append({'file': name, 'mask': mask, 'cornerHeights': [int(bool(mask&(1<<i))) for i in range(4)],
                        'anchor': [128, 96], 'alphaEdgePixelsCopied': repaired})
    # Validate the complete sheet before writing any accepted tile from it.
    out_dir.mkdir(parents=True, exist_ok=True)
    for record,(name,image) in zip(records,staged):
        image.save(out_dir/name)
        record['sha256']=hashlib.sha256((out_dir/name).read_bytes()).hexdigest()
    (out_dir/'extraction.json').write_text(json.dumps({'source': str(sheet),
        'sourceSha256': hashlib.sha256(sheet.read_bytes()).hexdigest(),
        'pipeline': 'sprite-gen chroma removal / '+('fixed guide crop from AI bleed' if bleed else 'slope bbox normalization')+' / max-2px-per-axis source edge extrusion',
        'status': 'candidates-require-assembled-visual-QA', 'assets': records}, indent=2)+'\n')
    print(json.dumps({'count': len(records), 'edgePixelsCopied': sum(r['alphaEdgePixelsCopied'] for r in records)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('sheet', type=Path)
    parser.add_argument('out_dir', type=Path)
    parser.add_argument('--material', default='plain')
    parser.add_argument('--bleed', action='store_true', help='fixed-coordinate crop of AI sheet generated with the 12-guide-pixel bleed margin')
    args = parser.parse_args()
    extract(args.sheet, args.out_dir, args.material, args.bleed)
