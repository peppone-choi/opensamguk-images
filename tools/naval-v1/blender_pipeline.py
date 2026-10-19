#!/usr/bin/env python3
"""Original naval meshes -> preserved .blend -> CPU Cycles transparent frames.
Run from the repository root; --build writes sources, --render reloads those sources.
No third-party images, game files, remote services or runtime combat rules are used.
"""
import argparse
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'originals/naval-v1'
EXPORT = ROOT / 'exports/naval-v1'
SHIPS = ('scout', 'warship', 'transport')
BOARDS = ('river-narrow', 'estuary', 'lake', 'coastal-port')
DIRECTIONS = ('N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW')
ANIMATIONS = ('idle', 'drifting', 'burning', 'towed')
COLORS = {
    'wood': (0.24, 0.105, 0.045, 1), 'deck': (0.62, 0.38, 0.16, 1),
    'trim': (0.88, 0.66, 0.29, 1), 'sail': (0.86, 0.78, 0.56, 1),
    'scout': (0.12, 0.43, 0.36, 1), 'warship': (0.55, 0.095, 0.07, 1),
    'transport': (0.19, 0.28, 0.43, 1), 'rope': (0.73, 0.55, 0.26, 1),
    'fire': (1.0, 0.13, 0.005, 1), 'ember': (1.0, 0.65, 0.03, 1),
    'smoke': (0.12, 0.15, 0.16, 1), 'water': (0.045, 0.22, 0.29, 1),
    'shallow': (0.12, 0.40, 0.43, 1), 'sand': (0.63, 0.57, 0.36, 1),
    'land': (0.22, 0.32, 0.19, 1), 'stone': (0.31, 0.35, 0.32, 1),
}
MATS = {}


def material(name):
    if name in MATS:
        return MATS[name]
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = COLORS[name]
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = COLORS[name]
    bsdf.inputs['Roughness'].default_value = 0.86
    if name in ('wood', 'sail'):
        image = bpy.data.images.load(str(SOURCE / 'textures' / (name + '.png')), check_existing=True)
        image.filepath = '//textures/' + name + '.png'
        tex = mat.node_tree.nodes.new('ShaderNodeTexImage')
        tex.image = image
        mat.node_tree.links.new(tex.outputs['Color'], bsdf.inputs['Base Color'])
    if name in ('fire', 'ember'):
        bsdf.inputs['Emission Color'].default_value = COLORS[name]
        bsdf.inputs['Emission Strength'].default_value = 1.5
    MATS[name] = mat
    return mat


def mesh(name, verts, faces, mat):
    data = bpy.data.meshes.new(name)
    data.from_pydata(verts, [], faces)
    data.update()
    obj = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material(mat))
    uv = data.uv_layers.new(name='UVMap')
    for loop in data.loops:
        p = data.vertices[loop.vertex_index].co
        uv.data[loop.index].uv = (p.x * 0.4, p.y * 0.4)
    return obj


def cube(name, loc, scale, mat):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = scale
    o.data.materials.append(material(mat))
    return o


def rod(name, start, end, radius, mat):
    a, b = Vector(start), Vector(end)
    bpy.ops.mesh.primitive_cylinder_add(vertices=8, radius=radius, depth=(b-a).length, location=(a+b)/2)
    o = bpy.context.object
    o.name = name
    o.rotation_euler = (b-a).to_track_quat('Z', 'Y').to_euler()
    o.data.materials.append(material(mat))
    return o


