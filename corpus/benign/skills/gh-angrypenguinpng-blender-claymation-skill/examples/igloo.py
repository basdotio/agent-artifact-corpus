"""Igloo: a clay penguin peeks out of its igloo, waddles out, catches a snowflake, waves.
blender -b -P examples/igloo.py -- [--still F] [--range A B] [--res W H] [--samples N] [--out DIR]
"""
import bpy, sys, os, math, random
from mathutils import Vector, Matrix
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from claylib import *

OPTS = cli('igloo')

reset()
sc = setup_render(res=OPTS['res'], samples=OPTS['samples'])
world((0.55, 0.68, 0.85), 0.25)
sc.view_settings.exposure = -1.0
rnd = random.Random(11)

snow = clay('snow', (0.80, 0.85, 0.92), rough=0.75, sss=0.12, bump=0.5, thumb=0.3, scale=0.5, bumpdist=1.5)
block_m = clay('block', (0.84, 0.88, 0.94), rough=0.6, sss=0.15, bump=0.45, thumb=0.35, scale=0.6, bumpdist=1.5)

# ------------------------------------------------------------------ ground + backdrop
bpy.ops.mesh.primitive_grid_add(x_subdivisions=220, y_subdivisions=220, size=1.6, location=(0, 0.3, 0))
ground = bpy.context.active_object
ground.name = 'ground'
smooth(ground)
tex = bpy.data.textures.new('drift', 'CLOUDS')
tex.noise_scale = 0.08
md = ground.modifiers.new('drift', 'DISPLACE')
md.texture = tex
md.strength = 0.008
md.mid_level = 0.5
assign(ground, snow)

sky = clay('sky', (0.36, 0.55, 0.76), rough=0.95, sss=0.0, bump=0.1, thumb=0.0, scale=0.1)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.95, 0.5), rotation=(math.pi / 2, 0, 0))
bd = bpy.context.active_object
bd.name = 'backdrop'
bd.scale = (3, 1.4, 1)
assign(bd, sky)

# puffy clay clouds stuck to the backdrop
cloud_m = clay('cloud', (0.92, 0.94, 0.97), rough=0.8, sss=0.1, bump=0.3, scale=0.4)
for cx, cz, s in [(-0.42, 0.33, 1.0), (0.05, 0.40, 0.8), (0.48, 0.30, 1.1)]:
    for k in range(5):
        sphere(f'cloud{cx}_{k}', 0.035 * s * rnd.uniform(0.7, 1.2), (cx + (k - 2) * 0.035 * s, 0.93, cz + rnd.uniform(-0.01, 0.015)),
               scale=(1.3, 0.35, 0.9), mat=cloud_m, segs=24, rings=12)

# pine trees (blurred background)
pine_m = clay('pine', (0.04, 0.17, 0.11), rough=0.7, sss=0.05, bump=0.5)
trunk_m = clay('trunk', (0.20, 0.10, 0.05), rough=0.8)
for i, (tx, ty, ts) in enumerate([(-0.33, 0.42, 1.2), (-0.22, 0.55, 0.9), (-0.12, 0.40, 0.75), (0.28, 0.45, 1.0),
                                  (0.40, 0.36, 1.3), (0.18, 0.62, 0.8), (-0.45, 0.30, 0.95)]):
    cylinder(f'trunk{i}', 0.006 * ts, 0.03 * ts, (tx, ty, 0.012 * ts), verts=16, mat=trunk_m)
    for k in range(3):
        z = (0.03 + k * 0.035) * ts
        r = (0.05 - k * 0.012) * ts
        bpy.ops.mesh.primitive_cone_add(vertices=40, radius1=r, radius2=0.004, depth=0.055 * ts, location=(tx, ty, z + 0.02 * ts))
        c = bpy.context.active_object
        c.name = f'pine{i}_{k}'
        smooth(c)
        add_lumps(c, 0.004 * ts, size=0.02)
        assign(c, pine_m)
    sphere(f'pinecap{i}', 0.012 * ts, (tx, ty, (0.03 + 2 * 0.035 + 0.045) * ts), scale=(1, 1, 0.7), mat=snow, segs=24, rings=12)

