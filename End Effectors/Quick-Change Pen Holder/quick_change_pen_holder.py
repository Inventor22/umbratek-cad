# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["build123d>=0.9,<0.14"]
# ///
"""
Quick-change, side-mount pen holder for the Umbratek UTRA 6-1000 arm (build123d)
===============================================================================

    uv run quick_change_pen_holder.py      # prints a design report, writes STEP / STL / GLB

The pen sits at right angles to the arm's tool-flange axis.

* Base (printed): bolts to the arm once - 6x M5 on PCD 64, Ø73 h7 pilot, Ø3 dowel - and
  carries a two-rod spring stage with 15 mm of compliant travel along the pen axis.
* Carriage (printed): slides on the rods; has a dovetail rail and an M6 ball spring plunger.
* Cartridge (printed, no hardware): slides up onto the rail until the plunger clicks into
  its detent, and pulls straight off. The plunger also pushes the dovetail flanks together
  so the cartridge sits without play. Print several and keep different pens loaded.
* Twist chucks: two of them, one at each end of the cartridge's pen tube, so the pen is held at
  two points far apart and cannot rock. In each, three jaws are driven by spiral slots in a
  knurled ring. Up to a third of a turn clamps or releases any pen from 6 to 17 mm and always
  centres it, so the TCP does not change with pen diameter. The shallow spiral is self-locking,
  and two spring fingers per chuck click into ratchet flutes inside the ring, so a knock can't
  turn it back past a click.
  The upper chuck is the lower one upside down, so both use the same ring and jaws.

Frame M (mm): origin = centre of the flange face, flange face = plane y = 0 with the arm
on +Y, pen axis = Z with the tip pointing -Z (the tool as it hangs when the flange axis is
horizontal). Flange frame F (Z into the arm, X towards the dowel): X_F = Z_M, Y_F = X_M,
Z_F = Y_M.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from build123d import (
    Align,
    Box,
    Circle,
    Color,
    Compound,
    Cone,
    Cylinder,
    Face,
    Kind,
    Location,
    Part,
    Plane,
    Pos,
    Rot,
    Shape,
    Sphere,
    Spline,
    Wire,
    export_gltf,
    export_step,
    export_stl,
    extrude,
    offset,
    sweep,
    trace,
)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "Pen Holder"))
import pen_holder as ph  # noqa: E402  (flange interface, shared helpers)
from pen_holder import cut_all, hex_prism, polar, revolved, zcyl  # noqa: E402

# Shapes modelled in the flange frame F (like the v1 adapter) are moved into frame M with this.
F2M = Location(Plane(origin=(0, 0, 0), x_dir=(0, 0, 1), z_dir=(0, 1, 0)))

# =============================================================================
# Base (bolts to the flange with the same interface as the v1 tool adapter)
# =============================================================================
BASE_T = 12.0  # plate thickness in front of the boss face (M5x12 heads sit flush)
STAGE_W = 43.0  # width of the chin and the stage frame (clear of the M5 heads at x = ±27.7)
STAGE_FRONT_Y = -25.0  # front face of the end blocks and side walls
SIDE_WALL_T = 4.0
TOP_BLOCK_H = 14.0
BOTTOM_BLOCK_H = 15.0

# =============================================================================
# Stage: two rods, carriage, two springs
# =============================================================================
ROD_D = 6.0  # Ø6 x 80 steel rods (h6 linear shaft or ISO 8734 dowel pins)
ROD_LEN = 80.0
ROD_X = 12.0  # rods at x = ±12
ROD_Y = -19.0
ROD_HOLE_D = 6.05
BUSHING_D = 6.2  # printed bushings in the carriage - ream for a smooth sliding fit
CARRIAGE_W = 34.0
CARRIAGE_Y = (-25.5, -12.5)  # front and back faces
CARRIAGE_L = 36.0
STROKE = 15.0  # compliant travel before the carriage hits the top block
STAGE_SPRING_OD = 8.0  # 2x compression spring 0.5 x 8 x 40 mm, around the rods
STAGE_SPRING_WIRE = 0.5
STAGE_SPRING_L0 = 40.0
STAGE_SPRING_ACTIVE = 14
SPRING_POCKET_D = 8.8
SPRING_POCKET_DEPTH = 9.0  # in the carriage and in the top block
Z_C0 = -49.0  # carriage bottom at rest (= rest stop on the bottom block = cartridge seat)

# =============================================================================
# Dock: dovetail rail on the carriage + M6 ball spring plunger
# =============================================================================
RAIL_W0, RAIL_W1, RAIL_H = 14.0, 19.0, 4.0  # width at the carriage face, outer width, height
DOVETAIL_CLEARANCE = 0.3
PLUNGER_Z = 6.0  # above the carriage bottom
PLUNGER_LEN = 14.0
PLUNGER_TAP_D = 5.0  # M6 thread-forming into the print
PLUNGER_BALL_D = 3.5  # M6 ball plungers: Ø3.5 ball, about 0.8-1 mm of ball travel
PLUNGER_BALL_FREE = 1.0  # assumed worst case: ball protrusion of an unloaded plunger
BALL_PROUD = 0.65  # target ball protrusion past the plunger face with a cartridge seated
DETENT_D = 2.2  # 90° dimple in the cartridge; the ball rests on its rim
LEAD_IN = 1.5  # 45° chamfer at the open end of the slot so the ball rides onto the slot floor
ACCESS_HOLE_D = 9.0  # hex-key access to the lowest M5 screw through the carriage

# =============================================================================
# Cartridge + twist chuck
# =============================================================================
PEN_Y = -56.0  # pen axis, 56 mm in front of the flange face
SPINE_W = 25.0
SPINE_FRONT_Y = -46.0
SPINE_TOP_Z = -15.0
CHUCK_D = 43.0  # jaw section, also the journal the ring turns on
JAW_SECTION_H = 16.0
TUBE_OD = 23.0  # pen tube joining the lower and upper chucks along the front of the spine
UPPER_CHUCK_GAP = 1.0  # upper ring above the spine top
RING_OD = 48.4  # knurled all round; small enough for the upper ring to slide past the rail and plunger
RING_WHEEL_T = 4.0
RING_SLEEVE_H = 4.0
RING_CLEARANCE = 0.4  # diametral, sleeve on the journal
SNAP = 0.5  # radial height of the snap ridge that keeps the ring on
PEN_HOLE_D = 18.0
PEN_D_MIN, PEN_D_MAX = 6.0, 17.0
JAW_ANGLES = (-90.0, 30.0, 150.0)  # one jaw at the front, two at the back
JAW_W, JAW_H, JAW_L = 6.0, 14.0, 12.5
JAW_TIP_W = 1.2
JAW_NOTCH = 1.0  # outer-bottom corner relief so fully open jaws clear the ring's snap ridge
# Pin that runs in the ring's spiral slot: as thick as the slot geometry allows and short to keep the bending lever
# small. The jaws print on their side, so the pin's layers run along it (no layer line at its root); a 45° teardrop
# facing the slot's open end lets it print without support.
JAW_PIN_D, JAW_PIN_L, JAW_PIN_U = 3.6, 2.5, 9.1  # pin Ø, length, distance from the jaw tip
SLOT_W = JAW_PIN_D + 0.4
PIN_TWIST_TORQUE = 1.0  # N·m, a hard twist of a ring by hand; about 0.1 N·m already holds the pen
PETG_STRENGTH = 45.0  # MPa, along the print lines
SLOT_SWEEP = 120.0  # ring rotation from fully open to fully closed, degrees (shallow spiral = self-locking)
# Detent: two spring fingers on each chuck body, between the jaw grooves and clear of the tongue, click into flutes
# inside the ring's sleeve. The flutes are ratchet-shaped: a gentle ramp to tighten over, a steep wall against
# loosening, so a finger resting on a flute flank never pushes the ring open. The fingers print standing up (their
# root is a layer line), so they are sized to stay at low strain. Notches in the ring's snap ridge line up with the
# fingers when the ring is fully open, so pushing the ring on doesn't bend them.
DETENT_ANGLES = (210.0, 330.0)
DETENT_FLUTES = 60  # a click every 6°
DETENT_DEPTH = 0.3  # finger deflection when its bump rides over a land between flutes
DETENT_FINGER = (1.2, 6.0, 14.0)  # radial thickness, width, length (PETG)
DETENT_RAMP, DETENT_WALL = 20.0, 50.0  # flute flanks from the tangent: tightening side, loosening side (degrees)
PETG_LAYER_STRENGTH = 25.0  # MPa, across layers
PEN_STICKOUT = 25.0  # tip below the lower ring (use the printed gauge)
GAUGE_D, GAUGE_HOLE_D, GAUGE_FLOOR = 40.0, 21.0, 1.6

# =============================================================================
# Derived
# =============================================================================
Z_C1 = Z_C0 + CARRIAGE_L
Z_TB0 = Z_C1 + STROKE  # top block underside = hard stop
Z_TB1 = Z_TB0 + TOP_BLOCK_H
Z_BB0 = Z_C0 - BOTTOM_BLOCK_H
RAIL_FRONT_Y = CARRIAGE_Y[0] - RAIL_H
# The plunger pushes the cartridge outward until the dovetail flanks touch. The flanks are therefore the locating
# datum: the slot is cut (and the cartridge modelled) in that seated position, SEAT_SHIFT out from centred.
_flank_dx = (RAIL_W1 - RAIL_W0) / 2
SEAT_SHIFT = DOVETAIL_CLEARANCE * math.hypot(RAIL_H, _flank_dx) / _flank_dx
SLOT_FLOOR_Y = RAIL_FRONT_Y - DOVETAIL_CLEARANCE - SEAT_SHIFT
SPINE_BACK_Y = CARRIAGE_Y[0] - DOVETAIL_CLEARANCE  # also stops the cartridge being pushed in onto the plunger
Z_JS1 = Z_C0 - 1.0  # jaw-section top
Z_JS0 = Z_JS1 - JAW_SECTION_H  # jaw-section bottom = ring-wheel top
Z_W0 = Z_JS0 - RING_WHEEL_T  # ring-wheel bottom
Z_SLEEVE1 = Z_JS0 + RING_SLEEVE_H
Z_TONGUE0 = Z_SLEEVE1  # tongue joining spine and chuck, above the ring
Z_U1 = SPINE_TOP_Z + UPPER_CHUCK_GAP + RING_SLEEVE_H  # upper chuck: jaw-section top = upper ring-wheel bottom
Z_U0 = Z_U1 - JAW_SECTION_H
Z_FLARE0 = Z_U0 - (CHUCK_D - TUBE_OD) / 2  # 45° flare carries the upper chuck when printed
# The upper chuck is the lower one turned upside down: 180° about Y maps the jaw angles onto themselves, so it uses
# the same ring and jaws. Each chuck's jaws bear hardest at their pinned ends, so the pen is held at both ends of
# this span.
FLIP = Pos(0, 0, Z_JS0 + Z_U1) * Rot(0, 180, 0)
GRIP_SPAN = Z_U1 - Z_JS0
Z_TIP = Z_W0 - PEN_STICKOUT
TCP_F = (Z_TIP, 0.0, PEN_Y)  # pen tip in the flange frame (spring relaxed)
R_TIP_MIN, R_TIP_MAX = PEN_D_MIN / 2, PEN_D_MAX / 2 + 0.5
R_PIN_CLOSED, R_PIN_OPEN = R_TIP_MIN + JAW_PIN_U, R_TIP_MAX + JAW_PIN_U
SPRING_REST_LEN = STROKE + 2 * SPRING_POCKET_DEPTH
SPRING_PRELOAD = STAGE_SPRING_L0 - SPRING_REST_LEN
_D = STAGE_SPRING_OD - STAGE_SPRING_WIRE
STAGE_RATE = 2 * ph.SPRING_G * STAGE_SPRING_WIRE**4 / (8 * _D**3 * STAGE_SPRING_ACTIVE)  # both springs
SLOT_SLOPE = (R_PIN_OPEN - R_PIN_CLOSED) / (math.radians(SLOT_SWEEP) * (R_PIN_OPEN + R_PIN_CLOSED) / 2)
SLOT_SLOPE_MAX = (R_PIN_OPEN - R_PIN_CLOSED) / (math.radians(SLOT_SWEEP) * R_PIN_CLOSED)  # steepest: smallest pen
_r_ball = PLUNGER_BALL_D / 2
BALL_DROP = _r_ball - math.sqrt(_r_ball**2 - (DETENT_D / 2) ** 2)  # how far the ball sinks into the dimple
BALL_Y = SLOT_FLOOR_Y - BALL_DROP + _r_ball  # ball centre with the cartridge seated
PLUNGER_FACE_Y = BALL_Y - _r_ball + BALL_PROUD
PLUNGER_SET = RAIL_FRONT_Y - PLUNGER_FACE_Y  # how far the plunger face stands proud of the rail
BALL_PROUD_SLIDING = PLUNGER_FACE_Y - SLOT_FLOOR_Y  # while the ball rides along the slot floor


def ring_angle(pen_d: float) -> float:
    """Ring rotation (deg) at which the jaws close on a pen of this diameter."""
    r_pin = pen_d / 2 + JAW_PIN_U
    return (R_PIN_OPEN - r_pin) / (R_PIN_OPEN - R_PIN_CLOSED) * SLOT_SWEEP


# =============================================================================
# Helpers
# =============================================================================
def box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Part:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))


def ycyl(d: float, x: float, z: float, y0: float, y1: float) -> Part:
    """Cylinder along Y at (x, z) between y0 and y1."""
    lo, hi = min(y0, y1), max(y0, y1)
    return Pos(x, lo, z) * Rot(-90, 0, 0) * Cylinder(d / 2, hi - lo, align=(Align.CENTER, Align.CENTER, Align.MIN))


def prism_xy(pts: list[tuple[float, float]], z0: float, z1: float) -> Part:
    """Extrude a closed XY polygon from z0 to z1."""
    face = Face(Wire.make_polygon([(x, y, 0) for x, y in pts], close=True))
    return Pos(0, 0, z0) * extrude(face, z1 - z0, dir=(0, 0, 1))


def prism_yz(pts: list[tuple[float, float]], x0: float, x1: float) -> Part:
    """Extrude a closed (y, z) polygon from x0 to x1."""
    face = Face(Wire.make_polygon([(0, y, z) for y, z in pts], close=True))
    return Pos(x0, 0, 0) * extrude(face, x1 - x0, dir=(1, 0, 0))


def at_pen(shape: Shape) -> Shape:
    return Pos(0, PEN_Y, 0) * shape


def rail_profile(grow: float = 0.0) -> list[tuple[float, float]]:
    """Dovetail cross-section (x, y), optionally grown by `grow` normal to every face."""
    y0, y1 = CARRIAGE_Y[0], RAIL_FRONT_Y
    pts = [(-RAIL_W0 / 2, y0 + 2.0), (RAIL_W0 / 2, y0 + 2.0), (RAIL_W0 / 2, y0), (RAIL_W1 / 2, y1),
           (-RAIL_W1 / 2, y1), (-RAIL_W0 / 2, y0)]
    if grow:
        face = offset(Face(Wire.make_polygon([(x, y, 0) for x, y in pts], close=True)), grow, kind=Kind.INTERSECTION)
        return [(v.X, v.Y) for v in face.vertices()]
    return pts


# =============================================================================
# Printed part 1: base
# =============================================================================
def make_base() -> Part:
    r_out, r_pilot = ph.ADAPTER_OD / 2, (ph.PILOT_D + ph.PILOT_CLEARANCE) / 2
    zt = ph.PILOT_RECESS_DEPTH
    plate = F2M * revolved(
        [
            (0, -BASE_T),
            (r_out - 1.0, -BASE_T),
            (r_out, -BASE_T + 1.0),
            (r_out, zt - 0.6),
            (r_out - 0.6, zt),
            (r_pilot + 0.5, zt),
            (r_pilot, zt - 0.5),
            (r_pilot, 0.0),
            (ph.RELIEF_D / 2, 0.0),
            (ph.RELIEF_D / 2, -ph.RELIEF_DEPTH),
            (0, -ph.RELIEF_DEPTH),
        ]
    )
    hw, wall = STAGE_W / 2, SIDE_WALL_T
    yb, yf = -BASE_T + 0.01, STAGE_FRONT_Y
    chin = r_out * math.sin(math.radians(45))  # carries the disc's lower rim: no overhang over 45° upright
    body = plate + box(-chin, chin, -BASE_T, 0.0, Z_BB0, -30.0)  # chin below the flange
    body += box(-hw, hw, yf, yb, Z_TB0, Z_TB1)  # top block (hard stop)
    body += box(-hw, hw, yf, yb, Z_BB0, Z_C0)  # bottom block (rest stop)
    for s in (-1, 1):  # side walls tie the blocks together and let the top block print as a bridge
        body += box(s * hw, s * (hw - wall), yf, yb, Z_BB0, Z_TB1)

    tools = []
    for i in range(ph.BOLT_COUNT):  # arm interface, modelled in the flange frame
        x, y = polar(ph.BOLT_PCD / 2, i * 360 / ph.BOLT_COUNT)
        tools.append(F2M * (Pos(x, y, 0) * zcyl(ph.M5_CLEAR_D, -BASE_T - 1, 1)))
        tools.append(F2M * (Pos(x, y, 0) * zcyl(ph.M5_CBORE_D, -BASE_T - 1, ph.Z_M5_SEAT)))
    tools.append(F2M * (Pos(ph.DOWEL_PCD / 2, 0, 0) * zcyl(ph.DOWEL_HOLE_D, -BASE_T - 1, 1)))
    for s in (-1, 1):
        x = s * ROD_X
        tools.append(Pos(x, ROD_Y, 0) * zcyl(ROD_HOLE_D, Z_BB0 - 1, Z_TB1 + 1))
        tools.append(Pos(x, ROD_Y, 0) * zcyl(SPRING_POCKET_D, Z_TB0 - 1, Z_TB0 + SPRING_POCKET_DEPTH))
        tools.append(ycyl(2.5, x, Z_TB1 - 3.0, yf - 1, ROD_Y))  # M3 set screw locks the rod
    return cut_all(body, tools)


# =============================================================================
# Printed part 2: carriage (local z = 0 at its bottom face)
# =============================================================================
def make_carriage() -> Part:
    hw = CARRIAGE_W / 2
    yf, yb = CARRIAGE_Y
    body = box(-hw, hw, yf, yb, 0, CARRIAGE_L) + prism_xy(rail_profile(), 0, CARRIAGE_L)
    tools = []
    for s in (-1, 1):
        tools.append(Pos(s * ROD_X, ROD_Y, 0) * zcyl(BUSHING_D, -1, CARRIAGE_L + 1))
        tools.append(Pos(s * ROD_X, ROD_Y, 0) * zcyl(SPRING_POCKET_D, CARRIAGE_L - SPRING_POCKET_DEPTH, CARRIAGE_L + 1))
    tools.append(ycyl(PLUNGER_TAP_D, 0, PLUNGER_Z, RAIL_FRONT_Y - 1, yb + 1))  # through: driven from behind
    m5 = polar(ph.BOLT_PCD / 2, 180.0)  # lowest M5 screw (F frame) sits behind the carriage
    tools.append(ycyl(ACCESS_HOLE_D, 0, m5[0] - Z_C0, RAIL_FRONT_Y - 1, yb + 1))
    return cut_all(body, tools)


# =============================================================================
# Printed part 3: cartridge body (frame M, cartridge seated, carriage at rest)
# =============================================================================
def chuck_tools() -> list[Shape]:
    """Jaw grooves and ring snap groove of the lower chuck; FLIP turns them into the upper chuck's."""
    r_js = CHUCK_D / 2
    tools = []
    for a in JAW_ANGLES:  # radial jaw grooves, open at the end face and the rim
        tools.append(at_pen(Rot(0, 0, a) * box(0, r_js + 2, -(JAW_W + 0.3) / 2, (JAW_W + 0.3) / 2,
                                                Z_JS0 - 1, Z_JS0 + JAW_H + 0.3)))
    zr0, zr1 = Z_SLEEVE1 - 1.2 - SNAP, Z_SLEEVE1 + 0.2
    tools.append(at_pen(zcyl(CHUCK_D + 2, zr0, zr1) - zcyl(CHUCK_D - 2 * (SNAP + 0.2), zr0 - 1, zr1 + 1)))
    return tools