def reset(size, ortho, target, location):
    MATS.clear()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.preferences.filepaths.save_version = 0
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = 8
    scene.cycles.use_denoising = False
    scene.render.threads_mode = 'FIXED'
    scene.render.threads = 1
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.color_depth = '8'
    scene.render.film_transparent = True
    scene.render.fps = 10
    scene.view_settings.view_transform = 'Standard'
    scene.world = bpy.data.worlds.new('NavalWorld')
    scene.world.use_nodes = True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value = (0.45, 0.51, 0.55, 1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value = 0.65
    bpy.ops.object.camera_add(location=location)
    camera = bpy.context.object
    camera.name = 'FixedOrthographicCamera'
    camera.data.type = 'ORTHO'
    camera.data.ortho_scale = ortho
    camera.rotation_euler = (Vector(target)-camera.location).to_track_quat('-Z', 'Y').to_euler()
    scene.camera = camera
    bpy.ops.object.light_add(type='SUN', location=(0, 0, 10))
    sun = bpy.context.object
    sun.name = 'FixedKeySun'
    sun.data.energy = 2.1
    sun.data.angle = math.radians(12)
    sun.rotation_euler = (math.radians(24), math.radians(-26), math.radians(-35))
    return scene


def textures():
    (SOURCE / 'textures').mkdir(parents=True, exist_ok=True)
    for name in ('wood', 'sail'):
        image = bpy.data.images.new(name, width=32, height=32, alpha=True)
        color = COLORS['deck' if name == 'wood' else 'sail']
        pixels = []
        for y in range(32):
            for x in range(32):
                shade = 0.68 if (y % 8 == 0 if name == 'wood' else x % 8 == 0 or y % 8 == 0) else 1 + ((x*13+y*7) % 5 - 2)*0.015
                pixels.extend([color[i]*shade for i in range(3)] + [1])
        image.pixels = pixels
        image.filepath_raw = str(SOURCE / 'textures' / (name + '.png'))
        image.file_format = 'PNG'
        image.save()


def ship(kind):
    scene = reset(160, 9.0, (0, 0, 0.8), (7, -7, 7.8))
    width, length = {'scout': (0.65, 2.0), 'warship': (1.05, 2.6), 'transport': (1.20, 2.25)}[kind]
    # Closed six-sided hull rings; pointed bow, broad working deck, narrower keel.
    ring = [(-.65, -1), (.65, -1), (1, -.55), (.9, .55), (0, 1.18), (-.9, .55), (-1, -.55)]
    verts = [(x*width*s, y*length, z) for s, z in ((.68, -.15), (1, .48)) for x,y in ring]
    n = len(ring)
    faces = [tuple(range(n-1, -1, -1)), tuple(range(n, n*2))]
    faces += [(i, (i+1)%n, (i+1)%n+n, i+n) for i in range(n)]
    mesh('Hull', verts, faces, 'wood')
    mesh('Deck', [(x*width*.92, y*length*.97, .495) for x,y in ring], [tuple(range(n))], 'deck')
    for i in range(n):
        a, b = ring[i], ring[(i+1)%n]
        rod('Gunwale', (a[0]*width, a[1]*length, .58), (b[0]*width, b[1]*length, .58), .055, 'trim')
    for y in (-1.3, -.8, -.3, .2, .7, 1.2):
        if abs(y) < length*.7:
            cube('DeckPlank', (0, y, .51), (width*1.5, .025, .025), 'wood')
    rod('SternRudder', (0, -length*.9, .6), (0, -length*1.22, -.05), .07, 'wood')
    mast_y = .15 if kind != 'transport' else .4
    mast_h = 2.9 if kind == 'warship' else 2.5
    rod('Mast', (0, mast_y, .5), (0, mast_y, mast_h), .055, 'wood')
    # A curved battened rectangular sail, not a flat screen-space painted shape.
    sv, sf = [], []
    sail_w = width*1.75
    for j in range(5):
        for i in range(5):
            sv.append(((i/4-.5)*sail_w, mast_y+.20*math.sin(math.pi*i/4), 1.0+j/4*(mast_h-1.2)))
    for j in range(4):
        for i in range(4):
            a = j*5+i
            sf.append((a, a+1, a+6, a+5))
    mesh('Sail', sv, sf, 'sail')
    for j in range(5):
        z = 1+j/4*(mast_h-1.2)
        rod('SailBatten', (-sail_w/2, mast_y, z), (sail_w/2, mast_y, z), .025, 'wood')
    mesh('Pennant', [(0,mast_y,mast_h),(.7,mast_y,mast_h-.08),(0,mast_y,mast_h-.35)], [(0,1,2)], kind)
    for side in (-1, 1):
        for y in (-.95, -.4, .15, .7):
            rod('Oar', (side*width*.75,y,.55), (side*(width+0.7),y-.35,.08), .035, 'wood')
            cube('OarBlade', (side*(width+.7), y-.35, .08), (.18,.34,.045), 'deck')
    if kind == 'warship':
        cube('FightingTower', (0,-1.15,.9), (width*1.35,1.0,.65), kind)
        cube('TowerRoof', (0,-1.15,1.3), (width*1.65,1.2,.14), 'wood')
        for side in (-1,1):
            for y in (-1.4,-.9):
                rod('TowerPost', (side*width*.6,y,.6), (side*width*.6,y,1.25), .04, 'trim')
        rod('BowSpar', (0,length*.8,.55), (0,length*1.28,.55), .085, 'trim')
    elif kind == 'transport':
        cube('CargoHold', (0,-.55,.85), (1.6,1.55,.65), kind)
        for x in (-.53,0,.53):
            cube('CargoBundle', (x,-.55,1.24), (.42,1.25,.15), 'sail')
            rod('CargoLashing', (x,-1.18,1.34), (x,.08,1.34), .035, 'rope')
    else:
        cube('LowCanopy', (0,-.9,.85), (.8,.8,.4), kind)
    # State geometry is stored in the source blend; render only toggles/animates it.
    for j in range(5):
        for layer, mat in enumerate(('fire','ember')):
            bpy.ops.mesh.primitive_cone_add(vertices=5, radius1=.23-layer*.075, radius2=0, depth=.8-layer*.15, location=((j%3-1)*.4,-.8+j*.34,1.0+layer*.1))
            o=bpy.context.object; o.name='Fire'; o.data.materials.append(material(mat))
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=.35, location=((j%3-1)*.3,-.6+j*.25,1.8+j*.17))
        o=bpy.context.object; o.name='Smoke'; o.data.materials.append(material('smoke'))
    for a,b in [((0,length*1.1,.5),(.65,length*1.45,.2)), ((.65,length*1.45,.2),(.8,length*1.6,.1))]:
        rod('TowRope', a,b,.05,'rope')
    for o in list(scene.objects):
        if o.type == 'MESH':
            o['navalBaseScale'] = list(o.scale)
            o['navalBaseZ'] = o.location.z
            o.hide_render = o.name.startswith(('Fire','Smoke','TowRope'))
    root=bpy.data.objects.new('ShipRoot', None)
    scene.collection.objects.link(root)
    for o in list(scene.objects):
        if o.type=='MESH': o.parent=root
    scene['navalId']=kind
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/(kind+'.blend')), check_existing=False)


