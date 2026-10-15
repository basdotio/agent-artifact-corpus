"""Clay Spark: a sleeping clay ball wakes, sprouts into the Claude spark, hops onto the books.
blender -b -P examples/clay_spark.py -- [--still F] [--range A B] [--res W H] [--samples N] [--out DIR]
"""
import bpy, sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'scripts'))
from claylib import *

OPTS = cli('clay_spark')

reset()
sc = setup_render(res=OPTS['res'], samples=OPTS['samples'])
world((0.30, 0.42, 0.40), 0.10)

# ------------------------------------------------------------------ set
wood = bpy.data.materials.new('wood')
wood.use_nodes = True
nt = wood.node_tree
N, L = nt.nodes, nt.links
p = N['Principled BSDF']
tc = N.new('ShaderNodeTexCoord')
mp = N.new('ShaderNodeMapping')
mp.inputs['Scale'].default_value = (0.6, 5.0, 1.0)
L.new(tc.outputs['Object'], mp.inputs['Vector'])
wv = N.new('ShaderNodeTexWave')
wv.wave_type = 'BANDS'
wv.bands_direction = 'Y'
wv.inputs['Scale'].default_value = 3.0
wv.inputs['Distortion'].default_value = 11.0
wv.inputs['Detail'].default_value = 4.0
wv.inputs['Detail Scale'].default_value = 1.5
L.new(mp.outputs['Vector'], wv.inputs['Vector'])
nz = N.new('ShaderNodeTexNoise')
nz.inputs['Scale'].default_value = 180
nz.inputs['Detail'].default_value = 8
L.new(mp.outputs['Vector'], nz.inputs['Vector'])
mx = N.new('ShaderNodeMix')
mx.data_type = 'FLOAT'
mx.inputs['Factor'].default_value = 0.3
L.new(wv.outputs['Fac'], mx.inputs['A'])
L.new(nz.outputs['Fac'], mx.inputs['B'])
ramp = N.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = 0.25
ramp.color_ramp.elements[0].color = (0.16, 0.075, 0.03, 1)
ramp.color_ramp.elements[1].position = 0.8
ramp.color_ramp.elements[1].color = (0.36, 0.19, 0.08, 1)
L.new(mx.outputs['Result'], ramp.inputs['Fac'])
L.new(ramp.outputs['Color'], p.inputs['Base Color'])
p.inputs['Roughness'].default_value = 0.5
p.inputs['Coat Weight'].default_value = 0.15
p.inputs['Coat Roughness'].default_value = 0.35
bp = N.new('ShaderNodeBump')
bp.inputs['Strength'].default_value = 0.05
bp.inputs['Distance'].default_value = 0.0005
L.new(mx.outputs['Result'], bp.inputs['Height'])
L.new(bp.outputs['Normal'], p.inputs['Normal'])

bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.2, 0))
desk = bpy.context.active_object
desk.name = 'desk'
desk.scale = (2.0, 1.1, 1)
assign(desk, wood)

wallm = clay('wall', (0.15, 0.28, 0.25), rough=0.92, sss=0.0, bump=0.12, thumb=0.0, scale=0.2)
bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0.66, 0.5), rotation=(math.pi / 2, 0, 0))
wall = bpy.context.active_object
wall.name = 'wall'
wall.scale = (3, 1.2, 1)
assign(wall, wallm)

# fairy lights: two drooping strings of warm bulbs on the wall -> bokeh
bulb = emissive('bulb', (1.0, 0.72, 0.42), 30)
rnd = random.Random(7)
for row, (z0, sag, n) in enumerate([(0.235, 0.02, 15), (0.19, 0.025, 14), (0.15, 0.02, 11)]):
    for i in range(n):
        t = i / (n - 1)
        x = lerp(-0.55, 0.55, t) + rnd.uniform(-0.03, 0.03) + row * 0.03
        z = z0 - sag * math.sin(math.pi * ((t * 2.3 + row * 0.4) % 1.0)) + rnd.uniform(-0.012, 0.012)
        sphere(f'bulb{row}_{i}', 0.0032 + rnd.uniform(0, 0.001), (x, 0.645, z), mat=bulb, segs=12, rings=8)