def detent_parts() -> tuple[list[Shape], list[Shape]]:
    """Lower chuck's detent: pockets to cut, and spring fingers with a 90° bump to add. FLIP gives the upper ones.

    Each finger stands in its pocket, free at the chuck's end face and joined to the body at its root, and its
    bump reaches DETENT_DEPTH past the ring's bore into the flutes.
    """
    t, w, length = DETENT_FINGER
    r1 = CHUCK_D / 2 - 0.9  # finger outer face, inside the snap groove's floor
    r_tip = (CHUCK_D + RING_CLEARANCE) / 2 + DETENT_DEPTH
    h_bump = 2.2
    # 45° lead-in at the free end, so the bump rides up onto a land if the ring is pushed on off its notches
    lead_in = at_pen(Pos(0, 0, Z_JS0) * Cone(r_tip - 1.0, r_tip - 1.0 + h_bump, h_bump,
                                             align=(Align.CENTER, Align.CENTER, Align.MIN)))
    cuts, adds = [], []
    for a in DETENT_ANGLES:
        rot = Rot(0, 0, a)
        cuts.append(at_pen(rot * box(r1 - t - 1.0, CHUCK_D / 2 + 1.5, -w / 2 - 0.5, w / 2 + 0.5,
                                     Z_JS0 - 1, Z_JS0 + length)))
        finger = box(r1 - t, r1, -w / 2, w / 2, Z_JS0, Z_JS0 + length + 0.5)
        # local +y = +θ: steep face against the flutes' steep (loosening) wall, 45° face on the tightening side
        h = r_tip - (r1 - 0.1)
        bump = prism_xy([(r1 - 0.1, -h), (r_tip, 0.0), (r1 - 0.1, h / math.tan(math.radians(DETENT_WALL)))],
                        Z_JS0, Z_JS0 + h_bump)
        adds.append(at_pen(rot * finger) + (at_pen(rot * bump) & lead_in))
    return cuts, adds


