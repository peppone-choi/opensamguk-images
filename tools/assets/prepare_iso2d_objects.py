"""Deterministic static PNG extraction; all painted RGB comes from AI sheets."""
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from sprite_gen.extract import remove_chroma_background
from sprite_gen.slice_sheet import DEFAULT_KEY_THRESHOLD, DEFAULT_FRINGE_KEY_THRESHOLD, DEFAULT_FRINGE_DELTA
from prepare_iso2d_tiles import normalize_alpha


ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT / 'originals/iso2d'


def clean_sheet(name):
    return remove_chroma_background(Image.open(BASE/'raw'/f'{name}.png').convert('RGBA'),
        (255, 0, 255), DEFAULT_KEY_THRESHOLD, DEFAULT_FRINGE_KEY_THRESHOLD, DEFAULT_FRINGE_DELTA)


BUILDING_TIERS = ['water', 'garrison', 'pass', 'tribal', 'county-small', 'county', 'commandery',
                  'commandery-mid', 'commandery-major', 'commandery-grand', 'capital']

# Ground-unit projection of the tile diamond, shared with build_iso2d_buildings.py.
BASE_CY, TILE_HALF, FRAME = 176.0, 64.0, 256


def spill(image):
    """Pixels below the tile diamond. Positive means the sprite hangs off its own tile."""
    alpha = np.array(image)[:, :, 3]
    worst = -TILE_HALF
    for x in range(FRAME):
        column = np.nonzero(alpha[:, x] >= 8)[0]
        if not column.size:
            continue
        limit = BASE_CY + TILE_HALF * (1 - abs(x - FRAME / 2) / (FRAME / 2))
        worst = max(worst, column.max() - limit)
    return worst


def save_group(group, source, images, sources=None):
    output = BASE/'candidates'/group
    output.mkdir(parents=True, exist_ok=True)
    records = []
    for name, image, anchor in images:
        file = output/f'{name}.png'
        image.save(file)
        records.append(dict(file=file.name, anchor=anchor, size=list(image.size),
            sha256=hashlib.sha256(file.read_bytes()).hexdigest()))
    paths = sources or [BASE/'raw'/f'{source}.png']
    (output/'extraction.json').write_text(json.dumps(dict(
        source=[str(f.relative_to(ROOT)) for f in paths],
        sourceSha256=[hashlib.sha256(f.read_bytes()).hexdigest() for f in paths],
        pipeline=('guide alpha mask / box downscale to the object frame' if sources else
                  'sprite-gen chroma removal / cell extraction / alpha crop / fit and baseline'),
        assets=records), indent=2)+'\n')
    return records


def buildings():
    """City tiers come out of the painter already in object-sprite coordinates: the guide frame
    IS the 256x256 object frame, base diamond centre (128,176), anchor (128,240). So there is
    nothing to crop and nothing to fit. The old bbox-crop-then-fit-to-a-box path is exactly what
    put four compounds at four different scales, off the diamond centre, hanging below the tile.

    The guide's own alpha is the mask. The painter is told to keep the background transparent and
    mostly does, but it still laid a water pool under the river station and rock under the pass;
    masking removes those and makes the no-spill rule hold by construction, not by inspection.
    """
    result, sources = [], []
    for name in BUILDING_TIERS:
        guide = Image.open(BASE/'guides/buildings'/f'{name}.png').convert('RGBA')
        painted_path = BASE/'raw'/f'buildings-{name}.png'
        painted = Image.open(painted_path).convert('RGBA')
        if guide.size != (FRAME, FRAME):
            raise ValueError(f'{name}: guide is {guide.size}, expected {FRAME}x{FRAME}')
        # The painter rounds the guide's hard edges by a pixel or two; keep that, drop
        # everything the guide never claimed.
        mask = Image.fromarray(np.array(guide)[:, :, 3]).resize(painted.size,
                                                                Image.Resampling.BILINEAR)
        mask = mask.filter(ImageFilter.MaxFilter(5))
        a = np.array(painted)
        a[:, :, 3] = np.minimum(a[:, :, 3], np.array(mask))
        out = Image.fromarray(a).resize((FRAME, FRAME), Image.Resampling.LANCZOS)
        over = spill(out)
        if over > 0:
            raise ValueError(f'{name}: {over:.1f}px below the tile diamond')
        result.append((name, out, [128, 240]))
        sources.append(painted_path)
    save_group('buildings', 'buildings', result, sources)