def terrain(kind, r, c):
    # Original fixed visual layouts, not historical/topology claims or navigability authority.
    if kind == 'river-narrow':
        lo = 19 + (r//12)%3
        hi = 44 + (r//16)%3
        distance = min(c-lo, hi-c)
    elif kind == 'estuary':
        half = 8 + r//3
        distance = half-abs(c-31)
    elif kind == 'lake':
        distance = min(r-4,59-r,c-4,59-c)
        if (r-22)**2+(c-40)**2 < 25: return 'land'
    else:
        distance = c-(10+(r//14)%2)
        if 24<=r<=28 and c<24: return 'port'
        if 37<=r<=40 and c<27: return 'port'
    if distance<0: return 'land'
    if distance==0: return 'sand'
    if distance<=3: return 'shallow'
    return 'water'


def board(kind):
    scene=reset(768, 100, (0,0,0), (70,-70,70))
    groups={k:([],[]) for k in ('land','sand','shallow','water','port')}
    rows=[]
    for r in range(64):
        row=[]
        for c in range(64):
            tile=terrain(kind,r,c); row.append(tile)
            verts,faces=groups[tile]
            x,y=c-31.5,31.5-r
            z={'land':.32,'sand':.08,'shallow':0,'water':0,'port':.48}[tile]
            i=len(verts)
            verts.extend([(x-.5,y-.5,z),(x+.5,y-.5,z),(x+.5,y+.5,z),(x-.5,y+.5,z)])
            faces.append((i,i+1,i+2,i+3))
        rows.append(row)
    for tile,(verts,faces) in groups.items():
        if verts: mesh(tile,verts,faces,'wood' if tile=='port' else tile)
    # Reeds, shoreline rocks and regular dock piles are actual 3D geometry.
    for r in range(4,64,6):
        for c in range(4,64,7):
            if rows[r][c]=='land' and any(rows[rr][cc]=='sand' for rr in range(max(0,r-2),min(64,r+3)) for cc in range(max(0,c-2),min(64,c+3))):
                bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.6,location=(c-31.5,31.5-r,.45))
                bpy.context.object.data.materials.append(material('stone'))
    if kind=='coastal-port':
        for r in (24,28,37,40):
            for c in (13,18,23):
                rod('DockPile',(c-31.5,31.5-r,-.2),(c-31.5,31.5-r,1.0),.16,'wood')
        cube('PortWarehouse',(-25,1,1.4),(4,6,2.2),'wood')
        cube('WarehouseRoof',(-25,1,2.7),(4.5,6.6,.4),'transport')
    scene['navalId']=kind
    scene['navalVisualRows']=json.dumps(rows,separators=(',',':'))
    bpy.ops.wm.save_as_mainfile(filepath=str(SOURCE/(kind+'.blend')),check_existing=False)


def projected(point):
    scene=bpy.context.scene
    p=world_to_camera_view(scene,scene.camera,Vector(point))
    return [round(p.x*scene.render.resolution_x,6),round((1-p.y)*scene.render.resolution_y,6)]


def record_settings():
    scene=bpy.context.scene
    sun=scene.objects['FixedKeySun']
    background=scene.world.node_tree.nodes['Background']
    return {
        'camera': {'type':scene.camera.data.type,'location':list(scene.camera.location),'rotationEuler':list(scene.camera.rotation_euler),'orthoScale':scene.camera.data.ortho_scale,'resolution':[scene.render.resolution_x,scene.render.resolution_y]},
        'lighting': {'worldColor':list(background.inputs[0].default_value)[:3],'worldStrength':background.inputs[1].default_value,'key':{'type':sun.data.type,'energy':sun.data.energy,'angleRadians':sun.data.angle,'rotationEuler':list(sun.rotation_euler)},'engine':scene.render.engine,'device':scene.cycles.device,'samples':scene.cycles.samples,'threads':scene.render.threads,'viewTransform':scene.view_settings.view_transform},
        'pivot': {'x':projected((0,0,0))[0],'y':projected((0,0,0))[1]},
    }


def render(asset):
    bpy.ops.wm.open_mainfile(filepath=str(SOURCE/(asset+'.blend')))
    scene=bpy.context.scene
    out=EXPORT/'frames'/asset
    out.mkdir(parents=True,exist_ok=True)
    settings=record_settings()
    settings['id']=asset
    if asset in SHIPS:
        root=bpy.data.objects['ShipRoot']
        for direction in DIRECTIONS:
            for animation in ANIMATIONS:
                for phase in range(2):
                    root.rotation_euler=(0,0,-DIRECTIONS.index(direction)*math.pi/4)
                    # Drifting/towed do not imply motion: only sail/rope/readable state art.
                    root.location.z=.035*phase if animation in ('idle','burning') else 0
                    for o in scene.objects:
                        if o.type!='MESH': continue
                        o.hide_render = (o.name.startswith(('Fire','Smoke')) and animation!='burning') or (o.name.startswith('TowRope') and animation!='towed')
                        o.scale=o['navalBaseScale']
                        o.location.z=o['navalBaseZ']
                        if o.name.startswith(('Sail','SailBatten')) and animation in ('drifting','towed'):
                            o.hide_render=True
                        if o.name.startswith(('Oar','OarBlade')) and animation in ('drifting','towed'):
                            o.hide_render=True
                        if o.name.startswith('Fire'): o.scale.z *= 1+phase*.24
                        if o.name.startswith('Smoke'): o.location.z += phase*.16
                        if o.name.startswith('Pennant'): o.scale.x *= 1-phase*.12
                    scene.render.filepath=str(out/f'{direction}-{animation}-{phase:02}.png')
                    bpy.ops.render.render(write_still=True)
    else:
        scene.render.filepath=str(out/'board.png')
        bpy.ops.render.render(write_still=True)
        settings['grid']={'rows':64,'cols':64,'order':'row-major','worldCellCenter':'(col-31.5,31.5-row,0)','origin':projected((-31.5,31.5,0)),'colStep':[a-b for a,b in zip(projected((-30.5,31.5,0)),projected((-31.5,31.5,0)))],'rowStep':[a-b for a,b in zip(projected((-31.5,30.5,0)),projected((-31.5,31.5,0)))],'visualRows':json.loads(scene['navalVisualRows']),'authority':'visual-only; backend terrain/topology pin required'}
    (out/'render-settings.json').write_text(json.dumps(settings,indent=2)+'\n')


def audit_sources():
    reports=[]
    for asset in SHIPS+BOARDS:
        bpy.ops.wm.open_mainfile(filepath=str(SOURCE/(asset+'.blend')))
        scene=bpy.context.scene
        settings=json.loads((EXPORT/'frames'/asset/'render-settings.json').read_text())
        actual=record_settings()
        for key in ('camera','lighting','pivot'):
            if actual[key]!=settings[key]: raise ValueError(f'{asset}: source/render {key} drift')
        if bpy.data.libraries: raise ValueError('external linked asset source forbidden')
        if scene.render.engine!='CYCLES' or not scene.render.film_transparent:
            raise ValueError('source not CPU Cycles/transparent')
        meshes=[o for o in scene.objects if o.type=='MESH']
        textures=[]
        for im in bpy.data.images:
            if im.filepath:
                path=Path(bpy.path.abspath(im.filepath)).resolve()
                if not path.is_relative_to(SOURCE.resolve()) or not path.exists():
                    raise ValueError(f'{asset}: missing/unscoped texture: {path}')
                textures.append(path.relative_to(ROOT).as_posix())
        if asset in SHIPS:
            if len(meshes)<25 or 'ShipRoot' not in scene.objects: raise ValueError('missing ship geometry')
            for prefix in ('Hull','Deck','Sail','Fire','TowRope'):
                if not any(o.name.startswith(prefix) for o in meshes): raise ValueError('missing state mesh')
        else:
            rows=json.loads(scene['navalVisualRows'])
            if rows!=settings['grid']['visualRows']: raise ValueError('source/render grid drift')
            tile_faces=sum(len(o.data.polygons) for o in meshes if o.name in ('land','sand','shallow','water','port'))
            if tile_faces!=4096: raise ValueError('board geometry not 4096 tiles')
        reports.append({'id':asset,'meshCount':len(meshes),'textures':sorted(set(textures)),'cameraMatchesRenderedMetadata':True,'nativeSourceReopened':True})
    out=ROOT/'assets/naval-v1/source-audit.json'
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps({'status':'PASS','blenderVersion':bpy.app.version_string,'assets':reports,'gamePNGCount':0,'productQA':'NOT_RUN'},indent=2)+'\n')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--build',action='store_true')
    parser.add_argument('--render',action='store_true')
    parser.add_argument('--audit',action='store_true')
    parser.add_argument('--asset',choices=SHIPS+BOARDS)
    args=parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    assets=(args.asset,) if args.asset else SHIPS+BOARDS
    SOURCE.mkdir(parents=True,exist_ok=True)
    if args.build:
        textures()
        for asset in assets: ship(asset) if asset in SHIPS else board(asset)
    if args.render:
        for asset in assets: render(asset)
    if args.audit: audit_sources()
    if not (args.build or args.render or args.audit): parser.error('select --build, --render and/or --audit')


if __name__=='__main__': main()