def make_cartridge() -> Part:
    hw = SPINE_W / 2
    r_js = CHUCK_D / 2
    body = at_pen(zcyl(CHUCK_D, Z_JS0, Z_JS1))
    body += box(-hw, hw, SPINE_FRONT_Y, SPINE_BACK_Y, Z_JS1 - 0.01, SPINE_TOP_Z)
    # tongue joining spine and chuck above the ring; 45° underside so it prints without support
    y_c = PEN_Y + math.sqrt(r_js**2 - hw**2)
    rise = SPINE_BACK_Y - y_c
    if Z_TONGUE0 + rise <= Z_JS1:
        tongue = [(PEN_Y, Z_TONGUE0), (y_c, Z_TONGUE0), (SPINE_BACK_Y, Z_TONGUE0 + rise), (SPINE_BACK_Y, Z_JS1)]
    else:  # the 45° underside meets the spine's bottom face just short of its back
        tongue = [(PEN_Y, Z_TONGUE0), (y_c, Z_TONGUE0), (y_c + Z_JS1 - Z_TONGUE0, Z_JS1)]
    body += prism_yz([*tongue, (PEN_Y, Z_JS1)], -hw, hw)
    # pen tube up the front of the spine, then the upper chuck on a 45° flare
    body += at_pen(zcyl(TUBE_OD, Z_JS1 - 0.01, Z_FLARE0 + 0.01))
    body += at_pen(Pos(0, 0, Z_FLARE0) * Cone(TUBE_OD / 2, r_js, Z_U0 - Z_FLARE0,
                                               align=(Align.CENTER, Align.CENTER, Align.MIN)))
    body += at_pen(zcyl(CHUCK_D, Z_U0 - 0.01, Z_U1))

    lower = chuck_tools()
    tools = [at_pen(zcyl(PEN_HOLE_D, Z_JS0 - 1, Z_U1 + 1)), *lower, *(FLIP * t for t in lower)]
    # dovetail slot (open at the top, closed at the seat), the plunger's detent dimple and a lead-in for the ball
    tools.append(Pos(0, -SEAT_SHIFT, 0) * prism_xy(rail_profile(DOVETAIL_CLEARANCE), Z_C0, SPINE_TOP_Z + 1))
    tools.append(Pos(0, SLOT_FLOOR_Y + 0.01, Z_C0 + PLUNGER_Z) * Rot(90, 0, 0)
                 * Cone(DETENT_D / 2, 0.3, DETENT_D / 2 - 0.3, align=(Align.CENTER, Align.CENTER, Align.MIN)))
    z_top = SPINE_TOP_Z
    tools.append(prism_yz([(SLOT_FLOOR_Y + 0.01, z_top - LEAD_IN - 0.01), (SLOT_FLOOR_Y + 0.01, z_top + 1),
                           (SLOT_FLOOR_Y - LEAD_IN - 1.0, z_top + 1)], -RAIL_W1 / 2 - 1, RAIL_W1 / 2 + 1))
    d_cuts, d_adds = detent_parts()
    body = cut_all(body, [*tools, *d_cuts, *(FLIP * c for c in d_cuts)])
    for finger in (*d_adds, *(FLIP * f for f in d_adds)):  # added after the cuts: they stand inside the pockets
        body += finger
    return body


