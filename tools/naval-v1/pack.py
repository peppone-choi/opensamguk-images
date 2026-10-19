#!/usr/bin/env python3
"""Pack rendered PNGs without resampling; audit byte provenance and exact rectangles."""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
SHIPS = ('scout', 'warship', 'transport')
BOARDS = ('river-narrow', 'estuary', 'lake', 'coastal-port')
DIRECTIONS = ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW')
ANIMATIONS = ('idle', 'drifting', 'burning', 'towed')
COORDINATE_SYSTEM = {'rows':64,'cols':64,'order':'row-major','north':'row-1','east':'col+1','shipBowAtN':'+worldY','directionOrder':list(DIRECTIONS),'directionRotationDegrees':-45,'frameRectUnits':'pixels','pivotUnits':'pixels-from-top-left','alpha':'straight-RGBA8','boardProjection':'grid.origin + col*grid.colStep + row*grid.rowStep; ground z=0'}
REQUIRED = {'id','kind','sourceBlend','texturePaths','camera','lighting','renderScript',
            'directions','animations','frames','atlas','frameRects','pivot','sha256','license'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(path):
    return path.relative_to(ROOT).as_posix()


def safe_path(root, path):
    if not isinstance(path,str) or Path(path).is_absolute():
        raise ValueError('expected repository-relative path')
    resolved = (root/path).resolve()
    if not resolved.is_relative_to(root.resolve()):
        raise ValueError('path escapes asset root')
    return resolved


def image(path):
    with Image.open(path) as im:
        if im.mode != 'RGBA': raise ValueError(f'expected RGBA: {path}')
        im.load()
        return im.copy()


def pack():
    export = ROOT/'exports/naval-v1'
    (export/'atlases').mkdir(parents=True,exist_ok=True)
    assets=[]
    for asset in SHIPS+BOARDS:
        kind='ship' if asset in SHIPS else 'board'
        folder=export/'frames'/asset
        settings=json.loads((folder/'render-settings.json').read_text())
        frame_paths = [folder/f'{direction}-{animation}-{phase:02}.png' for animation in ANIMATIONS for phase in range(2) for direction in DIRECTIONS] if kind=='ship' else [folder/'board.png']
        size=160 if kind=='ship' else 768
        atlas=Image.new('RGBA',(size*8,size*8) if kind=='ship' else (size,size))
        rects={}
        for i,path in enumerate(frame_paths):
            im=image(path)
            if im.size!=(size,size): raise ValueError(f'wrong frame dimensions {path}')
            x,y=(i%8*size,i//8*size) if kind=='ship' else (0,0)
            atlas.paste(im,(x,y))  # no mask: preserve straight alpha bytes, including edge pixels
            rects[relative(path)]={'x':x,'y':y,'w':size,'h':size}
        atlas_path=export/'atlases'/f'{asset}.png'
        atlas.save(atlas_path)
        source=ROOT/'originals/naval-v1'/f'{asset}.blend'
        texture_paths=[ROOT/'originals/naval-v1/textures'/f'{name}.png' for name in ('wood','sail')]
        script=ROOT/'tools/naval-v1/blender_pipeline.py'
        files=[source,script,*texture_paths,*frame_paths,atlas_path,folder/'render-settings.json',ROOT/'originals/naval-v1/LICENSE-NOTICE.md',export/'NOTICE.txt']
        entry={'id':asset,'kind':kind,'sourceBlend':relative(source),
               'texturePaths':[relative(p) for p in texture_paths],
               'camera':settings['camera'],'lighting':settings['lighting'],
               'renderScript':relative(script),'directions':list(DIRECTIONS) if kind=='ship' else ['fixed'],
               'animations':{a:{'frameCount':2,'fps':10,'loop':True} for a in ANIMATIONS} if kind=='ship' else {'static':{'frameCount':1,'fps':0,'loop':False}},
               'frames':[relative(p) for p in frame_paths],'atlas':relative(atlas_path),'frameRects':rects,
               'pivot':settings['pivot'],'sha256':{relative(p):digest(p) for p in files},
               'license':{'spdx':'MIT','notice':'exports/naval-v1/NOTICE.txt','thirdPartyInputs':[]}}
        if kind=='board': entry['grid']=settings['grid']
        assets.append(entry)
    manifest={'version':1,'coordinateSystem':COORDINATE_SYSTEM,'assets':assets}
    (export/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    previews(manifest)
    return manifest


def previews(manifest):
    out=ROOT/'assets/naval-v1'
    out.mkdir(parents=True,exist_ok=True)
    # Sheets are review previews, NOT actual game execution screenshots.
    sheet=Image.new('RGB',(160*8,32+3*4*184),(29,41,47))
    draw=ImageDraw.Draw(sheet)
    draw.text((10,10),'BLENDER ASSET PREVIEW ONLY - NOT GAME QA',(240,225,185))
    for s,asset in enumerate(manifest['assets'][:3]):
        for a,animation in enumerate(ANIMATIONS):
            y=32+(s*4+a)*184
            for d,direction in enumerate(DIRECTIONS):
                path=ROOT/f'exports/naval-v1/frames/{asset["id"]}/{direction}-{animation}-00.png'
                im=image(path)
                sheet.paste(im,(d*160,y+20),im)
                draw.text((d*160+5,y+3),f'{asset["id"]} {animation} {direction}',(230,216,177))
    sheet.save(out/'ships-preview.png')
    boards=Image.new('RGB',(1536,1584),(29,41,47))
    draw=ImageDraw.Draw(boards)
    for i,asset in enumerate(manifest['assets'][3:]):
        x,y=i%2*768,i//2*792
        draw.text((x+12,y+5),asset['id']+' - ASSET PREVIEW ONLY',(240,225,185))
        im=image(ROOT/asset['atlas']); boards.paste(im,(x,y+24),im)
    boards.save(out/'boards-preview.png')


def verify(root=ROOT, manifest=None):
    if manifest is None: manifest=json.loads((root/'exports/naval-v1/manifest.json').read_text())
    if type(manifest.get('version')) is not int or manifest['version']!=1: raise ValueError('unsupported manifest version')
    if manifest.get('coordinateSystem')!=COORDINATE_SYSTEM: raise ValueError('coordinate contract mismatch')
    assets=manifest.get('assets',[])
    if [a.get('id') for a in assets] != list(SHIPS+BOARDS): raise ValueError('exact ordered seven assets required')
    for entry in assets:
        if not REQUIRED.issubset(entry): raise ValueError('missing manifest fields')
        kind='ship' if entry['id'] in SHIPS else 'board'
        if entry['kind']!=kind: raise ValueError('kind mismatch')
        if entry['sourceBlend']!=f'originals/naval-v1/{entry["id"]}.blend' or entry['renderScript']!='tools/naval-v1/blender_pipeline.py' or entry['atlas']!=f'exports/naval-v1/atlases/{entry["id"]}.png':
            raise ValueError('asset path outside the fixed naval namespace')
        if entry['texturePaths']!=['originals/naval-v1/textures/wood.png','originals/naval-v1/textures/sail.png']:
            raise ValueError('texture provenance changed')
        if entry['camera']['type']!='ORTHO': raise ValueError('non-orthographic camera')
        if entry['license']!={'spdx':'MIT','notice':'exports/naval-v1/NOTICE.txt','thirdPartyInputs':[]}: raise ValueError('license boundary changed')
        expected=[f'exports/naval-v1/frames/{entry["id"]}/{d}-{a}-{p:02}.png' for a in ANIMATIONS for p in range(2) for d in DIRECTIONS] if kind=='ship' else [f'exports/naval-v1/frames/{entry["id"]}/board.png']
        if entry['frames']!=expected or set(entry['frameRects'])!=set(expected): raise ValueError('incomplete/duplicate frames')
        if entry['directions'] != (list(DIRECTIONS) if kind=='ship' else ['fixed']): raise ValueError('direction mismatch')
        expected_anim={a:{'frameCount':2,'fps':10,'loop':True} for a in ANIMATIONS} if kind=='ship' else {'static':{'frameCount':1,'fps':0,'loop':False}}
        if entry['animations']!=expected_anim: raise ValueError('animation mismatch')
        protected={entry['sourceBlend'],entry['renderScript'],entry['atlas'],entry['license']['notice'],'originals/naval-v1/LICENSE-NOTICE.md',*entry['texturePaths'],*expected,f'exports/naval-v1/frames/{entry["id"]}/render-settings.json'}
        if set(entry['sha256'])!=protected: raise ValueError('incomplete hash coverage')
        for path,sha in entry['sha256'].items():
            if digest(safe_path(root,path))!=sha: raise ValueError(f'hash mismatch: {path}')
        settings=json.loads((root/f'exports/naval-v1/frames/{entry["id"]}/render-settings.json').read_text())
        for key in ('camera','lighting','pivot'):
            if entry[key]!=settings[key]: raise ValueError(f'manifest/render {key} drift')
        if kind=='board' and entry['grid']!=settings['grid']: raise ValueError('manifest/render grid drift')
        source=safe_path(root,entry['sourceBlend'])
        if source.read_bytes()[:7]!=b'BLENDER': raise ValueError('not a native blend')
        size=160 if kind=='ship' else 768
        atlas=image(safe_path(root,entry['atlas']))
        if atlas.size!=((1280,1280) if kind=='ship' else (768,768)): raise ValueError('atlas dimensions')
        if entry['camera']['resolution']!=[size,size]: raise ValueError('camera frame dimensions')
        if not all(0<=entry['pivot'][axis]<size for axis in ('x','y')): raise ValueError('pivot out of bounds')
        for i,path in enumerate(expected):
            frame=image(safe_path(root,path))
            rect=entry['frameRects'][path]
            wanted={'x':i%8*size,'y':i//8*size,'w':size,'h':size} if kind=='ship' else {'x':0,'y':0,'w':size,'h':size}
            if rect!=wanted or frame.size!=(size,size): raise ValueError('frame rectangle mismatch')
            alpha=frame.getchannel('A')
            if alpha.getextrema()!=(0,255): raise ValueError('empty/nontransparent frame')
            bbox=alpha.getbbox()
            if kind=='ship' and (bbox[0]<=0 or bbox[1]<=0 or bbox[2]>=size or bbox[3]>=size): raise ValueError('clipped ship')
            crop=atlas.crop((rect['x'],rect['y'],rect['x']+size,rect['y']+size))
            if frame.tobytes()!=crop.tobytes(): raise ValueError('atlas pixel mismatch')
        if kind=='ship':
            for d in DIRECTIONS:
                states=[image(root/f'exports/naval-v1/frames/{entry["id"]}/{d}-{a}-00.png').tobytes() for a in ANIMATIONS]
                if len(set(states))!=4: raise ValueError('state silhouettes not distinct')
            for a in ANIMATIONS:
                for d in DIRECTIONS:
                    frames=[image(root/f'exports/naval-v1/frames/{entry["id"]}/{d}-{a}-{p:02}.png').tobytes() for p in range(2)]
                    if frames[0]==frames[1]: raise ValueError('identical animation phases')
        else:
            grid=entry['grid']; rows=grid['visualRows']
            if grid['rows']!=64 or grid['cols']!=64 or len(rows)!=64 or any(len(r)!=64 for r in rows): raise ValueError('board not 64x64')
            if set(c for r in rows for c in r)-{'land','sand','shallow','water','port'}: raise ValueError('visual terrain kind')
            if not all(k in {c for r in rows for c in r} for k in ('land','shallow','water')): raise ValueError('not a separate water board')
            if 'visual-only' not in grid['authority']: raise ValueError('visual art is not topology authority')
    return {'status':'PASS','assets':len(assets),'ships':len(SHIPS),'boards':len(BOARDS),'transparentFrames':sum(len(a['frames']) for a in assets),'atlases':len(assets),'gamePNGCount':0,'productQA':'NOT_RUN'}


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--check',action='store_true')
    args=parser.parse_args()
    if not args.check: pack()
    print(json.dumps(verify(),indent=2))
