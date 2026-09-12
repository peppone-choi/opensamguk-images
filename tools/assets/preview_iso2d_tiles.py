"""Compose actual extracted AI tiles on explicit synthetic elevation fixtures."""
import argparse
import json
from pathlib import Path
from PIL import Image, ImageDraw
import numpy as np
from prepare_iso2d_tiles import vertices


def heights(kind, x, y):
    if kind == 'flat':
        return 0
    if kind == 'saddle':
        return (x+y) % 2
    if kind == 'ridge':
        return max(0, 3-abs(x-4))
    z = max(0, 3-max(abs(x-4), abs(y-4)))
    return 3-z if kind == 'basin' else z


def preview(folder, output, material='plain'):
    tiles = {m: Image.open(folder/f'{material}-{m:02d}.png').convert('RGBA') for m in range(15)}
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for kind in ['flat', 'hill', 'basin', 'ridge', 'saddle']:
        out = Image.new('RGBA', (2080, 1184), (34, 38, 42, 255))
        coverage = Image.new('RGBA', out.size)
        expected = Image.new('L', out.size)
        d = ImageDraw.Draw(expected)
        for s in range(15):
            for i in range(8):
                j = s-i
                if not 0 <= j < 8:
                    continue
                z = [heights(kind, x, y) for x,y in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]]
                base = min(z)
                if max(z)-base > 1:
                    raise ValueError('fixture needs a slope outside the 1-step contract')
                mask = sum((v-base)<<k for k,v in enumerate(z))
                px, py = 16+896+(i-j)*128, 96+(i+j)*64-base*32
                out.alpha_composite(tiles[mask], (px, py))
                coverage.alpha_composite(tiles[mask], (px, py))
                d.polygon([(px+x,py+y) for x,y in vertices(mask)], fill=255)
        # Ignore only the outer silhouette. Shared edges remain in the test.
        e = np.array(expected)>0
        inner = e.copy()
        for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
            inner &= np.roll(e, (dy,dx), (0,1))
        alpha = np.array(coverage)[:,:,3]
        holes = int(np.sum(inner & (alpha<255)))
        name = f'{material}-{kind}-8x8.png'
        out.convert('RGB').save(output/name)
        records.append({'scene':kind,'file':name,'nonOpaqueInteriorPixels':holes})
    (output/f'{material}-coverage.json').write_text(json.dumps(records,indent=2)+'\n')
    print(json.dumps(records))


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('folder', type=Path)
    p.add_argument('output', type=Path)
    p.add_argument('--material',default='plain')
    args=p.parse_args()
    preview(args.folder,args.output,args.material)
