"""
Animated explainer for the chess-piece gripper (Blender / Cycles).

Builds the assembly from the STLs in ./STLs, adds what only exists in SolidWorks or not at all
(SG90 servo, pins, the broccoli rubber band that closes the claws, and a Staunton chess set on a
board, set up in a real opening position), and animates one move: the gripper picks up White's
king and plays Kf1. The only input is the servo angle: the claw, pusher and band poses are solved
from the real part geometry for every frame.

    blender -b --factory-startup --python animate_chess_gripper.py -- --check
    blender -b --factory-startup --python animate_chess_gripper.py -- --out frames
    uv run make_video.py frames

Options after "--":
    --out DIR        frame directory (frame_0001.png ...) and timeline.json     [./frames]
    --frames A-B     frame range                                                 [all]
    --stills LIST    render only these frames, e.g. 1,60,140
    --samples N      Cycles samples                                              [96]
    --res WxH        resolution                                                  [1920x1080]
    --check          print the kinematics / clearance report and exit
    --save FILE      also save the .blend
"""

import argparse
import json
import math
import os
import random
import sys
from collections import namedtuple

import bmesh
import bpy
import numpy as np
from mathutils import Matrix, Quaternion, Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
STL_DIR = os.path.join(HERE, "STLs")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser(prog="animate_chess_gripper.py")
ap.add_argument("--out", default=os.path.join(HERE, "frames"))
ap.add_argument("--frames", default=None)
ap.add_argument("--stills", default=None)
ap.add_argument("--samples", type=int, default=96)
ap.add_argument("--res", default="1920x1080")
ap.add_argument("--check", action="store_true")
ap.add_argument("--save", default=None)
ARGS = ap.parse_args(argv)

MM = 0.001  # the geometry below is in mm, the Blender scene in metres
Z = Vector((0.0, 0.0, 1.0))

# ---------------------------------------------------------------------------------------------
# Geometry measured from the STLs (mm).
# Gripper frame G: origin on the gripper axis at the underside of the hex plate, +Z up (to the arm).
# ---------------------------------------------------------------------------------------------
BASE_STL_AXIS = Vector((37.12, 0.0, 27.2))  # Gripper Base v3.STL: axis at X/Z; STL +Y is G +Z
PIVOT_R, PIVOT_Z = 26.004, 18.75            # Ø2.5 claw pivots in the three bracket forks
CLAW_AZ = (30.0, 150.0, 270.0)              # bracket azimuths in G, counter-clockwise
MOUNT_R, MOUNT_Z = 32.0, 35.0               # 3x M5 on PCD 64 (UTRA flange), top face of the tabs

CLAW_PIVOT = Vector((3.25, 89.74, 6.125))   # Gripper Claw v3.STL: pivot hole (Z = mid-width)
CLAW_OUTER_X, CLAW_MID_X, CLAW_INNER_X = 3.5, 5.0, 6.5  # 3 mm strip of the straight section
CLAW_HOLE_Y = 58.74                         # Ø6 peg hole, edges rounded out to ~Ø8.5
CLAW_WIDTH = 12.25
CLAW_TIP_X = 20.8                           # deepest point of the concave hook tip
CLAW_HOOK_Y0, CLAW_HOOK_Y1 = 0.0, 3.0       # hook is 3 mm thick

PUSHER_EYE = Vector((2.5, 3.25, 37.5))      # Gripper Claw Pusher.STL: Ø2.5 eye, peg runs along -Z
SHOULDER, PEG_TIP = 29.5, 37.5              # eye -> shoulder face / peg tip, along the peg axis
SHOULDER_HW, SHOULDER_HH = 2.0, 3.25        # shoulder face half-width (bulge axis), half-height

WHEEL_CENTRE = Vector((10.0, 1.0, 10.0))    # Gripper Servo Wheel v1.STL: disc centre, mid-thickness
WHEEL_HOLE_R = 7.5
Z_WHEEL = -11.95                            # disc mid-plane = peg height ~ claw hole height

PLATE_EDGE_R = 22.0                         # hex plate flats under the claws (z 0..5)

# Broccoli band: a #81 PLU 4060 produce band (12 mm cut width, 50 mm lay-flat length, 0.8 mm wall).
# Set these to match your band.
BAND_REST = 100.0                           # unstretched circumference (2 x lay-flat length)
BAND_W0, BAND_T0 = 12.0, 0.8                # unstretched width / thickness
BAND_GAP = 0.15                             # drawn clearance to the parts it wraps
BAND_ROWS, BAND_SAMPLES = 13, 720           # mesh rows across the band, samples round it
BAND_ALPHAS = [-3.0 + 0.5 * i for i in range(47)]  # shape keys every 0.5 deg of claw angle

# King: Staunton pattern, 96 mm. The hooks close on the neck under the collar.
KING_GRIP_R = 9.5                           # where the hook tips stop
KING_NECK_R = KING_GRIP_R - 0.05            # drawn neck, so the facets never interpenetrate
KING_SKIRT_H0 = 56.0                        # where the collar starts to flare out of the neck
SQUARE = 55.0
# The Traxler Counterattack: 1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.Ng5 Bc5 5.Nxf7 Bxf2+, and White's king
# steps out of check with 6.Kf1. FEN of the board before the move:
POSITION = "r1bqk2r/pppp1Npp/2n2n2/4p3/2B1P3/8/PPPP1bPP/RNBQK2R"
CAPTURED = (("p", (262.0, 34.0)), ("P", (-318.0, 352.0)))  # off the board, on the capturing player's side
GRIP_SQUARE, DROP_SQUARE = "e1", "f1"
GRIPPER_YAW = -30.0                         # claws at 0, 120, 240 deg: clear of Qd1 at e1 and Bf2 at f1


def square_xy(sq):
    """Centre of a square on the board (mm); e1 is the origin, +X towards h, +Y towards rank 8."""
    return Vector((("abcdefgh".index(sq[0]) - 4) * SQUARE, (int(sq[1]) - 1) * SQUARE, 0.0))


MOVE = square_xy(DROP_SQUARE) - square_xy(GRIP_SQUARE)


# ---------------------------------------------------------------------------------------------
# Kinematics (pure geometry, mm, frame G)
# ---------------------------------------------------------------------------------------------
def radial(az):
    a = math.radians(az)
    return Vector((math.cos(a), math.sin(a), 0.0))


def tangential(az):
    a = math.radians(az)
    return Vector((-math.sin(a), math.cos(a), 0.0))


def claw_frame(az, alpha):
    """Rotation and pivot of the claw at azimuth az. alpha > 0 swings the hook outwards (deg)."""
    r, t = radial(az), tangential(az)
    rest = Matrix((-r, Z, t)).transposed()  # claw STL X -> inwards, Y -> up, Z -> tangential
    return Matrix.Rotation(math.radians(-alpha), 3, t) @ rest, r * PIVOT_R + Z * PIVOT_Z


def claw_point(az, alpha, p):
    rot, loc = claw_frame(az, alpha)
    return loc + rot @ (Vector(p) - CLAW_PIVOT)


def wheel_angle(theta):
    """Wheel rotation for a pusher eye at az + theta (STL holes sit at 90, -30 and 210 deg)."""
    return theta - 60.0


def pusher_frame(az, theta, alpha):
    """The pusher eye rides on the wheel; its peg axis points through the claw's peg hole."""
    eye = radial(az + theta) * WHEEL_HOLE_R + Z * Z_WHEEL
    hole = claw_point(az, alpha, (CLAW_MID_X, CLAW_HOLE_Y, CLAW_PIVOT.z))
    u = hole - eye
    u.z = 0.0
    u.normalize()
    b = Z.cross(u)  # the C bulges this way, around the servo hub
    return Matrix((b, -Z, -u)).transposed(), eye, u, b, hole


def shoulder_gap(az, theta, alpha):
    """Signed gap between the pusher shoulder and the inner face of its claw (mm)."""
    _, eye, u, b, _ = pusher_frame(az, theta, alpha)
    s = eye + u * SHOULDER
    rot, _ = claw_frame(az, alpha)
    n_in = rot @ Vector((1.0, 0.0, 0.0))
    q = claw_point(az, alpha, (CLAW_INNER_X, CLAW_HOLE_Y, CLAW_PIVOT.z))
    return min(n_in.dot(s + b * (sb * SHOULDER_HW) + Z * (sz * SHOULDER_HH) - q)
               for sb in (-1.0, 1.0) for sz in (-1.0, 1.0))