# =============================================================================
# Printed part 4: twist ring (local: pen axis = Z at the origin, rotation 0 = fully open)
# =============================================================================
def make_ring() -> Part:
    r_o, r_j, r_h = RING_OD / 2, (CHUCK_D + RING_CLEARANCE) / 2, PEN_HOLE_D / 2
    ring = revolved(
        [
            (r_h, Z_W0),
            (r_o - 0.8, Z_W0),
            (r_o, Z_W0 + 0.8),
            (r_o, Z_SLEEVE1 - 0.8),
            (r_o - 0.8, Z_SLEEVE1),
            (r_j, Z_SLEEVE1),  # snap ridge: 45° lead-in on top rides the ring over the chuck and detent bumps,
            (r_j - SNAP, Z_SLEEVE1 - SNAP),  # 45° underneath lets it be pulled off again to service the jaws
            (r_j - SNAP, Z_SLEEVE1 - 1.0),
            (r_j, Z_SLEEVE1 - 1.0 - SNAP),
            (r_j, Z_JS0),
            (r_h, Z_JS0),
        ]
    )
    tools = []
    for a in JAW_ANGLES:  # spiral slot per jaw: radius falls as the ring turns
        pts = []
        for i in range(25):
            s = i / 24
            r = R_PIN_OPEN - (R_PIN_OPEN - R_PIN_CLOSED) * s
            pts.append((*polar(r, a - s * SLOT_SWEEP), Z_W0 - 1))
        path = Spline(*pts)
        slot = trace(path, line_width=SLOT_W)
        for p in (pts[0], pts[-1]):
            slot += Pos(p[0], p[1], p[2]) * Circle(SLOT_W / 2)
        # room for the pin's teardrop point (towards the jaw's +Y, i.e. the open end) when fully open
        dx, dy = polar((math.sqrt(2) - 1) * JAW_PIN_D / 2, a + 90.0)
        slot += Pos(pts[0][0] + dx, pts[0][1] + dy, pts[0][2]) * Circle(SLOT_W / 2)
        tools.append(extrude(slot, RING_WHEEL_T + 2, dir=(0, 0, 1)))
    for i in range(40):  # knurl
        tools.append(Pos(*polar(r_o + 0.25, i * 9.0), 0) * zcyl(1.3, Z_W0 - 1, Z_SLEEVE1 + 1))
    d = DETENT_DEPTH + 0.1  # flute depth: the seated bump keeps 0.1 mm clear, so the fingers rest unloaded
    # ratchet flute, local +y = +θ: the ring turns +θ to tighten, so a finger climbs out over the gentle -θ ramp
    # and must climb the steep +θ wall to loosen
    flute = prism_xy([(r_j - 0.1, -(d + 0.1) / math.tan(math.radians(DETENT_RAMP))), (r_j + d, 0.0),
                      (r_j - 0.1, (d + 0.1) / math.tan(math.radians(DETENT_WALL)))], Z_JS0, Z_JS0 + 2.4)
    for i in range(DETENT_FLUTES):  # detent flutes below the snap ridge
        tools.append(Rot(0, 0, i * 360 / DETENT_FLUTES) * flute)
    r_tip = r_j + DETENT_DEPTH
    # notches in the snap ridge: the fully open ring slides on past the finger bumps. Repeated every 120° like the
    # slots, so the ring fits on in any of its three orientations
    for a in sorted({(d + k * 120.0) % 360 for d in DETENT_ANGLES for k in range(3)}):
        tools.append(Rot(0, 0, a) * box(r_j - SNAP - 0.5, r_tip + 0.2, -1.4, 1.4, Z_JS0 + 2.0, Z_SLEEVE1 + 1))
    return cut_all(ring, tools)


