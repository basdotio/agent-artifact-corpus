"""claylib: helpers for stop-motion claymation scenes in Blender (4.2+, tested on 5.2 / Cycles).

Scene scripts build a miniature set in real-world metres, key every frame with CONSTANT
interpolation (stop motion "on twos" at 12 fps), and add per-frame boil and light flicker.
"""
import bpy, bmesh, math, random, sys, os
from mathutils import Vector, Euler

FPS = 12  # stop motion "on twos"


def cli(name):
    """Parse `blender -b -P scene.py -- [options]`.

    --still F        render one frame to <out>/still_F.png
    --range A B      render frames A..B
    --res W H        resolution (default 1920 1080)
    --samples N      Cycles samples (default 96)
    --out DIR        frame output dir (default ./renders/<name>)
    --blend PATH     also save the .blend for inspection
    """
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else []
    o = {'still': None, 'range': None, 'res': (1920, 1080), 'samples': 96,
         'out': os.path.join(os.getcwd(), 'renders', name), 'blend': None}
    i = 0
    while i < len(argv):
        a = argv[i].lstrip('-')
        if a == 'still':
            o['still'] = int(argv[i + 1]); i += 2
        elif a == 'range':
            o['range'] = (int(argv[i + 1]), int(argv[i + 2])); i += 3
        elif a == 'res':
            o['res'] = (int(argv[i + 1]), int(argv[i + 2])); i += 3
        elif a == 'samples':
            o['samples'] = int(argv[i + 1]); i += 2
        elif a == 'out':
            o['out'] = os.path.abspath(os.path.expanduser(argv[i + 1])); i += 2
        elif a == 'blend':
            o['blend'] = os.path.abspath(os.path.expanduser(argv[i + 1])); i += 2
        else:
            raise SystemExit(f'unknown option {argv[i]!r}')
    return o


