"""
Photoreal hero render of the UTRA 6-1000 quick-change pen holder (Blender / Cycles).

    uv run render_quick_change.py --hero-glb hero.glb
    blender --background --factory-startup --python blender_hero_quick_change.py -- hero.glb "../../Renders/Quick-Change Pen Holder Render 0.png"

Optional extra args after the output path: samples (default 256), width, height.
GPU (OptiX/CUDA/HIP/Metal) is enabled for this process only; --factory-startup keeps your preferences untouched.
"""

import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
GLB = os.path.abspath(argv[0]) if argv else os.path.abspath("hero.glb")
OUT = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.abspath("hero.png")
SAMPLES = int(argv[2]) if len(argv) > 2 else 256
RES = (int(argv[3]) if len(argv) > 3 else 1600, int(argv[4]) if len(argv) > 4 else 1200)

CAMERA_DIR = Vector((0.62, -1.0, 0.40))  # from the target towards the camera
CAMERA_DIST = 0.80  # m
LENS_MM = 85.0
F_STOP = 8.0
LIGHTS_W = {"Key": 30.0, "Rim": 28.0, "Fill": 3.0}  # area lights, W
WORLD_STRENGTH = 0.22
INK_WIDTH = 0.0009  # m (Sharpie Fine Point line)
VIEW_TRANSFORM = os.environ.get("HERO_VIEW", "AgX")
LOOK = os.environ.get("HERO_LOOK", "AgX - Punchy")
EXPOSURE = float(os.environ.get("HERO_EXPOSURE", "-0.2"))