# =============================================================================
# Printed part 5: jaw (local: tip at x = 0, radial direction +X), 3 per cartridge
# =============================================================================
def make_jaw() -> Part:
    hw, ht = JAW_W / 2, JAW_TIP_W / 2
    taper = (hw - ht) / math.tan(math.radians(50))  # tip tapers so three jaws can close on a 6 mm pen
    jaw = prism_xy([(0, -ht), (taper, -hw), (JAW_L, -hw), (JAW_L, hw), (taper, hw), (0, ht)], Z_JS0, Z_JS0 + JAW_H)
    jaw -= box(JAW_L - JAW_NOTCH, JAW_L + 1, -hw - 1, hw + 1, Z_JS0 - 1, Z_JS0 + RING_SLEEVE_H + 0.4)
    u, r, k = JAW_PIN_U, JAW_PIN_D / 2, math.sqrt(0.5)
    z0, z1 = Z_JS0 - JAW_PIN_L, Z_JS0 + 0.5
    pin = Pos(u, 0, 0) * zcyl(JAW_PIN_D, z0, z1)
    pin += prism_xy([(u - r * k, r * k), (u, r * math.sqrt(2)), (u + r * k, r * k), (u, 0)], z0, z1)  # teardrop, +Y
    return jaw + pin


# =============================================================================
# Printed part 6: stick-out gauge (stand the cartridge on it, push the pen to the bottom)
# =============================================================================
def make_gauge() -> Part:
    """Ring face sits on the rim, pen tip on the floor -> tip PEN_STICKOUT below the ring."""
    h = PEN_STICKOUT + GAUGE_FLOOR
    g = revolved([(0, 0), (GAUGE_D / 2 - 1, 0), (GAUGE_D / 2, 1), (GAUGE_D / 2, h - 0.6),
                  (GAUGE_D / 2 - 0.6, h), (0, h)])
    return g - zcyl(GAUGE_HOLE_D, GAUGE_FLOOR, h + 1)


# =============================================================================
# Hardware and pens (visual)
# =============================================================================
def make_rod() -> Part:
    r, c = ROD_D / 2, 0.5
    return revolved([(0, 0), (r - c, 0), (r, c), (r, ROD_LEN - c), (r - c, ROD_LEN), (0, ROD_LEN)])


def make_plunger() -> Part:
    """M6 ball spring plunger: face at y = 0, body along +Y, ball pushed in to its seated position."""
    r_b = PLUNGER_BALL_D / 2
    body = ycyl(6.0, 0, 0, 0, PLUNGER_LEN) - ycyl(PLUNGER_BALL_D + 0.1, 0, 0, -1, r_b + 1.5)
    body -= Pos(0, PLUNGER_LEN + 0.1, 0) * Rot(90, 0, 0) * hex_prism(3.0, 0, 2.5)
    return body + Pos(0, r_b - BALL_PROUD, 0) * Sphere(r_b)


def make_coil_spring(length: float) -> Part:
    """Closed-and-ground compression spring along Z from 0 to length."""
    d, r = STAGE_SPRING_WIRE, (STAGE_SPRING_OD - STAGE_SPRING_WIRE) / 2
    n_total = STAGE_SPRING_ACTIVE + 2
    p_active = (length - 3 * d) / STAGE_SPRING_ACTIVE

    def smooth(x: float) -> float:
        x = min(max(x, 0.0), 1.0)
        return x * x * (3 - 2 * x)

    pts, z, k = [], d / 2, 16
    for i in range(int(n_total * k) + 1):
        if i:
            t = (i - 0.5) / k
            z += (d + (p_active - d) * smooth((t - 0.75) / 0.5) * (1 - smooth((t - (n_total - 1.25)) / 0.5))) / k
        a = 2 * math.pi * i / k
        pts.append((r * math.cos(a), r * math.sin(a), z))
    path = Spline(*pts)
    coil = sweep(Plane(origin=path @ 0, z_dir=path % 0) * Circle(d / 2), path=path, is_frenet=True)
    return coil & zcyl(STAGE_SPRING_OD + 2, 0, length)


PENS = {  # name: (barrel Ø, length, barrel material) - the chucks take anything from 6 to 17 mm
    "Ballpoint 8 mm": (8.0, 148.0, "pen_blue"),
    "Gel pen 11 mm": (11.0, 145.0, "pen_black"),
    "Whiteboard marker 16 mm": (16.0, 128.0, "pen_red"),
}


