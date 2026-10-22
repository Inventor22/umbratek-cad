# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["build123d>=0.9,<0.14"]
# ///
"""
Compliant pen-holder end effector for the Umbratek UTRA 6-1000 arm (build123d)
=============================================================================

    uv run pen_holder.py          # prints a design report and writes STEP / STL / GLB

Parts (3 printed + off-the-shelf hardware)
  1. Tool adapter  - bolts to the arm's tool flange (6x M5 on PCD 64, Ø73 h7 pilot, Ø3 dowel).
                     Re-usable: future end effectors just bolt to its 3x M3 interface.
  2. Pen module    - flange + barrel; houses the spring and guides the carriage.
  3. Pen carriage  - slides in the barrel and clamps the pen with a thumb screw.

A compression spring between the module and the carriage pushes the pen down. If the arm
over-reaches, the carriage slides up the barrel (up to STROKE mm) instead of driving the pen
into the table. Two M3 set screws riding in slots in the barrel stop the carriage rotating or
falling out, and line up with tick marks that show how far it has been pushed.

Frame (mm): origin = centre of the arm's flange face (the face of the Ø73 pilot boss).
+Z points into the arm, so the tool hangs along -Z. +X points at the Ø3 dowel hole.
In the robot's flange frame (Z out of the flange) the TCP is (0, 0, +TCP_Z).
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path

from build123d import (
    Align,
    Axis,
    Box,
    Circle,
    Color,
    Compound,
    Cylinder,
    Face,
    Helix,
    Part,
    Plane,
    Pos,
    RegularPolygon,
    Rot,
    Shape,
    Spline,
    Wire,
    export_gltf,
    export_step,
    export_stl,
    extrude,
    revolve,
    sweep,
)

# =============================================================================
# 1. UTRA 6-1000 tool flange (Quick_Start_Guide_UTRA_6-1000.pdf, page 1)
# =============================================================================
FLANGE_OD = 86.0  # flange body Ø
FLANGE_LEN = 26.0  # overall flange length, pilot boss included
PILOT_D = 73.0  # Ø73 h7 pilot boss ...
PILOT_H = 3.0  # ... standing 3 mm proud of the Ø86 shoulder
BOLT_PCD = 64.0  # 6x M5 ↧6, 60° apart, first hole on +X
BOLT_COUNT = 6
BOLT_THREAD_DEPTH = 6.0
DOWEL_PCD = 52.0  # Ø3 H7 ↧5 on +X (same radial line as an M5 hole)
DOWEL_D = 3.0
DOWEL_HOLE_DEPTH = 5.0
IO_COVER_D = 47.0  # centre cover holding the two 8-pin tool-I/O connectors

# =============================================================================
# 2. Tool adapter (printed, re-usable for future tools)
# =============================================================================
ADAPTER_OD = 86.0
ADAPTER_T = 12.0  # plate thickness below the boss face
PILOT_RECESS_DEPTH = 2.5  # < PILOT_H: plate clamps on the boss face, 0.5 mm gap at the shoulder
PILOT_CLEARANCE = 0.3  # diametral, for FDM. Set 0 and machine as Ø73 H7 for a metal plate
RELIEF_D = 50.0  # keeps the plate off the tool-I/O cover and its screws (overlaps the dowel hole top)
RELIEF_DEPTH = 1.0
CENTER_HOLE_D = 16.0  # cable pass-through (and spare room for long pens)
M5_SCREW_LEN = 12.0  # ISO 4762 M5x12 ...
M5_ENGAGEMENT = 5.0  # ... engaging 5 of the 6 mm of thread in the arm
M5_CLEAR_D = 5.5
M5_CBORE_D = 10.0
M5_HEAD_D, M5_HEAD_H = 8.5, 5.0
DOWEL_HOLE_D = 3.0  # printed holes come out ~0.1 mm small -> light press on a Ø3 m6 pin
DOWEL_LEN = 8.0

# Adapter <-> module interface: 3x M3 SHCS from below into captive nuts on the arm side
MODULE_SCREW_PCD = 43.0
MODULE_SCREW_ANGLES = (30.0, 150.0, 270.0)
M3_CLEAR_D = 3.3
M3_NUT_AF, M3_NUT_T = 5.5, 2.4
NUT_POCKET_AF = 5.7
NUT_POCKET_DEPTH = 3.4  # below the relief floor
M3_HEAD_D, M3_HEAD_H = 5.5, 3.0
M3_CBORE_D, M3_CBORE_DEPTH = 6.0, 3.2
MODULE_SCREW_LEN = 14.0  # ISO 4762 M3x14

# =============================================================================
# 3. Pen module (printed): flange + barrel
# =============================================================================
MODULE_FLANGE_D = 53.0  # inside the M5 counterbores -> adapter unbolts with the module fitted
MODULE_FLANGE_T = 7.0
BARREL_OD = 32.0
BARREL_BORE = 24.0
SPRING_POCKET_DEPTH = 3.0  # centres the top of the spring
MODULE_CENTER_HOLE_D = 16.0

# =============================================================================
# 4. Spring and travel
# =============================================================================
SPRING_OD = 20.0  # off-the-shelf compression spring, 1.0 x 20 x 50 mm
SPRING_WIRE = 1.0
SPRING_FREE_LEN = 50.0
SPRING_ACTIVE_COILS = 8
SPRING_G = 79_300.0  # N/mm², music / spring steel
SPRING_PRELOAD = 10.0  # spring compression with the pen in free air
STROKE = 15.0  # compliant over-travel before the carriage reaches its hard stop

# =============================================================================
# 5. Pen carriage (printed)
# =============================================================================
SLIDE_CLEARANCE = 0.4  # diametral piston/bore clearance - tune for your printer
PISTON_L = 50.0  # guided length: 35 mm engaged at rest, 50 mm at full stroke
NOSE_D = BARREL_OD
NOSE_L = 18.0
SPIGOT_H = 3.0  # centres the bottom of the spring
GUIDE_PIN_D = 3.0  # ISO 4026 M3x6 set screws act as guide pins ...
GUIDE_PIN_LEN = 6.0
GUIDE_PIN_HOLE_D = 2.5  # ... thread-forming into the printed carriage
GUIDE_PIN_HOLE_DEPTH = 3.5
GUIDE_SLOT_W = 3.4
SLOT_BOTTOM_RING = 10.0  # barrel bottom -> guide-pin centre at rest
SLOT_OVERTRAVEL = 1.0  # slots run past the hard stop so the pins never take the load
THUMB_SCREW_LEN = 10.0  # DIN 464 / DIN 653 M3x10 knurled thumb screw ...
CLAMP_NUT_X0 = 9.0  # ... into a captive M3 nut slid in from the nose face
CLAMP_NUT_POCKET_T = 2.7
CLAMP_SPOT_FACE_X = 15.3

# =============================================================================
# 6. Pen (default: Sharpie Fine Point, uncapped)
# =============================================================================
PEN_D = 13.1  # Ø of the pen section that sits inside the carriage
PEN_BORE_CLEARANCE = 0.5
PEN_LEN = 123.0
PEN_GRIP_D = 10.6  # visual model only: narrow front section
PEN_STICKOUT = 35.0  # tip protrusion below the carriage nose

# =============================================================================
# Derived geometry (Z positions are for the "pen in free air" state)
# =============================================================================
SPRING_ID = SPRING_OD - 2 * SPRING_WIRE
SPRING_MEAN_D = SPRING_OD - SPRING_WIRE
SPRING_RATE = SPRING_G * SPRING_WIRE**4 / (8 * SPRING_MEAN_D**3 * SPRING_ACTIVE_COILS)
SPRING_SOLID = (SPRING_ACTIVE_COILS + 2) * SPRING_WIRE
SPRING_INSTALLED = SPRING_FREE_LEN - SPRING_PRELOAD

PISTON_D = BARREL_BORE - SLIDE_CLEARANCE
PEN_BORE = PEN_D + PEN_BORE_CLEARANCE
SPIGOT_D = SPRING_ID - 0.6
SPRING_POCKET_D = SPRING_OD + 0.8

Z_ADAPTER_TOP = PILOT_RECESS_DEPTH
Z_ADAPTER_BOTTOM = -ADAPTER_T
Z_M5_SEAT = M5_ENGAGEMENT - M5_SCREW_LEN  # under-head face of the M5 screws
Z_NUT_POCKET_BOTTOM = -RELIEF_DEPTH - NUT_POCKET_DEPTH
Z_FLANGE_BOTTOM = Z_ADAPTER_BOTTOM - MODULE_FLANGE_T
Z_M3_SEAT = Z_FLANGE_BOTTOM + M3_CBORE_DEPTH  # under-head face of the module screws
Z_SPRING_TOP = Z_FLANGE_BOTTOM + SPRING_POCKET_DEPTH
Z_CARRIAGE_TOP = Z_SPRING_TOP - SPRING_INSTALLED  # spring seat on the carriage
Z_NOSE_TOP = Z_CARRIAGE_TOP - PISTON_L
Z_NOSE_BOTTOM = Z_NOSE_TOP - NOSE_L
Z_BARREL_BOTTOM = Z_NOSE_TOP + STROKE  # the nose shoulder lands here at full stroke
Z_PIN = Z_BARREL_BOTTOM + SLOT_BOTTOM_RING  # guide-pin centre
Z_CLAMP = Z_NOSE_TOP - NOSE_L / 2
Z_TIP = Z_NOSE_BOTTOM - PEN_STICKOUT
TCP_Z = -Z_TIP

# =============================================================================
# Geometry helpers
# =============================================================================
def polar(r: float, angle_deg: float) -> tuple[float, float]:
    a = math.radians(angle_deg)
    return r * math.cos(a), r * math.sin(a)


def zcyl(d: float, z0: float, z1: float) -> Part:
    """Cylinder of diameter d on the Z axis between heights z0 and z1."""
    lo, hi = min(z0, z1), max(z0, z1)
    return Pos(0, 0, lo) * Cylinder(d / 2, hi - lo, align=(Align.CENTER, Align.CENTER, Align.MIN))


def radial_cyl(d: float, r0: float, r1: float, z: float, angle_deg: float = 0.0) -> Part:
    """Cylinder pointing radially outward (angle from +X) from radius r0 to r1 at height z."""
    cyl = Cylinder(d / 2, r1 - r0, align=(Align.CENTER, Align.CENTER, Align.MIN))
    return Rot(0, 0, angle_deg) * Pos(r0, 0, z) * Rot(0, 90, 0) * cyl


def hex_prism(af: float, z0: float, z1: float) -> Part:
    """Hexagonal prism (across flats = af, flats facing ±Y) between heights z0 and z1."""
    return Pos(0, 0, min(z0, z1)) * extrude(RegularPolygon(af / 2, 6, major_radius=False), abs(z1 - z0))


def revolved(rz: list[tuple[float, float]]) -> Part:
    """Revolve a closed (radius, z) polyline about the Z axis."""
    return revolve(Face(Wire.make_polygon([(r, 0, z) for r, z in rz], close=True)), Axis.Z)


def cut_all(body: Part, tools: list[Part]) -> Part:
    for tool in tools:
        body = body - tool
    return body


# =============================================================================
# Printed part 1: tool adapter
# =============================================================================
def make_adapter() -> Part:
    r_out = ADAPTER_OD / 2
    r_pilot = (PILOT_D + PILOT_CLEARANCE) / 2
    zt, zb = Z_ADAPTER_TOP, Z_ADAPTER_BOTTOM
    body = revolved(
        [
            (CENTER_HOLE_D / 2, zb),
            (r_out - 1.0, zb),
            (r_out, zb + 1.0),
            (r_out, zt - 0.6),
            (r_out - 0.6, zt),
            (r_pilot + 0.5, zt),  # lead-in chamfer for the pilot boss
            (r_pilot, zt - 0.5),
            (r_pilot, 0.0),  # recess floor = seating face on the arm's boss face
            (RELIEF_D / 2, 0.0),
            (RELIEF_D / 2, -RELIEF_DEPTH),
            (CENTER_HOLE_D / 2, -RELIEF_DEPTH),
        ]
    )
    tools = []
    for i in range(BOLT_COUNT):
        x, y = polar(BOLT_PCD / 2, i * 360 / BOLT_COUNT)
        tools.append(Pos(x, y, 0) * zcyl(M5_CLEAR_D, zb - 1, 1))
        tools.append(Pos(x, y, 0) * zcyl(M5_CBORE_D, zb - 1, Z_M5_SEAT))
    tools.append(Pos(DOWEL_PCD / 2, 0, 0) * zcyl(DOWEL_HOLE_D, zb - 1, 1))
    for a in MODULE_SCREW_ANGLES:
        x, y = polar(MODULE_SCREW_PCD / 2, a)
        tools.append(Pos(x, y, 0) * zcyl(M3_CLEAR_D, zb - 1, 0))
        # captive-nut pocket, opening into the relief pocket, one flat facing the axis
        tools.append(Pos(x, y, 0) * Rot(0, 0, a - 30) * hex_prism(NUT_POCKET_AF, Z_NUT_POCKET_BOTTOM, 0.5))
    # index groove on the rim, in line with the dowel pin (+X)
    tools.append(Pos(r_out, 0, 0) * zcyl(1.6, zb - 1, zt + 1))
    return cut_all(body, tools)


# =============================================================================
# Printed part 2: pen module (flange + barrel)
# =============================================================================
TICKS = [float(t) for t in range(0, int(STROKE) + 1, 5)]


def make_module() -> Part:
    r_fl, r_o, r_b = MODULE_FLANGE_D / 2, BARREL_OD / 2, BARREL_BORE / 2
    zt, zf, zb = Z_ADAPTER_BOTTOM, Z_FLANGE_BOTTOM, Z_BARREL_BOTTOM
    body = revolved(
        [
            (MODULE_CENTER_HOLE_D / 2, zt),
            (r_fl - 0.6, zt),
            (r_fl, zt - 0.6),
            (r_fl, zf + 0.6),
            (r_fl - 0.6, zf),
            (r_o + 1.5, zf),  # 45° root chamfer, flange -> barrel
            (r_o, zf - 1.5),
            (r_o, zb + 0.8),
            (r_o - 0.8, zb),
            (r_b + 1.0, zb),  # lead-in for the carriage
            (r_b, zb + 1.0),
            (r_b, zf),
            (SPRING_POCKET_D / 2, zf),
            (SPRING_POCKET_D / 2, Z_SPRING_TOP),
            (MODULE_CENTER_HOLE_D / 2, Z_SPRING_TOP),
        ]
    )
    tools = []
    for a in MODULE_SCREW_ANGLES:
        x, y = polar(MODULE_SCREW_PCD / 2, a)
        tools.append(Pos(x, y, 0) * zcyl(M3_CLEAR_D, zf - 1, zt + 1))
        tools.append(Pos(x, y, 0) * zcyl(M3_CBORE_D, zf - 1, Z_M3_SEAT))

    # Guide slots on ±Y: the pins rest on the bottom end, the nose shoulder stops them
    # 1 mm short of the top end.
    z_lo = Z_PIN + (GUIDE_SLOT_W - GUIDE_PIN_D) / 2  # pin tangent to the slot's bottom end at rest
    z_hi = Z_PIN + STROKE + SLOT_OVERTRAVEL
    span = BARREL_OD + 4
    tools.append(Pos(0, 0, (z_lo + z_hi) / 2) * Box(GUIDE_SLOT_W, span, z_hi - z_lo))
    for z in (z_lo, z_hi):
        tools.append(Pos(0, 0, z) * Rot(90, 0, 0) * Cylinder(GUIDE_SLOT_W / 2, span))

    # Travel ticks every 5 mm beside each slot (long ticks at 0 and full stroke)
    for side in (1, -1):
        for dz in TICKS:
            length = 4.0 if dz in (0.0, STROKE) else 2.5
            gap = GUIDE_SLOT_W / 2 + 0.8 + length / 2
            theta = side * (90 - math.degrees(gap / r_o))
            tools.append(Rot(0, 0, theta) * Pos(r_o, 0, Z_PIN + dz) * Box(1.2, length, 0.6))
    return cut_all(body, tools)


# =============================================================================
# Printed part 3: pen carriage (local frame: z = 0 is the spring seat, tool along -Z)
# =============================================================================
def carriage_z(z_global: float) -> float:
    return z_global - Z_CARRIAGE_TOP


def make_carriage() -> Part:
    r_b, r_s, r_p, r_n = PEN_BORE / 2, SPIGOT_D / 2, PISTON_D / 2, NOSE_D / 2
    zn, zbot = -PISTON_L, -PISTON_L - NOSE_L
    body = revolved(
        [
            (r_b, SPIGOT_H),
            (r_s - 0.4, SPIGOT_H),
            (r_s, SPIGOT_H - 0.4),
            (r_s, 0.0),
            (r_p - 0.5, 0.0),
            (r_p, -0.5),
            (r_p, zn),
            (r_n - 0.6, zn),  # nose shoulder = hard stop against the barrel
            (r_n, zn - 0.6),
            (r_n, zbot + 1.5),
            (r_n - 1.5, zbot),
            (r_b + 1.0, zbot),  # pen lead-in
            (r_b, zbot + 1.0),
        ]
    )
    z_pin, z_cl = carriage_z(Z_PIN), carriage_z(Z_CLAMP)
    tools = [
        radial_cyl(GUIDE_PIN_HOLE_D, r_p - GUIDE_PIN_HOLE_DEPTH, r_p + 1, z_pin, a) for a in (90, -90)
    ]
    # thumb-screw clearance hole (+X) and the captive-nut slot, open at the nose face
    tools.append(radial_cyl(M3_CLEAR_D + 0.1, r_b - 0.5, r_n + 1, z_cl, 0))
    x0, x1 = CLAMP_NUT_X0, CLAMP_NUT_X0 + CLAMP_NUT_POCKET_T
    z_top = z_cl + NUT_POCKET_AF / math.sqrt(3)  # nut corner lands here -> nut centred on the screw
    tools.append(Pos((x0 + x1) / 2, 0, (zbot - 1 + z_top) / 2) * Box(x1 - x0, NUT_POCKET_AF, z_top - zbot + 1))
    # spot face for the thumb-screw collar
    tools.append(Pos(CLAMP_SPOT_FACE_X + 5, 0, z_cl) * Box(10, 14, 10))
    return cut_all(body, tools)


# =============================================================================
# Hardware, spring, pen and arm (visual / reference models)
# =============================================================================
def make_shcs(d: float, length: float, head_d: float, head_h: float, key: float) -> Part:
    """ISO 4762 socket head cap screw: under-head face at z = 0, shank along +Z."""
    c = 0.1 * d
    body = revolved(
        [
            (0, -head_h),
            (head_d / 2 - 0.4, -head_h),
            (head_d / 2, -head_h + 0.4),
            (head_d / 2, 0),
            (d / 2, 0),
            (d / 2, length - c),
            (d / 2 - c, length),
            (0, length),
        ]
    )
    return body - hex_prism(key, -head_h - 0.1, -0.4 * head_h)


def make_set_screw(d: float, length: float, key: float) -> Part:
    """ISO 4026 flat-point set screw along +X from x = 0 to x = length (socket at the outer end)."""
    c = 0.15 * d
    body = revolved([(0, 0), (d / 2 - c, 0), (d / 2, c), (d / 2, length - c), (d / 2 - c, length), (0, length)])
    body = body - hex_prism(key, length - 0.6 * d, length + 0.1)
    return Rot(0, 90, 0) * body


def make_thumb_screw() -> Part:
    """DIN 464-style M3 knurled thumb screw along +X: tip at x = 0, head outboard."""
    L, collar_l, head_l, head_d = THUMB_SCREW_LEN, 2.5, 4.5, 12.0
    body = revolved(
        [
            (0, 0),
            (1.2, 0),
            (1.5, 0.3),
            (1.5, L),
            (3.0, L),
            (3.0, L + collar_l),
            (head_d / 2 - 0.5, L + collar_l),
            (head_d / 2, L + collar_l + 0.5),
            (head_d / 2, L + collar_l + head_l - 0.5),
            (head_d / 2 - 0.5, L + collar_l + head_l),
            (0, L + collar_l + head_l),
        ]
    )
    knurl = [
        Pos(*polar(head_d / 2 + 0.15, i * 360 / 30), 0) * zcyl(0.8, L + collar_l, L + collar_l + head_l + 1)
        for i in range(30)
    ]
    return Rot(0, 90, 0) * cut_all(body, knurl)


def make_nut(af: float = M3_NUT_AF, t: float = M3_NUT_T, d: float = 3.0) -> Part:
    """Hex nut centred on the origin, axis Z, flats facing ±Y."""
    return hex_prism(af, -t / 2, t / 2) - zcyl(d, -t, t)


def make_dowel() -> Part:
    r, L, c = DOWEL_D / 2, DOWEL_LEN, 0.3
    return revolved([(0, 0), (r - c, 0), (r, c), (r, L - c), (r - c, L), (0, L)])


def make_spring(length: float) -> Part:
    """Closed-and-ground compression spring from z = 0 to z = length (axis Z)."""
    d, r = SPRING_WIRE, SPRING_MEAN_D / 2
    n_total = SPRING_ACTIVE_COILS + 2
    p_active = (length - 3 * d) / SPRING_ACTIVE_COILS  # one closed coil (pitch = d) at each end

    def pitch(t: float) -> float:  # t in turns; smooth blend between closed and active pitch
        def smooth(x: float) -> float:
            x = min(max(x, 0.0), 1.0)
            return x * x * (3 - 2 * x)

        blend = smooth((t - 0.75) / 0.5) * (1 - smooth((t - (n_total - 1.25)) / 0.5))
        return d + (p_active - d) * blend

    pts, z, steps_per_turn = [], d / 2, 24
    n = int(n_total * steps_per_turn)
    for i in range(n + 1):
        t = i / steps_per_turn
        if i:
            t_mid = (i - 0.5) / steps_per_turn
            z += pitch(t_mid) / steps_per_turn
        a = 2 * math.pi * t
        pts.append((r * math.cos(a), r * math.sin(a), z))
    try:
        path = Spline(*pts)
        profile = Plane(origin=path @ 0, z_dir=path % 0) * Circle(d / 2)
        coil = sweep(profile, path=path, is_frenet=True)
        return coil & zcyl(SPRING_OD + 2, 0, length)  # grind the ends flat
    except Exception:  # pragma: no cover - fall back to a plain helix
        helix = Helix(pitch=(length - d) / n_total, height=length - d, radius=r, center=(0, 0, d / 2))
        profile = Plane(origin=helix @ 0, z_dir=helix % 0) * Circle(d / 2)
        return sweep(profile, path=helix, is_frenet=True)


def make_pen() -> list[tuple[str, Part, str]]:
    """Sharpie Fine Point-like marker: tip at the origin, body along +Z."""
    r_g, r_b, z_step, L = PEN_GRIP_D / 2, PEN_D / 2, PEN_STICKOUT, PEN_LEN
    nib = revolved([(0, 0), (0.35, 0), (0.9, 1.0), (0.9, 4.5), (0, 4.5)])
    front = revolved([(0, 3.5), (1.5, 3.5), (2.6, 6.0), (4.3, 9.5), (r_g, 12.0), (r_g, z_step), (0, z_step)])
    barrel = revolved([(0, z_step), (r_g + 0.2, z_step), (r_b, z_step + 1.2), (r_b, L - 4), (0, L - 4)])
    end = revolved([(0, L - 4), (r_b, L - 4), (r_b, L - 1.2), (r_b - 0.8, L), (0, L)])
    return [("Pen nib", nib, "pen_nib"), ("Pen front", front, "pen_black"),
            ("Pen barrel", barrel, "pen_body"), ("Pen end", end, "pen_black")]


def make_arm_flange() -> Part:
    """UTRA 6-1000 tool flange per the Quick Start Guide (reference only, z >= 0)."""
    r_p, r_o = PILOT_D / 2, FLANGE_OD / 2
    body = revolved(
        [
            (0, 0),
            (r_p - 0.5, 0),
            (r_p, 0.5),  # C0.5
            (r_p, PILOT_H),
            (r_o - 0.5, PILOT_H),
            (r_o, PILOT_H + 0.5),
            (r_o, FLANGE_LEN),
            (0, FLANGE_LEN),
        ]
    )
    tools = []
    for i in range(BOLT_COUNT):
        x, y = polar(BOLT_PCD / 2, i * 360 / BOLT_COUNT)
        tools.append(Pos(x, y, 0) * zcyl(4.2, -1, BOLT_THREAD_DEPTH))
        tools.append(Pos(x, y, 0) * zcyl(5.2, -1, 0.4))
    tools.append(Pos(DOWEL_PCD / 2, 0, 0) * zcyl(DOWEL_D, -1, DOWEL_HOLE_DEPTH))
    tools.append(zcyl(IO_COVER_D + 0.6, -1, 0.3) - zcyl(IO_COVER_D - 0.6, -2, 1))
    for a in (30, 150, 270):  # I/O-cover screws
        x, y = polar(18.7, a)
        tools.append(Pos(x, y, 0) * zcyl(3.6, -1, 0.5))
        tools.append(Pos(x, y, 0) * hex_prism(1.5, -1, 1.5))
    for sx in (-7.5, 7.5):  # two 2x4-pin tool-I/O connectors
        tools.append(Pos(sx, 0, 0) * Box(7.6, 13.4, 2.4))
        for ix in (-1.6, 1.6):
            for iy in (-4.5, -1.5, 1.5, 4.5):
                tools.append(Pos(sx + ix, iy, 0) * zcyl(1.1, -1, 4))
    return cut_all(body, tools)


def make_arm_housing(height: float = 34.0) -> Part:
    """Stub of the J6 joint housing behind the flange (render context only)."""
    z0, r = FLANGE_LEN, 49.0
    return revolved([(0, z0 + 1.0), (42.0, z0 + 1.0), (42.0, z0), (r - 1.0, z0), (r, z0 + 1.0),
                     (r, z0 + height), (0, z0 + height)])


# =============================================================================
# Assembly
# =============================================================================
COLORS = {  # STEP / GLB colours, keyed by material name
    "printed": "#2e3035",
    "accent": "#f26b1d",
    "steel_black": "#1d1e20",
    "steel": "#b9bec4",
    "spring": "#c9ced4",
    "aluminum": "#c6cad0",
    "arm_dark": "#3a3e45",
    "pen_body": "#d7dadf",
    "pen_black": "#151515",
    "pen_nib": "#202a44",
}


@dataclass
class Item:
    name: str
    shape: Shape
    material: str  # key into COLORS (and the renderer's material table)
    explode: tuple[float, float, float] = (0.0, 0.0, 0.0)  # offset used for exploded views


_cache: dict = {}


def _cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


def assembly(travel: float = 0.0, arm: bool = True, hardware: bool = True, pen: bool = True) -> list[Item]:
    """Every part in place. `travel` = how far the carriage has been pushed up (0..STROKE)."""
    if not 0.0 <= travel <= STROKE:
        raise ValueError(f"travel must be within 0..{STROKE} mm")
    up = travel
    ex_carriage = (0.0, 0.0, -195.0)
    items: list[Item] = []
    if arm:
        items.append(Item("UTRA 6-1000 tool flange (ref)", _cached("arm_flange", make_arm_flange), "aluminum", (0, 0, 70)))
        items.append(Item("UTRA 6-1000 J6 housing (ref)", _cached("arm_housing", make_arm_housing), "arm_dark", (0, 0, 70)))
    items.append(Item("Tool adapter", _cached("adapter", make_adapter), "printed"))
    items.append(Item("Pen module", _cached("module", make_module), "printed", (0, 0, -50)))
    items.append(Item("Pen carriage", Pos(0, 0, Z_CARRIAGE_TOP + up) * _cached("carriage", make_carriage), "accent", ex_carriage))
    spring = _cached(("spring", round(SPRING_INSTALLED - up, 3)), lambda: make_spring(SPRING_INSTALLED - up))
    items.append(Item("Compression spring", Pos(0, 0, Z_CARRIAGE_TOP + up) * spring, "spring", (0, 0, -170)))

    if hardware:
        m5 = _cached("m5", lambda: make_shcs(5.0, M5_SCREW_LEN, M5_HEAD_D, M5_HEAD_H, 4.0))
        for i in range(BOLT_COUNT):
            x, y = polar(BOLT_PCD / 2, i * 360 / BOLT_COUNT)
            items.append(Item(f"M5x12 SHCS {i + 1}", Pos(x, y, Z_M5_SEAT) * m5, "steel_black", (0, 0, -28)))
        z_dowel = DOWEL_HOLE_DEPTH - 0.5 - DOWEL_LEN
        items.append(Item("Dowel pin 3x8", Pos(DOWEL_PCD / 2, 0, z_dowel) * _cached("dowel", make_dowel), "steel", (0, 0, 32)))
        m3 = _cached("m3", lambda: make_shcs(3.0, MODULE_SCREW_LEN, M3_HEAD_D, M3_HEAD_H, 2.5))
        nut = _cached("nut", make_nut)
        for i, a in enumerate(MODULE_SCREW_ANGLES):
            x, y = polar(MODULE_SCREW_PCD / 2, a)
            items.append(Item(f"M3x14 SHCS {i + 1}", Pos(x, y, Z_M3_SEAT) * m3, "steel_black", (0, 0, -95)))
            z_nut = Z_NUT_POCKET_BOTTOM + M3_NUT_T / 2
            items.append(Item(f"M3 nut {i + 1}", Pos(x, y, z_nut) * Rot(0, 0, a - 30) * nut, "steel", (0, 0, 24)))
        pin = _cached("set_screw", lambda: make_set_screw(GUIDE_PIN_D, GUIDE_PIN_LEN, 1.5))
        r_pin = PISTON_D / 2 - GUIDE_PIN_HOLE_DEPTH
        for a in (90, -90):
            ex = (0.0, math.copysign(16.0, a), ex_carriage[2])
            items.append(Item(f"M3x6 set screw (guide pin, {'+' if a > 0 else '-'}Y)",
                              Rot(0, 0, a) * Pos(r_pin, 0, Z_PIN + up) * pin, "steel_black", ex))
        items.append(Item("M3x10 thumb screw", Pos(PEN_D / 2, 0, Z_CLAMP + up) * _cached("thumb", make_thumb_screw),
                          "steel", (20.0, 0.0, ex_carriage[2])))
        x_nut = CLAMP_NUT_X0 + CLAMP_NUT_POCKET_T - M3_NUT_T / 2
        items.append(Item("M3 nut (pen clamp)", Pos(x_nut, 0, Z_CLAMP + up) * Rot(0, 90, 0) * nut, "steel",
                          (0.0, 0.0, ex_carriage[2] - 22)))
    if pen:
        for name, shape, material in _cached("pen", make_pen):
            items.append(Item(name, Pos(0, 0, Z_TIP + up) * shape, material, (-70, 0, -140)))
    return items


# =============================================================================
# Design checks and report
# =============================================================================
def design_checks() -> list[tuple[str, bool, str]]:
    r_pin_out = PISTON_D / 2 - GUIDE_PIN_HOLE_DEPTH + GUIDE_PIN_LEN
    m3_tip = Z_M3_SEAT + MODULE_SCREW_LEN
    nut_top = Z_NUT_POCKET_BOTTOM + M3_NUT_T
    pen_end_full = Z_TIP + STROKE + PEN_LEN
    return [
        ("M5 engagement within the 6 mm arm thread", M5_ENGAGEMENT <= BOLT_THREAD_DEPTH - 0.5,
         f"{M5_ENGAGEMENT:.1f} mm"),
        ("M5 heads recessed in the adapter", Z_M5_SEAT - Z_ADAPTER_BOTTOM >= M5_HEAD_H,
         f"counterbore {Z_M5_SEAT - Z_ADAPTER_BOTTOM:.1f} mm"),
        ("Module screws pass through their nuts but stay below the relief floor",
         nut_top <= m3_tip <= -RELIEF_DEPTH - 0.5, f"tip at z = {m3_tip:.1f}"),
        ("Module flange clears the M5 counterbores", MODULE_FLANGE_D / 2 <= BOLT_PCD / 2 - M5_CBORE_D / 2,
         f"{MODULE_FLANGE_D / 2:.1f} <= {BOLT_PCD / 2 - M5_CBORE_D / 2:.1f}"),
        ("Nut pockets stay inside the I/O relief", MODULE_SCREW_PCD / 2 + NUT_POCKET_AF / 2 <= RELIEF_D / 2,
         f"r {MODULE_SCREW_PCD / 2 + NUT_POCKET_AF / 2:.2f} <= {RELIEF_D / 2:.2f}"),
        ("Relief clears the I/O cover", RELIEF_D >= IO_COVER_D + 1, f"dia {RELIEF_D} vs dia {IO_COVER_D}"),
        ("Pen passes through the spring", PEN_D <= SPRING_ID - 2, f"dia {PEN_D} in ID {SPRING_ID:.1f}"),
        ("Spring fits the barrel bore", SPRING_OD <= BARREL_BORE - 2, f"OD {SPRING_OD} in dia {BARREL_BORE}"),
        ("Spring never goes solid", SPRING_SOLID < SPRING_INSTALLED - STROKE,
         f"solid {SPRING_SOLID:.1f} < {SPRING_INSTALLED - STROKE:.1f} mm"),
        ("Spring-seat spigot wall", (SPIGOT_D - PEN_BORE) / 2 >= 1.2, f"{(SPIGOT_D - PEN_BORE) / 2:.2f} mm"),
        ("Wall under the guide-pin holes", (PISTON_D - PEN_BORE) / 2 - GUIDE_PIN_HOLE_DEPTH >= 0.8,
         f"{(PISTON_D - PEN_BORE) / 2 - GUIDE_PIN_HOLE_DEPTH:.2f} mm"),
        ("Guide pins engage the slots and sit below the barrel surface",
         BARREL_BORE / 2 + 1.5 <= r_pin_out <= BARREL_OD / 2 - 0.3, f"pin end at r = {r_pin_out:.2f}"),
        ("Engaged length / piston dia at rest >= 1.4 (no jamming)", (PISTON_L - STROKE) / PISTON_D >= 1.4,
         f"{(PISTON_L - STROKE) / PISTON_D:.2f}"),
        ("Thumb screw reaches the pen", CLAMP_SPOT_FACE_X - THUMB_SCREW_LEN <= PEN_D / 2 - 0.5,
         f"reach to r = {CLAMP_SPOT_FACE_X - THUMB_SCREW_LEN:.1f}"),
        ("Clamp-nut slot walls >= 2 mm", CLAMP_NUT_X0 - PEN_BORE / 2 >= 2.0
         and CLAMP_SPOT_FACE_X - CLAMP_NUT_X0 - CLAMP_NUT_POCKET_T >= 2.0, ""),
        ("Pen end stays clear of the arm at full stroke", pen_end_full <= -RELIEF_DEPTH - 3,
         f"pen end at z = {pen_end_full:.1f}"),
    ]


def design_report() -> str:
    lines = ["UTRA 6-1000 compliant pen holder", "=" * 33]
    for label, ok, detail in design_checks():
        lines.append(f"  [{'ok' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))
    f0 = SPRING_RATE * SPRING_PRELOAD
    f1 = SPRING_RATE * (SPRING_PRELOAD + STROKE)
    lines += [
        "",
        f"  TCP (pen tip, spring relaxed): X 0, Y 0, Z +{TCP_Z:.1f} mm along the flange axis",
        f"  Compliant over-travel: {STROKE:.0f} mm, then a hard stop",
        f"  Spring {SPRING_WIRE} x {SPRING_OD} x {SPRING_FREE_LEN} mm, rate ~{SPRING_RATE:.2f} N/mm:"
        f" {f0:.1f} N at first touch -> {f1:.1f} N at full over-travel",
        f"  Pen: dia {PEN_D} mm bore section, {PEN_LEN:.0f} mm long, {PEN_STICKOUT:.0f} mm sticking out",
    ]
    return "\n".join(lines)


# =============================================================================
# Export
# =============================================================================
def printed_parts() -> dict[str, tuple[Part, Part]]:
    """name -> (part in the assembly frame, part in its print orientation)."""
    adapter, module, carriage = make_adapter(), make_module(), make_carriage()
    return {
        "Pen Holder - Tool Adapter": (adapter, Pos(0, 0, -Z_ADAPTER_BOTTOM) * adapter),
        "Pen Holder - Module": (module, Pos(0, 0, Z_ADAPTER_BOTTOM) * Rot(180, 0, 0) * module),
        "Pen Holder - Carriage": (Pos(0, 0, Z_CARRIAGE_TOP) * carriage, Pos(0, 0, PISTON_L + NOSE_L) * carriage),
    }


def labelled_compound(items: list[Item], label: str) -> Compound:
    children = []
    for item in items:
        shape = item.shape.moved(Pos(0, 0, 0))
        shape.label, shape.color = item.name, Color(COLORS[item.material])
        children.append(shape)
    return Compound(label=label, children=children)


def export_all(out_dir: Path) -> None:
    (out_dir / "STEP").mkdir(parents=True, exist_ok=True)
    (out_dir / "STLs").mkdir(parents=True, exist_ok=True)
    for name, (part, printable) in printed_parts().items():
        part.label = name
        export_step(part, out_dir / "STEP" / f"{name}.step")
        export_stl(printable, out_dir / "STLs" / f"{name}.stl", tolerance=0.01, angular_tolerance=0.1)
        bb = printable.bounding_box()
        print(f"  {name:28s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:6.1f} mm (print orientation)")
    asm = labelled_compound(assembly(), "UTRA 6-1000 pen holder")
    export_step(asm, out_dir / "STEP" / "Pen Holder - Assembly.step")
    export_gltf(asm, out_dir / "Pen Holder - Assembly.glb", binary=True, linear_deflection=0.08, angular_deflection=0.35)
    print(f"  wrote {out_dir / 'STEP'}, {out_dir / 'STLs'} and the .glb assembly")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent, help="output folder")
    ap.add_argument("--no-export", action="store_true", help="only print the design report")
    args = ap.parse_args()
    print(design_report())
    if any(not ok for _, ok, _ in design_checks()):
        raise SystemExit("Design check failed - adjust the parameters above.")
    if not args.no_export:
        export_all(args.out)


if __name__ == "__main__":
    main()