# ------------------------------------------------------------------ igloo
CX, CY, R = 0.075, 0.07, 0.11
BH, BT = 0.021, 0.017  # block height, thickness
DOOR_W, DOOR_Z = 0.043, 0.078


def place_block(name, pos, t, n, d, size):
    ob = rounded_box(name, size, bevel=0.003, mat=block_m, lumpy=0.0012)
    rot = Matrix((t, n, d)).transposed()
    ob.matrix_world = Matrix.Translation(pos) @ rot.to_4x4()
    return ob


rings = 7
count = 0
for k in range(rings):
    phi = (k + 0.5) * (BH / R) * 1.02
    if phi > math.radians(80):
        break
    rr = R * math.cos(phi)
    z = R * math.sin(phi)
    nblk = max(5, int(2 * math.pi * rr / 0.034))
    off = (k % 2) * 0.5
    for j in range(nblk):
        th = 2 * math.pi * (j + off) / nblk + rnd.uniform(-0.02, 0.02)
        x, y = CX + rr * math.cos(th), CY + rr * math.sin(th)
        if z < DOOR_Z and y < CY and abs(x - CX) < DOOR_W:
            continue
        n = Vector((math.cos(phi) * math.cos(th), math.cos(phi) * math.sin(th), math.sin(phi)))
        t = Vector((-math.sin(th), math.cos(th), 0))
        b = n.cross(t)
        w = 2 * math.pi * rr / nblk * 0.93
        place_block(f'blk{k}_{j}', Vector((x, y, z)), t, -n, b, (w * rnd.uniform(0.95, 1.02), BT, BH * rnd.uniform(0.9, 0.98)))
        count += 1
sphere('igloo_cap', 0.03, (CX, CY, R - 0.006), scale=(1, 1, 0.45), mat=block_m, segs=32, rings=16, lumpy=0.002)

# entrance tunnel: an arch of blocks sticking out toward the camera
AR, AZ = 0.038, 0.034
for row, y in enumerate([CY - R * 0.93, CY - R * 0.93 - 0.024, CY - R * 0.93 - 0.048]):
    na = 7
    for j in range(na):
        a = math.pi * (j + 0.5) / na
        pos = Vector((CX + AR * math.cos(a), y, AZ + AR * math.sin(a)))
        n = Vector((math.cos(a), 0, math.sin(a)))
        t = Vector((-math.sin(a), 0, math.cos(a)))
        place_block(f'arch{row}_{j}', pos, t, n, Vector((0, 1, 0)), (2 * math.pi * AR / (2 * na) * 1.0, BT, 0.021))
    for side in (-1, 1):
        for zz in (0.009, 0.026):
            pos = Vector((CX + side * AR, y, zz))
            place_block(f'wall{row}_{side}_{zz}', pos, Vector((0, 0, side)), Vector((side, 0, 0)), Vector((0, 1, 0)), (0.017, BT, 0.021))
TUNNEL_END = CY - R * 0.93 - 0.06

# warm lantern glow inside
glow = point_light('glow', (CX, CY + 0.01, 0.035), 2.2, radius=0.01, color=(1.0, 0.52, 0.22))
glow2 = point_light('glow2', (CX, CY - R * 0.8, 0.03), 0.35, radius=0.01, color=(1.0, 0.55, 0.25))

