# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["build123d>=0.9,<0.14"]
# ///
"""
Pen holder v2 for the Umbratek UTRA 6-1000 arm: printed flexure instead of a coil spring (build123d)
==================================================================================================

    uv run pen_holder_v2.py          # prints a design report and writes STEP / STL / GLB

Same job as v1 (pen on the flange axis, 15 mm of compliant over-travel), but the spring and the sliding guide are
one printed PETG part: a folded-beam flexure stage. Eight 0.8 mm beams carry the pen carriage on a straight line
with no friction or play, and provide the spring force. Two M3 stop screws lift the carriage 5 mm when they are
screwed home, which preloads the beams; a printed hard stop ends the travel.

Parts
  1. Tool adapter    - the v1 part, unchanged (6x M5 on PCD 64, Ø73 h7 pilot, Ø3 dowel).
  2. Flexure module  - frame, beams, carriage and pen clamp in one print, lying on its back.

Frame (mm), as in v1: origin = centre of the arm's flange face, +Z into the arm (the tool hangs along -Z),
+X towards the Ø3 dowel. The flexure profile lies in the XZ plane; the module is printed with -Y down.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from build123d import (
    Color,
    Compound,
    Face,
    Part,
    Pos,
    Rot,
    Shape,
    Wire,
    export_gltf,
    export_step,
    export_stl,
    extrude,
)

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "Pen Holder"))
sys.path.insert(0, str(HERE))
import pen_holder as ph  # noqa: E402  (flange, adapter, hardware and pen models)
from flexure import PETG_DENSITY, PETG_STRENGTH, CrossDP, box, prism_xz, s_curve  # noqa: E402
from pen_holder import cut_all, hex_prism, polar, zcyl  # noqa: E402

# =============================================================================
# Travel and spring
# =============================================================================
STROKE = 15.0  # compliant over-travel, then the hard stop
PRELOAD = 5.0  # the stop screw lifts the carriage this far above its printed position
TRAVEL = PRELOAD + STROKE  # largest lift above the printed position
DRAWING = 3.0  # typical commanded over-reach, for the report

# =============================================================================
# Flexure: one folded double parallelogram spanning the plate behind the pen
# =============================================================================
BEAM_L = 45.0  # free length of each beam
BEAM_T = 0.8  # two 0.4 mm perimeters: print with 2 walls and no infill in the beams
BEAM_B = 20.0  # beam depth = plate thickness (print height)
PLATE_Y = (-28.0, -8.0)  # flexure plate, behind the pen (pen axis at y = 0)
H_CARRIAGE = 44.0  # spacing of the carriage parallelogram's two beams
H_GROUND = 30.0  # spacing of the ground parallelogram's two beams
MEMBER_W = 6.0  # carriage member and ground anchor, at the beams' roots
MEMBER_EXT = 2.0  # carriage member reaches past its top beam (hard-stop face)
SIDE_BAR_W = 5.0
TOP_BAR_MIN = 5.0
BOTTOM_BAR_T = 6.0
CLR = 1.5  # minimum gap around moving parts

# =============================================================================
# Pen block (part of the carriage, standing in front of the plate) and clamp
# =============================================================================
BLOCK_HW = 12.0  # half-width
BLOCK_FRONT_Y = 15.0
PEN_D, PEN_LEN, PEN_STICKOUT = ph.PEN_D, ph.PEN_LEN, ph.PEN_STICKOUT  # Sharpie Fine Point
PEN_BORE = PEN_D + 0.5
PEN_HOLE_D = 15.0  # through the mount block
TIP_BELOW_FRAME = 30.0  # pen tip below the frame's bottom face
THUMB_SCREW_LEN = ph.THUMB_SCREW_LEN
NUT_SLOT_Y = 8.6  # clamp-nut slot (opens at the pen block's bottom face): y from here ...
NUT_SLOT_T = 2.7  # ... and this thick

# =============================================================================
# Mount (to the v1 adapter): 2x M3 x 14 from the arm side, heads in the adapter's nut pockets, thread-forming into
# the mount block. The adapter's third nut pocket (on -Y) is not used.
# =============================================================================
Z_TOP = ph.Z_ADAPTER_BOTTOM  # adapter's tool-side face
MOUNT_ANGLES = (30.0, 150.0)
MOUNT_BLOCK = (25.0, 14.5)  # half-width, +Y reach; it is as thick as the top bar
MOUNT_TAP_D = 2.5
MOUNT_SCREW_LEN = 14.0
TOP_BAR_GAP = 1.0  # the frame's top stays this far below the adapter, outside the mount block

# =============================================================================
# Preload stop screw: up through the bottom bar and the ground anchor to the carriage member
# =============================================================================
STOP_SCREW_LEN = 40.0  # ISO 4762 M3 x 40
STOP_TAP_D, STOP_TAP_LEN = 2.5, 10.0  # thread-forming only in the top of its hole
STOP_CLEAR_D, STOP_CBORE_D = 3.4, 6.2

# =============================================================================
# Derived (Z positions in the printed position; the carriage sits PRELOAD higher at rest)
# =============================================================================
T2 = BEAM_T / 2
X_ROOT = -BEAM_L / 2  # beam roots; the beams run towards +X
X_MEMBER0 = X_ROOT - MEMBER_W  # outer face of the carriage member and the anchor
X_IN = X_ROOT + BEAM_L + MEMBER_W + CLR  # frame sides' inner faces at ±X_IN (bar width = member width)
X_OUT = X_IN + SIDE_BAR_W
Z_TB_TOP = Z_TOP - TOP_BAR_GAP
Z_HS = Z_TB_TOP - TOP_BAR_MIN  # top bar's underside over the carriage member = hard stop
Z_M1 = Z_HS - TRAVEL  # carriage member top (printed)
Z_P2T = Z_M1 - MEMBER_EXT - T2  # carriage parallelogram: upper beam ...
Z_P2B = Z_P2T - H_CARRIAGE  # ... and lower beam
Z_M0 = Z_P2B - T2 - 1.0  # carriage member bottom (printed); the stop screw lifts it
Z_A1 = Z_M0 - CLR  # ground anchor top
Z_P1T = Z_A1 - 1.0 - T2  # ground parallelogram: upper beam ...
Z_P1B = Z_P1T - H_GROUND  # ... and lower beam
X_STOP = X_ROOT - MEMBER_W / 2 - 0.75  # stop screw, under the carriage member (its counterbore stays in the anchor)
Y_MID = sum(PLATE_Y) / 2

FLEX = CrossDP(X_ROOT, BEAM_L, BEAM_T, BEAM_B, PLATE_Y[0], (Z_P2T, Z_P2B), (Z_P1T, Z_P1B), TRAVEL,
               twin_gap=0.0, bar_w=MEMBER_W)
Z_BB1 = FLEX.bar_z()[0] - CLR  # bottom bar top
Z_BB0 = Z_BB1 - BOTTOM_BAR_T  # bottom face of the frame
Z_REST0 = Z_M0 + PRELOAD  # carriage member bottom at rest = stop-screw tip
Z_STOP_SEAT = Z_REST0 - STOP_SCREW_LEN  # under-head face of the stop screw
Z_TIP = Z_BB0 - TIP_BELOW_FRAME  # pen tip at rest
TCP_Z = -Z_TIP
Z_C0 = Z_P2B + T2 + CLR  # carriage body bottom (printed)


def body_top(x: float) -> float:
    """Carriage body's top edge (printed): below the upper carriage beam, which lags behind it away from the root."""
    return Z_P2T - T2 - CLR - TRAVEL / 2 * s_curve(FLEX.xi(x))