def bisect(f, lo, hi, iters=60):
    f_lo = f(lo)
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        f_mid = f(mid)
        if (f_mid > 0) == (f_lo > 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def alpha_push(theta):
    """Claw angle at which the pusher shoulder touches the claw; -inf if it is clear of it."""
    g = lambda a: shoulder_gap(CLAW_AZ[0], theta, a)
    if g(-8.0) >= 0.0:
        return -math.inf
    return bisect(g, -8.0, 45.0)


def tip_point(alpha, y=0.5 * (CLAW_HOOK_Y0 + CLAW_HOOK_Y1)):
    """Hook tip in the claw's radial plane: (radius, height) in G."""
    p = claw_point(0.0, alpha, (CLAW_TIP_X, y, CLAW_PIVOT.z))
    return p.x, p.z


def plate_stop():
    """Claw angle at which the arm's inner face reaches the edge of the hex plate."""
    def g(a):
        # inner face line of the straight section, evaluated at the plate's underside (z = 0)
        p0 = claw_point(0.0, a, (CLAW_INNER_X, 60.0, CLAW_PIVOT.z))
        p1 = claw_point(0.0, a, (CLAW_INNER_X, 80.0, CLAW_PIVOT.z))
        s = (0.0 - p0.z) / (p1.z - p0.z)
        return p0.x + (p1.x - p0.x) * s - PLATE_EDGE_R
    return bisect(g, -10.0, 10.0)


ALPHA_STEM = bisect(lambda a: tip_point(a)[0] - KING_GRIP_R, -8.0, 30.0)
ALPHA_PLATE = plate_stop()

# ---------------------------------------------------------------------------------------------
# Materials
# ---------------------------------------------------------------------------------------------
def lin(hex_colour):
    rgb = [int(hex_colour.lstrip("#")[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in rgb) + (1.0,)


def principled(name, colour, metallic=0.0, roughness=0.5, coat=0.0, bump=0.0, bump_scale=3000.0, sheen=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = lin(colour)
    bsdf.inputs["Metallic"].default_value = metallic
    bsdf.inputs["Roughness"].default_value = roughness
    if coat:
        bsdf.inputs["Coat Weight"].default_value = coat
        bsdf.inputs["Coat Roughness"].default_value = 0.1
    if sheen:
        bsdf.inputs["Sheen Weight"].default_value = sheen
    if bump:
        noise = nt.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = bump_scale
        bmp = nt.nodes.new("ShaderNodeBump")
        bmp.inputs["Strength"].default_value = bump
        nt.links.new(noise.outputs["Fac"], bmp.inputs["Height"])
        nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def wood(name, dark, light, grain_scale=(2.0, 60.0, 2.0), coat=0.35, roughness=0.42):
    """Streaky wood in object space, grain along local Y; Object Info random shifts each piece."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    coord = nt.nodes.new("ShaderNodeTexCoord")
    info = nt.nodes.new("ShaderNodeObjectInfo")
    shift = nt.nodes.new("ShaderNodeVectorMath")
    shift.operation = "ADD"
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = grain_scale
    grain = nt.nodes.new("ShaderNodeTexNoise")
    grain.inputs["Scale"].default_value = 14.0
    grain.inputs["Detail"].default_value = 8.0
    grain.inputs["Roughness"].default_value = 0.6
    grain.inputs["Distortion"].default_value = 0.8
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    ramp.color_ramp.elements[0].position = 0.32
    ramp.color_ramp.elements[0].color = lin(dark)
    ramp.color_ramp.elements[1].position = 0.7
    ramp.color_ramp.elements[1].color = lin(light)
    fine = nt.nodes.new("ShaderNodeTexNoise")
    fine.inputs["Scale"].default_value = 4000.0
    bmp = nt.nodes.new("ShaderNodeBump")
    bmp.inputs["Strength"].default_value = 0.02
    nt.links.new(coord.outputs["Object"], shift.inputs[0])
    nt.links.new(info.outputs["Random"], shift.inputs[1])
    nt.links.new(shift.outputs["Vector"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], grain.inputs["Vector"])
    nt.links.new(grain.outputs["Fac"], ramp.inputs["Fac"])
    nt.links.new(ramp.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(fine.outputs["Fac"], bmp.inputs["Height"])
    nt.links.new(bmp.outputs["Normal"], bsdf.inputs["Normal"])
    bsdf.inputs["Roughness"].default_value = roughness
    bsdf.inputs["Coat Weight"].default_value = coat
    return mat


# ---------------------------------------------------------------------------------------------
# Mesh helpers (all inputs in mm, meshes stored in metres)
# ---------------------------------------------------------------------------------------------
def new_object(name, me, parent=None, mat=None, collection=None):
    ob = bpy.data.objects.new(name, me)
    (collection or bpy.context.scene.collection).objects.link(ob)
    if parent is not None:
        ob.parent = parent
    if mat is not None and me is not None:
        me.materials.append(mat)
    return ob


def smooth(me, angle=32.0):
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(angle))


def import_stl(name, filename, transform):
    """Import an STL (mm) and bake `transform` (mm -> mm) plus the mm -> m scale into the mesh."""
    before = set(bpy.data.objects)
    bpy.ops.wm.stl_import(filepath=os.path.join(STL_DIR, filename))
    ob = (set(bpy.data.objects) - before).pop()
    for coll in list(ob.users_collection):
        coll.objects.unlink(ob)
    me = ob.data
    bpy.data.objects.remove(ob)
    me.name = name
    me.transform(Matrix.Scale(MM, 4) @ transform)
    smooth(me)
    return me


def bm_to_mesh(bm, name, sharp=32.0):
    me = bpy.data.meshes.new(name)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.transform(Matrix.Scale(MM, 4))
    smooth(me, sharp)
    return me


def add_box(bm, lo, hi):
    lo, hi = Vector(lo), Vector(hi)
    bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.LocRotScale((lo + hi) / 2, None, hi - lo))


def add_cylinder(bm, centre, axis, radius, length, segments=32, radius2=None):
    """Cylinder (or cone with radius2) centred on `centre` along `axis`."""
    rot = Vector((0.0, 0.0, 1.0)).rotation_difference(Vector(axis).normalized()).to_matrix().to_4x4()
    m = Matrix.Translation(Vector(centre)) @ rot
    bmesh.ops.create_cone(bm, cap_ends=True, segments=segments, radius1=radius,
                          radius2=radius if radius2 is None else radius2, depth=length, matrix=m)


def lathe(name, profile, segments=96, sharp=38.0):
    """Revolve [(r, h), ...] (bottom to top, r may be 0 at the ends) about Z."""
    bm = bmesh.new()
    rings = []
    for r, h in profile:
        if r < 1e-6:
            rings.append([bm.verts.new((0.0, 0.0, h))])
        else:
            rings.append([bm.verts.new((r * math.cos(2 * math.pi * i / segments),
                                        r * math.sin(2 * math.pi * i / segments), h))
                          for i in range(segments)])
    for a, b in zip(rings, rings[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            for i in range(segments):
                bm.faces.new((a[0], b[i], b[(i + 1) % segments]))
        elif len(b) == 1:
            for i in range(segments):
                bm.faces.new((a[i], a[(i + 1) % segments], b[0]))
        else:
            for i in range(segments):
                j = (i + 1) % segments
                bm.faces.new((a[i], a[j], b[j], b[i]))
    return bm_to_mesh(bm, name, sharp)


def bez(p0, c, p1, n=8):
    """Quadratic Bezier samples from p0 (excluded) to p1 (included)."""
    out = []
    for i in range(1, n + 1):
        s = i / n
        out.append(((1 - s) ** 2 * p0[0] + 2 * (1 - s) * s * c[0] + s * s * p1[0],
                    (1 - s) ** 2 * p0[1] + 2 * (1 - s) * s * c[1] + s * s * p1[1]))
    return out


def tube(bm, path, radius, segments=16):
    """Sweep a circle along a polyline (mm points)."""
    rings = []
    prev_n = None
    for i, p in enumerate(path):
        t = (path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]).normalized()
        if prev_n is None:
            n = t.orthogonal().normalized()
        else:
            n = (prev_n - t * prev_n.dot(t)).normalized()
        prev_n = n
        b = t.cross(n)
        rings.append([bm.verts.new(p + (n * math.cos(2 * math.pi * k / segments)
                                         + b * math.sin(2 * math.pi * k / segments)) * radius)
                      for k in range(segments)])
    for a, c in zip(rings, rings[1:]):
        for k in range(segments):
            bm.faces.new((a[k], a[(k + 1) % segments], c[(k + 1) % segments], c[k]))
    bm.faces.new(list(reversed(rings[0])))
    bm.faces.new(rings[-1])


# ---------------------------------------------------------------------------------------------
# Parts that are not in the STL set
# ---------------------------------------------------------------------------------------------
SERVO_AXES = Matrix((radial(-30.0), -tangential(-30.0), -Z)).transposed()  # x_s, y_s, z_s in G
SERVO_ORIGIN = Vector((0.0, 0.0, 0.7))  # shaft face of an upside-down SG90 whose tabs sit on the plate


def servo_point(p):
    return SERVO_ORIGIN + SERVO_AXES @ Vector(p)


def build_servo(parent, mats):
    """SG90 (TowerPro) micro servo, mounted upside down in the plate pocket, shaft on the axis."""
    bm = bmesh.new()
    for lo, hi in (((-5.8, -5.9, -22.7), (16.4, 5.9, 0.0)),     # case
                   ((-10.8, -5.9, -6.8), (21.4, 5.9, -4.3)),    # mounting tabs (rest on the plate)
                   ((0.0, -5.9, 0.0), (7.0, 5.9, 4.0))):        # gear housing
        add_box(bm, lo, hi)
    add_cylinder(bm, (0, 0, 2.0), (0, 0, 1), 5.9, 4.0, 48)
    add_cylinder(bm, (7.6, 0, 1.1), (0, 0, 1), 2.8, 2.2, 32)
    add_cylinder(bm, (0, 0, 4.825), (0, 0, 1), 2.9, 1.65, 32)  # output boss, meets the wheel hub
    add_cylinder(bm, (0, 0, 7.4), (0, 0, 1), 2.35, 3.5, 24)    # spline
    bmesh.ops.transform(bm, matrix=Matrix.Translation(SERVO_ORIGIN) @ SERVO_AXES.to_4x4(), verts=bm.verts)
    case = new_object("Servo", bm_to_mesh(bm, "Servo"), parent, mats["servo"])
    bev = case.modifiers.new("Bevel", "BEVEL")
    bev.width, bev.segments, bev.limit_method, bev.angle_limit = 0.25 * MM, 2, "ANGLE", math.radians(40)

    bm = bmesh.new()  # tab screws (M2 pan head)
    for x in (-8.5, 19.1):
        add_cylinder(bm, servo_point((x, 0, -7.5)), Z, 1.9, 1.4, 24)
    new_object("Servo screws", bm_to_mesh(bm, "Servo screws"), parent, mats["steel"])

    for i, colour in enumerate(("wire_brown", "wire_red", "wire_orange")):  # lead up to the tool I/O
        y = (i - 1) * 1.05
        path = [servo_point(p) for p in ((15.8, y, -20.6), (18.6, y, -20.6), (20.6, y, -21.6),
                                          (21.7, y, -23.6), (22.0, y, -27.0), (21.7, y, -31.0),
                                          (20.6, y, -34.4), (19.0, y, -37.0))]
        dense = []
        for a, b in zip(path, path[1:]):
            dense += [a.lerp(b, s / 4) for s in range(4)]
        dense.append(path[-1])
        bm = bmesh.new()
        tube(bm, dense, 0.5, 10)
        new_object(f"Servo lead {i}", bm_to_mesh(bm, f"Servo lead {i}", 60), parent, mats[colour])


def build_hardware(parent, wheel, mats):
    bm = bmesh.new()  # claw pivot pins, Ø2.5 x 22 (drawn Ø2.4 so they do not touch the holes)
    for az in CLAW_AZ:
        add_cylinder(bm, radial(az) * PIVOT_R + Z * PIVOT_Z, tangential(az), 1.2, 22.0, 20)
    new_object("Pivot pins", bm_to_mesh(bm, "Pivot pins"), parent, mats["steel"])

    bm = bmesh.new()  # M5 socket heads under the mounting tabs
    for az in CLAW_AZ:
        add_cylinder(bm, radial(az) * MOUNT_R + Z * (MOUNT_Z - 3.0 - 2.5), Z, 4.2, 5.0, 32)
    new_object("Mount screws", bm_to_mesh(bm, "Mount screws"), parent, mats["black_oxide"])

    bm = bmesh.new()  # clevis pins through the pusher eyes, and the horn screw; ride on the wheel
    for az in (90.0, -30.0, 210.0):
        add_cylinder(bm, radial(az) * WHEEL_HOLE_R, Z, 1.2, 8.3, 20)
    add_cylinder(bm, (0, 0, -1.6), Z, 2.1, 1.2, 24)
    new_object("Wheel pins", bm_to_mesh(bm, "Wheel pins"), wheel, mats["steel"])

    bm = bmesh.new()  # tool flange of the UTRA 6-1000 and the start of its wrist housing
    add_cylinder(bm, (0, 0, MOUNT_Z + 3.0), Z, 43.0, 6.0, 96)
    new_object("Tool flange", bm_to_mesh(bm, "Tool flange"), parent, mats["aluminium"])
    bm = bmesh.new()
    add_cylinder(bm, (0, 0, MOUNT_Z + 7.0), Z, 43.4, 2.0, 96)
    new_object("Flange seal", bm_to_mesh(bm, "Flange seal"), parent, mats["black_oxide"])
    bm = bmesh.new()
    add_cylinder(bm, (0, 0, MOUNT_Z + 8.0 + 500.0), Z, 43.0, 1000.0, 96)
    new_object("Wrist", bm_to_mesh(bm, "Wrist"), parent, mats["housing"])


# ---------------------------------------------------------------------------------------------
# Chess set: Staunton pattern, 96 mm king. Turned pieces are lathe profiles [(r, h), ...] in mm.
# ---------------------------------------------------------------------------------------------
def ball(centre, rad, r_from, n=16):
    """Sphere profile from where it is r_from wide (below its centre) up to its top."""
    a0 = math.asin(min(r_from / rad, 1.0))
    out = []
    for i in range(1, n + 1):
        a = a0 + (math.pi - a0) * i / n
        out.append((max(0.0, rad * math.sin(a)), centre - rad * math.cos(a)))
    return out


def turned_base(r0, k_h):
    """The king's base scaled to a base radius r0 (heights by k_h). It ends on top of its bead."""
    p = [(0.0, 0.0), (18.9, 0.0), (19.6, 0.7), (19.6, 4.2)]
    p += bez((19.6, 4.2), (19.6, 5.0), (18.9, 5.25), 3)
    p += [(18.6, 5.7), (18.9, 6.1)]
    p += bez((18.9, 6.1), (19.5, 7.0), (18.8, 7.9), 4)
    p += bez((18.8, 7.9), (14.6, 8.9), (14.4, 15.0), 10)                 # base cove
    p += bez((14.4, 15.0), (15.4, 15.6), (15.3, 16.8), 4)
    p += bez((15.3, 16.8), (15.1, 17.7), (13.9, 17.9), 4)
    return [(r * r0 / 19.6, h * k_h) for r, h in p]


def king_profile():
    p = turned_base(19.6, 1.0)
    p += bez((13.9, 17.9), (10.0, 23.5), (KING_NECK_R, 46.0), 16)        # trumpet stem
    p += [(KING_NECK_R, KING_SKIRT_H0)]                                  # neck: the hooks close here
    p += bez((KING_NECK_R, KING_SKIRT_H0), (11.6, 56.3), (13.4, 58.4), 6)  # collar
    p += bez((13.4, 58.4), (13.95, 59.3), (13.3, 60.2), 4)
    p += bez((13.3, 60.2), (12.0, 60.6), (10.9, 61.3), 4)
    p += [(10.6, 61.7)]
    p += bez((10.6, 61.7), (11.7, 62.6), (10.7, 63.6), 5)                # bead
    p += bez((10.7, 63.6), (9.8, 64.2), (9.9, 65.2), 3)
    p += bez((9.9, 65.2), (10.3, 77.0), (13.3, 84.0), 14)                # crown
    p += bez((13.3, 84.0), (13.9, 85.0), (13.2, 86.0), 4)
    p += bez((13.2, 86.0), (11.0, 86.5), (8.9, 86.6), 4)
    p += [(8.6, 87.0), (8.2, 87.4)]
    p += bez((8.2, 87.4), (6.0, 88.3), (3.4, 88.4), 5)
    p += [(3.4, 89.7), (0.0, 89.7)]
    return p


def queen_profile():
    p = turned_base(18.6, 0.95)
    p += bez(p[-1], (9.3, 22.0), (8.3, 42.0), 16)
    p += [(8.1, 46.5)]
    p += bez((8.1, 46.5), (10.6, 46.8), (12.3, 48.6), 6)                 # collar
    p += bez((12.3, 48.6), (12.8, 49.4), (12.2, 50.2), 4)
    p += bez((12.2, 50.2), (10.9, 50.6), (9.9, 51.2), 4)
    p += [(9.6, 51.6)]
    p += bez((9.6, 51.6), (10.6, 52.4), (9.7, 53.3), 5)                  # bead
    p += bez((9.7, 53.3), (8.8, 53.9), (8.9, 54.9), 3)
    p += bez((8.9, 54.9), (9.3, 66.0), (12.4, 72.0), 14)                 # crown
    p += bez((12.4, 72.0), (12.95, 72.9), (12.2, 73.8), 4)               # coronet rim
    p += bez((12.2, 73.8), (9.0, 74.0), (6.0, 73.6), 4)
    p += bez((6.0, 73.6), (4.9, 73.7), (4.4, 75.4), 4)                   # dome
    p += [(3.0, 76.6), (2.5, 77.4)]
    return p + ball(80.6, 3.7, 2.5)


def bishop_profile():
    p = turned_base(16.6, 0.86)
    p += bez(p[-1], (8.2, 20.0), (6.6, 36.0), 14)
    p += [(6.4, 39.0)]
    p += bez((6.4, 39.0), (8.8, 39.3), (10.4, 41.0), 5)                  # collar
    p += bez((10.4, 41.0), (10.9, 41.8), (10.3, 42.6), 4)
    p += bez((10.3, 42.6), (8.8, 42.9), (7.7, 43.5), 4)
    p += bez((7.7, 43.5), (8.5, 44.3), (7.6, 45.1), 4)                   # bead
    p += [(6.2, 45.8)]
    p += bez((6.2, 45.8), (5.0, 47.0), (7.4, 50.0), 5)                   # mitre
    p += bez((7.4, 50.0), (9.9, 53.5), (9.4, 57.5), 8)
    p += bez((9.4, 57.5), (8.6, 62.5), (4.6, 65.4), 8)
    p += bez((4.6, 65.4), (2.6, 66.6), (1.9, 67.0), 3)
    return p + ball(69.3, 2.6, 1.9)


def rook_profile():
    p = turned_base(16.6, 0.86)
    p += bez(p[-1], (10.6, 17.0), (10.6, 20.0), 4)
    p += bez((10.6, 20.0), (9.6, 30.0), (9.4, 37.0), 8)                  # tower
    p += bez((9.4, 37.0), (11.8, 37.2), (12.6, 38.8), 5)                 # collar
    p += bez((12.6, 38.8), (12.9, 39.6), (12.2, 40.3), 3)
    p += bez((12.2, 40.3), (10.8, 40.6), (10.6, 41.4), 3)
    p += bez((10.6, 41.4), (11.0, 43.0), (12.6, 44.0), 4)                # turret
    p += [(12.8, 45.0), (12.8, 53.7)]
    p += bez((12.8, 53.7), (12.8, 54.5), (12.1, 54.5), 2)
    return p + [(9.8, 54.5), (9.8, 50.0), (0.0, 50.0)]


def knight_base_profile():
    p = turned_base(16.6, 0.86)
    p += bez(p[-1], (12.5, 16.2), (12.0, 17.0), 3)
    p += [(11.2, 17.4)]
    p += bez((11.2, 17.4), (11.5, 18.3), (10.6, 19.0), 3)
    return p + [(0.0, 19.0)]


def pawn_profile():
    p = [(0.0, 0.0), (14.2, 0.0), (14.8, 0.6), (14.8, 3.2)]
    p += bez((14.8, 3.2), (14.8, 3.9), (14.2, 4.1), 3)
    p += [(13.9, 4.5)]
    p += bez((13.9, 4.5), (14.4, 5.3), (13.6, 6.1), 4)
    p += bez((13.6, 6.1), (10.6, 7.0), (10.3, 11.0), 8)
    p += bez((10.3, 11.0), (11.0, 11.8), (10.3, 12.6), 4)
    p += bez((10.3, 12.6), (7.0, 17.0), (6.0, 29.8), 12)
    p += bez((6.0, 29.8), (9.7, 30.2), (9.7, 31.4), 4)
    p += bez((9.7, 31.4), (9.6, 32.5), (6.4, 32.9), 4)
    p += [(5.6, 33.8)]
    return p + ball(41.6, 8.2, 5.6, 24)


# The knight's head: a side profile (x forward, z up) with a thickness and rounded edges, as a
# signed distance field (mm). The ears are split and the eyes, nostrils and mane carved, then the
# field is meshed with surface nets.
KNIGHT_OUTLINE = [
    (-8.0, 13.0), (-10.2, 22.0), (-11.6, 28.5), (-12.4, 35.0), (-12.3, 41.0), (-11.4, 46.5),
    (-9.7, 51.5), (-7.4, 55.5), (-5.2, 58.5), (-4.4, 61.5), (-3.2, 65.0), (-1.4, 62.0),
    (-0.6, 60.5), (1.2, 60.0), (4.6, 58.4), (8.6, 55.6), (12.6, 52.2), (16.2, 48.4),
    (19.2, 44.6), (21.2, 41.0), (22.0, 38.0), (21.6, 35.6), (20.2, 34.0), (18.4, 34.4),
    (17.2, 35.6), (16.4, 34.6), (14.8, 33.4), (12.2, 32.8), (9.2, 32.6), (6.4, 31.6),
    (4.6, 29.4), (4.0, 26.4), (4.5, 23.0), (5.6, 20.0), (5.8, 13.0),
]
KNIGHT_EYE, KNIGHT_NOSTRIL = (4.8, 51.0), (19.6, 37.8)


def smoothstep(e0, e1, v):
    s = np.clip((v - e0) / (e1 - e0), 0.0, 1.0)
    return s * s * (3.0 - 2.0 * s)


def knight_thickness(x, z):
    t = 13.8 * (1.0 + 0.12 * (1.0 - smoothstep(18.0, 28.0, z)))          # the neck flares into the base
    t = t * (1.0 - 0.38 * smoothstep(10.0, 22.0, x))                     # narrow muzzle
    t = t * (1.0 + 0.10 * np.exp(-((x - 7.0) ** 2 + (z - 43.0) ** 2) / 72.0))  # cheeks
    t = t * (1.0 - 0.3 * smoothstep(57.0, 63.0, z) * (1.0 - smoothstep(2.0, 6.0, x)))  # ears
    return t * (1.0 - 0.18 * smoothstep(-8.0, -12.0, x))                 # mane ridge


def polygon_distance(poly, x, z):
    """Signed distance from points (x, z) to a closed polygon, positive inside (mm)."""
    p = np.stack([x, z], axis=-1)
    dist = np.full(x.shape, np.inf)
    inside = np.zeros(x.shape, dtype=bool)
    for (ax, az), (bx, bz) in zip(poly, np.roll(poly, -1, axis=0)):
        e = np.array([bx - ax, bz - az])
        w = p - np.array([ax, az])
        t = np.clip((w @ e) / (e @ e), 0.0, 1.0)
        dist = np.minimum(dist, np.hypot(w[..., 0] - t * e[0], w[..., 1] - t * e[1]))
        x_at = ax + (z - az) * (bx - ax) / (bz - az if bz != az else 1.0)
        inside ^= ((az > z) != (bz > z)) & (x < x_at)
    return np.where(inside, dist, -dist)


def smin(a, b, k):
    """Smooth minimum (blend radius k) of two distance fields."""
    h = np.clip(0.5 + 0.5 * (b - a) / k, 0.0, 1.0)
    return b + (a - b) * h - k * h * (1.0 - h)


def surface_nets(sdf, origin, step):
    """Quad mesh of the zero level set of a sampled distance field: vertices (mm) and faces."""
    inside = sdf < 0.0
    n = sdf.shape
    count = np.zeros((n[0] - 1, n[1] - 1, n[2] - 1), dtype=np.int8)
    for i in (0, 1):
        for j in (0, 1):
            for k in (0, 1):
                count += inside[i:n[0] - 1 + i, j:n[1] - 1 + j, k:n[2] - 1 + k]
    active = (count > 0) & (count < 8)
    cells = np.argwhere(active)
    index = np.full(active.shape, -1, dtype=np.int64)
    index[active] = np.arange(len(cells))
    # each cell's vertex sits at the mean of the surface crossings on its twelve edges
    acc, hits = np.zeros((len(cells), 3)), np.zeros(len(cells))
    for axis in range(3):
        d = np.eye(3, dtype=np.int64)[axis]
        b, c = (axis + 1) % 3, (axis + 2) % 3
        for u in (0, 1):
            for v in (0, 1):
                off = np.zeros(3, dtype=np.int64)
                off[b], off[c] = u, v
                p0, p1 = cells + off, cells + off + d
                s0, s1 = sdf[p0[:, 0], p0[:, 1], p0[:, 2]], sdf[p1[:, 0], p1[:, 1], p1[:, 2]]
                m = (s0 < 0.0) != (s1 < 0.0)
                t = s0[m] / (s0[m] - s1[m])
                acc[m] += off + t[:, None] * d
                hits[m] += 1.0
    verts = np.asarray(origin, dtype=float) + (cells + acc / hits[:, None]) * step
    # a quad round every grid edge the surface crosses, from the four cells that share the edge
    quads = []
    for axis in range(3):
        b, c = (axis + 1) % 3, (axis + 2) % 3
        lo, hi = [slice(None)] * 3, [slice(None)] * 3
        lo[axis], hi[axis] = slice(0, -1), slice(1, None)
        e = np.argwhere(inside[tuple(lo)] != inside[tuple(hi)])
        e = e[(e[:, b] >= 1) & (e[:, b] <= n[b] - 2) & (e[:, c] >= 1) & (e[:, c] <= n[c] - 2)]

        def cell(db, dc):
            q = e.copy()
            q[:, b] += db
            q[:, c] += dc
            return index[q[:, 0], q[:, 1], q[:, 2]]
        quad = np.stack([cell(-1, -1), cell(0, -1), cell(0, 0), cell(-1, 0)], axis=1)
        outward = inside[e[:, 0], e[:, 1], e[:, 2]]  # inside at the low end: the quad faces +axis
        quad[~outward] = quad[~outward, ::-1]
        quads.append(quad)
    return verts, np.concatenate(quads)


def knight_head(step=0.3):
    """Mesh (metres) of the knight's head from its distance field, sampled every `step` mm."""
    outline = np.array(KNIGHT_OUTLINE)
    for _ in range(2):  # Chaikin corner cutting rounds the outline off
        nxt = np.roll(outline, -1, axis=0)
        outline = np.stack([0.75 * outline + 0.25 * nxt, 0.25 * outline + 0.75 * nxt], axis=1).reshape(-1, 2)
    xs = np.arange(-15.0, 25.0, step)
    ys = step * np.arange(-math.ceil(10.0 / step), math.ceil(10.0 / step) + 1)
    zs = np.arange(10.0, 68.0, step)
    X2, Z2 = np.meshgrid(xs, zs, indexing="ij")
    X, Y, Z3 = X2[:, None, :], np.abs(ys)[None, :, None], Z2[:, None, :]
    h = (knight_thickness(X2, Z2) / 2.0)[:, None, :]
    r = 0.8 * h  # edge rounding: nearly round, with a little flat on the cheeks

    def rounded(d, y, h, r):
        """Distance to the profile extruded to half-thickness h, its edges rounded with radius r."""
        w1, w2 = r - d, y - h + r
        return np.minimum(np.maximum(w1, w2), 0.0) + np.hypot(np.maximum(w1, 0.0), np.maximum(w2, 0.0)) - r

    def cheek_y(x, z):
        """Where the surface is at (x, z): its half-thickness."""
        d = float(polygon_distance(outline, np.array([x]), np.array([z]))[0])
        hh = float(knight_thickness(x, z)) / 2.0
        rr = 0.8 * hh
        return hh - rr + math.sqrt(max(rr * rr - (rr - min(d, rr)) ** 2, 0.0))

    sdf = rounded(polygon_distance(outline, X2, Z2)[:, None, :], Y, h, r)
    ex, ez = KNIGHT_EYE  # eyes: a smooth bump on each cheek
    sdf = smin(sdf, np.sqrt((X - ex) ** 2 + (Y - cheek_y(ex, ez) + 0.8) ** 2 + (Z3 - ez) ** 2) - 1.9, 0.9)
    nx_, nz_ = KNIGHT_NOSTRIL  # nostrils: a dimple each side of the muzzle
    sdf = -smin(-sdf, np.sqrt((X - nx_) ** 2 + (Y - cheek_y(nx_, nz_) - 0.5) ** 2 + (Z3 - nz_) ** 2) - 1.3, 0.4)
    # the ears: a V-shaped gap between them
    gap = np.maximum(np.maximum(Y - (0.25 + 0.22 * (Z3 - 59.0)), 59.0 - Z3), X - 1.5)
    sdf = np.maximum(sdf, -gap)
    # the mane: shallow grooves across the back of the neck
    mane = smoothstep(-7.0, -10.5, X) * smoothstep(20.0, 25.0, Z3) * (1.0 - smoothstep(51.0, 56.0, Z3))
    sdf = sdf + 0.5 * mane * (0.5 + 0.5 * np.cos(2.0 * np.pi * (Z3 - 0.55 * X) / 3.4)) ** 6

    verts, faces = surface_nets(sdf, (xs[0], ys[0], zs[0]), step)
    me = bpy.data.meshes.new("Knight head")
    me.from_pydata((verts * MM).tolist(), [], faces.tolist())
    me.validate()

    def soften(ob):
        sm = ob.modifiers.new("Smooth", "SMOOTH")
        sm.factor, sm.iterations = 0.5, 3
    me = bake_modifiers(me, soften)
    me.shade_smooth()
    return me


def join_meshes(name, meshes):
    bm = bmesh.new()
    for me in meshes:
        bm.from_mesh(me)
        bpy.data.meshes.remove(me)
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out)
    bm.free()
    return out


def bake_modifiers(me, setup):
    """Apply modifiers to a mesh: setup(ob) adds them and returns any helper objects to delete."""
    ob = bpy.data.objects.new("_bake", me)
    bpy.context.scene.collection.objects.link(ob)
    helpers = setup(ob) or []
    out = bpy.data.meshes.new_from_object(ob.evaluated_get(bpy.context.evaluated_depsgraph_get()))
    out.name = me.name
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    for h in helpers:
        data = h.data
        bpy.data.objects.remove(h)
        bpy.data.meshes.remove(data)
    return out


def carve(me, cutter):
    """Boolean difference of two meshes (both in metres)."""
    def setup(ob):
        c = bpy.data.objects.new("_cutter", cutter)
        bpy.context.scene.collection.objects.link(c)
        mod = ob.modifiers.new("Carve", "BOOLEAN")
        mod.operation, mod.solver, mod.object = "DIFFERENCE", "EXACT", c
        return [c]
    out = bake_modifiers(me, setup)
    smooth(out, 38.0)
    return out


def king_mesh():
    bm = bmesh.new()
    add_box(bm, (-1.5, -1.4, 89.5), (1.5, 1.4, 96.0))
    add_box(bm, (-4.0, -1.4, 92.0), (4.0, 1.4, 94.4))

    def bevel(ob):
        mod = ob.modifiers.new("Bevel", "BEVEL")
        mod.width, mod.segments = 0.35 * MM, 2
    return join_meshes("King", [lathe("King body", king_profile()),
                                bake_modifiers(bm_to_mesh(bm, "King cross"), bevel)])


def queen_mesh():
    bm = bmesh.new()  # the coronet's eight points
    for k in range(8):
        a = 2.0 * math.pi * (k + 0.5) / 8
        bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=1.9,
                                  matrix=Matrix.Translation((11.1 * math.cos(a), 11.1 * math.sin(a), 74.3)))
    return join_meshes("Queen", [lathe("Queen body", queen_profile()), bm_to_mesh(bm, "Coronet", 60)])


def bishop_mesh():
    bm = bmesh.new()  # the mitre's slit: a saw cut across the head, sloping up to the front
    add_box(bm, (-12.0, -1.0, -0.85), (12.0, 14.0, 0.85))
    bmesh.ops.transform(bm, matrix=Matrix.Translation((0.0, 0.0, 57.0)) @ Matrix.Rotation(math.radians(38), 4, "X"),
                        verts=bm.verts)
    return carve(lathe("Bishop", bishop_profile()), bm_to_mesh(bm, "Slit"))


def rook_mesh():
    bm = bmesh.new()  # five crenels
    for k in range(5):
        bmesh.ops.create_cube(bm, size=1.0, matrix=Matrix.Rotation(2.0 * math.pi * k / 5, 4, "Z")
                              @ Matrix.LocRotScale(Vector((11.5, 0.0, 54.0)), None, Vector((8.0, 4.4, 6.0))))
    return carve(lathe("Rook", rook_profile()), bm_to_mesh(bm, "Crenels"))


def knight_mesh():
    return join_meshes("Knight", [lathe("Knight base", knight_base_profile()), knight_head()])


def build_chess_set(mats):
    """The pieces of POSITION. Returns the king that gets moved, and every other piece."""
    coll = bpy.data.collections.new("Chess set")
    bpy.context.scene.collection.children.link(coll)
    meshes = {"p": lathe("Pawn", pawn_profile()), "r": rook_mesh(), "n": knight_mesh(),
              "b": bishop_mesh(), "q": queen_mesh(), "k": king_mesh()}
    names = dict(p="pawn", r="rook", n="knight", b="bishop", q="queen", k="king")
    rng = random.Random(6)  # pieces sit a little off-centre, turned any which way, as in a real game
    moved, others = None, []

    def place(code, label, xy, z=0.0):
        white = code.isupper()
        ob = new_object(f"{'White' if white else 'Black'} {names[code.lower()]} {label}",
                        meshes[code.lower()], None, None, coll)
        _link_object_material(ob, mats["boxwood" if white else "ebony"])
        ob.location = Vector((xy[0], xy[1], z)) * MM
        if code.lower() == "n":  # knights look at the other side
            ob.rotation_euler.z = math.radians((90.0 if white else -90.0) + rng.uniform(-18.0, 18.0))
        elif code.lower() == "k":  # crosses face the players
            ob.rotation_euler.z = math.radians(rng.uniform(-6.0, 6.0))
        else:
            ob.rotation_euler.z = rng.uniform(0.0, 2.0 * math.pi)
        return ob

    for rank, row in zip(range(8, 0, -1), POSITION.split("/")):
        f = 0
        for code in row:
            if code.isdigit():
                f += int(code)
                continue
            sq = "abcdefgh"[f] + str(rank)
            f += 1
            if sq == GRIP_SQUARE:
                moved = place(code, sq, square_xy(sq))
                moved.rotation_euler.z = 0.0
                continue
            jitter = Vector((rng.uniform(-1.2, 1.2), rng.uniform(-1.2, 1.2), 0.0))
            others.append(place(code, sq, square_xy(sq) + jitter))
    for code, xy in CAPTURED:
        others.append(place(code, "(captured)", xy, z=-20.0))
    return moved, others


def build_board(mats):
    tiles = bpy.data.collections.new("Board")
    bpy.context.scene.collection.children.link(tiles)
    for i in range(8):
        for j in range(8):
            light = (i + j) % 2 == 1
            bm = bmesh.new()
            add_box(bm, (-27.4, -27.4, -3.0), (27.4, 27.4, 0.0))
            ob = new_object(f"Square {'abcdefgh'[i]}{j + 1}", bm_to_mesh(bm, "Square"), None,
                            mats["maple" if light else "walnut"], tiles)
            ob.location = Vector(((i - 4) * SQUARE, j * SQUARE, 0.0)) * MM
            ob.rotation_euler.z = math.radians(90.0 * ((i * 3 + j * 5) % 2))
            bev = ob.modifiers.new("Bevel", "BEVEL")
            bev.width, bev.segments = 0.3 * MM, 2
    bm = bmesh.new()
    add_box(bm, (-4.5 * SQUARE - 32, -0.5 * SQUARE - 32, -20.0), (3.5 * SQUARE + 32, 7.5 * SQUARE + 32, -0.4))
    frame = new_object("Board frame", bm_to_mesh(bm, "Board frame"), None, mats["walnut"], tiles)
    bev = frame.modifiers.new("Bevel", "BEVEL")
    bev.width, bev.segments = 1.5 * MM, 3
    # studio cyclorama all round (the shots look from every side): a floor that sweeps up into a
    # wall. Only the camera sees it; the pieces are still lit and reflect the studio HDRI as if it
    # were open.
    profile = [(0.0, -20.0), (1050.0, -20.0)]
    for i in range(1, 17):
        a = math.pi / 2 * i / 16
        profile.append((1050.0 + 450.0 * math.sin(a), -20.0 + 450.0 * (1 - math.cos(a))))
    profile.append((1500.0, 3000.0))
    cyc = new_object("Cyclorama", lathe("Cyclorama", profile, segments=180, sharp=80.0), None, mats["table"], tiles)
    cyc.location = Vector((0.0, 120.0, 0.0)) * MM
    cyc.visible_diffuse = cyc.visible_glossy = cyc.visible_transmission = cyc.visible_shadow = False


# ---------------------------------------------------------------------------------------------
# The broccoli band. While the claws are open it rides up them into the valley where the angled
# faces of the base's forks meet the claws, and friction keeps it there. Each fibre of the band
# takes the shortest way round the parts at its own height, so at any claw angle the band is the
# convex hull of the parts' cross-sections, row by row across its width, grown by the gap and its
# thickness. Stored as absolute shape keys (one per BAND_ALPHAS step); it thins as it stretches.
# ---------------------------------------------------------------------------------------------
def mesh_triangles(me):
    """Triangles of a mesh (stored in metres) as an (n, 3, 3) array in mm."""
    me.calc_loop_triangles()
    co = np.empty(len(me.vertices) * 3, dtype=np.float32)
    me.vertices.foreach_get("co", co)
    idx = np.empty(len(me.loop_triangles) * 3, dtype=np.int32)
    me.loop_triangles.foreach_get("vertices", idx)
    return co.reshape(-1, 3).astype(np.float64)[idx.reshape(-1, 3)] / MM


def section_points(tris, z):
    """Points where the triangles' edges cross height z: (n, 2) array."""
    dz = tris[:, :, 2] - z
    out = [np.zeros((0, 2))]
    for i, j in ((0, 1), (1, 2), (2, 0)):
        m = dz[:, i] * dz[:, j] < 0.0
        s = (dz[m, i] / (dz[m, i] - dz[m, j]))[:, None]
        out.append(tris[m, i, :2] + (tris[m, j, :2] - tris[m, i, :2]) * s)
    return np.concatenate(out)


def convex_hull(pts):
    """Counter-clockwise convex hull of (n, 2) points round the axis (monotone chain)."""
    r = np.hypot(pts[:, 0], pts[:, 1])
    pts = [tuple(p) for p in np.unique(pts[r > 0.5 * r.max()].round(6), axis=0)]

    def chain(points):
        h = []
        for p in points:
            while len(h) > 1 and ((h[-1][0] - h[-2][0]) * (p[1] - h[-2][1])
                                  - (h[-1][1] - h[-2][1]) * (p[0] - h[-2][0])) <= 1e-12:
                h.pop()
            h.append(p)
        return h

    return np.array(chain(pts)[:-1] + chain(pts[::-1])[:-1])


def hull_length(hull):
    return float(np.hypot(*(np.roll(hull, -1, axis=0) - hull).T).sum())


def radial_offset(hull, d, phis):
    """Distance from the axis to the hull grown by d (rounded corners), along each angle in phis."""
    e = np.roll(hull, -1, axis=0) - hull
    n = np.stack([e[:, 1], -e[:, 0]], axis=1) / np.hypot(e[:, 0], e[:, 1])[:, None]  # outward normals
    starts = np.empty((2 * len(hull), 2))
    starts[0::2] = hull + d * np.roll(n, 1, axis=0)  # the arc round vertex i starts here ...
    starts[1::2] = hull + d * n                      # ... and the offset edge i here
    ang = np.unwrap(np.arctan2(starts[:, 1], starts[:, 0]))
    k = np.searchsorted(ang, ang[0] + np.mod(phis - ang[0], 2.0 * math.pi), side="right") - 1
    i = k // 2
    u = np.stack([np.cos(phis), np.sin(phis)], axis=1)
    uv = (u * hull[i]).sum(axis=1)
    on_arc = uv + np.sqrt(np.maximum(uv * uv - (hull[i] ** 2).sum(axis=1) + d * d, 0.0))
    on_edge = ((hull[i] * n[i]).sum(axis=1) + d) / (u * n[i]).sum(axis=1)
    return np.where(k % 2 == 0, on_arc, on_edge)


class BandModel:
    """Shape of the band (mm, frame G) at any claw angle."""

    def __init__(self, static_tris, claw_tris):
        zt = static_tris[:, :, 2]
        self.static = static_tris[(zt.max(axis=1) > -10.0) & (zt.min(axis=1) < 32.0)]
        self.claw = claw_tris[claw_tris[:, :, 1].min(axis=1) > -45.0]  # the claw's top, round the pivot
        self.phis = np.linspace(0.0, 2.0 * math.pi, BAND_SAMPLES, endpoint=False)
        self.z_mid, self.profile = None, None

    def tris(self, alpha):
        out = [self.static]
        for az in CLAW_AZ:
            rot, loc = claw_frame(az, alpha)
            out.append(self.claw @ np.array(rot).T + np.array(loc))
        return np.concatenate(out)

    @staticmethod
    def hull(tris, z):
        return convex_hull(section_points(tris, z + 1.234e-7))

    @staticmethod
    def rows(z_mid, w):
        return z_mid + w * (np.arange(BAND_ROWS) / (BAND_ROWS - 1) - 0.5)

    def fibre_lengths(self, alpha, zs):
        """Length of the band's centre fibre at each height in zs (mm)."""
        tris = self.tris(alpha)
        extra = 2.0 * math.pi * (BAND_GAP + BAND_T0 / math.sqrt(1.6) / 2.0)
        return np.array([hull_length(self.hull(tris, z)) + extra for z in zs])

    def settle(self, alpha):
        """Band height (its centre) with the least stretch energy at claw angle alpha."""
        zs = np.arange(-8.0, 30.0, 0.1)
        length = self.fibre_lengths(alpha, zs)
        best = None
        for z_mid in np.arange(-1.0, 23.0, 0.05):
            s = 1.6
            for _ in range(3):
                lk = np.interp(self.rows(z_mid, BAND_W0 / math.sqrt(s)), zs, length)
                s = float(lk.mean()) / BAND_REST
            energy = float(((lk / BAND_REST - 1.0) ** 2).sum())
            if best is None or energy < best[0]:
                best = (energy, float(z_mid))
        self.z_mid, self.profile = best[1], (zs, length)
        return self.z_mid

    def solve(self, alpha):
        """Rows across the band as (z, inner radii, outer radii) by angle, plus stretch, width, thickness."""
        tris = self.tris(alpha)
        s = 1.6
        for _ in range(4):
            w, t = BAND_W0 / math.sqrt(s), BAND_T0 / math.sqrt(s)
            hulls = [(z, self.hull(tris, z)) for z in self.rows(self.z_mid, w)]
            s = (np.mean([hull_length(h) for _, h in hulls]) + 2.0 * math.pi * (BAND_GAP + t / 2.0)) / BAND_REST
        rows = [(z, radial_offset(h, BAND_GAP, self.phis), radial_offset(h, BAND_GAP + t, self.phis))
                for z, h in hulls]
        return rows, float(s), w, t

    def vertices(self, alpha):
        """(rows x samples x [inner, outer]) vertices in mm, flattened, plus stretch, width, thickness."""
        rows, s, w, t = self.solve(alpha)
        out = np.empty((BAND_ROWS, BAND_SAMPLES, 2, 3))
        for k, (z, r_in, r_out) in enumerate(rows):
            for side, r in enumerate((r_in, r_out)):
                out[k, :, side, 0] = r * np.cos(self.phis)
                out[k, :, side, 1] = r * np.sin(self.phis)
                out[k, :, side, 2] = z
        return out.reshape(-1, 3), s, w, t


def build_band(parent, model, mat):
    n_r, n_a = BAND_ROWS, BAND_SAMPLES
    verts0, *_ = model.vertices(BAND_ALPHAS[0])

    def vid(k, j, side):
        return (k * n_a + j % n_a) * 2 + side

    bm = bmesh.new()
    vs = [bm.verts.new(v * MM) for v in verts0]
    for j in range(n_a):
        for k in range(n_r - 1):
            for side in (0, 1):
                bm.faces.new([vs[vid(k, j, side)], vs[vid(k, j + 1, side)],
                              vs[vid(k + 1, j + 1, side)], vs[vid(k + 1, j, side)]])
        for k in (0, n_r - 1):  # bottom and top edges
            bm.faces.new([vs[vid(k, j, 0)], vs[vid(k, j + 1, 0)], vs[vid(k, j + 1, 1)], vs[vid(k, j, 1)]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("Broccoli band")
    bm.to_mesh(me)
    bm.free()
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(40))
    ob = new_object("Broccoli band", me, parent, mat)
    ob.shape_key_add(name="Basis")
    for a in BAND_ALPHAS[1:]:
        kb = ob.shape_key_add(name=f"claws {a:+.1f} deg", from_mix=False)
        verts, *_ = model.vertices(a)
        kb.data.foreach_set("co", (verts * MM).astype(np.float32).ravel())
    me.shape_keys.use_relative = False
    for kb in me.shape_keys.key_blocks:
        kb.interpolation = "KEY_LINEAR"
    bev = ob.modifiers.new("Bevel", "BEVEL")
    bev.width, bev.segments, bev.limit_method = 0.12 * MM, 2, "ANGLE"
    bev.angle_limit = math.radians(40)
    return ob


def band_eval_time(alpha, band):
    """Absolute shape keys sit at frames 0, 10, 20 ... (checked at build time)."""
    pos = (min(max(alpha, BAND_ALPHAS[0]), BAND_ALPHAS[-1]) - BAND_ALPHAS[0]) / (BAND_ALPHAS[1] - BAND_ALPHAS[0])
    lo = int(min(pos, len(BAND_ALPHAS) - 2))
    kbs = band.data.shape_keys.key_blocks
    return kbs[lo].frame + (kbs[lo + 1].frame - kbs[lo].frame) * (pos - lo)


# ---------------------------------------------------------------------------------------------
# Timeline (30 fps). One input - the servo angle theta - plus the robot moving the tool.
# ---------------------------------------------------------------------------------------------
FPS = 30
THETA_CLOSED, THETA_OPEN = 180.0, 82.0      # pusher eye angle behind its claw (deg); 98 deg of servo travel
HOVER, LIFT = 60.0, 50.0                    # tool heights above the grip pose (mm)
# The action, timed for the edit below: two beauty shots before anything moves, and a slow grip.
PH = {"open": (118, 176), "descend": (190, 244), "close": (256, 326), "lift": (344, 380),
      "move": (384, 420), "lower": (432, 468), "release": (478, 512), "rise": (528, 566),
      "relax": (572, 604)}
FRAME_END = 630


def ease(s):
    s = min(max(s, 0.0), 1.0)
    return s * s * s * (s * (6.0 * s - 15.0) + 10.0)


def segment(f, phase, a, b):
    lo, hi = PH[phase]
    return a + (b - a) * ease((f - lo) / (hi - lo))


def servo_theta(f):
    if f < PH["close"][0]:
        return segment(f, "open", THETA_CLOSED, THETA_OPEN)
    if f < PH["release"][0]:
        return segment(f, "close", THETA_OPEN, THETA_CLOSED)
    if f < PH["relax"][0]:
        return segment(f, "release", THETA_CLOSED, THETA_OPEN)
    return segment(f, "relax", THETA_OPEN, THETA_CLOSED)


def tool_offset(f):
    """Tool position relative to the grip pose over the king (mm)."""
    if f < PH["lift"][0]:
        return Vector((0.0, 0.0, segment(f, "descend", HOVER, 0.0)))
    if f < PH["move"][0]:
        return Vector((0.0, 0.0, segment(f, "lift", 0.0, LIFT)))
    if f < PH["lower"][0]:
        return MOVE * ease((f - PH["move"][0]) / (PH["move"][1] - PH["move"][0])) + Vector((0.0, 0.0, LIFT))
    if f < PH["rise"][0]:
        return MOVE + Vector((0.0, 0.0, segment(f, "lower", LIFT, 0.0)))
    return MOVE + Vector((0.0, 0.0, segment(f, "rise", 0.0, HOVER)))


def king_between_claws(f):
    return PH["descend"][1] <= f < PH["rise"][0]


def claw_alpha(f):
    a_push = alpha_push(servo_theta(f))
    stop = ALPHA_STEM if king_between_claws(f) else ALPHA_PLATE
    # the band holds each claw against whichever is further out: its pusher or the piece
    return a_push + 0.03 if a_push > stop else stop


def grip_frames():
    """First frame the hooks land on the neck, and first frame the pushers lift them off again."""
    land = next(f for f in range(PH["close"][0], PH["close"][1] + 1) if alpha_push(servo_theta(f)) <= ALPHA_STEM)
    free = next(f for f in range(PH["release"][0], PH["release"][1] + 1) if alpha_push(servo_theta(f)) > ALPHA_STEM)
    return land, free


# ---------------------------------------------------------------------------------------------
# The edit: hard cuts between nine shots, as in a product film. Each shot is one slow, steady move
# (a push-in, a slide or a crane): the point the camera looks at and the camera itself both travel in
# straight lines. The camera is given as (azimuth, elevation (deg), distance (mm)) from that point,
# at the shot's first and last frame. Points are in mm: "world" ones are on the board (e1 is the
# origin); "tool" ones are relative to where the tool is at the shot's first frame, and then follow
# it by the factors in `follow` (point, camera). `dof` is the depth of field at the point (mm).
# The claws are at azimuths 0, 120 and 240 deg, so 300 deg looks in between two of them.
# ---------------------------------------------------------------------------------------------
Shot = namedtuple("Shot", "name first last anchor aim view lens dof ease follow")
SHOTS = [
    Shot("Hero", 1, 60, "world", ((-10.0, 70.0, 110.0), (-10.0, 60.0, 115.0)),
         ((-124.0, 17.0, 900.0), (-121.0, 14.0, 770.0)), (45.0, 45.0), (400.0, 400.0), "linear", (0.0, 0.0)),
    Shot("Band", 61, 114, "tool", ((-21.0, -18.5, 9.7), (-5.5, -27.5, 9.7)),
         ((252.0, 6.0, 115.0), (252.0, 6.0, 115.0)), (70.0, 70.0), (12.0, 12.0), "linear", (1.0, 1.0)),
    Shot("Mechanism", 115, 186, "tool", ((0.0, 0.0, -16.0), (0.0, 0.0, -19.0)),
         ((300.0, -20.0, 205.0), (300.0, -14.0, 175.0)), (40.0, 40.0), (70.0, 70.0), "linear", (1.0, 1.0)),
    Shot("Descend", 187, 250, "tool", ((0.0, 0.0, -40.0), (0.0, 0.0, -40.0)),
         ((-82.0, 32.0, 470.0), (-78.0, 30.0, 420.0)), (50.0, 50.0), (130.0, 130.0), "linear", (1.0, 0.5)),
    Shot("Close", 251, 290, "world", ((0.0, 0.0, 100.0), (0.0, 0.0, 97.0)),
         ((-60.0, 6.0, 330.0), (-60.0, 5.0, 305.0)), (50.0, 50.0), (70.0, 70.0), "linear", (0.0, 0.0)),
    Shot("Hooks", 291, 343, "world", ((0.0, 0.0, 64.0), (0.0, 0.0, 62.0)),
         ((-63.0, 4.0, 270.0), (-58.0, 3.0, 236.0)), (70.0, 70.0), (40.0, 40.0), "linear", (0.0, 0.0)),
    Shot("Carry", 344, 428, "tool", ((0.0, 0.0, -45.0), (0.0, 0.0, -45.0)),
         ((-100.0, 22.0, 450.0), (-92.0, 26.0, 430.0)), (45.0, 45.0), (130.0, 130.0), "linear", (1.0, 0.55)),
    Shot("Set down", 429, 524, "world", ((55.0, 0.0, 90.0), (55.0, 0.0, 84.0)),
         ((-45.0, 4.0, 340.0), (-50.0, 3.0, 300.0)), (50.0, 50.0), (60.0, 60.0), "linear", (0.0, 0.0)),
    Shot("Hero end", 525, FRAME_END, "world", ((55.0, 10.0, 105.0), (40.0, 60.0, 120.0)),
         ((-95.0, 14.0, 400.0), (-100.0, 22.0, 620.0)), (45.0, 40.0), (160.0, 250.0), "out", (0.0, 0.0)),
]


def shot_at(f):
    return next((s for s in SHOTS if s.first <= f <= s.last), SHOTS[0] if f < SHOTS[0].first else SHOTS[-1])


def tool_position(f):
    """Where the tool (frame G's origin) is at frame f, in the world (mm)."""
    return square_xy(GRIP_SQUARE) + tool_offset(f) + Vector((0.0, 0.0, -king_base_in_tool()))


def spherical(az, el, d):
    a, e = math.radians(az), math.radians(el)
    return Vector((math.cos(e) * math.cos(a), math.cos(e) * math.sin(a), math.sin(e))) * d


def shot_camera(s, f):
    """Camera position and the point it looks at (mm, world), lens (mm) and f-stop for shot s at frame f.

    Frames just outside the shot continue its move, so motion blur at a cut never smears two shots.
    """
    u = (f - s.first) / (s.last - s.first)
    if s.ease == "out":  # slows to a stop at the end
        u = 1.0 - (1.0 - min(u, 1.0)) ** 2

    def mix(a, b):
        return a + (b - a) * u

    aims = [Vector(p) for p in s.aim]
    cams = [aims[i] + spherical(*s.view[i]) for i in (0, 1)]
    aim, cam = mix(*aims), mix(*cams)
    if s.anchor == "tool":
        t0 = tool_position(s.first)
        moved = tool_position(f) - t0
        aim += t0 + moved * s.follow[0]
        cam += t0 + moved * s.follow[1]
    lens, dof = mix(*s.lens), mix(*s.dof)
    d = (aim - cam).length
    return cam, aim, lens, min(max(dof * lens * lens / (2.0 * 0.03 * d * d), 2.0), 128.0)  # 0.03 mm CoC


# ---------------------------------------------------------------------------------------------
# Scene
# ---------------------------------------------------------------------------------------------
def make_materials():
    mats = {
        "printed": principled("Black PETG", "#1f2125", roughness=0.55, bump=0.06, bump_scale=2500.0),
        "servo": principled("SG90 case", "#2459d8", roughness=0.32, coat=0.2),
        "steel": principled("Stainless steel", "#cfd3d8", metallic=1.0, roughness=0.24),
        "black_oxide": principled("Black-oxide steel", "#1d1e20", metallic=0.8, roughness=0.35),
        "aluminium": principled("Anodised aluminium", "#7d828a", metallic=1.0, roughness=0.42),
        "housing": principled("Arm housing", "#e4e5e3", roughness=0.38, coat=0.3),
        "wire_brown": principled("Lead brown", "#5b3a24", roughness=0.45),
        "wire_red": principled("Lead red", "#b8231d", roughness=0.45),
        "wire_orange": principled("Lead orange", "#e48a1a", roughness=0.45),
        "band": principled("Broccoli band", "#2f9b45", roughness=0.62, sheen=0.25),
        # turned boxwood and ebonised boxwood, lacquered; the grain runs along each piece's axis
        "boxwood": wood("Boxwood", "#d2ad73", "#ecd4a4", grain_scale=(40.0, 40.0, 1.5), coat=0.45, roughness=0.36),
        "ebony": wood("Ebonised boxwood", "#0f0b09", "#2a1f18", grain_scale=(40.0, 40.0, 1.5), coat=0.45,
                      roughness=0.34),
        "maple": wood("Maple", "#c39a68", "#e6cb9c"),
        "walnut": wood("Walnut", "#3b2415", "#6e4a30"),
        "table": principled("Studio cyclorama", "#77736e", roughness=1.0),
    }
    mats["table"].node_tree.nodes["Principled BSDF"].inputs["Specular IOR Level"].default_value = 0.15
    return mats


def reset_scene():
    scene = bpy.context.scene
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in list(bpy.data.collections):
        bpy.data.collections.remove(coll)
    return scene


def build(scene, mats):
    root = bpy.data.objects.new("Gripper", None)
    root.empty_display_size = 0.03
    scene.collection.objects.link(root)
    parts = {"root": root}

    base_t = Matrix(((1, 0, 0, -BASE_STL_AXIS.x), (0, 0, -1, BASE_STL_AXIS.z), (0, 1, 0, 0), (0, 0, 0, 1)))
    parts["base"] = new_object("Gripper base", import_stl("Gripper base", "Gripper Base v3.STL", base_t),
                               root, mats["printed"])
    wheel_t = Matrix(((1, 0, 0, -WHEEL_CENTRE.x), (0, 0, -1, WHEEL_CENTRE.z), (0, 1, 0, -WHEEL_CENTRE.y),
                      (0, 0, 0, 1)))
    wheel = new_object("Servo wheel", import_stl("Servo wheel", "Gripper Servo Wheel v1.STL", wheel_t),
                       root, mats["printed"])
    wheel.location = (0.0, 0.0, Z_WHEEL * MM)
    parts["wheel"] = wheel
    claw_me = import_stl("Claw", "Gripper Claw v3.STL", Matrix.Translation(-CLAW_PIVOT))
    pusher_me = import_stl("Pusher", "Gripper Claw Pusher.STL", Matrix.Translation(-PUSHER_EYE))
    for k in range(3):
        parts[f"claw{k}"] = new_object(f"Claw {k + 1}", claw_me, root, mats["printed"] if k == 0 else None)
        parts[f"pusher{k}"] = new_object(f"Pusher {k + 1}", pusher_me, root, mats["printed"] if k == 0 else None)
    build_servo(root, mats)
    build_hardware(root, wheel, mats)
    parts["servo"] = bpy.data.objects["Servo"]
    static = [parts["base"].data] + [bpy.data.objects[n].data for n in (
        "Pivot pins", "Servo", "Servo screws", "Servo lead 0", "Servo lead 1", "Servo lead 2")]
    model = BandModel(np.concatenate([mesh_triangles(me) for me in static]), mesh_triangles(claw_me))
    model.settle(alpha_push(THETA_OPEN))  # it rides up into the valley while the claws are open
    parts["band_model"] = model
    parts["band"] = build_band(root, model, mats["band"])
    parts["king"], parts["pieces"] = build_chess_set(mats)
    build_board(mats)
    return parts


def _link_object_material(ob, mat):
    """Shared meshes get per-object materials (object-linked slot)."""
    if not ob.data.materials:
        ob.data.materials.append(None)
    ob.material_slots[0].link = "OBJECT"
    ob.material_slots[0].material = mat


def king_base_in_tool():
    """Height of the king's base in G when gripped: hook tops 1.2 mm under the collar flare."""
    hook_top = tip_point(ALPHA_STEM, CLAW_HOOK_Y1)[1]
    return hook_top + 1.2 - KING_SKIRT_H0


def bake(scene, parts):
    """Solve every frame and key the poses (linear interpolation between frames)."""
    yaw = Matrix.Rotation(math.radians(GRIPPER_YAW), 3, "Z")
    land, free = grip_frames()
    band = parts["band"]
    quats = {}

    def key_pose(ob, f, loc_mm, rot):
        q = rot.to_quaternion() if isinstance(rot, Matrix) else rot
        if ob.name in quats and quats[ob.name].dot(q) < 0.0:
            q.negate()
        quats[ob.name] = q
        ob.rotation_mode = "QUATERNION"
        ob.location = loc_mm * MM
        ob.rotation_quaternion = q
        ob.keyframe_insert("location", frame=f)
        ob.keyframe_insert("rotation_quaternion", frame=f)

    king = parts["king"]
    info = []
    for f in range(1, FRAME_END + 1):
        theta = servo_theta(f)
        alpha = claw_alpha(f)
        key_pose(parts["root"], f, tool_position(f), yaw)
        key_pose(parts["wheel"], f, Vector((0.0, 0.0, Z_WHEEL)), Matrix.Rotation(math.radians(wheel_angle(theta)), 3, "Z"))
        for k, az in enumerate(CLAW_AZ):
            rot, loc = claw_frame(az, alpha)
            key_pose(parts[f"claw{k}"], f, loc, rot)
            prot, eye, *_ = pusher_frame(az, theta, alpha)
            key_pose(parts[f"pusher{k}"], f, eye, prot)
        band.data.shape_keys.eval_time = band_eval_time(alpha, band)
        band.data.shape_keys.keyframe_insert("eval_time", frame=f)
        # the king rides along while the hooks are closed on it
        carried = tool_offset(min(max(f, land), free)) - tool_offset(land)
        king.location = (square_xy(GRIP_SQUARE) + carried) * MM
        king.keyframe_insert("location", frame=f)
        info.append((f, theta, alpha))
    # one camera per shot, keyed a frame either side of it
    for s, cam in zip(SHOTS, parts["cameras"]):
        for f in range(s.first - 1, s.last + 2):
            pos, aim, lens, fstop = shot_camera(s, f)
            key_pose(cam, f, pos, (aim - pos).to_track_quat("-Z", "Y"))
            cam.data.lens = lens
            cam.data.dof.focus_distance = (aim - pos).length * MM
            cam.data.dof.aperture_fstop = fstop
            cam.data.keyframe_insert("lens", frame=f)
            cam.data.dof.keyframe_insert("focus_distance", frame=f)
            cam.data.dof.keyframe_insert("aperture_fstop", frame=f)
    return info, land, free


def setup_render(scene):
    world = bpy.data.worlds.new("Studio")
    scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    out = nt.nodes["World Output"]
    bg_light = nt.nodes["Background"]
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(os.path.join(bpy.utils.system_resource("DATAFILES", path="studiolights/world"),
                                                  "studio.exr"))
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(150.0))
    coord = nt.nodes.new("ShaderNodeTexCoord")
    nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], bg_light.inputs["Color"])
    bg_light.inputs["Strength"].default_value = 0.35
    # what the camera sees behind the board: a soft studio gradient
    grad_in = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(coord.outputs["Window"], grad_in.inputs["Vector"])
    ramp_n = nt.nodes.new("ShaderNodeValToRGB")
    ramp_n.color_ramp.elements[0].color = lin("#cfd2d6")
    ramp_n.color_ramp.elements[1].color = lin("#8f949b")
    nt.links.new(grad_in.outputs["Y"], ramp_n.inputs["Fac"])
    bg_cam = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(ramp_n.outputs["Color"], bg_cam.inputs["Color"])
    bg_cam.inputs["Strength"].default_value = 1.0
    path = nt.nodes.new("ShaderNodeLightPath")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(path.outputs["Is Camera Ray"], mix.inputs["Fac"])
    nt.links.new(bg_light.outputs["Background"], mix.inputs[1])
    nt.links.new(bg_cam.outputs["Background"], mix.inputs[2])
    nt.links.new(mix.outputs["Shader"], out.inputs["Surface"])

    centre = Vector((0.03, 0.0, 0.12))
    for name, offset, size, power, colour in [
            ("Key", Vector((0.55, -0.6, 0.55)), 0.5, 55.0, "#fff1e2"),
            ("Rim", Vector((-0.45, 0.6, 0.45)), 0.35, 45.0, "#e8f0ff"),
            ("Fill", Vector((-0.7, -0.45, 0.12)), 0.9, 10.0, "#ffffff"),
            ("Top", Vector((0.05, 0.15, 0.9)), 0.8, 13.0, "#ffffff"),
            ("Bounce", Vector((0.1, -0.45, -0.08)), 0.6, 6.0, "#fff6ec")]:
        light = bpy.data.lights.new(name, "AREA")
        light.energy, light.size, light.color = power, size, lin(colour)[:3]
        ob = bpy.data.objects.new(name, light)
        scene.collection.objects.link(ob)
        ob.location = centre + offset
        ob.rotation_euler = (-offset).to_track_quat("-Z", "Y").to_euler()
        ob.visible_camera = False  # the shots look from every side; never let one see a soft box

    scene.render.engine = "CYCLES"
    scene.cycles.device = enable_gpu(scene)
    scene.cycles.samples = ARGS.samples
    scene.cycles.use_adaptive_sampling = True
    scene.cycles.adaptive_threshold = 0.015
    scene.cycles.use_denoising = True
    scene.cycles.denoiser = "OPENIMAGEDENOISE"
    if hasattr(scene.cycles, "denoising_use_gpu"):
        scene.cycles.denoising_use_gpu = True
    scene.cycles.sample_clamp_indirect = 8.0
    scene.cycles.max_bounces, scene.cycles.glossy_bounces, scene.cycles.transparent_max_bounces = 8, 4, 4
    scene.render.use_motion_blur = True
    scene.render.motion_blur_shutter = 0.5
    scene.render.use_persistent_data = True
    w, h = (int(v) for v in ARGS.res.lower().split("x"))
    scene.render.resolution_x, scene.render.resolution_y, scene.render.resolution_percentage = w, h, 100
    scene.render.fps = FPS
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_depth = "8"
    for transform, look in (("AgX", "AgX - Medium High Contrast"), ("Filmic", "Medium High Contrast")):
        try:
            scene.view_settings.view_transform = transform
            scene.view_settings.look = look
            break
        except TypeError:
            continue
    scene.view_settings.exposure = -0.25
    scene.frame_start, scene.frame_end = 1, FRAME_END