# pencil cup (open clay cylinder) with pencils + brush
cupm = clay('cup', (0.80, 0.78, 0.73), rough=0.55, sss=0.05, bump=0.2)
cup = cylinder('cup', 0.021, 0.056, (-0.135, 0.07, 0.028), verts=64, mat=cupm)
import bmesh
bm = bmesh.new()
bm.from_mesh(cup.data)
top = [f for f in bm.faces if f.normal.z > 0.9]
bmesh.ops.delete(bm, geom=top, context='FACES_ONLY')
bm.to_mesh(cup.data)
bm.free()
sol = cup.modifiers.new('sol', 'SOLIDIFY')
sol.thickness = 0.0022
bev = cup.modifiers.new('bev', 'BEVEL')
bev.width = 0.0008
bev.segments = 3
sub = cup.modifiers.new('sub', 'SUBSURF')
sub.levels = sub.render_levels = 1
smooth(cup)
cylinder('cup_dark', 0.0185, 0.001, (-0.135, 0.07, 0.048), mat=clay('cupin', (0.12, 0.11, 0.1)))


def pencil(name, color, loc, tilt, length=0.085, tip=(0.83, 0.62, 0.4), lead=(0.05, 0.05, 0.05), hexa=True):
    body = cylinder(name, 0.0032, length, (0, 0, 0), verts=6 if hexa else 24, mat=clay(name + 'm', color, rough=0.45, sss=0.02, bump=0.15))
    b = body.modifiers.new('bev', 'BEVEL')
    b.width = 0.0005
    b.segments = 2
    smooth(body)
    bpy.ops.mesh.primitive_cone_add(vertices=24, radius1=0.0032, radius2=0.0006, depth=0.009, location=(0, 0, length / 2 + 0.0045))
    cone = bpy.context.active_object
    cone.name = name + '_tip'
    assign(cone, clay(name + 'tm', tip, rough=0.6))
    smooth(cone)
    sphere(name + '_lead', 0.0009, (0, 0, length / 2 + 0.009), mat=clay(name + 'lm', lead, rough=0.3))
    root = empty(name + '_root', loc)
    for o in (body, cone, bpy.data.objects[name + '_lead']):
        o.parent = root
    root.rotation_euler = tilt
    return root


pencil('pencil_y', (0.85, 0.66, 0.07), (-0.142, 0.075, 0.06), (0.05, -0.28, 0))
pencil('pencil_w', (0.86, 0.80, 0.62), (-0.133, 0.062, 0.058), (-0.1, 0.05, 0), length=0.075, hexa=False, tip=(0.86, 0.80, 0.62), lead=(0.9, 0.86, 0.72))
pencil('brush', (0.08, 0.06, 0.06), (-0.126, 0.074, 0.062), (0.02, 0.26, 0), length=0.09, hexa=False, tip=(0.55, 0.06, 0.05), lead=(0.5, 0.05, 0.04))

# stacked books
def book(name, cover, size, loc, rot=0.0):
    w, d, h = size
    root = empty(name, loc)
    cm = clay(name + 'c', cover, rough=0.7, sss=0.02, bump=0.25)
    pm = clay(name + 'p', (0.82, 0.80, 0.72), rough=0.8, sss=0.02, bump=0.4, thumb=0.0, scale=3)
    board = 0.0022
    for z, nm in ((board / 2, 'bot'), (h - board / 2, 'top')):
        o = rounded_box(f'{name}_{nm}', (w, d, board), (0, 0, z), bevel=0.0008, mat=cm)
        o.parent = root
    o = rounded_box(f'{name}_spine', (w, board * 1.4, h), (0, d / 2 - board * 0.5, h / 2), bevel=0.0012, mat=cm)
    o.parent = root
    o = rounded_box(f'{name}_pages', (w - 0.004, d - 0.004, h - board * 2), (0, -0.001, h / 2), bevel=0.0005, mat=pm)
    o.parent = root
    root.rotation_euler.z = rot
    return root

BOOK_H = 0.019
book('book_blue', (0.035, 0.07, 0.30), (0.118, 0.080, BOOK_H), (0.118, 0.055, 0.0), rot=-0.03)
book('book_green', (0.30, 0.42, 0.30), (0.110, 0.074, 0.017), (0.114, 0.052, BOOK_H), rot=0.02)
BOOK_TOP = BOOK_H + 0.017

# wooden dowel pencil lying on the desk
dow = cylinder('dowel', 0.0026, 0.15, (0.052, -0.06, 0.0026), verts=24, mat=clay('dowel', (0.78, 0.62, 0.40), rough=0.55, bump=0.2),
               rot=(0, math.pi / 2, 0.16))
smooth(dow)
b = dow.modifiers.new('bev', 'BEVEL')
b.width = 0.001
b.segments = 3

# clay crumbs
orange = (0.72, 0.21, 0.085)
crumb = clay('crumb', orange, rough=0.6, sss=0.15)
for i, (x, y) in enumerate([(-0.065, -0.012), (0.035, -0.03), (0.018, 0.012), (-0.04, 0.03)]):
    sphere(f'crumb{i}', 0.0015 + 0.0005 * (i % 2), (x, y, 0.001), scale=(1.2, 1, 0.7), mat=crumb, segs=16, rings=8, lumpy=0.0004, seed=i)

