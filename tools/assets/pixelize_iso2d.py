"""Convert the painted iso2d assets to real pixel art on one shared palette.

The painted assets are semi-realistic: continuous tone, anti-aliased edges, a different
colour cloud per sheet. Shrinking them in the browser does not make them pixel art, it makes
them mush, and the per-sheet colour clouds are why the map never looked like one game.

So the conversion is done once, offline, and it is a real conversion:

  * one palette for EVERYTHING - terrain, buildings, units, props, skirts. Median-cut over the
    whole corpus at once, so a wall and the ground under it are quantised against the same set.
  * a block grid. SCALE=4 turns the 256x128 tile diamond into a 64x32 logical diamond, the
    classic 2:1 iso pixel tile, and each logical pixel ships as a 4x4 block so the runtime
    contract (256x160 terrain / 256x256 objects) never changes.
  * hard alpha for objects. A block is opaque when at least half of it was opaque, so a sprite
    gets a real pixel-art silhouette instead of a feathered one.
  * exact alpha kept for terrain and skirts. Their alpha is not decoration, it is the tiling
    contract: export_iso2d_assets.py compares it byte-for-byte against footprint(mask), and a
    single wrong pixel on a shared edge is a visible seam across the whole map. Only the colour
    is blocked there.
  * no dithering. Dithered ramps read as noise once the map is zoomed out.

Nearest colour is measured in Oklab, not RGB: in RGB the nearest entry to a shaded loess wall
is frequently a green, because RGB distance has no idea what lightness is.
"""
import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'originals/iso2d'
SCALE = 2
PALETTE_SIZE = 96
GROUPS = ('terrain', 'objects', 'skirts')

# Median-cut splits by population, and the corpus is 93 terrain tiles against 22 sprites. Left
# unweighted it spends the whole palette on ground and every building collapses into one brown.
# So each group buys a fixed share of the samples instead of whatever its file count buys.
GROUP_SHARE = {'terrain': 0.50, 'objects': 0.42, 'skirts': 0.08}

# Colours that carry meaning on too few pixels to survive a population split. Left to the
# median cut, a courtyard tree quantises to grey and a tiled roof to the same brown as the wall
# under it - the two reads a player actually uses to tell one city tier from another.
ANCHORS = (
    (150, 62, 48),      # 旗 banner
    (196, 122, 66),     # camp fire
    (36, 30, 24),       # gate opening / shadow
    (232, 226, 208),    # canvas highlight
    (96, 112, 68),      # 樹 foliage, lit
    (62, 76, 46),       # 樹 foliage, shade
    (86, 66, 58),       # 瓦 roof tile, lit
    (58, 44, 38),       # 瓦 roof tile, shade
)