def enable_gpu(scene):
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
            return "GPU"
    return "CPU"


def make_cameras(scene):
    """One camera per shot; timeline markers cut between them."""
    cams = []
    for i, s in enumerate(SHOTS):
        cam = bpy.data.objects.new(f"Shot {i + 1} - {s.name}", bpy.data.cameras.new(f"Shot {i + 1} - {s.name}"))
        scene.collection.objects.link(cam)
        cam.data.sensor_width = 36.0
        cam.data.clip_start = 0.005
        cam.data.dof.use_dof = True
        scene.timeline_markers.new(f"{i + 1} {s.name}", frame=s.first).camera = cam
        cams.append(cam)
    scene.camera = cams[0]
    return cams


def camera_for(parts, f):
    return parts["cameras"][SHOTS.index(shot_at(f))]


def world_bvh(ob, dg):
    ev = ob.evaluated_get(dg)
    me = ev.to_mesh()
    mw = ev.matrix_world
    tree = BVHTree.FromPolygons([mw @ v.co for v in me.vertices], [tuple(p.vertices) for p in me.polygons])
    ev.to_mesh_clear()
    return tree


def group_bvh(obs, dg):
    """One BVH for a group of objects, as they are at the current frame."""
    verts, polys = [], []
    for ob in obs:
        ev = ob.evaluated_get(dg)
        me = ev.to_mesh()
        base = len(verts)
        verts += [ev.matrix_world @ v.co for v in me.vertices]
        polys += [tuple(base + i for i in p.vertices) for p in me.polygons]
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys)