Z_CLAMP = (Z_C0 + body_top(BLOCK_HW)) / 2  # thumb screw height (printed)


# =============================================================================
# Printed part: flexure module (frame + beams + carriage), built at any lift
# =============================================================================
def frame_window() -> list[tuple[float, float]]:
    """Opening in the frame: everything that moves lives in here (the ground anchor stays solid, lower left)."""
    x_step = FLEX.x_bar - FLEX.shortening(TRAVEL) - CLR  # the bar slides inward as the beams bend
    ceiling = [(x, Z_P2T + T2 + CLR + FLEX.rise_p2(x)) for x in (X_ROOT + (x_step - X_ROOT) * i / 12 for i in range(13))]
    bar_top = FLEX.bar_z(TRAVEL)[1] + CLR
    return [(-X_IN, Z_A1), (-X_IN, Z_HS), (X_ROOT, Z_HS), *ceiling, (x_step, bar_top), (X_IN, bar_top),
            (X_IN, Z_BB1), (X_ROOT, Z_BB1), (X_ROOT, Z_A1)]


def make_ground() -> Part:
    """Everything that does not move: frame, ground anchor, mount block."""
    y0, y1 = PLATE_Y
    outline = [(-X_OUT, Z_TB_TOP), (X_OUT, Z_TB_TOP), (X_OUT, Z_BB0), (-X_OUT, Z_BB0)]
    frame = prism_xz(outline, y0, y1) - prism_xz(frame_window(), y0 - 1, y1 + 1)
    hw, reach = MOUNT_BLOCK
    frame += box(-hw, hw, y0, reach, Z_HS, Z_TOP)  # mount block, touches the adapter
    tools = [zcyl(PEN_HOLE_D, Z_HS - 1, Z_TOP + 1)]
    for a in MOUNT_ANGLES:  # the screw tips come out below, in front of the plate
        x, y = polar(ph.MODULE_SCREW_PCD / 2, a)
        tools.append(Pos(x, y, 0) * zcyl(MOUNT_TAP_D, Z_HS - 1, Z_TOP + 1))
    stop = Pos(X_STOP, Y_MID, 0)
    tools.append(stop * zcyl(STOP_TAP_D, Z_A1 - STOP_TAP_LEN, Z_A1 + 1))
    tools.append(stop * zcyl(STOP_CLEAR_D, Z_BB0 - 1, Z_A1 - STOP_TAP_LEN))
    tools.append(stop * zcyl(STOP_CBORE_D, Z_BB0 - 1, Z_STOP_SEAT))
    return cut_all(frame, tools)