def _srgb_to_linear(c):
    c = c / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def oklab(rgb):
    """sRGB 0..255 -> Oklab. Perceptual, so 'nearest colour' means what it says."""
    r, g, b = (_srgb_to_linear(rgb[..., i]) for i in range(3))
    l = np.cbrt(0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b)
    m = np.cbrt(0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b)
    s = np.cbrt(0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    return np.stack([0.2104542553 * l + 0.7936177850 * m - 0.0040720468 * s,
                     1.9779984951 * l - 2.4285922050 * m + 0.4505937099 * s,
                     0.0259040371 * l + 0.7827717662 * m - 0.8086757660 * s], axis=-1)


def blocks(image):
    """Downsample to the logical pixel grid. Colour is averaged over the opaque part of each
    block only - averaging in the transparent zeros would ring every silhouette with a dark
    fringe, which is the one artefact that reads as 'a shrunk photo' rather than as pixel art."""
    a = np.array(image.convert('RGBA'), dtype=np.float64)
    h, w = a.shape[0] // SCALE, a.shape[1] // SCALE
    tiles = a[:h * SCALE, :w * SCALE].reshape(h, SCALE, w, SCALE, 4).transpose(0, 2, 1, 3, 4)
    weight = tiles[..., 3] / 255.0
    total = weight.sum(axis=(2, 3))
    covered = total / (SCALE * SCALE)
    safe = np.where(total > 0, total, 1.0)
    colour = (tiles[..., :3] * weight[..., None]).sum(axis=(2, 3)) / safe[..., None]
    return colour, covered


def corpus_palette(groups):
    """One median-cut palette over every asset at once. Per-sheet palettes are why the shipped
    map reads as a collage rather than as one game."""
    per_group = {}
    for group, files in groups.items():
        rows = []
        for file in files:
            colour, covered = blocks(Image.open(file))
            rows.append(colour[covered >= 0.5].reshape(-1, 3))
        per_group[group] = np.concatenate(rows)
    budget = max(len(v) / GROUP_SHARE[k] for k, v in per_group.items())
    parts = []
    for group, rows in per_group.items():
        want = int(round(budget * GROUP_SHARE[group]))
        repeat = int(np.ceil(want / len(rows)))
        parts.append(np.tile(rows, (repeat, 1))[:want])
    flat = np.concatenate(parts).astype('uint8')
    side = int(np.ceil(np.sqrt(len(flat))))
    plate = np.zeros((side * side, 3), dtype='uint8')
    plate[:len(flat)] = flat
    plate[len(flat):] = flat[-1]
    learnt = PALETTE_SIZE - len(ANCHORS)
    quantised = Image.fromarray(plate.reshape(side, side, 3), 'RGB').quantize(
        colors=learnt, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    table = np.array(quantised.getpalette()[:learnt * 3], dtype='uint8').reshape(-1, 3)
    table = np.vstack([table, np.array(ANCHORS, dtype='uint8')])
    return table[np.lexsort((table[:, 2], table[:, 1], table[:, 0]))]


def pixelize(file, palette, lab, hard_alpha):
    source = Image.open(file).convert('RGBA')
    colour, covered = blocks(source)
    h, w = covered.shape
    index = np.argmin(((oklab(colour).reshape(-1, 1, 3) - lab[None]) ** 2).sum(axis=2), axis=1)
    out = np.zeros((h, w, 4), dtype='uint8')
    out[..., :3] = palette[index].reshape(h, w, 3)
    out[..., 3] = 255
    grown = Image.fromarray(out, 'RGBA').resize((w * SCALE, h * SCALE), Image.Resampling.NEAREST)
    a = np.array(grown)
    if hard_alpha:
        keep = np.repeat(np.repeat(covered >= 0.5, SCALE, axis=0), SCALE, axis=1)
    else:
        keep = np.array(source)[:, :, 3] > 0
        a[:, :, 3] = np.array(source)[:, :, 3]
    a[~keep] = 0
    return Image.fromarray(a, 'RGBA')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='curation', help='curation | candidates')
    parser.add_argument('--out', default='pixel')
    args = parser.parse_args()

    groups = {}
    for group in GROUPS:
        folder = BASE / args.source / group / 'curated'
        if not folder.is_dir():
            folder = BASE / args.source / group
        groups[group] = sorted(folder.glob('*.png'))
        if not groups[group]:
            raise SystemExit(f'no PNGs under {folder}')

    palette = corpus_palette(groups)
    lab = oklab(palette.astype(np.float64))

    counts = {}
    for group, files in groups.items():
        output = BASE / args.out / group
        output.mkdir(parents=True, exist_ok=True)
        hard = group == 'objects'
        for file in files:
            pixelize(file, palette, lab, hard).save(output / file.name)
        counts[group] = len(files)
    (BASE / args.out / 'palette.json').write_text(json.dumps(dict(
        scale=SCALE, size=PALETTE_SIZE, source=args.source, counts=counts,
        colors=['#%02x%02x%02x' % tuple(int(v) for v in c) for c in palette]), indent=2) + '\n')
    print(json.dumps(dict(ok=True, palette=PALETTE_SIZE, scale=SCALE, counts=counts)))


if __name__ == '__main__':
    main()