def run(sc, o):
    """Render according to cli() options: a still, a range, or the whole shot."""
    os.makedirs(o['out'], exist_ok=True)
    if o['blend']:
        bpy.ops.wm.save_as_mainfile(filepath=o['blend'])
    if o['still'] is not None:
        sc.frame_set(o['still'])
        sc.render.filepath = os.path.join(o['out'], 'still_%04d.png' % o['still'])
        bpy.ops.render.render(write_still=True)
        print('STILL', sc.render.filepath, flush=True)
        return
    if o['range']:
        sc.frame_start, sc.frame_end = o['range']
    sc.render.filepath = o['out'] + os.sep  # frames land as 0001.png, 0002.png, ...
    bpy.ops.render.render(animation=True)
    print('DONE', o['out'], flush=True)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def use_gpu(sc):
    """Pick the first available Cycles GPU backend, else fall back to CPU."""
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for backend in ('METAL', 'OPTIX', 'CUDA', 'HIP', 'ONEAPI'):
        try:
            prefs.compute_device_type = backend
        except TypeError:
            continue
        prefs.get_devices()
        if any(d.type == backend for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == backend
            sc.cycles.device = 'GPU'
            print('CYCLES DEVICE', backend, flush=True)
            return backend
    sc.cycles.device = 'CPU'
    print('CYCLES DEVICE CPU', flush=True)
    return 'CPU'


def setup_render(res=(1920, 1080), samples=96, frames=240):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    use_gpu(sc)
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    except TypeError:
        pass
    sc.cycles.max_bounces = 6
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.use_persistent_data = True
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, frames
    sc.render.image_settings.file_format = 'PNG'
    sc.view_settings.view_transform = 'AgX'
    try:
        sc.view_settings.look = 'AgX - Medium High Contrast'
    except TypeError:
        pass
    sc.view_settings.exposure = -0.45  # clay washes out to pastel fast; keep it a touch under
    sc.render.film_transparent = False
    return sc


def world(color=(0.05, 0.06, 0.07), strength=0.4):
    w = bpy.data.worlds.new('World')
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs[0].default_value = (*color, 1)
    bg.inputs[1].default_value = strength


# ---------------------------------------------------------------- materials

def clay(name, color, rough=0.62, sss=0.08, bump=0.35, thumb=0.25, scale=1.0, coat=0.0, bumpdist=1.0):
    """Plasticine: soft SSS, lumpy low-freq bump + thumbprint smears."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    N, L = nt.nodes, nt.links
    p = N['Principled BSDF']
    p.inputs['Base Color'].default_value = (*color, 1)
    p.inputs['Roughness'].default_value = rough
    p.inputs['Subsurface Weight'].default_value = sss
    p.inputs['Subsurface Radius'].default_value = (color[0] * 2 + .2, color[1] * 2 + .2, color[2] * 2 + .2)
    p.inputs['Subsurface Scale'].default_value = 0.004
    p.inputs['Specular IOR Level'].default_value = 0.35
    p.inputs['Coat Weight'].default_value = coat
    tc = N.new('ShaderNodeTexCoord')
    # low-frequency lumps
    n1 = N.new('ShaderNodeTexNoise')
    n1.inputs['Scale'].default_value = 60 * scale
    n1.inputs['Detail'].default_value = 3
    n1.inputs['Roughness'].default_value = 0.5
    L.new(tc.outputs['Object'], n1.inputs['Vector'])
    # thumbprints / tool smears: stretched voronoi edges
    mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1.0, 2.2, 1.0)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    v = N.new('ShaderNodeTexVoronoi')
    v.feature = 'DISTANCE_TO_EDGE'
    v.inputs['Scale'].default_value = 90 * scale
    L.new(mp.outputs['Vector'], v.inputs['Vector'])
    cr = N.new('ShaderNodeMapRange')
    cr.inputs['From Min'].default_value = 0.0
    cr.inputs['From Max'].default_value = 0.08
    L.new(v.outputs['Distance'], cr.inputs['Value'])
    mix = N.new('ShaderNodeMath')
    mix.operation = 'MULTIPLY_ADD'
    L.new(cr.outputs['Result'], mix.inputs[0])
    mix.inputs[1].default_value = thumb
    L.new(n1.outputs['Fac'], mix.inputs[2])
    b = N.new('ShaderNodeBump')
    b.inputs['Strength'].default_value = bump
    b.inputs['Distance'].default_value = 0.0006 * bumpdist
    L.new(mix.outputs['Value'], b.inputs['Height'])
    L.new(b.outputs['Normal'], p.inputs['Normal'])
    # subtle colour mottling like hand-kneaded plasticine
    n2 = N.new('ShaderNodeTexNoise')
    n2.inputs['Scale'].default_value = 25 * scale
    L.new(tc.outputs['Object'], n2.inputs['Vector'])
    hsv = N.new('ShaderNodeHueSaturation')
    hsv.inputs['Color'].default_value = (*color, 1)
    mr = N.new('ShaderNodeMapRange')
    mr.inputs['To Min'].default_value = 0.9
    mr.inputs['To Max'].default_value = 1.1
    L.new(n2.outputs['Fac'], mr.inputs['Value'])
    L.new(mr.outputs['Result'], hsv.inputs['Value'])
    L.new(hsv.outputs['Color'], p.inputs['Base Color'])
    return m


def emissive(name, color, strength):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    N = m.node_tree.nodes
    N.remove(N['Principled BSDF'])
    e = N.new('ShaderNodeEmission')
    e.inputs[0].default_value = (*color, 1)
    e.inputs[1].default_value = strength
    m.node_tree.links.new(e.outputs[0], N['Material Output'].inputs[0])
    return m


def glossy_black(name='eye_black'):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes['Principled BSDF']
    p.inputs['Base Color'].default_value = (0.012, 0.01, 0.01, 1)
    p.inputs['Roughness'].default_value = 0.18
    p.inputs['Coat Weight'].default_value = 0.6
    p.inputs['Coat Roughness'].default_value = 0.05
    return m


# ---------------------------------------------------------------- geometry

def assign(ob, mat):
    ob.data.materials.clear()
    ob.data.materials.append(mat)
    return ob


def smooth(ob):
    for p in ob.data.polygons:
        p.use_smooth = True
    return ob


def sphere(name, r=1.0, loc=(0, 0, 0), scale=(1, 1, 1), mat=None, segs=48, rings=24, lumpy=0.0, seed=0):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segs, ring_count=rings, radius=r, location=loc)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = scale
    smooth(ob)
    if lumpy:
        add_lumps(ob, lumpy, seed=seed, size=r * 0.6)
    if mat:
        assign(ob, mat)
    return ob


def add_lumps(ob, strength, seed=0, size=0.02):
    tex = bpy.data.textures.new(ob.name + '_lump', 'CLOUDS')
    tex.noise_scale = size
    tex.noise_depth = 1
    md = ob.modifiers.new('lumps', 'DISPLACE')
    md.texture = tex
    md.texture_coords = 'OBJECT'
    md.strength = strength
    md.mid_level = 0.5
    return md


def rounded_box(name, size, loc=(0, 0, 0), bevel=0.004, mat=None, rot=(0, 0, 0), lumpy=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    ob.scale = size
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    b = ob.modifiers.new('bevel', 'BEVEL')
    b.width = bevel
    b.segments = 4
    b.limit_method = 'NONE'
    s = ob.modifiers.new('sub', 'SUBSURF')
    s.levels = s.render_levels = 1
    smooth(ob)
    if lumpy:
        add_lumps(ob, lumpy, size=max(size) * 0.3)
    if mat:
        assign(ob, mat)
    return ob


def cylinder(name, r, depth, loc=(0, 0, 0), verts=48, mat=None, rot=(0, 0, 0)):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)
    ob = bpy.context.active_object
    ob.name = name
    if mat:
        assign(ob, mat)
    return ob


def empty(name, loc=(0, 0, 0), parent=None):
    e = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(e)
    e.location = loc
    if parent:
        e.parent = parent
    return e


def parent(child, par):
    child.parent = par
    child.matrix_parent_inverse = par.matrix_world.inverted()
    return child


def area_light(name, loc, target, energy, size, color=(1, 1, 1), shape='DISK'):
    ld = bpy.data.lights.new(name, 'AREA')
    ld.energy = energy
    ld.size = size
    ld.shape = shape
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    look_at(ob, target)
    return ob


def point_light(name, loc, energy, radius=0.01, color=(1, 1, 1)):
    ld = bpy.data.lights.new(name, 'POINT')
    ld.energy = energy
    ld.shadow_soft_size = radius
    ld.color = color
    ob = bpy.data.objects.new(name, ld)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    return ob


def look_at(ob, target):
    d = Vector(target) - ob.location
    ob.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()


def camera(loc, target, lens=50, fstop=2.0, focus=None):
    cd = bpy.data.cameras.new('Cam')
    cd.lens = lens
    cd.sensor_width = 36
    cd.dof.use_dof = True
    cd.dof.aperture_fstop = fstop
    cd.dof.aperture_blades = 0
    ob = bpy.data.objects.new('Cam', cd)
    bpy.context.collection.objects.link(ob)
    ob.location = loc
    look_at(ob, target)
    cd.dof.focus_distance = focus if focus else (Vector(target) - Vector(loc)).length
    bpy.context.scene.camera = ob
    return ob


# ---------------------------------------------------------------- animation

def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def ease_out_back(t, s=1.9):
    t = max(0.0, min(1.0, t)) - 1
    return t * t * ((s + 1) * t + s) + 1


def seg(f, a, b):
    """0..1 progress of frame f through [a, b]."""
    if b == a:
        return 1.0 if f >= b else 0.0
    return max(0.0, min(1.0, (f - a) / (b - a)))


def lerp(a, b, t):
    return a + (b - a) * t


def key(ob, f, loc=None, rot=None, scale=None):
    if loc is not None:
        ob.location = loc
        ob.keyframe_insert('location', frame=f)
    if rot is not None:
        ob.rotation_euler = rot
        ob.keyframe_insert('rotation_euler', frame=f)
    if scale is not None:
        ob.scale = scale
        ob.keyframe_insert('scale', frame=f)


def constant_interp():
    """Stop motion: every keyed frame holds until the next one."""
    for a in bpy.data.actions:
        for fc in all_fcurves(a):
            for kp in fc.keyframe_points:
                kp.interpolation = 'CONSTANT'
    for ld in bpy.data.lights:
        if ld.animation_data and ld.animation_data.action:
            for fc in all_fcurves(ld.animation_data.action):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'CONSTANT'


def all_fcurves(action):
    # Blender 4.4+ layered actions keep fcurves in channelbags
    fcs = []
    if hasattr(action, 'layers') and len(action.layers):
        for layer in action.layers:
            for strip in layer.strips:
                for cb in strip.channelbags:
                    fcs.extend(cb.fcurves)
    elif hasattr(action, 'fcurves'):
        fcs.extend(action.fcurves)
    return fcs


class Boil:
    """Per-frame hand-placement jitter: the thing that sells real stop motion."""

    def __init__(self, seed, amp=0.00025, rot=0.004):
        self.r = random.Random(seed)
        self.amp, self.rot = amp, rot

    def v(self):
        a = self.amp
        return Vector((self.r.uniform(-a, a), self.r.uniform(-a, a), self.r.uniform(-a, a) * 0.5))

    def e(self):
        a = self.rot
        return Vector((self.r.uniform(-a, a), self.r.uniform(-a, a), self.r.uniform(-a, a)))