def make_pen(d: float, length: float) -> tuple[Part, Part, Part]:
    """Generic pen, tip at the origin: (nib, front cone, barrel)."""
    r = d / 2
    nib_r = 0.6 if d < 10 else 1.4
    nib = revolved([(0, 0), (nib_r * 0.4, 0), (nib_r, 0.8), (nib_r, 3.5), (0, 3.5)])
    cone_len = 9.0 + r
    front = revolved([(0, 3.0), (nib_r + 0.6, 3.0), (r * 0.75, cone_len * 0.75), (r, cone_len), (0, cone_len)])
    barrel = revolved([(0, cone_len), (r, cone_len), (r, length - 1.0), (r - 1.0, length), (0, length)])
    return nib, front, barrel


# =============================================================================
# Assembly
# =============================================================================
COLORS = {**ph.COLORS, "pen_blue": "#1f4fa8", "pen_red": "#b3202a", "cartridge": "#dcdfe3"}


@dataclass
class Item:
    name: str
    shape: Shape
    material: str
    explode: tuple[float, float, float] = (0.0, 0.0, 0.0)


_cache: dict = {}


def _cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]


EX_CARRIAGE = (0.0, -40.0, 0.0)
EX_CARTRIDGE = (0.0, -95.0, -60.0)


def cartridge_items(pen: str | None, up: float = 0.0, place: Location | None = None,
                    label: str = "", explode: bool = False) -> list[Item]:
    """Cartridge body, ring, jaws and (optionally) a pen, clamped and seated on the carriage."""
    move = (place or Location()) * Pos(0, 0, up)
    pen_d = PENS[pen][0] if pen else PEN_D_MAX + 1.0
    r_tip = min(pen_d / 2, R_TIP_MAX)
    psi = ring_angle(2 * r_tip)
    ex = EX_CARTRIDGE
    ring, jaw = _cached("ring", make_ring), _cached("jaw", make_jaw)
    items = [Item(f"{label}Cartridge body", move * _cached("cartridge", make_cartridge), "cartridge", ex)]
    for tag, flip, s in (("lower", Location(), -1), ("upper", FLIP, 1)):
        items.append(Item(f"{label}Twist ring ({tag})", move * flip * at_pen(Rot(0, 0, psi) * ring), "accent",
                          (ex[0], ex[1], ex[2] + s * 30)))
        for i, a in enumerate(JAW_ANGLES):
            shape = move * flip * at_pen(Rot(0, 0, a) * Pos(r_tip, 0, 0) * jaw)
            dx, dy = polar(14.0 if explode else 0.0, a if s < 0 else 180.0 - a)
            items.append(Item(f"{label}Jaw {i + 1} ({tag})", shape, "printed", (ex[0] + dx, ex[1] + dy, ex[2] + s * 12)))
    if pen:
        d, length, colour = PENS[pen]
        nib, front, barrel = _cached(("pen", pen), lambda: make_pen(d, length))
        tip = move * Pos(0, PEN_Y, Z_TIP)
        exp = (ex[0], ex[1], ex[2] - 70)
        items += [Item(f"{label}{pen} nib", tip * nib, "pen_nib", exp),
                  Item(f"{label}{pen} front", tip * front, "pen_black", exp),
                  Item(f"{label}{pen} barrel", tip * barrel, colour, exp)]
    return items


def assembly(travel: float = 0.0, pen: str | None = "Gel pen 11 mm", arm: bool = True, hardware: bool = True,
             explode: bool = False) -> list[Item]:
    if not 0.0 <= travel <= STROKE:
        raise ValueError(f"travel must be within 0..{STROKE} mm")
    up = travel
    items: list[Item] = []
    if arm:
        items.append(Item("UTRA 6-1000 tool flange (ref)", F2M * _cached("arm_flange", ph.make_arm_flange),
                          "aluminum", (0, 60, 0)))
        items.append(Item("UTRA 6-1000 J6 housing (ref)", F2M * _cached("arm_housing", ph.make_arm_housing),
                          "arm_dark", (0, 60, 0)))
    items.append(Item("Base", _cached("base", make_base), "printed"))
    items.append(Item("Carriage", Pos(0, 0, Z_C0 + up) * _cached("carriage", make_carriage), "accent", EX_CARRIAGE))
    spring = _cached(("spring", round(SPRING_REST_LEN - up, 3)), lambda: make_coil_spring(SPRING_REST_LEN - up))
    for s in (-1, 1):
        x = s * ROD_X
        items.append(Item(f"Rod {'L' if s < 0 else 'R'}", Pos(x, ROD_Y, Z_BB0) * _cached("rod", make_rod),
                          "steel", (0, 0, 100)))
        items.append(Item(f"Stage spring {'L' if s < 0 else 'R'}",
                          Pos(x, ROD_Y, Z_C1 + up - SPRING_POCKET_DEPTH) * spring, "spring",
                          (EX_CARRIAGE[0], EX_CARRIAGE[1], 48)))
    if hardware:
        m5 = _cached("m5", lambda: ph.make_shcs(5.0, ph.M5_SCREW_LEN, ph.M5_HEAD_D, ph.M5_HEAD_H, 4.0))
        for i in range(ph.BOLT_COUNT):
            x, y = polar(ph.BOLT_PCD / 2, i * 360 / ph.BOLT_COUNT)
            items.append(Item(f"M5x12 SHCS {i + 1}", F2M * (Pos(x, y, ph.Z_M5_SEAT) * m5), "steel_black", (0, -30, 0)))
        z_dowel = ph.DOWEL_HOLE_DEPTH - 0.5 - ph.DOWEL_LEN
        items.append(Item("Dowel pin 3x8", F2M * (Pos(ph.DOWEL_PCD / 2, 0, z_dowel) * _cached("dowel", ph.make_dowel)),
                          "steel", (0, 30, 0)))
        set_screw = _cached("set3", lambda: ph.make_set_screw(3.0, 3.0, 1.5))
        for s in (-1, 1):
            items.append(Item(f"M3x3 set screw {'L' if s < 0 else 'R'}",
                              Pos(s * ROD_X, ROD_Y - ROD_D / 2, Z_TB1 - 3.0) * Rot(0, 0, -90) * set_screw,
                              "steel_black", (0, -20, 0)))
        items.append(Item("M6 ball spring plunger",
                          Pos(0, PLUNGER_FACE_Y, Z_C0 + up + PLUNGER_Z) * _cached("plunger", make_plunger),
                          "steel", (EX_CARRIAGE[0], EX_CARRIAGE[1] - 35, 0)))
    for it in cartridge_items(pen, up, explode=explode):
        items.append(it)
    return items


