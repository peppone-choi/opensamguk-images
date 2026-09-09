"""Deterministic isometric city-tier buildings, drawn to the tile diamond.

Why this exists. The AI buildings sheet (raw/buildings.png) was generated free
form: no geometry guide, no projection contract, and prepare_iso2d_objects.py
cropped it by bounding box. The four tiers therefore landed at four different
scales, off the tile centre, and spilled 10-31px below the tile diamond. Both
image backends are out of credit, so the geometry is baked here instead, and
only the palette is inherited from the AI sheet (measured from the shipped
objects/*.png, see PALETTE).

Contract shared with the renderer (web/shared/src/isoTileGrid.ts):
  frame 256x256, anchor (128, 240)
  tile diamond centre (128, 176), half extents (128, 64)
  no-spill: for every occupied column x, bottom(x) <= 176 + 64 * (1 - |x-128|/128)

Ground units. One ground unit is one screen pixel of horizontal travel, so a
footprint half extent of H fills the diamond when H == 64. Every tier keeps
H < 64, which leaves a uniform (64 - H)px margin under the whole base edge.
"""
import argparse
import hashlib
import math
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'originals/iso2d/guides/buildings'

SS = 4                      # supersample factor; LANCZOS back down to 256
FRAME = 256
CX, CY = 128.0, 176.0       # tile diamond centre inside the frame
TILE_HALF = 64.0            # ground half extent that exactly fills the diamond

# Sun sits upper right, matching the AI sheet: right-facing walls are lit,
# left-facing walls are in shade. One rule for every solid in the scene.
TOP_F, XF, YF = 1.00, 0.86, 0.60

# Measured from web/game/public/sprites/iso2d/objects/*.png (top quantised
# colours: #a48869 lit rammed earth, #6d5b46 its shade, #564639 roof tile).
# Values below are the *top face* colour; the face factors reproduce the rest.
EARTH = (190, 166, 132)     # 夯土 rammed-earth wall
STONE = (172, 156, 132)     # tower body, greyer than the wall
ROOF = (96, 74, 64)         # fired roof tile
PLASTER = (201, 186, 156)   # plastered hall body between timber posts
WOOD = (104, 80, 56)        # timber posts, gate leaves, fences
THATCH = (150, 128, 88)     # hamlet roofs
PLINTH = (158, 140, 116)    # hall platform
SOIL = (126, 106, 80)       # courtyard / threshing floor
TREE = (96, 112, 68)
BANNER = (150, 62, 48)
HIDE = (176, 160, 134)        # felt / hide tent cover
CANVAS = (198, 186, 160)      # 軍幕 canvas
DUCK = (176, 166, 142)        # 大帳, one shade darker so the command tent reads apart
PLANK = (150, 126, 94)        # deck planking
WATTLE = (166, 148, 118)      # 编竹 wattle-and-daub, the river station's walling
EMBER = (196, 122, 66)      # camp fire
DARK = (36, 30, 24)         # gate mouth, windows
COURSE = 4.5                # 夯土 lift height; wall faces get a line at each lift


def project(x, y, z):
    """Ground (x, y, z) -> frame pixels. 2:1 isometric, z is straight up."""
    return CX + (x - y), CY + (x + y) * 0.5 - z


def tint(rgb, f):
    return tuple(min(255, int(round(c * f))) for c in rgb) + (255,)


class Scene:
    def __init__(self):
        self.image = Image.new('RGBA', (FRAME * SS, FRAME * SS), (0, 0, 0, 0))
        self.draw = ImageDraw.Draw(self.image)

    def poly(self, points, colour):
        flat = [(SS * px, SS * py) for px, py in (project(*p) for p in points)]
        # outline in the same colour closes the half-pixel seams between faces
        self.draw.polygon(flat, fill=colour, outline=colour)

    def ellipse(self, cx, cy, rx, ry, colour):
        self.draw.ellipse([SS * (cx - rx), SS * (cy - ry), SS * (cx + rx), SS * (cy + ry)],
                          fill=colour)

    def stroke(self, points, colour, width=1.0):
        flat = [(SS * px, SS * py) for px, py in (project(*p) for p in points)]
        self.draw.line(flat, fill=colour, width=max(1, round(width * SS)))

    def finish(self, seed):
        return grain(self.image.resize((FRAME, FRAME), Image.Resampling.LANCZOS), seed)