def block_outline(x0: float, x1: float) -> list[tuple[float, float]]:
    """Carriage body from x0 to x1: flat bottom, top following the upper carriage beam's lag."""
    top = [(x, body_top(x)) for x in (x0 + (x1 - x0) * i / 10 for i in range(11))]
    return [(x0, Z_C0), *top, (x1, Z_C0)]


def make_carriage() -> Part:
    """Carriage member, body and pen block in their printed position."""
    y0, y1 = PLATE_Y
    body = box(X_MEMBER0, X_ROOT, y0, y1, Z_M0, Z_M1)  # member: the carriage beams root on it
    body += prism_xz(block_outline(X_ROOT - 0.01, BLOCK_HW), y0, y1)  # body between the carriage beams
    body += prism_xz(block_outline(-BLOCK_HW, BLOCK_HW), y1 - 0.01, BLOCK_FRONT_Y)  # pen block, in front
    z0, z1 = Z_C0 - 1, body_top(-BLOCK_HW) + 1
    tools = [zcyl(PEN_BORE, z0, z1), teardrop_z(PEN_BORE, z0, z1, NUT_SLOT_Y - 1.0)]
    tools.append(Pos(0, 0, Z_C0) * zcyl(PEN_BORE + 2.0, Z_C0 - 1, Z_C0 + 1.0))  # pen lead-in at the bottom
    # thumb screw along -Y from the front face, captive nut in a slot open at the block's bottom face
    tools.append(Pos(0, 0, Z_CLAMP) * Rot(90, 0, 0) * zcyl(ph.M3_CLEAR_D + 0.1, -BLOCK_FRONT_Y - 1, 0))
    z_top = Z_CLAMP + ph.NUT_POCKET_AF / math.sqrt(3)
    tools.append(box(-ph.NUT_POCKET_AF / 2, ph.NUT_POCKET_AF / 2, NUT_SLOT_Y, NUT_SLOT_Y + NUT_SLOT_T, Z_C0 - 1, z_top))
    return cut_all(body, tools)