# ------------------------------------------------------------------ penguin
PS = 0.88
black = clay('peng_black', (0.02, 0.025, 0.045), rough=0.5, sss=0.03, bump=0.55, thumb=0.4, scale=0.15, bumpdist=2.0)
white = clay('peng_white', (0.86, 0.86, 0.84), rough=0.6, sss=0.1, bump=0.5, thumb=0.4, scale=0.15, bumpdist=2.0)
orange = clay('peng_orange', (0.85, 0.32, 0.04), rough=0.55, sss=0.1, bump=0.4, scale=0.15, bumpdist=2.0)
pink = clay('peng_pink', (0.85, 0.35, 0.38), rough=0.7, sss=0.1)
eye_black = glossy_black()

p_root = empty('p_root', (CX, CY, 0))
p_body = empty('p_body', (0, 0, 0), p_root)  # waddle roll pivot at the feet
p_body.scale = (PS,) * 3


def part(name, loc, scale, mat, par, lump=0.02, segs=48):
    o = sphere(name, 1.0, loc, scale=scale, mat=mat, segs=segs, rings=segs // 2, lumpy=lump)
    o.parent = par
    return o


part('body', (0, 0, 0.030), (0.023, 0.021, 0.029), black, p_body)
part('belly', (0, -0.009, 0.027), (0.018, 0.014, 0.024), white, p_body)
head = empty('p_head', (0, 0, 0.052), p_body)
part('head', (0, 0, 0.012), (0.018, 0.017, 0.017), black, head)
part('face', (0, -0.009, 0.012), (0.013, 0.010, 0.011), white, head)
part('cheekL', (-0.0085, -0.0165, 0.0075), (0.0032, 0.0015, 0.0022), pink, head, lump=0)
part('cheekR', (0.0085, -0.0165, 0.0075), (0.0032, 0.0015, 0.0022), pink, head, lump=0)
eyes_open, eyes_closed = [], []
for side in (-1, 1):
    e = part(f'eye{side}', (side * 0.0055, -0.0182, 0.0145), (0.0024, 0.0016, 0.0031), eye_black, head, lump=0, segs=24)
    eyes_open.append(e)
    cd = bpy.data.curves.new(f'plid{side}', 'CURVE')
    cd.dimensions = '3D'
    cd.bevel_depth = 0.0006
    cd.bevel_resolution = 3
    cd.use_fill_caps = True
    sp = cd.splines.new('NURBS')
    pts = [(side * 0.0055 + (tt - 0.5) * 0.006, -0.0186 + 0.0012 * abs(tt - 0.5), 0.0142 - 0.0014 * math.sin(math.pi * tt)) for tt in [i / 6 for i in range(7)]]
    sp.points.add(len(pts) - 1)
    for pt, co in zip(sp.points, pts):
        pt.co = (*co, 1)
    sp.use_endpoint_u = True
    lid = bpy.data.objects.new(f'plid{side}', cd)
    bpy.context.collection.objects.link(lid)
    lid.data.materials.append(eye_black)
    lid.parent = head
    eyes_closed.append(lid)
bpy.ops.mesh.primitive_cone_add(vertices=32, radius1=0.0045, radius2=0.0008, depth=0.011, location=(0, -0.0215, 0.0095), rotation=(math.pi / 2, 0, 0))
beak = bpy.context.active_object
beak.name = 'beak'
beak.scale = (1, 0.75, 1)
smooth(beak)
assign(beak, orange)
beak.parent = head
BEAK_TIP_LOCAL = Vector((0, -0.0275, 0.0095))

flippers = []
for side in (-1, 1):
    piv = empty(f'flip_piv{side}', (side * 0.020, 0.0, 0.043), p_body)
    part(f'flipper{side}', (side * 0.003, 0.001, -0.015), (0.0045, 0.010, 0.017), black, piv)
    flippers.append(piv)
feet = []
for side in (-1, 1):
    f_ = part(f'foot{side}', (side * 0.009, -0.013, 0.0025), (0.0075, 0.010, 0.0028), orange, p_body, lump=0.01)
    feet.append(f_)

# ------------------------------------------------------------------ snow
flake_m = clay('flake', (0.95, 0.97, 1.0), rough=0.6, sss=0.2, bump=0.1)
flakes = []
for i in range(80):
    y = rnd.uniform(-0.28, 0.6)
    fl = sphere(f'flake{i}', rnd.uniform(0.0011, 0.0021), (0, 0, 0), mat=flake_m, segs=12, rings=6, lumpy=0.0004)
    flakes.append((fl, rnd.uniform(-0.35, 0.35) * (1 + y), y, rnd.uniform(0, 0.4), rnd.uniform(0.0035, 0.006), rnd.uniform(0, 6.28)))
hero = sphere('hero_flake', 0.0032, (0, 0, 0), mat=flake_m, segs=16, rings=8, lumpy=0.0005)

# ------------------------------------------------------------------ lights + camera
key_l = area_light('key', (-0.35, -0.4, 0.45), (0.03, 0.0, 0.03), 22, 0.4, (1.0, 0.96, 0.92))
fill = area_light('fill', (0.5, -0.35, 0.2), (0.03, 0.0, 0.04), 4, 0.6, (0.75, 0.85, 1.0))
rim = area_light('rim', (-0.1, 0.5, 0.4), (0.03, 0.0, 0.04), 6, 0.4, (0.9, 0.95, 1.0))
cam = camera((0.02, -0.58, 0.115), (0.03, 0.0, 0.038), lens=50, fstop=5.0, focus=0.50)

# ------------------------------------------------------------------ animation
boil = Boil(5, amp=0.0002, rot=0.004)
F = 240
START = Vector((CX, CY, 0))
DOOR = Vector((CX, TUNNEL_END + 0.005, 0))
SPOT = Vector((-0.04, -0.145, 0))
YAW_WALK = math.atan2((SPOT - DOOR).x, -(SPOT - DOOR).y)  # face travel direction


def path(f):
    if f < 30:
        return START.copy()
    if f < 50:
        return START.lerp(DOOR, ease(seg(f, 30, 50)))
    if f < 62:
        return DOOR.copy()
    # waddle along a slight curve
    t = seg(f, 62, 96)
    p = DOOR.lerp(SPOT, t)
    p.x += 0.012 * math.sin(math.pi * t)
    return p


def blink(f):
    return f in (34, 35, 104, 105, 137, 138, 176, 177, 212, 213) or f >= 229


walk_phase = 0
hero_land = None
for f in range(1, F + 1):
    pos = path(f)
    walking = (30 <= f < 50) or (62 <= f < 96)
    step = (f // 3) % 2  # stop-motion waddle, new pose every 3 frames
    roll = (0.16 if step else -0.16) * (1 if walking else 0)
    bob = 0.0025 * (1 if walking and (f % 3 == 1) else 0)

    yaw = 0.0
    yaw += YAW_WALK * ease(seg(f, 60, 64)) * (1 - ease(seg(f, 94, 100)))
    # hops
    hz = 0.0
    for a, b in ((153, 159), (163, 169)):
        hz += 0.018 * math.sin(math.pi * seg(f, a, b))
    sq = 0.0
    for a, b in ((150, 153), (160, 163), (169, 172)):
        sq += 0.12 * math.sin(math.pi * seg(f, a, b))
    st = 0.0
    for a, b in ((153, 159), (163, 169)):
        st += 0.08 * math.sin(math.pi * seg(f, a, b))

    # duck through the tunnel so the head clears the arch
    duck = 0.2 * ease(seg(f, 28, 32)) * (1 - ease(seg(f, 48, 52)))
    sq += duck

    j, je = boil.v(), boil.e()
    key(p_root, f, loc=(pos.x + j.x, pos.y + j.y, pos.z + bob + hz), rot=(je.x, je.y, yaw + je.z))
    key(p_body, f, rot=(0, roll, 0), scale=(PS * (1 + sq * 0.5 - st * 0.4), PS * (1 + sq * 0.5 - st * 0.4), PS * (1 - sq + st)))

    # head: peek left/right at the door, look around, look up at flake, shake
    hy = 0.0
    hy += 0.45 * math.sin(math.pi * 2 * seg(f, 50, 60))
    hy += -0.5 * ease(seg(f, 100, 106)) * (1 - ease(seg(f, 110, 113)))
    hy += 0.5 * ease(seg(f, 112, 117)) * (1 - ease(seg(f, 119, 122)))
    if 140 <= f < 150:
        hy += (0.4 if f % 2 else -0.4) * (1 - seg(f, 140, 150) * 0.5)
    hp = -0.45 * ease(seg(f, 122, 128)) * (1 - ease(seg(f, 134, 138)))  # look up
    ht = 0.18 * ease(seg(f, 188, 194)) * (1 - ease(seg(f, 226, 232)))    # tilt while waving
    key(head, f, rot=(hp, ht, hy))

    # flippers
    flapL = flapR = 0.0
    if walking:
        flapL = flapR = 0.22 if step else 0.12
    for a, b in ((153, 159), (163, 169)):
        s = math.sin(math.pi * seg(f, a, b))
        flapL += 0.9 * s
        flapR += 0.9 * s
    if 140 <= f < 150:
        flapL += 0.3
        flapR += 0.3
    wave = ease(seg(f, 188, 194)) * (1 - ease(seg(f, 222, 228)))
    flapR += wave * (2.55 + 0.3 * (1 if (f // 3) % 2 else -1))
    key(flippers[0], f, rot=(0, flapL, 0))
    key(flippers[1], f, rot=(0, -flapR, 0))

    # feet lift while walking
    for k, ft in enumerate(feet):
        up = walking and (step == k)
        key(ft, f, loc=(ft.location.x, ft.location.y, 0.0025 + (0.003 if up else 0.0)))

    op = not blink(f)
    for e in eyes_open:
        key(e, f, scale=(0.0024, 0.0016, 0.0031) if op else (1e-5,) * 3)
    for e in eyes_closed:
        key(e, f, scale=(1e-4,) * 3 if op else (1, 1, 1))

    # falling snow (stepped, like a hand-moved snowflake rig)
    for fl, x, y, z0, spd, ph in flakes:
        z = (z0 + 0.4 - spd * f) % 0.4
        key(fl, f, loc=(x + 0.006 * math.sin(ph + f * 0.2), y, z))

    # hero flake: drifts down onto the beak at f=132, flicked off by the head shake at 142
    sc.frame_set(f)
    bpy.context.view_layer.update()
    tip = head.matrix_world @ BEAK_TIP_LOCAL
    if f < 116:
        hp_ = Vector((SPOT.x + 0.02, SPOT.y - 0.005, 0.42))
    elif f < 132:
        t = seg(f, 116, 132)
        hp_ = Vector((lerp(SPOT.x + 0.02, tip.x, t) + 0.004 * math.sin(f), lerp(SPOT.y - 0.005, tip.y, t), lerp(0.16, tip.z + 0.0030, t)))
    elif f < 142:
        hp_ = tip + Vector((0, 0, 0.0030))
    else:
        t = seg(f, 142, 150)
        hp_ = Vector((tip.x + 0.03 * t, tip.y - 0.005 * t, lerp(tip.z, 0.004, ease(t))))
        if f >= 150:
            hp_ = Vector((tip.x + 0.03, tip.y - 0.005, 0.004)) if hero_land is None else hero_land
            hero_land = hp_
    key(hero, f, loc=hp_)

    glow.data.energy = 2.2 * (1 + 0.12 * math.sin(f * 1.7) * boil.r.uniform(0.5, 1.0))
    glow.data.keyframe_insert('energy', frame=f)
    key_l.data.energy = 22 * (1 + boil.r.uniform(-0.012, 0.012))
    key_l.data.keyframe_insert('energy', frame=f)

constant_interp()
print('BLOCKS', count)
run(sc, OPTS)