def water():
    clean = clean_sheet('water')
    w,h = clean.size
    result = []
    for i,name in enumerate(['sea','river','lake']):
        cell = clean.crop((round(i*w/3),0,round((i+1)*w/3),h))
        bbox = Image.fromarray((np.array(cell)[:,:,3]>=240).astype('uint8')*255).getbbox()
        if bbox is None:
            raise ValueError('empty water cell')
        # Flat-only source: generated layout moved vertically. Use the painted
        # bleed interior; never apply this path to directional slope artwork.
        x0,y0,x1,y1=bbox
        dx,dy=(x1-x0)*.045,(y1-y0)*.045
        box=(x0+dx,y0+dy,x1-dx,y1-dy)
        cut = cell.transform((256,128),Image.Transform.EXTENT,box,Image.Resampling.BICUBIC)
        padded = Image.new('RGBA',(256,160))
        padded.alpha_composite(cut,(0,32))
        fixed,copied = normalize_alpha(padded,0)
        if copied:
            raise ValueError(f'water {name} needs edge repair: {copied}')
        result.append((f'{name}-00',fixed,[128,96]))
    save_group('water','water',result)


def skirts():
    clean = clean_sheet('skirt')
    w,h = clean.size
    result=[]
    for i,name in enumerate(['left','right']):
        box=((i*768+128)*w/1536,160*h/768,(i*768+640)*w/1536,544*h/768)
        cut=clean.transform((128,96),Image.Transform.EXTENT,box,Image.Resampling.BICUBIC)
        mask=Image.new('L',cut.size)
        points = [(0,0),(128,64),(128,96),(0,32)] if i==0 else [(0,64),(128,0),(128,32),(0,96)]
        ImageDraw.Draw(mask).polygon(points,fill=255)
        a=np.array(cut)
        expected=np.array(mask)>0
        if np.any(a[:,:,3][expected]<240):
            raise ValueError(f'{name}: missing skirt source coverage')
        a[:,:,3]=np.array(mask)
        a[~expected]=0
        result.append((f'skirt-{name}',Image.fromarray(a),[0,0]))
    save_group('skirts','skirt',result)


def objects(source, columns, rows, specs):
    clean=clean_sheet(source)
    w,h=clean.size
    occupancy=np.array(clean)[:,:,3]>=12
    ycuts=[0]
    for row in range(1,rows):
        nominal=round(row*h/rows)
        gaps=[y for y in range(max(3,nominal-h//6),min(h-3,nominal+h//6)) if not occupancy[y-3:y+4].any()]
        if not gaps:
            raise ValueError('no empty row separating authored objects')
        ycuts.append(min(gaps,key=lambda y:abs(y-nominal)))
    ycuts.append(h)
    result=[]
    for n,(name,max_w,max_h) in enumerate(specs):
        col,row=n%columns,n//columns
        cell=clean.crop((round(col*w/columns),ycuts[row],round((col+1)*w/columns),ycuts[row+1]))
        # Keep all components within one authored cell (e.g. three hamlet houses).
        a=np.array(cell)
        significant=Image.fromarray((a[:,:,3]>=12).astype('uint8')*255).getbbox()
        if significant is None:
            raise ValueError(f'empty object {name}')
        x0,y0,x1,y1=significant
        if min(x0,y0,cell.width-x1,cell.height-y1)<2:
            raise ValueError(f'object {name} intersects cell boundary')
        crop=cell.crop(significant)
        ratio=min(max_w/crop.width,max_h/crop.height)
        size=(round(crop.width*ratio),round(crop.height*ratio))
        crop=crop.resize(size,Image.Resampling.LANCZOS)
        out=Image.new('RGBA',(256,256))
        out.alpha_composite(crop,((256-size[0])//2,240-size[1]))
        result.append((name,out,[128,240]))
    save_group(source,source,result)


if __name__=='__main__':
    water()
    skirts()
    buildings()
    objects('units',3,2,[('wall',160,100),('infantry',90,128),('archer',90,128),('cavalry',144,144),('siege',168,132),('tower',144,176)])
    objects('props',3,1,[('mountain-rock',240,176),('mountain-snow',240,208),('gate',240,160)])
    print(f'Extracted {3 + 2 + len(BUILDING_TIERS) + 6 + 3} water, skirt, building, unit and prop PNGs.')