def teardrop_z(d: float, z0: float, z1: float, y_flat: float) -> Part:
    """45° roof over a Z-axis bore (prints lying on -Y without support), flattened at y = y_flat."""
    r = d / 2
    k = r / math.sqrt(2)
    xf = r * math.sqrt(2) - y_flat
    pts = [(0.0, 0.0), (k, k), (xf, y_flat), (-xf, y_flat), (-k, k)]
    face = Face(Wire.make_polygon([(x, y, z0) for x, y in pts], close=True))
    return extrude(face, z1 - z0, dir=(0, 0, 1))


def module_bodies(lift: float) -> dict[str, list[Part]]:
    """The module's rigid bodies and beams with the carriage `lift` mm above its printed position."""
    return {
        "ground": [_cached("ground", make_ground)],
        "carriage": [Pos(0, 0, lift) * _cached("carriage", make_carriage)],
        "bars": [FLEX.bar(lift)],
        "beams": FLEX.beams(lift),
    }


def make_module(lift: float = 0.0) -> Part:
    parts = [p for group in module_bodies(lift).values() for p in group]
    body = parts[0]
    for p in parts[1:]:
        body = body + p
    return body


_cache: dict = {}


def _cached(key, fn):
    if key not in _cache:
        _cache[key] = fn()
    return _cache[key]

# =============================================================================
# Assembly
# =============================================================================
COLORS = ph.COLORS
M5_USED = (0, 1, 2, 3)  # the frame covers the two M5 holes on -Y; four of six are plenty for a pen


@dataclass
class Item:
    name: str
    shape: Shape
    material: str
    explode: tuple[float, float, float] = (0.0, 0.0, 0.0)


