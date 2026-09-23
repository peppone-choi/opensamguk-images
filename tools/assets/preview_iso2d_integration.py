"""QA compositions of AI PNGs and the pinned, actual iso3d glTF assets.

Material blending is a renderer contract demo, never a generated asset source.
"""
import argparse
import base64
import json
import subprocess
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from prepare_iso2d_tiles import vertices, footprint

ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'originals/iso2d'
OUT=ROOT/'previews/iso2d'


def tile(material,mask=0):
    folder=BASE/'plain15-fine-fixed' if material=='plain' else BASE/'candidates'/('water' if material in ['sea','river','lake'] else material)
    return Image.open(folder/f'{material}-{mask:02d}.png').convert('RGBA')


def uv_map(mask):
    corners=vertices(mask)
    center=(128,96-8*mask.bit_count())
    points=corners+[center]
    uv=np.array([(0,0),(1,0),(1,1),(0,1),(.5,.5)])
    yy,xx=np.mgrid[:160,:256]
    coords=np.stack([xx.ravel(),yy.ravel(),np.ones(xx.size)])
    result=np.zeros((2,xx.size))
    for a in range(4):
        ids=[a,(a+1)%4,4]
        matrix=np.array([[*points[k],1] for k in ids]).T
        weights=np.linalg.solve(matrix,coords)
        inside=(weights>=-1e-8).all(axis=0)
        result[:,inside]=(uv[ids].T@weights)[:,inside]
    return result.reshape(2,160,256)


def smooth(x):
    t=np.clip(x,0,1)
    return t*t*(3-2*t)


def elevation(x,y):
    return max(0,min(3,x-3,4-y))


def mixed():
    scene=Image.new('RGBA',(2080,1184),(34,38,42,255))
    for s in range(15):
        for i in range(8):
            j=s-i
            if not 0<=j<8:continue
            z=[elevation(x,y) for x,y in [(i,j),(i+1,j),(i+1,j+1),(i,j+1)]]
            base=min(z);mask=sum((v-base)<<k for k,v in enumerate(z))
            u,v=uv_map(mask);u+=i;v+=j
            water=smooth((v-4.05)/.35)*(1-smooth((v-5.1)/.35))
            hill=smooth((u-3.5)/2)*(1-smooth((v-3)/1.05))
            mountain=smooth((u-5.3)/1.4)*(1-smooth((v-1.8)/1.2))
            weights={'river':water,'mountain':(1-water)*mountain,
                     'hill':(1-water)*(1-mountain)*hill,
                     'plain':(1-water)*(1-mountain)*(1-hill)}
            rgb=np.zeros((160,256,3))
            for material,weight in weights.items():
                if material=='river' and mask:
                    if np.max(weight[footprint(mask)])>1e-8:raise ValueError('water on slope')
                    continue
                rgb+=np.array(tile(material,mask))[:,:,:3]*weight[:,:,None]
            a=np.zeros((160,256,4),dtype=np.uint8)
            a[:,:,:3]=np.round(rgb).clip(0,255).astype(np.uint8)
            a[:,:,3]=footprint(mask).astype(np.uint8)*255
            px,py=912+(i-j)*128,96+(i+j)*64-base*32
            scene.alpha_composite(Image.fromarray(a),(px,py))
    scene.convert('RGB').save(OUT/'mixed-terrain-8x8.png')
    # Separate prop layer. Baselines are screen anchors, not a ground-height DEM.
    for name,group,i,j,dy in [('mountain-snow','props',6,1,-72),('mountain-rock','props',5,2,-48),
            ('capital','buildings',2,2,0),('hamlet','buildings',4,6,0),
            ('cavalry','units',3,6,0),('infantry','units',2,6,0),('archer','units',1,6,0)]:
        sprite=Image.open(BASE/'candidates'/group/f'{name}.png')
        cx,cy=1040+(i-j)*128,192+(i+j)*64+dy
        scene.alpha_composite(sprite,(cx-128,cy-240))
    scene.convert('RGB').save(OUT/'mixed-with-objects.png')


def cliff():
    out=Image.new('RGBA',(1300,850),(34,38,42,255))
    left=Image.open(BASE/'candidates/skirts/skirt-left.png')
    right=Image.open(BASE/'candidates/skirts/skirt-right.png')
    for s in range(9):
        for i in range(5):
            j=s-i
            if not 0<=j<5:continue
            px,py=512+(i-j)*128,64+(i+j)*64
            out.alpha_composite(tile('plain'),(px,py))
    # 2x2 plateau, raised two steps; skirts only along the visible exposed edges.
    for s in range(2,5):
        for i in range(1,3):
            j=s-i
            if not 1<=j<=2:continue
            px,py=512+(i-j)*128,64+(i+j)*64-64
            if j==2:
                for k in range(2):out.alpha_composite(left,(px,py+96+k*32))
            if i==2:
                for k in range(2):out.alpha_composite(right,(px+128,py+96+k*32))
            out.alpha_composite(tile('plateau'),(px,py))
    out.convert('RGB').save(OUT/'cliff-two-steps.png')