def report(scene, parts, info, land, free):
    kbs = parts["band"].data.shape_keys.key_blocks
    print(f"\nband shape-key frames: {[round(kb.frame, 2) for kb in kbs[:4]]} ... {round(kbs[-1].frame, 2)}")
    print(f"alpha: stem {ALPHA_STEM:.3f}, plate stop {ALPHA_PLATE:.3f}, pusher limit {alpha_push(THETA_CLOSED):.3f}, "
          f"open {alpha_push(THETA_OPEN):.3f} deg")
    print(f"king base in tool frame {king_base_in_tool():.2f} mm; hooks land on frame {land}, lift off on frame {free}")
    print(f"shoulder clearance while holding: {shoulder_gap(0.0, THETA_CLOSED, ALPHA_STEM):.2f} mm")
    model = parts["band_model"]
    print(f"band: {BAND_W0:.1f} x {BAND_T0:.1f} mm, {BAND_REST:.0f} mm round; settles with its centre at "
          f"z = {model.z_mid:.2f} mm (pivots at z = {PIVOT_Z:.2f}, plate top at z = 5.00)")
    for a in (BAND_ALPHAS[0], alpha_push(THETA_CLOSED), ALPHA_STEM, alpha_push(THETA_OPEN)):
        rows, s, w, t = model.solve(a)
        print(f"band at {a:+6.2f} deg: stretch {s:.3f}, {w:.2f} x {t:.2f} mm, z {rows[0][0]:.2f} to {rows[-1][0]:.2f}")
    print(f"position {POSITION}: {len(parts['pieces'])} other pieces; the king goes {GRIP_SQUARE} -> {DROP_SQUARE}")
    names = ["base", "wheel", "servo", "band", "king"] + [f"claw{k}" for k in range(3)] + [f"pusher{k}" for k in range(3)]
    pairs = [(f"pusher{i}", f"pusher{j}") for i in range(3) for j in range(i + 1, 3)]
    pairs += [(f"pusher{i}", o) for i in range(3) for o in ("wheel", "servo", "base", "band", "king")]
    pairs += [(f"pusher{i}", f"claw{j}") for i in range(3) for j in range(3)]
    pairs += [(f"claw{i}", o) for i in range(3) for o in ("base", "band", "king", "wheel")]
    pairs += [("band", "base"), ("band", "servo"), ("wheel", "king")]
    movers = ["king", "base", "band"] + [f"claw{k}" for k in range(3)] + [f"pusher{k}" for k in range(3)]
    dg = bpy.context.evaluated_depsgraph_get()
    others = group_bvh(parts["pieces"], dg)
    board = group_bvh([ob for ob in bpy.data.collections["Board"].objects if ob.name != "Cyclorama"], dg)
    gripper_obs = [ob for ob in parts["root"].children_recursive if ob.type == "MESH"] + [parts["king"]]
    for f in sorted(set([1, PH["open"][1], PH["descend"][1], land, PH["close"][1], PH["lift"][1], PH["move"][1],
                         PH["lower"][1], free, PH["release"][1], PH["rise"][1], FRAME_END] +
                        list(range(1, FRAME_END + 1, 12)))):
        scene.frame_set(f)
        dg = bpy.context.evaluated_depsgraph_get()
        trees = {n: world_bvh(parts[n], dg) for n in names}
        hits = []
        for a, b in pairs:
            n_hit = len(trees[a].overlap(trees[b]))
            if n_hit:
                hits.append(f"{a}/{b}:{n_hit}")
        hits += [f"{n}/pieces:{len(trees[n].overlap(others))}" for n in movers if trees[n].overlap(others)]
        _, theta, alpha = info[f - 1]
        print(f"frame {f:3d} theta {theta:6.1f} alpha {alpha:6.2f}  " + ("clear" if not hits else " ".join(hits)))
    # the cameras: how close each one gets to anything, and whether a piece or the board ever gets in
    # between it and what it is looking at
    print("\nshot          frames     lens   f-stop      nearest: piece  board  gripper   view")
    for s, cam_ob in zip(SHOTS, parts["cameras"]):
        near = {"piece": math.inf, "board": math.inf, "gripper": math.inf}
        blocked = []
        stops = []
        for f in sorted(set(list(range(s.first, s.last + 1, 3)) + [s.last])):
            scene.frame_set(f)
            dg = bpy.context.evaluated_depsgraph_get()
            gripper = group_bvh(gripper_obs, dg)
            pos, aim, lens, fstop = shot_camera(s, f)
            stops.append(fstop)
            cam, to = pos * MM, (aim - pos) * MM
            if (cam_ob.matrix_world.translation - cam).length > 1e-6:
                blocked.append(f"{f}: camera not at its baked pose")
            for key, tree in (("piece", others), ("board", board), ("gripper", gripper)):
                near[key] = min(near[key], tree.find_nearest(cam)[3] / MM)
            for key, tree in (("piece", others), ("board", board)):
                hit = tree.ray_cast(cam, to.normalized(), to.length)
                if hit[0] is not None and hit[3] < to.length - 20.0 * MM:
                    blocked.append(f"{f}: {key} at {hit[3] / MM:.0f} of {to.length / MM:.0f} mm")
        print(f"{s.name:12s} {s.first:4d}-{s.last:<4d}  {s.lens[0]:3.0f}-{s.lens[1]:<3.0f} {min(stops):5.1f}-{max(stops):<5.1f}"
              f"     {near['piece']:6.0f} {near['board']:6.0f} {near['gripper']:7.0f}   "
              + ("clear" if not blocked else "; ".join(blocked[:4]) + (" ..." if len(blocked) > 4 else "")))