def assembly(travel: float = 0.0, arm: bool = True, hardware: bool = True, pen: bool = True,
             split_module: bool = False) -> list[Item]:
    """Every part in place. `travel` = over-reach past first touch (0..STROKE).

    split_module=True returns the module's frame, carriage, bars and beams as separate items (for renders).
    """
    if not 0.0 <= travel <= STROKE:
        raise ValueError(f"travel must be within 0..{STROKE} mm")
    lift = PRELOAD + travel
    ex_mod = (0.0, 0.0, -45.0)
    items: list[Item] = []
    if arm:
        items.append(Item("UTRA 6-1000 tool flange (ref)", _cached("arm_flange", ph.make_arm_flange), "aluminum", (0, 0, 70)))
        items.append(Item("UTRA 6-1000 J6 housing (ref)", _cached("arm_housing", ph.make_arm_housing), "arm_dark", (0, 0, 70)))
    items.append(Item("Tool adapter (v1)", _cached("adapter", ph.make_adapter), "printed"))
    if split_module:
        for group, parts in module_bodies(lift).items():
            for i, p in enumerate(parts):
                items.append(Item(f"Flexure module - {group} {i + 1}", p, "accent", ex_mod))
    else:
        items.append(Item("Flexure module", _cached(("module", lift), lambda: make_module(lift)), "accent", ex_mod))
    if hardware:
        m5 = _cached("m5", lambda: ph.make_shcs(5.0, ph.M5_SCREW_LEN, ph.M5_HEAD_D, ph.M5_HEAD_H, 4.0))
        for i in M5_USED:
            x, y = polar(ph.BOLT_PCD / 2, i * 360 / ph.BOLT_COUNT)
            items.append(Item(f"M5x12 SHCS {i + 1}", Pos(x, y, ph.Z_M5_SEAT) * m5, "steel_black", (0, 0, -28)))
        z_dowel = ph.DOWEL_HOLE_DEPTH - 0.5 - ph.DOWEL_LEN
        items.append(Item("Dowel pin 3x8", Pos(ph.DOWEL_PCD / 2, 0, z_dowel) * _cached("dowel", ph.make_dowel), "steel",
                          (0, 0, 32)))
        m3 = _cached("m3", lambda: ph.make_shcs(3.0, MOUNT_SCREW_LEN, ph.M3_HEAD_D, ph.M3_HEAD_H, 2.5))
        for i, a in enumerate(MOUNT_ANGLES):
            x, y = polar(ph.MODULE_SCREW_PCD / 2, a)
            items.append(Item(f"M3x14 SHCS (mount) {i + 1}", Pos(x, y, ph.Z_NUT_POCKET_BOTTOM) * Rot(180, 0, 0) * m3,
                              "steel_black", (0, 0, 40)))
        stop = _cached("m3x40", lambda: ph.make_shcs(3.0, STOP_SCREW_LEN, ph.M3_HEAD_D, ph.M3_HEAD_H, 2.5))
        items.append(Item("M3x40 SHCS (preload stop)", Pos(X_STOP, Y_MID, Z_STOP_SEAT) * stop, "steel_black",
                          (0, 0, -95)))
        items.append(Item("M3x10 thumb screw", Pos(0, PEN_D / 2, Z_CLAMP + lift) * Rot(0, 0, 90)
                          * _cached("thumb", ph.make_thumb_screw), "steel", (0.0, 25.0, ex_mod[2])))
        nut = Pos(0, NUT_SLOT_Y + NUT_SLOT_T / 2, Z_CLAMP + lift) * Rot(90, 0, 0) * Rot(0, 0, 90) * _cached("nut", ph.make_nut)
        items.append(Item("M3 nut (pen clamp)", nut, "steel", (0.0, 0.0, ex_mod[2] - 60)))
    if pen:
        for name, shape, material in _cached("pen", ph.make_pen):
            items.append(Item(name, Pos(0, 0, Z_TIP + travel) * shape, material, (-95, 0, -110)))
    return items


# =============================================================================
# Design checks and report
# =============================================================================
def _overlap(a: Shape, b: Shape) -> float:
    try:
        return (a & b).volume
    except Exception:  # pragma: no cover - empty intersection
        return 0.0


def interference() -> dict[str, float]:
    """Volume (mm³) shared by rigid bodies that must not touch, at the printed position and the hard stop."""
    out = {}
    ground = _cached("ground", make_ground)
    for lift in (0.0, TRAVEL):
        b = module_bodies(lift)
        out[f"carriage/frame @{lift:g}"] = _overlap(b["carriage"][0], ground)
        out[f"bars/frame @{lift:g}"] = sum(_overlap(bar, ground) for bar in b["bars"])
    return out


