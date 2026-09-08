"""Copy only sprite-gen curated exports and build the deployment contract."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import numpy as np
from PIL import Image
from prepare_iso2d_tiles import footprint

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'originals/iso2d'
OUT=ROOT/'web/game/public/sprites/iso2d'
TAG='v2026.09.08-iso2d-v1'
LAND=['plain','mountain','desert','plateau','basin','hill']
WATER=['sea','river','lake']
BUILDINGS={'hamlet':[4,4],'county':[5,6],'commandery':[7,8],'capital':[9,11]}
UNITS={str(k):v for k,v in enumerate(['wall','infantry','archer','cavalry','siege','tower'])}


def build(check=False):
    records=[]
    for group,size,anchor in [('terrain',(256,160),[128,96]),('objects',(256,256),[128,240]),('skirts',(128,96),[0,0])]:
        paths=sorted((BASE/'curation'/group/'curated').glob('*.png'))
        expected_count={'terrain':93,'objects':13,'skirts':2}[group]
        if len(paths)!=expected_count:raise ValueError(f'{group}: expected {expected_count} curated PNGs')
        for p in paths:
            with Image.open(p) as im:
                a=np.array(im.convert('RGBA'))
                if im.size!=size or not a[:,:,3].any():raise ValueError(f'bad size/empty {p}')
            candidate=BASE/'curation-input'/group/p.name
            if not np.array_equal(a,np.array(Image.open(candidate).convert('RGBA'))):
                raise ValueError(f'curation changed pixels unexpectedly: {p.name}')
            r={'file':f'{group}/{p.name}','size':list(size),'anchor':anchor,
               'sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
               'curatedSource':str(p.relative_to(ROOT))}
            if group=='terrain':
                material,mask_text=p.stem.rsplit('-',1);mask=int(mask_text)
                if material not in LAND+WATER or mask not in range(15) or material in WATER and mask!=0:
                    raise ValueError(f'unknown terrain {p.name}')
                if not np.array_equal(a[:,:,3],footprint(mask).astype(np.uint8)*255):
                    raise ValueError(f'geometry mismatch {p.name}')
                r.update(material=material.upper(),mask=mask,cornerHeights=[(mask>>k)&1 for k in range(4)])
            dest=OUT/r['file']
            if check:
                if not dest.is_file() or dest.read_bytes()!=p.read_bytes():raise ValueError(f'export drift {dest}')
            else:
                dest.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(p,dest)
            records.append(r)
    manifest={'schemaVersion':1,'artifactId':'iso2d-assets-v1','sourceRepository':'opensamguk-images','sourceTag':TAG,
        'authorship':'AI image generation; deterministic chroma removal, extraction and curation export',
        'paletteReference':{'repository':'opensamguk','commit':'dfec1516','path':'tools/assets/build_iso3d_assets.py',
                            'comparison':'CPU orthographic rendering of actual pinned glTF vertex colors; not engine lighting'},
        'rasterGroup':4,'tileGrid':{'cols':192,'rows':167},'flatFootprint':[256,128],
        'height':{'cornerOrder':['N','E','S','W'],'stepScreenPixels':32,
            'baselineCorners':[[128,32],[256,96],[128,160],[0,96]],'maskRange':[0,14],
            'allRaisedRule':'mask 15 normalizes to mask 0 with baseHeight + 1',
            'interpolation':'four triangles joining corners to center at mean corner height',
            'sharedCornersRequired':True,'maxWithinTileHeightDifference':1,
            'water':'horizontal surface only; never select a land slope mask for water',
            'cliffs':'two visible flat-edge skirt orientations, stack at 32px intervals only at discontinuities',
            'heightSource':'not supplied; current han-tiles.json contains terrain classes, no map-wide elevation grid'},
        'terrain':{m.upper():{'masks':list(range(15)) if m in LAND else [0]} for m in LAND+WATER},
        'buildingTiers':{k:{'cityLevelFrom':v[0],'cityLevelTo':v[1],'file':f'objects/{k}.png'} for k,v in BUILDINGS.items()},
        'unitArmTypes':{k:{'name':v,'file':f'objects/{v}.png'} for k,v in UNITS.items()},
        'strategicFeatures':{'sourceCommit':'dfec1516','reviewedPassSiteCount':3,'passAsset':'objects/gate.png',
            'deferred':['ford','port','bridge'],'reason':'No reviewed river crossing or port/landing evidence in pinned water topology'},
        'runtimeRequirements':['Select prepainted slope by shared corner mask; translate by baseHeight * 32px.',
            'Blend matching slope-material layers in continuous world coordinates at material boundaries, as QA demo shows.',
            'Draw props separately at ground anchors and sort by ground depth; placement scale is symbolic.',
            'Use nation UI markers or whole-sprite RGB multiplication; no isolated recolorable flag mask is supplied.'],
        'limitations':['Not a game renderer integration or reconstructed historical DEM.',
            'No steep two-step-within-one-tile variants, overhangs, slanted cliff caps, or arbitrary shoreline bank sprite set.',
            'AI painted lighting approximates the geometry guide; textures are static and direction-specific.',
            'Object colors follow the muted palette family but are darker and more textured than unlit iso3d vertex colors.',
            'Visual QA and curation selection performed by the agent; no claim of human approval.'],
        'files':records}
    text=json.dumps(manifest,ensure_ascii=False,indent=2)+'\n'
    path=OUT/'manifest.json'
    if check:
        if path.read_text()!=text:raise ValueError('manifest drift')
        actual={str(p.relative_to(OUT)) for p in OUT.rglob('*.png')}
        if actual!={r['file'] for r in records}:raise ValueError('unexpected exported PNGs')
    else:path.write_text(text)
    print(json.dumps({'ok':True,'count':len(records),'bytes':sum((OUT/r['file']).stat().st_size for r in records),'check':check}))


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--check',action='store_true');build(p.parse_args().check)