def main():
    scene = reset_scene()
    os.makedirs(ARGS.out, exist_ok=True)
    mats = make_materials()
    parts = build(scene, mats)
    parts["cameras"] = make_cameras(scene)
    bpy.context.preferences.edit.keyframe_new_interpolation_type = "LINEAR"
    info, land, free = bake(scene, parts)
    setup_render(scene)
    with open(os.path.join(ARGS.out, "timeline.json"), "w") as fh:
        json.dump({"fps": FPS, "frame_end": FRAME_END, "grip": [land, free],
                   "shots": [[s.name, s.first, s.last] for s in SHOTS]}, fh, indent=1)
    if ARGS.save:
        bpy.ops.wm.save_as_mainfile(filepath=os.path.abspath(ARGS.save))
    if ARGS.check:
        report(scene, parts, info, land, free)
        return
    if ARGS.stills:
        for f in (int(v) for v in ARGS.stills.split(",")):
            scene.frame_set(f)
            scene.camera = camera_for(parts, f)
            scene.render.filepath = os.path.join(ARGS.out, f"still_{f:04d}.png")
            bpy.ops.render.render(write_still=True)
        return
    first, last = (int(v) for v in ARGS.frames.split("-")) if ARGS.frames else (1, FRAME_END)
    scene.render.filepath = os.path.join(ARGS.out, "frame_")
    for s, cam in zip(SHOTS, parts["cameras"]):  # shot by shot, each with its own camera
        a, b = max(first, s.first), min(last, s.last)
        if a <= b:
            scene.camera = cam
            scene.frame_start, scene.frame_end = a, b
            bpy.ops.render.render(animation=True)


main()