def design_checks() -> list[tuple[str, bool, str]]:
    m5 = [polar(ph.BOLT_PCD / 2, i * 360 / ph.BOLT_COUNT) for i in M5_USED]
    hw, reach = MOUNT_BLOCK
    footprints = [(-X_OUT, X_OUT, PLATE_Y[0], PLATE_Y[1]), (-hw, hw, PLATE_Y[0], reach)]  # frame, mount block
    clear_m5 = min(math.hypot(max(x0 - x, 0, x - x1), max(y0 - y, 0, y - y1))
                   for x, y in m5 for x0, x1, y0, y1 in footprints)
    m3_tip = ph.Z_NUT_POCKET_BOTTOM - MOUNT_SCREW_LEN
    engage = Z_TOP - max(m3_tip, Z_HS)
    sf = PETG_STRENGTH / FLEX.stress(TRAVEL)
    pen_end_full = Z_TIP + STROKE + PEN_LEN
    block_top_full = body_top(-BLOCK_HW) + TRAVEL
    lever = (Z_C0 + body_top(0)) / 2 + PRELOAD - Z_TIP  # carriage centre to pen tip
    tip_drift = lever**2 / FLEX.k_tilt + 1.0 / FLEX.k_out_of_plane  # 1 N sideways (Y) at the tip
    tip_x = 1.0 / FLEX.k_turn(lever)  # 1 N sideways (X) at the tip, turning the carriage in its plane
    clash = interference()
    return [
        ("M5 engagement within the 6 mm arm thread", ph.M5_ENGAGEMENT <= ph.BOLT_THREAD_DEPTH - 0.5,
         f"{ph.M5_ENGAGEMENT:.1f} mm"),
        ("Mount screws: heads fit the adapter's nut pockets, >= 5 mm of thread in the module",
         ph.M3_HEAD_D <= ph.NUT_POCKET_AF - 0.1 and engage >= 5.0, f"{engage:.1f} mm"),
        ("Mount screw tips stay clear of the pen block at full stroke", m3_tip - block_top_full >= 2.0,
         f"{m3_tip - block_top_full:.1f} mm"),
        (f"The {len(M5_USED)} M5 screws used stay reachable beside the module", clear_m5 >= ph.M5_CBORE_D / 2 + 0.5,
         f"{clear_m5:.1f} mm from the module"),
        ("Beam stress at the hard stop (SF >= 1.8 on PETG)", sf >= 1.8,
         f"{FLEX.stress(TRAVEL):.1f} MPa, SF {sf:.1f}"),
        ("Beam stress at rest is low enough to limit creep (<= 8 MPa)", FLEX.stress(PRELOAD) <= 8.0,
         f"{FLEX.stress(PRELOAD):.1f} MPa"),
        ("Beams are at least two 0.4 mm perimeters", BEAM_T >= 0.8, f"{BEAM_T} mm"),
        ("Hard stop lands before the top beam reaches the frame", MEMBER_EXT >= 1.0, f"{MEMBER_EXT} mm left"),
        ("Carriage member clears the ground anchor as printed", Z_M0 - Z_A1 >= 1.0, f"{Z_M0 - Z_A1:.1f} mm"),
        ("Ground beams root fully on the anchor", Z_P1T + T2 <= Z_A1 - 0.5, ""),
        ("Carriage body clears its beams: >= 4 mm tall where it is thinnest",
         body_top(BLOCK_HW) - Z_C0 >= 4.0, f"{body_top(BLOCK_HW) - Z_C0:.1f} mm"),
        ("Stop screw: head recessed, threads only in the top of the anchor, under the carriage member",
         Z_BB0 <= Z_STOP_SEAT <= Z_A1 - STOP_TAP_LEN - 2.0
         and X_MEMBER0 + 1.0 <= X_STOP - STOP_TAP_D / 2 and X_STOP + STOP_TAP_D / 2 <= X_ROOT - 1.0
         and -X_IN + 0.5 <= X_STOP - STOP_CBORE_D / 2 and X_STOP + STOP_CBORE_D / 2 <= X_ROOT - 0.5,
         f"seat {Z_STOP_SEAT - Z_BB0:.1f} mm deep, {STOP_TAP_LEN:g} mm of thread"),
        ("Pen passes in front of the plate", -PLATE_Y[1] - PEN_D / 2 >= 1.0, f"{-PLATE_Y[1] - PEN_D / 2:.2f} mm"),
        ("Pen bore leaves a wall over the plate", -PLATE_Y[1] - PEN_BORE / 2 >= 1.0, ""),
        ("Clamp-nut slot walls", NUT_SLOT_Y - PEN_BORE / 2 >= 1.2 and BLOCK_FRONT_Y - NUT_SLOT_Y - NUT_SLOT_T >= 2.0, ""),
        ("Thumb screw reaches the pen", BLOCK_FRONT_Y - THUMB_SCREW_LEN <= PEN_D / 2 - 0.5,
         f"reach to y = {BLOCK_FRONT_Y - THUMB_SCREW_LEN:.1f}"),
        ("Pen end stays clear of the arm at full stroke", pen_end_full <= -ph.RELIEF_DEPTH - 3,
         f"pen end at z = {pen_end_full:.1f}"),
        ("Pen tip stays below the frame at full stroke (10 mm margin)", TIP_BELOW_FRAME - STROKE >= 10.0,
         f"{TIP_BELOW_FRAME - STROKE:.0f} mm"),
        ("No rigid bodies collide (printed position and hard stop)", max(clash.values()) < 0.01,
         ", ".join(f"{k} {v:.2f}" for k, v in clash.items() if v >= 0.01) or "none"),
        ("Pen tip moves < 0.4 mm under 1 N of drawing drag, either way",
         tip_drift < 0.4 and tip_x < 0.4, f"{tip_drift:.2f} mm across the plate, {tip_x:.2f} mm along it"),
    ]