def grain(image, seed):
    """Two-octave multiplicative grain. Flat vector faces read as painted next to
    the hand-painted terrain; the seed keeps the builder deterministic."""
    rng = np.random.default_rng(seed)
    fine = rng.normal(0.0, 1.0, (FRAME, FRAME)).astype(np.float32)
    small = (rng.normal(0.0, 1.0, (FRAME // 6, FRAME // 6)) * 42 + 128).clip(0, 255)
    coarse = np.asarray(Image.fromarray(small.astype(np.uint8)).resize(
        (FRAME, FRAME), Image.Resampling.BICUBIC), dtype=np.float32) / 128.0 - 1.0
    factor = 1.0 + 0.085 * coarse + 0.05 * fine
    a = np.array(image).astype(np.float32)
    a[:, :, :3] = np.clip(a[:, :, :3] * factor[:, :, None], 0, 255)
    return Image.fromarray(a.astype(np.uint8), 'RGBA')


def box(scene, x0, y0, z0, x1, y1, z1, base, top_f=TOP_F, courses=False, posts=False):
    """Axis-aligned cuboid. Only +x, +y and top faces can face this camera.

    courses draws the 夯土 lift lines that make a rammed-earth wall read as earth
    rather than as a flat block; posts draws the timber frame of a plastered hall.
    """
    scene.poly([(x1, y0, z0), (x1, y1, z0), (x1, y1, z1), (x1, y0, z1)], tint(base, XF))
    scene.poly([(x0, y1, z0), (x1, y1, z0), (x1, y1, z1), (x0, y1, z1)], tint(base, YF))
    scene.poly([(x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)], tint(base, top_f))
    if courses:
        z = z0 + COURSE
        while z < z1 - 0.8:
            scene.stroke([(x1, y0, z), (x1, y1, z)], tint(base, XF * 0.84), 0.7)
            scene.stroke([(x0, y1, z), (x1, y1, z)], tint(base, YF * 0.84), 0.7)
            z += COURSE
    if posts:
        step = 6.0
        n = max(1, int((y1 - y0) // step))
        for i in range(1, n):
            y = y0 + (y1 - y0) * i / n
            scene.stroke([(x1, y, z0), (x1, y, z1)], tint(WOOD, XF), 0.9)
        n = max(1, int((x1 - x0) // step))
        for i in range(1, n):
            x = x0 + (x1 - x0) * i / n
            scene.stroke([(x, y1, z0), (x, y1, z1)], tint(WOOD, YF), 0.9)
    # contact shade: the last lift sits in its own shadow
    scene.stroke([(x1, y0, z0 + 0.6), (x1, y1, z0 + 0.6)], tint(base, XF * 0.72), 1.2)
    scene.stroke([(x0, y1, z0 + 0.6), (x1, y1, z0 + 0.6)], tint(base, YF * 0.72), 1.2)


def hip_roof(scene, x0, y0, x1, y1, z, eave, rise, base=ROOF):
    """廡殿 hip roof with overhanging eaves. Ridge runs along the longer axis.

    rise is kept above half the short span so the two rear slopes stay hidden;
    they are still drawn first so the silhouette can never develop a hole.
    """
    ax0, ay0, ax1, ay1 = x0 - eave, y0 - eave, x1 + eave, y1 + eave
    dx, dy = ax1 - ax0, ay1 - ay0
    lit, shade, cap = tint(base, 0.92), tint(base, 0.64), tint(base, 1.12)
    if dx >= dy:
        rise = max(rise, dy / 2 + 3)
        mid, ins = (ay0 + ay1) / 2, dy / 2
        r0, r1 = (ax0 + ins, mid, z + rise), (ax1 - ins, mid, z + rise)
        scene.poly([(ax0, ay0, z), (ax1, ay0, z), r1, r0], shade)          # rear, hidden
        scene.poly([(ax0, ay0, z), (ax0, ay1, z), r0], lit)                # rear, hidden
        scene.poly([(ax0, ay1, z), (ax1, ay1, z), r1, r0], shade)          # +y, screen left
        scene.poly([(ax1, ay0, z), (ax1, ay1, z), r1], lit)                # +x, screen right
        ribs = max(2, int((r1[0] - r0[0]) // 5))
        for i in range(1, ribs):
            rx = r0[0] + (r1[0] - r0[0]) * i / ribs
            scene.stroke([(rx, mid, z + rise), (rx, ay1, z)], tint(base, 0.52), 0.7)
        scene.stroke([(ax0, ay1, z), (ax1, ay1, z)], tint(base, 0.42), 1.0)
    else:
        rise = max(rise, dx / 2 + 3)
        mid, ins = (ax0 + ax1) / 2, dx / 2
        r0, r1 = (mid, ay0 + ins, z + rise), (mid, ay1 - ins, z + rise)
        scene.poly([(ax0, ay0, z), (ax0, ay1, z), r1, r0], lit)            # rear, hidden
        scene.poly([(ax0, ay0, z), (ax1, ay0, z), r0], shade)              # rear, hidden
        scene.poly([(ax1, ay0, z), (ax1, ay1, z), r1, r0], lit)            # +x, screen right
        scene.poly([(ax0, ay1, z), (ax1, ay1, z), r1], shade)              # +y, screen left
    scene.stroke([r0, r1], cap, 1.6)


def hall(scene, cx, cy, dx, dy, height, base=PLASTER, roof=ROOF, plinth=0.0, storeys=1):
    """Post-and-beam hall: optional stone plinth, plastered body, hip roof.
    A second storey is the one change that still reads once the sprite is scaled down —
    the upper roof breaks the wall line, so 大衙 and 郡衙 stop looking alike."""
    x0, y0, x1, y1 = cx - dx / 2, cy - dy / 2, cx + dx / 2, cy + dy / 2
    if plinth:
        box(scene, x0 - 2, y0 - 2, 0, x1 + 2, y1 + 2, plinth, PLINTH, courses=True)
    box(scene, x0, y0, plinth, x1, y1, plinth + height, base, posts=True)
    if storeys < 2:
        hip_roof(scene, x0, y0, x1, y1, plinth + height, 3.0, max(dx, dy) * 0.34, roof)
        return
    # 腰簷: the skirt roof over the lower storey, then the set-back upper body
    hip_roof(scene, x0, y0, x1, y1, plinth + height, 3.5, max(dx, dy) * 0.22, roof)
    ix, iy = dx * 0.16, dy * 0.16
    top = plinth + height + max(dx, dy) * 0.22
    box(scene, x0 + ix, y0 + iy, top, x1 - ix, y1 - iy, top + height * 0.72, base, posts=True)
    hip_roof(scene, x0 + ix, y0 + iy, x1 - ix, y1 - iy, top + height * 0.72, 3.0,
             max(dx, dy) * 0.32, roof)


def merlons(scene, x0, y0, x1, y1, z, along, base):
    """城堞. A capping band notched from above, not a row of free-standing blocks —
    separate blocks alias into a ladder once the sprite is scaled down."""
    step, gap, mh = 9.0, 3.2, 3.0
    length = (x1 - x0) if along == 'x' else (y1 - y0)
    if length < step:
        return
    box(scene, x0, y0, z, x1, y1, z + mh, base)
    count = int((length - gap) // step)
    pad = (length - (count * step - (step - gap))) / 2
    slot = tint(base, 0.44)
    for i in range(count):
        a = pad + i * step
        if along == 'x':
            scene.poly([(x0 + a, y0, z + mh), (x0 + a + gap, y0, z + mh),
                        (x0 + a + gap, y1, z + mh), (x0 + a, y1, z + mh)], slot)
        else:
            scene.poly([(x0, y0 + a, z + mh), (x1, y0 + a, z + mh),
                        (x1, y0 + a + gap, z + mh), (x0, y0 + a + gap, z + mh)], slot)


def tower(scene, x0, y0, side, wall_h, rise, base=STONE):
    """角樓 corner watchtower: battered body, timber gallery, hip roof."""
    x1, y1 = x0 + side, y0 + side
    box(scene, x0, y0, 0, x1, y1, wall_h + rise, base, courses=True)
    box(scene, x0 - 1.5, y0 - 1.5, wall_h + rise, x1 + 1.5, y1 + 1.5, wall_h + rise + 5, WOOD)
    hip_roof(scene, x0 - 1.5, y0 - 1.5, x1 + 1.5, y1 + 1.5, wall_h + rise + 5, 3.0, side * 0.55)
    # one shuttered window on the lit face
    wy0, wy1 = y0 + side * 0.32, y0 + side * 0.68
    zt = wall_h + rise - 4
    scene.poly([(x1, wy0, zt - 6), (x1, wy1, zt - 6), (x1, wy1, zt), (x1, wy0, zt)], tint(DARK, 1.0))


def palisade(scene, half, height, post=3.2, step=4.6):
    """木柵. Tribal settlements get timber posts lashed to a rail, never rammed earth."""
    for side in ('N', 'W', 'E', 'S'):
        n = int((2 * half) // step)
        for i in range(n + 1):
            a = -half + i * step
            if side == 'S' and abs(a) < 9:
                continue                      # gap where the track comes in
            if side == 'N':   x0, y0 = a, -half
            elif side == 'S': x0, y0 = a, half - post
            elif side == 'W': x0, y0 = -half, a
            else:             x0, y0 = half - post, a
            if x0 > half - post or y0 > half - post:
                continue
            box(scene, x0, y0, 0, x0 + post, y0 + post, height + (i % 3) * 0.8, WOOD)
        # lashing rail, so the posts read as one fence instead of loose stakes
        rz = height * 0.62
        if side == 'N':   a0, a1 = (-half, -half, rz), (half, -half, rz)
        elif side == 'S': a0, a1 = (-half, half - post, rz), (half, half - post, rz)
        elif side == 'W': a0, a1 = (-half, -half, rz), (-half, half, rz)
        else:             a0, a1 = (half - post, -half, rz), (half - post, half, rz)
        scene.stroke([a0, a1], tint(WOOD, 0.62), 1.1)


def tent(scene, cx, cy, radius, height):
    """穹廬 felt tent: a cone on a low ring. The one shape that reads non-Han at a glance."""
    steps = 14
    ring = [(cx + radius * math.cos(2 * math.pi * i / steps),
             cy + radius * math.sin(2 * math.pi * i / steps), 0.0) for i in range(steps)]
    # contact shade first, so overlapping tents stay separate silhouettes
    scene.poly([(x, y, 0.0) for x, y, _ in ring], tint(SOIL, 0.62))
    apex = (cx, cy, height)
    for i in range(steps):
        a, b = ring[i], ring[(i + 1) % steps]
        u = ((a[0] + b[0]) / 2 - cx) / radius - ((a[1] + b[1]) / 2 - cy) / radius
        scene.poly([a, b, apex], tint(HIDE, 0.52 + 0.46 * (u + 2) / 4))
    # felt seams running down from the crown
    for i in range(0, steps, 2):
        scene.stroke([apex, ring[i]], tint(HIDE, 0.44), 0.7)
    # door flap on the near-left face, the way a ger is always pitched
    dx, dy = radius * 0.24, radius * 0.80
    scene.poly([(cx - dx, cy + dy, 0), (cx + dx, cy + dy, 0),
                (cx + dx, cy + dy, height * 0.40), (cx - dx, cy + dy, height * 0.40)],
               tint(DARK, 1.0))
    scene.stroke([(cx, cy, height), (cx, cy, height + 3.5)], tint(WOOD, 0.85), 0.9)


def tree(scene, x, y, height, radius):
    box(scene, x - 1, y - 1, 0, x + 1, y + 1, height * 0.5, WOOD)
    cx, cy = project(x, y, height)
    scene.ellipse(cx, cy, radius, radius * 0.80, tint(TREE, 0.58))
    scene.ellipse(cx + radius * 0.30, cy - radius * 0.28, radius * 0.62, radius * 0.50,
                  tint(TREE, 0.98))


def banner(scene, x, y, z, height, cloth):
    box(scene, x - 0.8, y - 0.8, z, x + 0.8, y + 0.8, z + height, WOOD)
    top = z + height - 2
    scene.poly([(x, y - 0.8, top), (x, y - 0.8, top - cloth),
                (x, y - 9.0, top - cloth - 2), (x, y - 9.0, top)], tint(BANNER, 0.92))


def courtyard(scene, half, thickness, gap):
    """Packed-earth yard plus the lane running in from the gate."""
    inner = half - thickness
    scene.poly([(-inner, -inner, 0), (inner, -inner, 0), (inner, inner, 0), (-inner, inner, 0)],
               tint(SOIL, 0.94))
    lane = gap * 0.34
    scene.poly([(-lane, -inner, 0), (lane, -inner, 0), (lane, inner, 0), (-lane, inner, 0)],
               tint(SOIL, 1.16))


def gatehouse(scene, half, thickness, wall_h, gap, storeys):
    """門 on the lower-left (+y) wall. storeys 0 plain opening, 1 roofed, 2 a 門樓."""
    x0, x1 = -gap / 2, gap / 2
    y0, y1 = half - thickness, half
    top = wall_h + (2 if storeys == 0 else 6)
    box(scene, x0, y0, 0, x1, y1, top, EARTH, courses=True)
    mouth, lintel = gap * 0.46, wall_h * 0.62
    scene.poly([(-mouth, y1, 0), (mouth, y1, 0), (mouth, y1, lintel), (-mouth, y1, lintel)],
               tint(DARK, 1.0))
    scene.poly([(-mouth, y1, lintel - 1.5), (mouth, y1, lintel - 1.5),
                (mouth, y1, lintel + 2.5), (-mouth, y1, lintel + 2.5)], tint(WOOD, 0.9))
    if storeys == 0:
        merlons(scene, x0, y0, x1, y1, top, 'x', EARTH)
        return
    if storeys == 2:
        # upper chamber set back from the wall face, then the roof
        box(scene, x0 + 1.5, y0 - 1.5, top, x1 - 1.5, y1 - 1.0, top + gap * 0.42, WOOD, posts=True)
        top += gap * 0.42
        hip_roof(scene, x0 + 1.5, y0 - 1.5, x1 - 1.5, y1 - 1.0, top, 4.0, gap * 0.30)
    else:
        hip_roof(scene, x0, y0, x1, y1, top, 3.0, gap * 0.34)


def que_pair(scene, half, thickness, wall_h, gap):
    """雙闕: the paired gate towers that mark an imperial capital."""
    side, rise = gap * 0.34, wall_h * 0.75
    for sign in (-1, 1):
        cx = sign * (gap / 2 + side * 0.9)
        box(scene, cx - side / 2, half - thickness, 0, cx + side / 2, half, wall_h + rise,
            STONE, courses=True)
        hip_roof(scene, cx - side / 2, half - thickness, cx + side / 2, half,
                 wall_h + rise, 3.0, side * 0.6)


def barbican(scene, half, thickness, wall_h, gap):
    """內甕城: a U of wall inside the gate, so the lane cannot be rushed straight."""
    t, reach = thickness * 0.8, gap * 1.5
    y1 = half - thickness
    y0 = y1 - reach
    for sign in (-1, 1):
        cx = sign * (gap * 0.95)
        box(scene, cx - t / 2, y0, 0, cx + t / 2, y1, wall_h * 0.7, EARTH, courses=True)
    box(scene, -gap * 0.95, y0, 0, gap * 0.95, y0 + t, wall_h * 0.7, EARTH, courses=True)


def terrace(scene, half, thickness, height):
    """宮城 platform: the palace precinct stands on its own raised ground."""
    inner = half - thickness - 1.0
    box(scene, -inner * 0.78, -inner, 0, inner * 0.78, inner * 0.16, height, PLINTH, courses=True)


# Courtyard slots in normalised inner coordinates. Kept disjoint so a tier can
# take the first N of them and never overlap. (cx, cy, w, d, height factor)
SLOTS = [
    (0.05, -0.55, 1.10, 0.34, 0.26),   # 正堂
    (-0.62, 0.05, 0.30, 0.66, 0.20),   # 西廡
    (0.66, 0.05, 0.28, 0.60, 0.20),    # 東廡
    (0.05, 0.62, 0.80, 0.26, 0.19),    # 南舍
    (0.05, -0.05, 0.62, 0.24, 0.22),   # 中堂
    (-0.68, -0.62, 0.28, 0.24, 0.18),  # 창고
    (0.72, -0.62, 0.24, 0.24, 0.18),   # 창고
    (-0.60, 0.62, 0.32, 0.22, 0.18),   # 마구간
]
TREE_SLOTS = [(-0.30, -0.18), (0.36, 0.40), (-0.30, 0.34), (0.44, -0.30), (-0.02, 0.30)]


def yard(inner, halls, trees, plinth, storeys=1):
    """Buildings and planting for one compound, scaled to the inner yard."""
    out = []
    for i, (cx, cy, w, d, hf) in enumerate(SLOTS[:halls]):
        out.append(dict(kind='hall', x=cx * inner, y=cy * inner, dx=w * inner, dy=d * inner,
                        h=6 + hf * inner, plinth=plinth if i == 0 else 0.0,
                        storeys=storeys if i == 0 else 1))
    planting = [(cx * inner, cy * inner, 12 + inner * 0.16, 6 + inner * 0.08)
                for cx, cy in TREE_SLOTS[:trees]]
    return out, planting


def walled_tier(half, wall_h, thickness, towers, gap, gate_storeys, halls, trees,
                crenels=True, plinth=0.0, que=False, moat=False, palace=0.0, flag=False,
                storeys=1):
    scene = Scene()
    courtyard(scene, half, thickness, gap)
    h, t = half, thickness
    ts = round(half * 0.30, 1)
    rise = wall_h

    def edge(name):
        return ts if name in towers else 0.0

    def run(x0, y0, x1, y1, along):
        if (x1 - x0) <= 0 or (y1 - y0) <= 0:
            return
        box(scene, x0, y0, 0, x1, y1, wall_h, EARTH, courses=True)
        if crenels:
            merlons(scene, x0, y0, x1, y1, wall_h, along, EARTH)

    run(-h, -h + edge('N'), -h + t, h - edge('W'), 'y')          # far, upper left
    run(-h + edge('N'), -h, h - edge('E'), -h + t, 'x')          # far, upper right
    if 'N' in towers:
        tower(scene, -h, -h, ts, wall_h, rise)
        if flag:
            banner(scene, -h + ts * 0.5, -h + ts * 0.5, wall_h + rise + 5 + ts * 0.55, 26, 14)
    if 'W' in towers:
        tower(scene, -h, h - ts, ts, wall_h, rise)
    if 'E' in towers:
        tower(scene, h - ts, -h, ts, wall_h, rise)
    if palace:
        terrace(scene, half, thickness, palace)

    buildings, planting = yard(half - thickness - 2, halls, trees, plinth, storeys)
    for spec in sorted(buildings, key=lambda s: s['x'] + s['y']):
        hall(scene, spec['x'], spec['y'], spec['dx'], spec['dy'], spec['h'],
             plinth=spec['plinth'] + (palace if spec['y'] < 0 else 0.0),
             storeys=spec['storeys'])
    for x, y, th, r in planting:
        tree(scene, x, y, th, r)
    if moat:
        barbican(scene, half, thickness, wall_h, gap)

    run(h - t, -h + edge('E'), h, h - edge('S'), 'y')            # near, lower right
    for x0, x1 in ((-h + edge('W'), -gap / 2), (gap / 2, h - edge('S'))):
        run(x0, h - t, x1, h, 'x')
    if 'S' in towers:
        tower(scene, h - ts, h - ts, ts, wall_h, rise)
    gatehouse(scene, h, t, wall_h, gap, gate_storeys)
    if que:
        que_pair(scene, half, thickness, wall_h, gap)
    return scene.finish(SEED['walled'])


def ridge_tent(scene, cx, cy, dx, dy, height, cloth=None):
    """軍幕: a ridged canvas tent. Straight ridge, so it never reads as a Han tiled roof."""
    cloth = cloth or CANVAS
    x0, y0, x1, y1 = cx - dx / 2, cy - dy / 2, cx + dx / 2, cy + dy / 2
    scene.poly([(x0 - 1.5, y0 - 1.5, 0), (x1 + 1.5, y0 - 1.5, 0),
                (x1 + 1.5, y1 + 1.5, 0), (x0 - 1.5, y1 + 1.5, 0)], tint(SOIL, 0.60))
    r0, r1 = (x0, (y0 + y1) / 2, height), (x1, (y0 + y1) / 2, height)
    scene.poly([(x0, y0, 0), (x1, y0, 0), r1, r0], tint(cloth, 1.00))   # +x-ish, lit
    scene.poly([(x0, y1, 0), (x1, y1, 0), r1, r0], tint(cloth, 0.66))   # +y, shade
    scene.poly([(x0, y0, 0), (x0, y1, 0), r0], tint(cloth, 0.80))       # gable
    scene.poly([(x1, y0, 0), (x1, y1, 0), r1], tint(cloth, 0.88))
    scene.stroke([r0, r1], tint(cloth, 0.52), 1.1)
    scene.poly([(x1, (y0 + y1) / 2 - dy * 0.16, 0), (x1, (y0 + y1) / 2 + dy * 0.16, 0),
                (x1, (y0 + y1) / 2 + dy * 0.16, height * 0.55),
                (x1, (y0 + y1) / 2 - dy * 0.16, height * 0.55)], tint(DARK, 1.0))


def abatis(scene, x, y, size):
    """拒馬 / 鹿角: crossed stakes. Reads as a field camp, not a settlement."""
    for a, b in (((-1, -1), (1, 1)), ((-1, 1), (1, -1))):
        scene.stroke([(x + a[0] * size, y + a[1] * size, 0),
                      (x + b[0] * size, y + b[1] * size, size * 1.5)], tint(WOOD, 0.86), 1.3)


def boat(scene, cx, cy, length, beam, heading_x=True):
    """A moored river craft: hull, deck house and mast."""
    dx, dy = (length, beam) if heading_x else (beam, length)
    x0, y0, x1, y1 = cx - dx / 2, cy - dy / 2, cx + dx / 2, cy + dy / 2
    box(scene, x0, y0, 0, x1, y1, 4.0, WOOD)
    scene.poly([(x0, y0, 4.0), (x1, y0, 4.0), (x1, y1, 4.0), (x0, y1, 4.0)], tint(WOOD, 0.74))
    hx, hy = dx * 0.30, dy * 0.62
    box(scene, cx - hx / 2, cy - hy / 2, 4.0, cx + hx / 2, cy + hy / 2, 11.0, THATCH)
    scene.stroke([(cx + dx * 0.16, cy, 4.0), (cx + dx * 0.16, cy, 26.0)], tint(WOOD, 0.62), 1.2)


def water():
    """Level 1 수(水): 水寨. Piles, plank deck, craft moored off the edge. No wall and no
    rammed earth — 유구·적벽·파양·탐라 are river and island stations, not walled seats."""
    scene = Scene()
    half, deck = 34.0, 6.0
    for x in range(-30, 31, 10):                       # piles, so the deck stands above water
        for y in range(-30, 31, 10):
            box(scene, x - 1.6, y - 1.6, 0, x + 1.6, y + 1.6, deck, tint(WOOD, 0.60)[:3])
    box(scene, -half, -half, deck - 2.0, half, half, deck, PLANK)
    for i in range(-3, 4):
        scene.stroke([(-half, i * 9.0, deck), (half, i * 9.0, deck)], tint(PLANK, 0.70), 0.8)
    # 望樓 on stilts, far side, drawn before the near buildings
    box(scene, -4, -30, deck, 10, -16, 24, WOOD, posts=True)
    hip_roof(scene, -4, -30, 10, -16, deck + 24, 3.0, 8.0, THATCH)
    boat(scene, 46, -2, 12, 30, heading_x=False)       # moored to the far-right side
    hall(scene, -14, 2, 28, 20, 13, base=WATTLE, roof=THATCH, plinth=deck)
    hall(scene, 14, 16, 22, 17, 11, base=WATTLE, roof=THATCH, plinth=deck)
    box(scene, -6, half, deck - 2.0, 6, 46, deck, PLANK)   # gangway out to the near berth
    boat(scene, -2, 50, 32, 12, heading_x=True)
    banner(scene, -28, -4, deck, 22, 12)
    return scene.finish(SEED['camp'])


def garrison():
    """Level 2 진(鎭): 營寨. 관도·적벽·합비 are battlefields an army holds, so this is a field
    camp — canvas, stakes and one watchtower, nothing a mason ever touched."""
    scene = Scene()
    half = 42.0
    scene.poly([(-36, -34, 0), (36, -34, 0), (36, 36, 0), (-36, 36, 0)], tint(SOIL, 0.94))
    palisade(scene, half, 11.0, post=3.0, step=6.4)
    for x, y in ((-28, 32), (-15, 35), (26, 32), (32, 21), (32, -8)):
        abatis(scene, x, y, 3.2)
    box(scene, 24, -32, 0, 35, -21, 25, WOOD, posts=True)     # 望樓, far corner
    hip_roof(scene, 24, -32, 35, -21, 25, 2.5, 6.5, THATCH)
    for tx, ty, w, d, h in ((-22, -20, 19, 11, 12), (14, -24, 18, 11, 12),
                            (-26, 16, 18, 11, 12), (22, 14, 18, 11, 12)):
        ridge_tent(scene, tx, ty, w, d, h)
    ridge_tent(scene, -2, -2, 26, 15, 17, cloth=DUCK)         # 大帳
    banner(scene, -2, -2, 17, 24, 13)
    return scene.finish(SEED['camp'])


def pass_fort():
    """Level 3 관(關): 關城. 함곡·호로·사수 block a defile — one wall across the gorge with a
    gate tower, never a square enclosure. The wall runs the full tile, ends buttressed."""
    scene = Scene()
    t, wall_h, span = 13.0, 26.0, 60.0
    gap, ts = 17.0, 17.0
    for x0, x1 in ((-span, -gap / 2), (gap / 2, span)):
        box(scene, x0, -t / 2, 0, x1, t / 2, wall_h, STONE, courses=True)
        merlons(scene, x0, -t / 2, x1, t / 2, wall_h, 'x', STONE)
    # 甕城 spur running back from the gate, the thing that makes a pass a pass
    box(scene, -gap / 2 - 3, t / 2, 0, -gap / 2 + 3, t / 2 + 16, wall_h * 0.6, STONE, courses=True)
    box(scene, gap / 2 - 3, t / 2, 0, gap / 2 + 3, t / 2 + 16, wall_h * 0.6, STONE, courses=True)
    for sign in (-1, 1):                                       # buttressed ends against the cliff
        cx = sign * (span - ts / 2)
        box(scene, cx - ts / 2, -t / 2 - 2, 0, cx + ts / 2, t / 2 + 2, wall_h + 9, STONE,
            courses=True)
        hip_roof(scene, cx - ts / 2, -t / 2 - 2, cx + ts / 2, t / 2 + 2, wall_h + 9, 3.0, 9.0)
    # 門樓: gate block, then a two-storey timber pavilion over it
    box(scene, -gap / 2, -t / 2, 0, gap / 2, t / 2, wall_h + 4, STONE, courses=True)
    scene.poly([(-gap * 0.42, t / 2, 0), (gap * 0.42, t / 2, 0),
                (gap * 0.42, t / 2, wall_h * 0.60), (-gap * 0.42, t / 2, wall_h * 0.60)],
               tint(DARK, 1.0))
    top = wall_h + 4
    box(scene, -gap / 2 - 2, -t / 2 - 2, top, gap / 2 + 2, t / 2 + 2, top + 13, WOOD, posts=True)
    hip_roof(scene, -gap / 2 - 2, -t / 2 - 2, gap / 2 + 2, t / 2 + 2, top + 13, 4.0, 11.0)
    banner(scene, 0, 0, top + 13 + 11, 22, 12)
    return scene.finish(SEED['walled'])


def tribal():
    """Level 4 이: a non-Han camp. Timber palisade, felt tents, no rammed earth, no tile."""
    h = 30.0
    scene = Scene()
    scene.poly([(-22, -20, 0), (22, -20, 0), (22, 22, 0), (-22, 22, 0)], tint(SOIL, 0.96))
    palisade(scene, h, 13.0)
    # far to near, so the near tent overlaps the far one instead of merging with it
    for tx, ty, r, th in ((-14, -13, 8.5, 17), (13, -9, 7.5, 15), (-3, 14, 8, 16)):
        tent(scene, tx, ty, r, th)
    for jx, jy in ((13, 9), (17, 13)):
        box(scene, jx - 2, jy - 2, 0, jx + 2, jy + 2, 4.5, WOOD)   # 車 / drying rack
    fx, fy = project(2.0, 0.0, 2.0)
    scene.ellipse(fx, fy, 5.0, 2.8, tint(EMBER, 1.0))
    scene.ellipse(fx, fy, 2.4, 1.4, tint(EMBER, 1.28))
    return scene.finish(SEED['tribal'])


TIERS = {
    'water': water,
    'garrison': garrison,
    'pass': pass_fort,
    'tribal': tribal,
    'county-small': lambda: walled_tier(34, 9, 4.0, (), 14, 0, 2, 1, crenels=False),
    'county': lambda: walled_tier(40, 12, 5.0, ('E',), 16, 1, 3, 2),
    'commandery': lambda: walled_tier(45, 14, 5.5, ('E', 'W'), 17, 1, 4, 2, plinth=2.5),
    'commandery-mid': lambda: walled_tier(49, 16, 6.0, ('E', 'W', 'N'), 18, 1, 5, 3, plinth=3.0),
    'commandery-major': lambda: walled_tier(53, 18, 6.5, ('E', 'W', 'N', 'S'), 19, 2, 6, 3,
                                            plinth=4.0),
    'commandery-grand': lambda: walled_tier(57, 20, 7.0, ('E', 'W', 'N', 'S'), 20, 2, 7, 4,
                                            plinth=5.0, moat=True, storeys=2),
    'capital': lambda: walled_tier(60, 23, 7.5, ('E', 'W', 'N', 'S'), 22, 2, 8, 5,
                                   plinth=6.0, que=True, palace=5.0, flag=True, storeys=2),
}

# City level -> tier. Levels 9/10/11 were appended for the han world and are NOT
# above 8 in settlement size: 10 영현 and 11 장현 are 縣, the smallest unit, while
# 9 경 is 京. Reading the numbers as a size ladder drew 604 of 774 cities as the
# capital (common/src/main/kotlin/opensamguk/common/constants/CityLevelList.kt).
# Levels 1-3 are not smaller cities, they are different kinds of place: 수(水) 유구·적벽·파양·탐라
# are river and island stations, 진(鎭) 관도·적벽·합비 are field camps on battlefields, 관(關)
# 함곡·호로·사수 are gate forts blocking a defile. WarUnitCity.kt:50-51 gives level 1 and 3 their
# own training bonus, so the engine already treats them as terrain rather than as settlement size.
# They occur only in the che 94-city world; the han worlds use 4-11 alone.
LEVEL_TIER = {1: 'water', 2: 'garrison', 3: 'pass', 4: 'tribal',
              11: 'county-small', 10: 'county', 5: 'commandery',
              6: 'commandery-mid', 7: 'commandery-major', 8: 'commandery-grand', 9: 'capital'}

SEED = {'tribal': 20260910, 'walled': 20260911, 'camp': 20260912}


def spill(image):
    """Max px any occupied column drops below the tile diamond. <= 0 is the gate."""
    alpha = image.split()[3].load()
    worst = None
    for x in range(image.width):
        bottom = None
        for y in range(image.height - 1, -1, -1):
            if alpha[x, y] >= 12:
                bottom = y
                break
        if bottom is None:
            continue
        limit = CY + TILE_HALF * (1.0 - abs(x - CX) / (FRAME / 2))
        d = bottom - limit
        worst = d if worst is None else max(worst, d)
    return worst


def build(check=False):
    OUT.mkdir(parents=True, exist_ok=True)
    records = []
    for name, fn in TIERS.items():
        image = fn()
        over = spill(image)
        if over is None or over > 0:
            raise ValueError(f'{name}: spills {over}px below the tile diamond')
        path = OUT / f'{name}.png'
        data = path.read_bytes() if path.is_file() else None
        image.save(path)
        if check and data is not None and data != path.read_bytes():
            raise ValueError(f'{name}: deterministic output drifted')
        records.append(dict(file=path.name, anchor=[128, 240], size=list(image.size),
                            spillPx=round(over, 2),
                            sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    (OUT / 'extraction.json').write_text(json.dumps(dict(
        source='tools/assets/build_iso2d_buildings.py',
        role='geometry guide for gen_iso2d_buildings.py; not a shippable asset',
        pipeline='deterministic isometric render; palette measured from the AI buildings sheet',
        note='AI regeneration was unavailable (both image backends out of credit, 2026-09-10)',
        assets=records), indent=2) + '\n')
    print(json.dumps(dict(ok=True, tiers=[r['file'] for r in records],
                          spill=[r['spillPx'] for r in records]), ensure_ascii=False))


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--check', action='store_true')
    build(p.parse_args().check)