# ------------------------------------------------------------------ character
spark = clay('spark', (0.72, 0.21, 0.085), rough=0.6, sss=0.06, bump=0.6, thumb=0.45, scale=0.13, bumpdist=2.5)
root = empty('char_root', (-0.03, 0.0, 0.028))
BALL_R, CORE_R = 0.028, 0.019
core = sphere('core', 1.0, (0, 0, 0), mat=spark, segs=64, rings=32, lumpy=0.018)
core.parent = root
core.scale = (BALL_R,) * 3

eye_black = glossy_black()
eyes_open, eyes_closed = [], []
for side in (-1, 1):
    e = sphere(f'eye_open{side}', 1.0, (side * 0.33, -0.93, 0.16), scale=(0.1, 0.07, 0.16), mat=eye_black, segs=24, rings=12)
    e.parent = core
    eyes_open.append(e)
    # closed eye: a lashy "‿" arc lying on the sphere surface
    cd = bpy.data.curves.new(f'lid{side}', 'CURVE')
    cd.dimensions = '3D'
    cd.bevel_depth = 0.022
    cd.bevel_resolution = 3
    cd.use_fill_caps = True
    sp = cd.splines.new('NURBS')
    pts = []
    for k in range(7):
        t = k / 6
        x = side * 0.33 + (t - 0.5) * 0.34
        z = 0.12 - 0.07 * math.sin(math.pi * t)
        y = -math.sqrt(max(0.0, 1 - x * x - z * z)) - 0.012
        pts.append((x, y, z))
    sp.points.add(len(pts) - 1)
    for pt, co in zip(sp.points, pts):
        pt.co = (*co, 1)
    sp.use_endpoint_u = True
    sp.order_u = 3
    lid = bpy.data.objects.new(f'eye_closed{side}', cd)
    bpy.context.collection.objects.link(lid)
    lid.data.materials.append(eye_black)
    lid.parent = core
    eyes_closed.append(lid)

# spark rays (Claude logo): tapered clay capsules radiating in the XZ plane
RAYS = [(0, 1.0), (31, .82), (61, .96), (90, .86), (119, 1.0), (149, .80), (180, .93),
        (211, .85), (243, 1.0), (271, .82), (301, .95), (331, .86)]
RAY_LEN, RAY_W = 0.05, 0.0125
rays_grp = empty('rays', (0, 0, 0), root)
rays = []
for i, (ang, ln) in enumerate(RAYS):
    # capsule along +X from 0..1: split a pole-on-X sphere into two round caps
    bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, rotation=(0, math.pi / 2, 0))
    r = bpy.context.active_object
    r.name = f'ray{i}'
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=False)
    CAP = 0.14
    for v in r.data.vertices:
        xs = v.co.x
        x = CAP * (1 + xs) if xs <= 0 else 1 - CAP + CAP * xs
        taper = lerp(1.0, 0.86, x)
        v.co.x = x
        v.co.y *= taper * 0.5
        v.co.z *= taper * 0.5
    smooth(r)
    add_lumps(r, 0.06, seed=i, size=0.4)
    assign(r, spark)
    r.parent = rays_grp
    r.rotation_euler = (0, -math.radians(ang + random.Random(i).uniform(-3, 3)), 0)
    rays.append((r, math.radians(ang), ln))

# ------------------------------------------------------------------ lights + camera
key_l = area_light('key', (-0.38, -0.30, 0.40), (0, 0.03, 0.02), 16, 0.25, (1.0, 0.86, 0.70))
fill = area_light('fill', (0.45, -0.3, 0.18), (0, 0.03, 0.03), 1.6, 0.6, (0.80, 0.90, 1.0))
rim = area_light('rim', (0.1, 0.45, 0.35), (0, 0, 0.03), 4, 0.3, (1.0, 0.9, 0.8))
cam = camera((0.0, -0.50, 0.095), (0.0, 0.03, 0.035), lens=50, fstop=3.2, focus=0.505)

# ------------------------------------------------------------------ animation
boil = Boil(3)
X0, Y0 = -0.03, 0.0
BOOK_X, BOOK_Y = 0.112, 0.050
F = 240


def ray_len(i, f):
    """Current ray length (fraction of full)."""
    start = 113 + i * 1.2
    t = seg(f, start, start + 9)
    return 0.0 if t <= 0 else 0.25 + 0.75 * ease_out_back(t, 2.2)