def mass_properties(its: list) -> tuple[float, tuple[float, float, float]]:
    """Rough mass (g) and centre of mass (robot flange frame: X to the dowel, Z out of the flange) of a tool."""
    density = {"printed": PETG_DENSITY * 0.6, "accent": PETG_DENSITY * 0.6, "steel": 7.85e-3, "steel_black": 7.85e-3}
    m_tot, acc = 0.0, [0.0, 0.0, 0.0]
    for it in its:
        rho = density.get(it.material, 0.6e-3 if it.material.startswith("pen") else 0.0)  # pens: ~9 g Sharpie
        if not rho:
            continue
        m = it.shape.volume * rho
        c = it.shape.center()
        m_tot += m
        for i, v in enumerate((c.X, -c.Y, -c.Z)):
            acc[i] += m * v
    return m_tot, tuple(a / m_tot for a in acc)


def design_report() -> str:
    lines = ["UTRA 6-1000 pen holder v2 (printed flexure)", "=" * 43]
    for label, ok, detail in design_checks():
        lines.append(f"  [{'ok' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))
    vol = make_module().volume
    mass, com = mass_properties(assembly(arm=False))
    lines += [
        "",
        f"  TCP (pen tip at rest): X 0, Y 0, Z +{TCP_Z:.1f} mm along the flange axis",
        f"  Compliant over-travel: {STROKE:g} mm, then a hard stop; preload {PRELOAD:g} mm set by the stop screws",
        *FLEX.report(PRELOAD, STROKE, DRAWING),
        f"  Module: {2 * X_OUT:.0f} x {BLOCK_FRONT_Y - PLATE_Y[0]:.0f} x {Z_TOP - Z_BB0:.0f} mm (W x D x H),"
        f" {vol / 1000:.0f} cm³ (~{vol * PETG_DENSITY * 0.6:.0f} g printed)",
        f"  Out-of-plane stiffness {FLEX.k_out_of_plane:.0f} N/mm, tilt {FLEX.k_tilt / 1000:.1f} N·m/rad",
        f"  Payload ~{mass / 1000:.2f} kg with the pen, centre of mass X {com[0]:.0f}, Y {com[1]:.0f}, Z {com[2]:+.0f} mm"
        " (flange frame, Z out of the flange)",
    ]
    return "\n".join(lines)


# =============================================================================
# Export
# =============================================================================
PRINT_POSE = Pos(0, 0, -PLATE_Y[0]) * Rot(90, 0, 0)  # lying on its back (-Y) face


def printed_parts() -> dict[str, tuple[Part, Part]]:
    """name -> (part in the assembly frame, part in its print orientation)."""
    module = make_module()
    return {"Pen Holder v2 - Flexure Module": (module, PRINT_POSE * module)}


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
        print(f"  {name:34s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:6.1f} mm (print orientation)")
    asm = labelled_compound(assembly(), "UTRA 6-1000 pen holder v2")
    export_step(asm, out_dir / "STEP" / "Pen Holder v2 - Assembly.step")
    export_gltf(asm, out_dir / "Pen Holder v2 - Assembly.glb", binary=True, linear_deflection=0.08,
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