# =============================================================================
# Design checks and report
# =============================================================================
def design_checks() -> list[tuple[str, bool, str]]:
    hw_wall = STAGE_W / 2 - SIDE_WALL_T
    m5_side_x = ph.BOLT_PCD / 2 * math.sin(math.radians(60))
    access_z = -ph.BOLT_PCD / 2 - Z_C0
    worst = 0.0  # jaws closed on the smallest pen: angular half-width must stay under 60°
    hw, ht = JAW_W / 2, JAW_TIP_W / 2
    taper = (hw - ht) / math.tan(math.radians(50))
    for i in range(101):
        u = JAW_L * i / 100
        w = ht + (hw - ht) * min(u / taper, 1.0)
        worst = max(worst, math.degrees(math.asin(min(1.0, w / (R_TIP_MIN + u)))))
    solid = (STAGE_SPRING_ACTIVE + 2) * STAGE_SPRING_WIRE
    # Jaw pin under a hard twist with the smallest pen (pins at their smallest radius carry the most force):
    # slot-wall normal force from the ring torque, plus friction, acting halfway along the pin; 1.6 = sharp root.
    alpha, mu = math.atan(SLOT_SLOPE), 0.3
    f_pin = PIN_TWIST_TORQUE * 1000 / (3 * R_PIN_CLOSED * (math.sin(alpha) + mu * math.cos(alpha))) * math.hypot(1, mu)
    pin_stress = 1.6 * f_pin * JAW_PIN_L / 2 / (math.pi * JAW_PIN_D**3 / 32)
    # Detent finger: a cantilever loaded at its bump (~1.6 mm from the free end). It prints standing up, so its root
    # is a layer line: its bending stress (1.3 notch factor) must stay well under PETG's strength across layers, both
    # resting on a land and while a ring is turned back over the steep walls (which also bends it sideways).
    # Ratchet flutes: the clicks alone must hold a ring against the pen's back-drive at the steepest point of the
    # spiral even if PETG friction were only 0.2 (it is ~0.3, which already self-locks), with 20 N on each jaw.
    t_f, w_f, l_f = DETENT_FINGER
    l_eff, r_bore = l_f - 1.6, (CHUCK_D + RING_CLEARANCE) / 2
    f_finger = 3 * 2000 * (w_f * t_f**3 / 12) / l_eff**3 * DETENT_DEPTH
    s_rest = 1.3 * 1.5 * t_f * DETENT_DEPTH * 2000 / l_eff**2
    f_side = f_finger * math.tan(math.radians(DETENT_WALL) + math.atan(mu))
    s_release = s_rest + 1.3 * 6 * f_side * l_eff / (t_f * w_f**2)

    def ride(flank: float, mu_c: float) -> float:  # N·m to ride every finger over a flank
        return len(DETENT_ANGLES) * f_finger * math.tan(math.radians(flank) + math.atan(mu_c)) * r_bore / 1000

    a_max = math.atan(SLOT_SLOPE_MAX)
    backdrive = 3 * 20 * R_PIN_CLOSED * (math.sin(a_max) - 0.2 * math.cos(a_max)) / 1000
    hold, tighten, release = ride(DETENT_WALL, 0.2), ride(DETENT_RAMP, mu), ride(DETENT_WALL, mu)
    return [
        ("M5 engagement within the 6 mm arm thread", ph.M5_ENGAGEMENT <= ph.BOLT_THREAD_DEPTH - 0.5,
         f"{ph.M5_ENGAGEMENT:.1f} mm"),
        ("Rods span both end blocks", abs((Z_TB1 - Z_BB0) - ROD_LEN) < 1e-6, f"{ROD_LEN:g} mm"),
        ("Stage springs never go solid", solid < SPRING_REST_LEN - STROKE,
         f"solid {solid:.1f} < {SPRING_REST_LEN - STROKE:.1f} mm"),
        ("Spring ID clears the rod", STAGE_SPRING_OD - 2 * STAGE_SPRING_WIRE >= ROD_D + 0.5, ""),
        ("Spring pockets clear the springs", SPRING_POCKET_D >= STAGE_SPRING_OD + 0.5, ""),
        ("Carriage clears the side walls", CARRIAGE_W / 2 <= hw_wall - 0.4, f"{CARRIAGE_W / 2} <= {hw_wall - 0.4}"),
        ("Side M5 heads clear of the stage frame", STAGE_W / 2 <= m5_side_x - ph.M5_HEAD_D / 2 - 0.5,
         f"{STAGE_W / 2} <= {m5_side_x - ph.M5_HEAD_D / 2 - 0.5:.2f}"),
        ("Top M5 head clear above the top block", ph.BOLT_PCD / 2 - ph.M5_HEAD_D / 2 >= Z_TB1 + 0.5, ""),
        ("Lowest M5 reachable through the carriage", ACCESS_HOLE_D / 2 + 1 <= access_z <= CARRIAGE_L - ACCESS_HOLE_D / 2 - 1
         and access_z - ACCESS_HOLE_D / 2 >= PLUNGER_Z + 6.0 / 2 + 1, f"hole at carriage z = {access_z:.1f}"),
        ("Rings clear the base's end blocks", PEN_Y + RING_OD / 2 <= STAGE_FRONT_Y - 1.0,
         f"{PEN_Y + RING_OD / 2:.1f} <= {STAGE_FRONT_Y - 1.0:.1f}"),
        ("Upper ring slides past the rail and an unloaded plunger ball",
         PEN_Y + RING_OD / 2 <= PLUNGER_FACE_Y - PLUNGER_BALL_FREE - 0.3,
         f"{PEN_Y + RING_OD / 2:.1f} <= {PLUNGER_FACE_Y - PLUNGER_BALL_FREE - 0.3:.1f}"),
        ("Upper chuck clears the slot lead-in", PEN_Y + CHUCK_D / 2 <= SLOT_FLOOR_Y - LEAD_IN - 1.5, ""),
        ("Upper ring turns clear of the spine top", Z_U1 - RING_SLEEVE_H >= SPINE_TOP_Z + 0.5, ""),
        ("Pen tube joins the spine", PEN_Y + TUBE_OD / 2 >= SPINE_FRONT_Y + 1.0, ""),
        ("Every listed pen reaches through the upper ring",
         min(v[1] for v in PENS.values()) >= Z_U1 + RING_WHEEL_T + 5.0 - Z_TIP,
         f"needs {Z_U1 + RING_WHEEL_T + 5.0 - Z_TIP:.0f} mm"),
        ("Spine clears the largest pen", SPINE_FRONT_Y >= PEN_Y + PEN_D_MAX / 2 + 1.0, ""),
        ("Jaws stay inside the chuck when fully open", R_TIP_MAX + JAW_L <= CHUCK_D / 2 + 1e-6, ""),
        ("Open jaws clear the ring's snap ridge",
         math.hypot(R_TIP_MAX + JAW_L - JAW_NOTCH, JAW_W / 2) <= (CHUCK_D + RING_CLEARANCE) / 2 - SNAP - 0.3,
         f"r {math.hypot(R_TIP_MAX + JAW_L - JAW_NOTCH, JAW_W / 2):.2f}"),
        ("Jaws do not collide on the smallest pen", worst < 58.0, f"max half-angle {worst:.1f} deg"),
        ("Ring slot wall at the pen hole", R_PIN_CLOSED - SLOT_W / 2 - PEN_HOLE_D / 2 >= 1.0,
         f"{R_PIN_CLOSED - SLOT_W / 2 - PEN_HOLE_D / 2:.2f} mm"),
        ("Ring slots inside the knurl", R_PIN_OPEN + SLOT_W / 2 <= RING_OD / 2 - 2.5, ""),
        ("Spiral is self-locking even at its steepest (slope < 0.3 = PETG friction)", SLOT_SLOPE_MAX < 0.3,
         f"slope {SLOT_SLOPE_MAX:.2f} at the smallest pen, {SLOT_SLOPE:.2f} on average"),
        (f"Jaw pins survive a hard {PIN_TWIST_TORQUE:g} Nm twist (SF >= 1.5, printed on their side)",
         PETG_STRENGTH / pin_stress >= 1.5, f"{f_pin:.0f} N per pin, {pin_stress:.0f} MPa, SF {PETG_STRENGTH / pin_stress:.1f}"),
        ("Jaw pins sit clear of the jaw's tapered tip and notch",
         JAW_PIN_U - JAW_PIN_D / 2 >= 3.0 and JAW_PIN_U + JAW_PIN_D / 2 <= JAW_L - JAW_NOTCH - 0.3, ""),
        ("Neighbouring ring slots keep a 1.5 mm wall",
         (R_PIN_OPEN - R_PIN_CLOSED) * 120 / SLOT_SWEEP - SLOT_W >= 1.5, ""),
        ("Detent fingers: root stress well under PETG's layer strength (SF >= 2.5 on a land, 1.5 turning back)",
         PETG_LAYER_STRENGTH / s_rest >= 2.5 and PETG_LAYER_STRENGTH / s_release >= 1.5,
         f"{s_rest:.0f} MPa on a land, {s_release:.0f} MPa turning back"),
        ("Clicks alone hold a ring if friction were only 0.2; tightening is light, loosening easy by hand",
         hold > backdrive and tighten <= 0.05 and release <= 0.2,
         f"hold {hold:.3f} vs back-drive {max(backdrive, 0):.3f} Nm; tighten {tighten:.3f}, loosen {release:.3f} Nm"),
        ("Plunger ball stays within its stroke: 0.15 mm sliding to 0.75 mm seated (rests on the dimple rim)",
         BALL_PROUD_SLIDING >= 0.15 and BALL_PROUD <= 0.75 and DETENT_D / 2 <= _r_ball / math.sqrt(2),
         f"{BALL_PROUD_SLIDING:.2f} sliding, {BALL_PROUD:.2f} seated; face {PLUNGER_SET:.2f} mm proud of the rail"),
        ("Slot lead-in catches a fully extended ball, even with the cartridge pushed in",
         PLUNGER_SET + PLUNGER_BALL_FREE - SEAT_SHIFT <= LEAD_IN,
         f"ball tip {PLUNGER_SET + PLUNGER_BALL_FREE - SEAT_SHIFT:.2f} mm below the floor, lead-in {LEAD_IN:.1f}"),
        ("Largest pen passes the ring", PEN_D_MAX + 1.0 <= PEN_HOLE_D, ""),
        ("Pen tip well below the J6 housing", -Z_TIP - 49.0 >= STROKE + 20.0, f"{-Z_TIP - 49.0:.0f} mm"),
    ]