def lin(hex_colour: str) -> tuple:
    """sRGB hex -> linear RGBA."""
    rgb = [int(hex_colour.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb) + (1.0,)


def principled(name, colour, metallic=0.0, roughness=0.5, coat=0.0, bump=0.0, bump_scale=2000.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = lin(colour)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if coat:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = 0.08
    if bump:
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = bump_scale
        bmp = nt.nodes.new("ShaderNodeBump")
        bmp.inputs["Strength"].default_value = bump
        nt.links.new(noise.outputs["Fac"], bmp.inputs["Height"])
        nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def wood(name="Oak desk"):
    """Streaky oak: noise stretched along the plank direction."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (3.0, 90.0, 3.0)
    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 2.5
    grain.inputs["Detail"].default_value = 10.0
    grain.inputs["Roughness"].default_value = 0.62
    grain.inputs["Distortion"].default_value = 0.6
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.35
    ramp.color_ramp.elements[0].color = lin("#6f4e33")
    ramp.color_ramp.elements[1].position = 0.65
    ramp.color_ramp.elements[1].color = lin("#a9855f")
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 900.0
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.03
    nt.links.new(coord.outputs["Object"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], grain.inputs["Vector"])
    nt.links.new(grain.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(fine.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = 0.38
    bsdf.inputs["Coat Weight"].default_value = 0.25
    return mat


MATERIALS = {}


def material_for(name: str):
    n = name.lower()
    table = [
        ("flange", ("Anodised aluminium", "#c9ccd1", 1.0, 0.28)),
        ("housing", ("Painted housing", "#3c4047", 0.0, 0.38, 0.4)),
        ("cartridge body", ("Light grey PETG", "#d6d9dd", 0.0, 0.42, 0.0, 0.08)),
        ("twist ring", ("Orange PETG", "#f2600f", 0.0, 0.36, 0.0, 0.08)),
        ("carriage", ("Orange PETG", "#f2600f", 0.0, 0.36, 0.0, 0.08)),
        ("base", ("Charcoal PETG", "#2f3237", 0.0, 0.4, 0.0, 0.08)),
        ("gauge", ("Charcoal PETG", "#2f3237", 0.0, 0.4, 0.0, 0.08)),
        ("jaw", ("Charcoal PETG", "#2f3237", 0.0, 0.4, 0.0, 0.08)),
        ("rod", ("Ground steel", "#d4d8dc", 1.0, 0.12)),
        ("plunger", ("Stainless steel", "#c8ccd0", 1.0, 0.22)),
        ("spring", ("Spring steel", "#d8dce0", 1.0, 0.18)),
        ("shcs", ("Black-oxide steel", "#1f2022", 0.75, 0.32)),
        ("set screw", ("Black-oxide steel", "#1f2022", 0.75, 0.32)),
        ("dowel", ("Stainless steel", "#c8ccd0", 1.0, 0.22)),
        ("nib", ("Pen nib", "#1b2040", 0.0, 0.6)),
        ("ballpoint 8 mm barrel", ("Blue pen", "#2152b0", 0.0, 0.25, 0.3)),
        ("marker 16 mm barrel", ("Red marker", "#bf2330", 0.0, 0.3, 0.2)),
        ("barrel", ("Pen black", "#141416", 0.0, 0.32, 0.2)),
        ("front", ("Pen black", "#141416", 0.0, 0.32, 0.2)),
    ]
    for key, spec in table:
        if key in n:
            if spec[0] not in MATERIALS:
                MATERIALS[spec[0]] = principled(*spec)
            return MATERIALS[spec[0]]
    return None


def enable_gpu(scene) -> str:
    prefs = bpy.context.preferences.addons["cycles"].preferences
    for kind in ("OPTIX", "CUDA", "HIP", "METAL", "ONEAPI"):
        try:
            prefs.compute_device_type = kind
        except TypeError:
            continue
        (getattr(prefs, "refresh_devices", None) or prefs.get_devices)()
        if any(d.type == kind for d in prefs.devices):
            for d in prefs.devices:
                d.use = d.type == kind
            scene.cycles.device = "GPU"
            return kind
    prefs.compute_device_type = "NONE"
    scene.cycles.device = "CPU"
    return "CPU"


def new_scene():
    if bpy.context.window is not None:  # running inside the UI: leave the user's scene alone
        old = bpy.data.scenes.get("Pen Holder Hero")
        if old:
            bpy.data.scenes.remove(old)
        scene = bpy.data.scenes.new("Pen Holder Hero")
        bpy.context.window.scene = scene
        return scene
    scene = bpy.context.scene
    for ob in list(scene.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    return scene


def link(scene, ob):
    scene.collection.objects.link(ob)
    return ob


def main():
    scene = new_scene()
    bpy.ops.import_scene.gltf(filepath=GLB)
    meshes = [ob for ob in scene.objects if ob.type == "MESH"]
    if not meshes:
        raise SystemExit(f"nothing imported from {GLB}")

    # glTF is metres; fall back to mm -> m if the exporter wrote millimetres
    bpy.context.view_layer.update()
    zs = [(ob.matrix_world @ Vector(c)).z for ob in meshes for c in ob.bound_box]
    if max(zs) - min(zs) > 5.0:
        for ob in scene.objects:
            if ob.parent is None:
                ob.scale = (0.001, 0.001, 0.001)
        bpy.context.view_layer.update()

    for ob in meshes:
        mat = material_for(ob.name)
        if mat:
            ob.data.materials.clear()
            ob.data.materials.append(mat)
        for poly in ob.data.polygons:
            poly.use_smooth = True

    nib = next(ob for ob in meshes if "nib" in ob.name.lower() and "spare" not in ob.name.lower())
    nib_pts = [nib.matrix_world @ Vector(c) for c in nib.bound_box]
    tip = Vector((sum(p.x for p in nib_pts) / 8, sum(p.y for p in nib_pts) / 8, 0.0))
    tip_z = min(p.z for p in nib_pts)

    # desk, paper and the drawing the pen is in the middle of
    bpy.ops.mesh.primitive_plane_add(size=3.0, location=(0, 0, tip_z - 0.00012))
    desk = bpy.context.active_object
    desk.data.materials.append(wood())

    # spirograph (hypotrochoid) the robot is part-way through drawing; it ends at the pen tip
    s, (R, r, d) = 0.0055, (10.0, 7.0, 6.0)
    t_end = 0.86 * 2 * math.pi * 7

    def hypo(t):
        return Vector(((R - r) * math.cos(t) + d * math.cos((R - r) / r * t),
                       (R - r) * math.sin(t) - d * math.sin((R - r) / r * t), 0.0)) * s

    end = hypo(t_end)
    centre = Vector((-0.040, -0.030, 0.0))
    centre = centre.normalized() * end.length
    phi = math.atan2(-centre.y, -centre.x) - math.atan2(end.y, end.x)
    rot = lambda v: Vector((v.x * math.cos(phi) - v.y * math.sin(phi), v.x * math.sin(phi) + v.y * math.cos(phi), 0))
    centre = centre + tip  # the curve ends exactly under the pen

    bpy.ops.mesh.primitive_plane_add(size=1.0, location=(centre.x - 0.01, centre.y + 0.02, tip_z - 0.00002),
                                     rotation=(0, 0, math.radians(-14)))
    paper = bpy.context.active_object
    paper.scale = (0.210, 0.297, 1.0)
    paper.data.materials.append(principled("Paper", "#f5f4ef", 0.0, 0.85))

    curve = bpy.data.curves.new("Ink", "CURVE")
    curve.dimensions = "3D"
    curve.bevel_depth = INK_WIDTH / 2
    curve.bevel_resolution = 2
    spline = curve.splines.new("POLY")
    n = 1400
    spline.points.add(n - 1)
    for i in range(n):
        p = centre + rot(hypo(t_end * i / (n - 1)))
        spline.points[i].co = (p.x, p.y, tip_z + 0.00003, 1.0)
    ink = link(scene, bpy.data.objects.new("Ink", curve))
    ink.data.materials.append(principled("Ink", "#16204a", 0.0, 0.35))

    # lighting: studio HDRI + soft boxes
    world = bpy.data.worlds.new("Studio")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    hdri = os.path.join(bpy.utils.system_resource("DATAFILES", path="studiolights/world"), "studio.exr")
    env.image = bpy.data.images.load(hdri)
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0, 0, math.radians(200))
    coord = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], nt.nodes["Background"].inputs["Color"])
    nt.nodes["Background"].inputs["Strength"].default_value = WORLD_STRENGTH

    target = Vector((tip.x, tip.y + 0.03, tip_z + 0.07))
    for name, offset, size, colour in [
        ("Key", Vector((0.55, -0.45, 0.55)), 0.55, "#fff2e4"),
        ("Rim", Vector((-0.35, 0.55, 0.35)), 0.35, "#e9f1ff"),
        ("Fill", Vector((-0.6, -0.5, 0.15)), 0.8, "#ffffff"),
    ]:
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.size, light.color = LIGHTS_W[name], size, lin(colour)[:3]
        ob = link(scene, bpy.data.objects.new(name, light))
        ob.location = target + offset
        ob.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()

    cam_data = bpy.data.cameras.new("Camera")
    cam_data.lens = LENS_MM
    cam_data.dof.use_dof = True
    cam_data.dof.aperture_fstop = F_STOP
    cam = link(scene, bpy.data.objects.new("Camera", cam_data))
    cam.location = target + CAMERA_DIR.normalized() * CAMERA_DIST
    cam.rotation_euler = (target - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam_data.dof.focus_distance = (cam.location - Vector((tip.x, tip.y, tip_z + 0.045))).length
    scene.camera = cam

    scene.render.engine = "CYCLES"
    device = enable_gpu(scene)
    scene.cycles.samples = SAMPLES
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.use_denoising = True
    scene.render.resolution_x, scene.render.resolution_y = RES
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    for transform, look in ((VIEW_TRANSFORM, LOOK), ("AgX", "AgX - Medium High Contrast")):
        try:
            scene.view_settings.view_transform = transform
        except TypeError:
            continue
        try:
            scene.view_settings.look = look
        except TypeError:
            pass
        break
    scene.view_settings.exposure = EXPOSURE
    scene.render.filepath = OUT
    print(f"rendering {RES[0]}x{RES[1]} @ {SAMPLES} spp on {device} -> {OUT}")
    bpy.ops.render.render(write_still=True)


main()