def eyes_state(f):
    if f < 44:
        return False
    for b in (58, 59, 148, 149, 197, 198):
        if f == b:
            return False
    return f < 226


for f in range(1, F + 1):
    # --- core size / breathing
    grow = ease(seg(f, 113, 128))
    cr = lerp(BALL_R, CORE_R, grow)
    sx = sy = sz = 1.0
    if f < 44:
        br = 0.025 * math.sin(2 * math.pi * f / 22)
        sz, sx = 1 + br, 1 - br * 0.5
        sy = sx
    # anticipation squash before sprouting
    sq = math.sin(math.pi * seg(f, 104, 113)) * 0.14
    sz -= sq
    sx += sq * 0.5
    sy += sq * 0.5

    # --- heading (look around, face travel direction, back to camera)
    yaw = 0.0
    yaw += -0.48 * ease(seg(f, 62, 71)) * (1 - ease(seg(f, 80, 86)))
    yaw += 0.48 * ease(seg(f, 82, 92)) * (1 - ease(seg(f, 98, 104)))
    yaw += 0.75 * ease(seg(f, 152, 157)) * (1 - ease(seg(f, 188, 195)))
    pitch = 0.0
    pitch += 0.28 * ease(seg(f, 134, 140)) * (1 - ease(seg(f, 144, 148)))  # looks down at its new rays

    # --- position: two hops to the books
    x, y, z_extra = X0, Y0, 0.0
    base = 0.0
    h1 = seg(f, 160, 168)
    h2 = seg(f, 175, 186)
    x = lerp(x, 0.04, ease(h1))
    z_extra += 0.03 * math.sin(math.pi * h1)
    x = lerp(x, BOOK_X, ease(h2))
    y = lerp(y, BOOK_Y, ease(h2))
    base = lerp(0.0, BOOK_TOP, ease(seg(f, 175, 184)))
    z_extra += 0.055 * math.sin(math.pi * h2)
    # sprout pop
    z_extra += 0.012 * math.sin(math.pi * seg(f, 113, 121))
    # joy bounce at the end
    z_extra += 0.012 * abs(math.sin(math.pi * seg(f, 214, 226) * 2))

    # hop squash & stretch
    for a, b in ((157, 160), (172, 175)):
        s = math.sin(math.pi * seg(f, a, b)) * 0.16
        sz -= s
        sx += s * 0.5
        sy += s * 0.5
    for a, b in ((160, 166), (175, 184)):
        s = math.sin(math.pi * seg(f, a, b)) * 0.1
        sz += s
        sx -= s * 0.4
        sy -= s * 0.4
    for a, b in ((168, 171), (186, 190)):
        s = math.sin(math.pi * seg(f, a, b)) * 0.14
        sz -= s
        sx += s * 0.5
        sy += s * 0.5

    # --- rays
    spin = 2 * math.pi * ease(seg(f, 200, 213))
    lowest = cr
    for i, (r, ang, ln) in enumerate(rays):
        k = ray_len(i, f)
        wig = 0.06 * math.sin(f * 0.9 + i) * seg(f, 128, 131) * (1 - seg(f, 146, 150))
        wig += 0.08 * math.sin(f * 1.3 + i * 2) * seg(f, 214, 216) * (1 - seg(f, 226, 230))
        L_ = max(1e-4, RAY_LEN * ln * k * (1 + boil.r.uniform(-0.015, 0.015)))
        W_ = max(1e-4, RAY_W * (0.4 + 0.6 * min(1.0, k)))
        key(r, f, rot=(0, -(ang + wig) + 0.0, 0), scale=(L_, W_, W_))
        reach = -math.sin(ang + wig + spin) * L_ * 0.985
        lowest = max(lowest, reach)
    key(rays_grp, f, rot=(0, -spin, 0))

    z = base + lowest * sz + z_extra
    j, je = boil.v(), boil.e()
    key(root, f, loc=(x + j.x, y + j.y, z + j.z), rot=(pitch + je.x, je.y, yaw + je.z), scale=(sx, sy, sz))
    key(core, f, scale=(cr * (1 + boil.r.uniform(-0.01, 0.01)),) * 3)

    op = eyes_state(f)
    for e in eyes_open:
        key(e, f, scale=(0.1, 0.07, 0.16) if op else (1e-4,) * 3)
    for e in eyes_closed:
        key(e, f, scale=(1e-4,) * 3 if op else (1, 1, 1))

    # hand-made light flicker
    key_l.data.energy = 16 * (1 + boil.r.uniform(-0.012, 0.012))
    key_l.data.keyframe_insert('energy', frame=f)

constant_interp()
run(sc, OPTS)