def design_report() -> str:
    lines = ["UTRA 6-1000 quick-change pen holder", "=" * 35]
    for label, ok, detail in design_checks():
        lines.append(f"  [{'ok' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))
    f0, f1 = STAGE_RATE * SPRING_PRELOAD, STAGE_RATE * (SPRING_PRELOAD + STROKE)
    lines += [
        "",
        f"  TCP (pen tip, spring relaxed): {-PEN_Y:.1f} mm out from the flange face, {-Z_TIP:.1f} mm off-axis on the",
        "      side opposite the dowel pin - the same for every pen from 6 to 17 mm",
        f"  Compliant travel {STROKE:g} mm along the pen; {f0:.1f} N at first touch -> {f1:.1f} N at the hard stop",
        f"  Two twist chucks hold the pen; their jaws span {GRIP_SPAN:.0f} mm along it",
        f"  Rings: {SLOT_SWEEP:g} deg from open to closed, spiral slope {SLOT_SLOPE_MAX:.2f} at its steepest, a ratchet "
        f"click every {360 / DETENT_FLUTES:g} deg",
        "  Ring angle per pen: " + ", ".join(f"{n} {ring_angle(v[0]):.0f} deg" for n, v in PENS.items()),
    ]
    return "\n".join(lines)


# =============================================================================
# Export
# =============================================================================
def printed_parts() -> dict[str, tuple[Part, Part]]:
    """name -> (part in frame M, part in print orientation)."""
    base, carriage, cart = make_base(), make_carriage(), make_cartridge()
    ring, jaw, gauge = make_ring(), make_jaw(), make_gauge()
    jaw_side = Rot(-90, 0, 0) * jaw  # on its side, teardrop down: the pin's layers run along it
    jb = jaw_side.bounding_box()
    return {
        "Quick-Change - Base": (base, Pos(0, 0, -Z_BB0) * base),
        "Quick-Change - Carriage": (Pos(0, 0, Z_C0) * carriage, Pos(0, -sum(CARRIAGE_Y) / 2, 0) * carriage),
        "Quick-Change - Cartridge": (cart, Pos(0, -PEN_Y, -Z_JS0) * cart),
        "Quick-Change - Twist Ring (print 2)": (at_pen(ring), Pos(0, 0, -Z_W0) * ring),
        "Quick-Change - Jaw (print 6)": (jaw, Pos(-jb.center().X, -jb.center().Y, -jb.min.Z) * jaw_side),
        "Quick-Change - Stick-out Gauge": (gauge, gauge),
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
        print(f"  {name:32s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:6.1f} mm (print orientation)")
    asm = labelled_compound(assembly(), "UTRA 6-1000 quick-change pen holder")
    export_step(asm, out_dir / "STEP" / "Quick-Change - Assembly.step")
    export_gltf(asm, out_dir / "Quick-Change - Assembly.glb", binary=True, linear_deflection=0.08,
                angular_deflection=0.35)
    print(f"  wrote {out_dir / 'STEP'}, {out_dir / 'STLs'} and the .glb assembly")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--out", type=Path, default=HERE, help="output folder")
    ap.add_argument("--no-export", action="store_true", help="only print the design report")
    args = ap.parse_args()
    print(design_report())
    if any(not ok for _, ok, _ in design_checks()):
        raise SystemExit("Design check failed - adjust the parameters above.")
    if not args.no_export:
        export_all(args.out)


if __name__ == "__main__":
    main()