def raster_triangle(pixels,depth,points,vertex_depth,color):
    points=np.asarray(points)
    x0,y0=np.maximum(np.floor(points.min(axis=0)).astype(int),0)
    x1,y1=np.minimum(np.ceil(points.max(axis=0)).astype(int)+1,[pixels.shape[1],pixels.shape[0]])
    if x1<=x0 or y1<=y0:return
    matrix=np.vstack([points.T,np.ones(3)])
    if abs(np.linalg.det(matrix))<1e-10:return
    yy,xx=np.mgrid[y0:y1,x0:x1]
    weights=np.linalg.solve(matrix,np.stack([xx.ravel()+.5,yy.ravel()+.5,np.ones(xx.size)]))
    z=(vertex_depth@weights).reshape(xx.shape)
    inside=(weights>=-1e-9).all(axis=0).reshape(xx.shape)
    visible=inside & (z>depth[y0:y1,x0:x1])
    depth[y0:y1,x0:x1][visible]=z[visible]
    pixels[y0:y1,x0:x1][visible]=color


def render_gltf(data):
    buffers=[base64.b64decode(b['uri'].split(',',1)[1]) for b in data['buffers']]
    def accessor(index):
        a=data['accessors'][index];b=data['bufferViews'][a['bufferView']]
        dtype={5126:'<f4',5125:'<u4',5123:'<u2'}[a['componentType']]
        n={'SCALAR':1,'VEC3':3,'VEC4':4}[a['type']]
        return np.frombuffer(buffers[b['buffer']],dtype=dtype,count=a['count']*n,
            offset=b.get('byteOffset',0)+a.get('byteOffset',0)).reshape(-1,n)
    pixels=np.zeros((512,512,4),dtype=np.uint8)
    depth=np.full((512,512),-np.inf)
    for mesh in data['meshes']:
        for p in mesh['primitives']:
            pos=accessor(p['attributes']['POSITION']);colors=accessor(p['attributes']['COLOR_0'])
            idx=accessor(p['indices']).reshape(-1,3)
            for tri in idx:
                v=pos[tri];color=np.mean(colors[tri,:3],axis=0)
                # Pinned model already contains per-face baked color variation.
                srgb=np.where(color<=.0031308,color*12.92,1.055*color**(1/2.4)-.055)
                xy=[(256+(x-z)*220,380+(x+z)*110-y*280) for x,y,z in v]
                vertex_depth=v[:,0]+v[:,2]+v[:,1]*(220/280)
                rgba=tuple(np.clip(srgb*255,0,255).astype(int))+(255,)
                raster_triangle(pixels,depth,xy,vertex_depth,rgba)
    out=Image.fromarray(pixels)
    return out.resize((256,256),Image.Resampling.LANCZOS)


def compare(repo):
    names=[('terrain',m) for m in ['plain','mountain','hill','desert','plateau','basin','sea','river','lake']]
    names += [('building',m) for m in ['hamlet','county','commandery','capital']]
    names += [('unit',m) for m in ['wall','infantry','archer','cavalry','siege','tower']]
    out=Image.new('RGB',(1536,7*280),(46,50,51));draw=ImageDraw.Draw(out)
    ref=BASE/'reference-iso3d';ref.mkdir(exist_ok=True)
    for n,(group,name) in enumerate(names):
        path=f'web/game/public/models/iso3d/{group}/{name}.gltf'
        source=subprocess.check_output(['git','-C',str(repo),'show',f'dfec1516:{path}'])
        (ref/f'{group}-{name}.gltf').write_bytes(source)
        three=render_gltf(json.loads(source))
        if group=='terrain':
            two=Image.new('RGBA',(256,256));two.alpha_composite(tile(name),(0,64))
            if name=='mountain':two.alpha_composite(Image.open(BASE/'candidates/props/mountain-snow.png'),(0,-20))
        else:two=Image.open(BASE/'candidates'/('buildings' if group=='building' else 'units')/f'{name}.png')
        x,y=n%3*512,n//3*280
        out.paste(three,(x,y+24),three);out.paste(two,(x+256,y+24),two)
        draw.text((x+12,y+8),f'{name}: pinned 3D | AI 2D',fill='white')
    out.save(OUT/'iso3d-vs-iso2d.png')


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--reference-repo',type=Path,required=True)
    args=p.parse_args();mixed();cliff();compare(args.reference_repo)
