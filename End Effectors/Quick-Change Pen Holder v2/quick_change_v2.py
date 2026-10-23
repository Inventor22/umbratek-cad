# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["build123d>=0.9,<0.14"]
# ///
"""
Quick-change pen holder v2 for the UTRA 6-1000: printed flexure stage instead of rods and coil springs (build123d)
================================================================================================================

    uv run quick_change_v2.py      # prints a design report, writes STEP / STL / GLB

Same pen cartridges as v1 (pen perpendicular to the flange, two twist chucks, dovetail + ball-plunger dock) and the
same 15 mm of compliant travel along the pen. What changed is the stage they ride on:

* v1: a printed base with two steel rods, a sliding carriage and two coil springs.
* v2: one printed PETG part, a folded-beam flexure. Eight 0.8 mm beams carry the carriage on a straight line with no
  sliding friction or play and provide the spring force. Two M3 stop screws lift the carriage 5 mm when they are
  screwed home, which preloads the beams; a printed hard stop ends the travel.

The stage bolts to the v1 tool adapter (the reusable plate from ../Pen Holder) with two of its three M3 nuts; the
third sits behind the carriage's path. The flexure prints lying on its back, so the beams are thin vertical walls.

Frame M (mm), as in v1: origin = centre of the flange face, flange face = plane y = 0 with the arm on +Y, pen axis
= Z with the tip pointing -Z. Flange frame F (Z into the arm, X towards the dowel): X_F = Z_M, Y_F = X_M, Z_F = Y_M.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from build123d import Color, Compound, Location, Part, Pos, Rot, Shape, export_gltf, export_step, export_stl

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "Pen Holder"))
sys.path.insert(0, str(HERE.parent / "Pen Holder v2"))
sys.path.insert(0, str(HERE.parent / "Quick-Change Pen Holder"))
import pen_holder as ph  # noqa: E402  (flange, adapter, hardware)
import quick_change_pen_holder as qc  # noqa: E402  (cartridge, rings, jaws, gauge, pens, plunger)
from flexure import PETG_DENSITY, PETG_STRENGTH, CrossDP, box, prism_xz, s_curve  # noqa: E402
from pen_holder import cut_all, polar  # noqa: E402

F2M = qc.F2M

# =============================================================================
# Travel and spring
# =============================================================================
STROKE = qc.STROKE  # 15 mm along the pen, then the hard stop
PRELOAD = 5.0  # the stop screws lift the carriage this far above its printed position
TRAVEL = PRELOAD + STROKE
DRAWING = 3.0

# =============================================================================
# Stage: one folded double parallelogram spanning the stage, carriage beams below, ground beams above
# =============================================================================
BACK_Y = -12.5  # stage back face: 0.5 mm in front of the adapter (M3 washers under the two mount pads)
FRONT_Y = qc.CARRIAGE_Y[0]  # carriage front face, where the v1 dovetail rail starts
FRAME_FRONT_Y = FRONT_Y + 1.0  # the frame stays 1 mm behind the carriage, clear of a passing cartridge
BEAM_L = 46.0
BEAM_T = 0.8  # two 0.4 mm perimeters
BEAM_B = 11.0  # beam depth (print height), from the back face
TWIN_GAP = 2.0  # each level is a pair of beams this far apart
X_ROOT = -17.0  # beam roots (carriage member below, ground anchor above); the beams run towards +X
MEMBER_W = 6.0
MEMBER_EXT = 1.5  # carriage member reaches past its top beam (hard-stop face)
BELOW_RAIL = 2.0  # carriage body reaches this far below the rail
CLR = 1.5
TOP_BAR_T = 5.0
BOTTOM_BAR_T = 5.0
SIDE_BAR_W = 5.0
WASHER_T = 0.5  # DIN 125 M3 washer

# Mount: 2x M3 x 20 from the front into the v1 adapter's captive nuts at F 270° (pad in the ground anchor) and F 30°
# (pad on a ground arm inside the ground parallelogram). The third nut (F 150°) is behind the carriage's path.
MOUNT_ANGLES = (30.0, 270.0)
MOUNT_SCREW_LEN = 20.0
MOUNT_CBORE_D, MOUNT_CBORE_DEPTH = 6.2, 3.0
PAD_R = 4.5  # material kept around each mount hole

# Preload stop screw (from below, through the ground block under the carriage member)
STOP_SCREW_LEN = 12.0  # ISO 4762 M3 x 12
STOP_TAP_D, STOP_CBORE_D = 2.5, 6.2


def mount_points() -> list[tuple[float, float]]:
    """Adapter nut positions used, in frame M (x, z)."""
    out = []
    for a in MOUNT_ANGLES:
        xf, yf = polar(ph.MODULE_SCREW_PCD / 2, a)
        out.append((yf, xf))
    return out


# =============================================================================
# Derived (Z in the printed position unless noted; the carriage sits PRELOAD higher at rest)
# =============================================================================
T2 = BEAM_T / 2
HALF_PAIR = (BEAM_T + TWIN_GAP) / 2 + T2  # pair centre to the outer face of its outer beam
X_MEMBER0 = X_ROOT - MEMBER_W
X_IN_L = X_MEMBER0 - CLR  # frame's left inner face
X_OUT_L = X_IN_L - SIDE_BAR_W
X_IN_R = X_ROOT + BEAM_L + MEMBER_W + CLR  # frame's right inner face (bar width = member width)
X_OUT_R = X_IN_R + SIDE_BAR_W
(PAD3_X, PAD3_Z), (PAD1_X, PAD1_Z) = sorted(mount_points())  # F 270° (left, in the anchor), F 30° (on the arm)
Z_AB = PAD3_Z - PAD_R - 1.5  # ground anchor's underside = hard stop (the left pad sits in the anchor)
Z_M1 = Z_AB - TRAVEL  # carriage member top (printed)
Z_P2T = Z_M1 - MEMBER_EXT - HALF_PAIR  # carriage parallelogram: upper pair centre
Z_P1B = Z_AB + 1.0 + HALF_PAIR  # ground parallelogram: lower pair centre
_FLEX0 = CrossDP(X_ROOT, BEAM_L, BEAM_T, BEAM_B, BACK_Y - BEAM_B, (Z_P2T, Z_P2T - 50), (Z_P1B + 30, Z_P1B), TRAVEL,
                 twin_gap=TWIN_GAP, bar_w=MEMBER_W)


def body_top(x: float) -> float:
    """Carriage body's top edge (printed): below the upper carriage pair, which lags behind it away from the root."""
    return Z_P2T - HALF_PAIR - CLR - TRAVEL / 2 * s_curve(_FLEX0.xi(x))


Z_RAIL1 = body_top(qc.RAIL_W1 / 2) + PRELOAD  # rail top at rest: the rail sits on the body
DZ = Z_RAIL1 - qc.Z_C1  # the whole cartridge seat moves this far along Z compared with v1
Z_RAIL0 = qc.Z_C0 + DZ  # rail bottom at rest = cartridge seat
Z_C0 = Z_RAIL0 - BELOW_RAIL - PRELOAD  # carriage body bottom (printed)
Z_P2B = Z_C0 - CLR - HALF_PAIR  # carriage parallelogram: lower pair centre
Z_M0 = Z_P2B - HALF_PAIR - 1.0  # carriage member bottom (printed)
Z_GB1 = Z_M0 - CLR  # ground block under the carriage member: top
# arm carrying the right mount pad, between the ground beams; the lower pair rises towards it
ARM = (X_ROOT - 0.01, PAD1_X + PAD_R, PAD1_Z - PAD_R, PAD1_Z + PAD_R)
Z_P1T = ARM[3] + CLR + HALF_PAIR  # ground parallelogram: upper pair centre
FLEX = CrossDP(X_ROOT, BEAM_L, BEAM_T, BEAM_B, BACK_Y - BEAM_B, (Z_P2T, Z_P2B), (Z_P1T, Z_P1B), TRAVEL,
               twin_gap=TWIN_GAP, bar_w=MEMBER_W)
Z_BB1 = FLEX.bar_z()[0] - CLR  # bottom bar top
Z_BB0 = Z_BB1 - BOTTOM_BAR_T
Z_TB0 = FLEX.bar_z(TRAVEL)[1] + CLR  # top bar underside
Z_TB1 = Z_TB0 + TOP_BAR_T
Z_REST0 = Z_M0 + PRELOAD  # carriage member bottom at rest = stop-screw tip
Z_STOP_SEAT = Z_REST0 - STOP_SCREW_LEN
X_STOP = X_ROOT - MEMBER_W / 2
Y_MID = (FRAME_FRONT_Y + BACK_Y) / 2
Z_TIP = qc.Z_TIP + DZ
TCP_F = (Z_TIP, 0.0, qc.PEN_Y)
PLACE = Pos(0, 0, DZ)  # v1 cartridge position -> v2


# =============================================================================
# Printed part: flexure stage (frame + beams + carriage + dovetail rail)
# =============================================================================
def make_ground() -> Part:
    y0, y1 = FRAME_FRONT_Y, BACK_Y
    outline = [(X_OUT_L, Z_TB1), (X_OUT_R, Z_TB1), (X_OUT_R, Z_BB0), (X_OUT_L, Z_BB0)]
    window = [(X_IN_L, Z_GB1), (X_IN_L, Z_AB), (X_ROOT, Z_AB), (X_ROOT, Z_TB0), (X_IN_R, Z_TB0), (X_IN_R, Z_BB1),
              (X_ROOT, Z_BB1), (X_ROOT, Z_GB1)]
    frame = prism_xz(outline, y0, y1) - prism_xz(window, y0 - 1, y1 + 1)
    frame += box(ARM[0], ARM[1], y0, y1, ARM[2], ARM[3])  # arm for the right mount pad
    tools = []
    for x, z in mount_points():
        hole = Pos(x, 0, z) * Rot(90, 0, 0)
        tools.append(hole * ph.zcyl(ph.M3_CLEAR_D, -y1 - 1, -y0 + 1))
        tools.append(hole * ph.zcyl(MOUNT_CBORE_D, -y0 - MOUNT_CBORE_DEPTH, -y0 + 1))
    stop = Pos(X_STOP, Y_MID, 0)
    tools.append(stop * ph.zcyl(STOP_TAP_D, Z_BB0 - 1, Z_GB1 + 1))
    tools.append(stop * ph.zcyl(STOP_CBORE_D, Z_BB0 - 1, Z_STOP_SEAT))
    return cut_all(frame, tools)


def make_carriage() -> Part:
    """Carriage member, body, v1 dovetail rail and the ball-plunger tapping hole (printed position)."""
    body = box(X_MEMBER0, X_ROOT, FRONT_Y, BACK_Y, Z_M0, Z_M1)  # member: the carriage beams root on it
    x1 = qc.RAIL_W1 / 2 + 2.5
    top = [(x, body_top(x)) for x in (X_ROOT + (x1 - X_ROOT) * i / 10 for i in range(11))]
    body += prism_xz([(X_ROOT - 0.01, Z_C0), *top, (x1, Z_C0)], FRONT_Y, BACK_Y)
    body += qc.prism_xy(qc.rail_profile(), Z_RAIL0 - PRELOAD, Z_RAIL1 - PRELOAD)
    z_pl = Z_RAIL0 - PRELOAD + qc.PLUNGER_Z
    return body - qc.ycyl(qc.PLUNGER_TAP_D, 0, z_pl, qc.RAIL_FRONT_Y - 1, BACK_Y + 1)


def stage_bodies(lift: float) -> dict[str, list[Part]]:
    return {
        "ground": [_cached("ground", make_ground)],
        "carriage": [Pos(0, 0, lift) * _cached("carriage", make_carriage)],
        "bars": [FLEX.bar(lift)],
        "beams": FLEX.beams(lift),
    }


def make_stage(lift: float = 0.0) -> Part:
    parts = [p for group in stage_bodies(lift).values() for p in group]
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
COLORS = qc.COLORS
EX_STAGE = (0.0, -40.0, 0.0)


@dataclass
class Item:
    name: str
    shape: Shape
    material: str
    explode: tuple[float, float, float] = (0.0, 0.0, 0.0)


def make_washer() -> Part:
    """DIN 125 M3 washer, axis Y, from y = 0 to y = WASHER_T."""
    return Rot(-90, 0, 0) * (ph.zcyl(7.0, 0, WASHER_T) - ph.zcyl(3.2, -1, 1))


def assembly(travel: float = 0.0, pen: str | None = "Gel pen 11 mm", arm: bool = True, hardware: bool = True,
             explode: bool = False, split_stage: bool = False) -> list[Item]:
    if not 0.0 <= travel <= STROKE:
        raise ValueError(f"travel must be within 0..{STROKE} mm")
    lift = PRELOAD + travel
    items: list = []
    if arm:
        items.append(Item("UTRA 6-1000 tool flange (ref)", F2M * _cached("arm_flange", ph.make_arm_flange),
                          "aluminum", (0, 60, 0)))
        items.append(Item("UTRA 6-1000 J6 housing (ref)", F2M * _cached("arm_housing", ph.make_arm_housing),
                          "arm_dark", (0, 60, 0)))
    items.append(Item("Tool adapter (v1)", F2M * _cached("adapter", ph.make_adapter), "printed", (0, 12, 0)))
    if split_stage:
        for group, parts in stage_bodies(lift).items():
            for i, p in enumerate(parts):
                items.append(Item(f"Flexure stage - {group} {i + 1}", p, "accent", EX_STAGE))
    else:
        items.append(Item("Flexure stage", _cached(("stage", lift), lambda: make_stage(lift)), "accent", EX_STAGE))
    if hardware:
        m5 = _cached("m5", lambda: ph.make_shcs(5.0, ph.M5_SCREW_LEN, ph.M5_HEAD_D, ph.M5_HEAD_H, 4.0))
        for i in range(ph.BOLT_COUNT):
            x, y = polar(ph.BOLT_PCD / 2, i * 360 / ph.BOLT_COUNT)
            items.append(Item(f"M5x12 SHCS {i + 1}", F2M * (Pos(x, y, ph.Z_M5_SEAT) * m5), "steel_black", (0, -10, 0)))
        z_dowel = ph.DOWEL_HOLE_DEPTH - 0.5 - ph.DOWEL_LEN
        items.append(Item("Dowel pin 3x8", F2M * (Pos(ph.DOWEL_PCD / 2, 0, z_dowel) * _cached("dowel", ph.make_dowel)),
                          "steel", (0, 30, 0)))
        m3 = _cached("m3x20", lambda: ph.make_shcs(3.0, MOUNT_SCREW_LEN, ph.M3_HEAD_D, ph.M3_HEAD_H, 2.5))
        nut, washer = _cached("nut", ph.make_nut), _cached("washer", make_washer)
        for a, (x, z) in zip(MOUNT_ANGLES, mount_points()):
            items.append(Item(f"M3x20 SHCS (mount, F {a:g} deg)", Pos(x, FRAME_FRONT_Y + MOUNT_CBORE_DEPTH, z)
                              * Rot(-90, 0, 0) * m3, "steel_black", (0, -75, 0)))
            items.append(Item(f"M3 washer (F {a:g} deg)", Pos(x, BACK_Y, z) * washer, "steel", (0, -20, 0)))
            xf, yf = polar(ph.MODULE_SCREW_PCD / 2, a)
            z_nut = ph.Z_NUT_POCKET_BOTTOM + ph.M3_NUT_T / 2
            items.append(Item(f"M3 nut (F {a:g} deg)", F2M * (Pos(xf, yf, z_nut) * Rot(0, 0, a - 30) * nut), "steel",
                              (0, 30, 0)))
        stop = _cached("m3x12", lambda: ph.make_shcs(3.0, STOP_SCREW_LEN, ph.M3_HEAD_D, ph.M3_HEAD_H, 2.5))
        items.append(Item("M3x12 SHCS (preload stop)", Pos(X_STOP, Y_MID, Z_STOP_SEAT) * stop, "steel_black",
                          (EX_STAGE[0], EX_STAGE[1], -40)))
        items.append(Item("M6 ball spring plunger", Pos(0, qc.PLUNGER_FACE_Y, Z_RAIL0 + travel + qc.PLUNGER_Z)
                          * _cached("plunger", qc.make_plunger), "steel", (EX_STAGE[0], EX_STAGE[1] - 35, 0)))
    items += qc.cartridge_items(pen, travel, place=PLACE, explode=explode)
    return items


# =============================================================================
# Design checks and report
# =============================================================================
def _overlap(a: Shape, b: Shape) -> float:
    try:
        return (a & b).volume
    except Exception:  # pragma: no cover
        return 0.0


def interference() -> dict[str, float]:
    out = {}
    ground = _cached("ground", make_ground)
    for lift in (0.0, TRAVEL):
        b = stage_bodies(lift)
        out[f"carriage/frame @{lift:g}"] = _overlap(b["carriage"][0], ground)
        out[f"bars/frame @{lift:g}"] = sum(_overlap(bar, ground) for bar in b["bars"])
    for travel in (0.0, STROKE):
        cart = PLACE * Pos(0, 0, travel) * _cached("cartridge", qc.make_cartridge)
        out[f"cartridge/frame @{travel:g}"] = _overlap(cart, ground)
    return out


def design_checks() -> list[tuple[str, bool, str]]:
    m3_tip = FRAME_FRONT_Y + MOUNT_CBORE_DEPTH + MOUNT_SCREW_LEN
    nut_far = -(ph.Z_NUT_POCKET_BOTTOM + ph.M3_NUT_T)  # far face of the adapter's nut, frame M
    sf = PETG_STRENGTH / FLEX.stress(TRAVEL)
    lever = (Z_C0 + body_top(0)) / 2 + PRELOAD - Z_TIP
    drift = lever**2 / FLEX.k_tilt + 1.0 / FLEX.k_out_of_plane
    drift_x = 1.0 / FLEX.k_turn(lever)
    arm_y = (BACK_Y - BEAM_B / 2) - qc.PEN_Y  # pen force acts this far in front of the beams
    nod = FLEX.rate * DRAWING * arm_y / FLEX.k_tilt * lever
    clash = interference()
    arm_gap = ARM[2] - (Z_P1B + FLEX.pitch / 2 + T2 + FLEX.rise_p1(ARM[1]))
    pad_wall = min(PAD3_X - MOUNT_CBORE_D / 2 - X_OUT_L, X_ROOT - PAD3_X - MOUNT_CBORE_D / 2,
                   PAD3_Z - MOUNT_CBORE_D / 2 - Z_AB)  # the anchor runs out to the frame's outer edge
    return [
        ("M5 engagement within the 6 mm arm thread", ph.M5_ENGAGEMENT <= ph.BOLT_THREAD_DEPTH - 0.5,
         f"{ph.M5_ENGAGEMENT:.1f} mm"),
        ("Mount screws pass through the adapter's nuts and stop short of the arm",
         -nut_far <= -m3_tip + 0.5 and m3_tip <= -ph.RELIEF_DEPTH - 0.5,
         f"tip at y = {m3_tip:.1f}, nut far face at y = {-nut_far:.1f}"),
        ("Washers set the stage clear of the adapter face", abs(-ph.ADAPTER_T - BACK_Y - WASHER_T) < 1e-6,
         f"{WASHER_T} mm"),
        ("Left mount pad sits in the ground anchor (>= 1.4 mm walls)", pad_wall >= 1.4, f"{pad_wall:.1f} mm"),
        ("Right mount pad's arm clears the rising ground beams", arm_gap >= CLR, f"{arm_gap:.1f} mm"),
        ("Beam stress at the hard stop (SF >= 1.8 on PETG)", sf >= 1.8, f"{FLEX.stress(TRAVEL):.1f} MPa, SF {sf:.1f}"),
        ("Beam stress at rest is low enough to limit creep (<= 8 MPa)", FLEX.stress(PRELOAD) <= 8.0,
         f"{FLEX.stress(PRELOAD):.1f} MPa"),
        ("Beams are at least two 0.4 mm perimeters", BEAM_T >= 0.8, f"{BEAM_T} mm"),
        ("Hard stop lands before the carriage beams reach the ground beams", MEMBER_EXT + 1.0 >= 2.0,
         f"{MEMBER_EXT + 1.0:.1f} mm left"),
        ("Carriage member clears the ground block as printed", Z_M0 - Z_GB1 >= 1.0, f"{Z_M0 - Z_GB1:.1f} mm"),
        ("Stop screw: head recessed, >= 5 mm of thread, under the carriage member",
         Z_BB0 <= Z_STOP_SEAT and Z_GB1 - Z_STOP_SEAT >= 5.0
         and X_MEMBER0 + 1.0 <= X_STOP - STOP_TAP_D / 2 and X_STOP + STOP_TAP_D / 2 <= X_ROOT - 1.0
         and X_IN_L - SIDE_BAR_W + 0.5 <= X_STOP - STOP_CBORE_D / 2,
         f"seat {Z_STOP_SEAT - Z_BB0:.1f} mm deep, {Z_GB1 - Z_STOP_SEAT:.1f} mm thread"),
        ("Rail sits on the carriage body", body_top(qc.RAIL_W1 / 2) >= Z_RAIL1 - PRELOAD - 1e-6, ""),
        ("Plunger tapping hole clear of the carriage's beams",
         Z_RAIL0 + qc.PLUNGER_Z - qc.PLUNGER_TAP_D / 2 >= Z_C0 + PRELOAD + 0.5, ""),
        ("Cartridge spine clears the static frame", FRAME_FRONT_Y - qc.SPINE_BACK_Y >= 1.0,
         f"{FRAME_FRONT_Y - qc.SPINE_BACK_Y:.1f} mm"),
        ("Pen tip stays below the frame at full stroke (10 mm margin)", Z_BB0 - Z_TIP - STROKE >= 10.0,
         f"{Z_BB0 - Z_TIP - STROKE:.1f} mm"),
        ("No rigid bodies collide (printed position, rest and hard stop)", max(clash.values()) < 0.01,
         ", ".join(f"{k} {v:.2f}" for k, v in clash.items() if v >= 0.01) or "none"),
        ("Preload holds the moving parts on their stop even with the pen pointing up (x1.3)",
         FLEX.rate * PRELOAD >= 1.3 * MOVING_WEIGHT, f"{FLEX.rate * PRELOAD:.2f} N vs {MOVING_WEIGHT:.2f} N"),
        ("Pen tip moves < 0.4 mm under 1 N of drawing drag, either way", drift < 0.4 and drift_x < 0.4,
         f"{drift:.2f} mm towards the flange, {drift_x:.2f} mm sideways"),
        (f"Pen tip nods < 0.2 mm as the force grows over {DRAWING:g} mm of over-reach", nod < 0.2, f"{nod:.2f} mm"),
    ]


MOVING = ("Cartridge", "Twist ring", "Jaw", "pen", "plunger", "carriage", "bars")
MOVING_WEIGHT = 0.80  # N: carriage, plunger, cartridge, rings, jaws and an 11 mm gel pen (see mass_properties)


def mass_properties(its: list) -> tuple[float, tuple[float, float, float], float]:
    """Rough mass (g), centre of mass (robot flange frame: X to the dowel, Z out of the flange), moving mass (g)."""
    density = {"printed": PETG_DENSITY * 0.6, "accent": PETG_DENSITY * 0.6, "cartridge": PETG_DENSITY * 0.6,
               "steel": 7.85e-3, "steel_black": 7.85e-3}
    m_tot, m_move, acc = 0.0, 0.0, [0.0, 0.0, 0.0]
    for it in its:
        rho = density.get(it.material, 0.6e-3 if it.material.startswith("pen") else 0.0)
        if not rho:
            continue
        m = it.shape.volume * rho
        c = it.shape.center()
        m_tot += m
        if any(k in it.name for k in MOVING):
            m_move += m
        for i, v in enumerate((c.Z, -c.X, -c.Y)):  # frame M -> robot flange frame
            acc[i] += m * v
    return m_tot, tuple(a / m_tot for a in acc), m_move


def design_report() -> str:
    lines = ["UTRA 6-1000 quick-change pen holder v2 (printed flexure)", "=" * 56]
    for label, ok, detail in design_checks():
        lines.append(f"  [{'ok' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))
    vol = make_stage().volume
    mass, com, moving = mass_properties(assembly(arm=False, split_stage=True))
    lines += [
        "",
        f"  TCP (pen tip at rest): X {TCP_F[0]:.1f}, Y 0, Z +{-qc.PEN_Y:.0f} mm in the flange frame"
        f" ({DZ:+.1f} mm along the pen vs v1, same for every pen)",
        f"  Compliant travel {STROKE:g} mm along the pen; preload {PRELOAD:g} mm set by the stop screws",
        *FLEX.report(PRELOAD, STROKE, DRAWING),
        f"  With the pen pointing down, the moving parts' weight (~{moving * 9.81e-3:.1f} N, {moving:.0f} g) adds to"
        " every force above",
        f"  Payload ~{mass / 1000:.2f} kg with an 11 mm gel pen, centre of mass X {com[0]:.0f}, Y {com[1]:.0f},"
        f" Z {com[2]:+.0f} mm (flange frame, Z out of the flange)",
        f"  Stage: {X_OUT_R - X_OUT_L:.0f} x {BACK_Y - qc.RAIL_FRONT_Y:.0f} x {Z_TB1 - Z_BB0:.0f} mm (W x D x H),"
        f" {vol / 1000:.0f} cm³ (~{vol * PETG_DENSITY * 0.6:.0f} g printed)",
        f"  Out-of-plane stiffness {FLEX.k_out_of_plane:.0f} N/mm, tilt {FLEX.k_tilt / 1000:.1f} N·m/rad",
        "  Cartridges, rings, jaws and the stick-out gauge are the v1 parts (../Quick-Change Pen Holder/STLs)",
    ]
    return "\n".join(lines)


# =============================================================================
# Export
# =============================================================================
PRINT_POSE = Pos(0, 0, BACK_Y) * Rot(-90, 0, 0)  # back face down


def printed_parts() -> dict[str, tuple[Part, Part]]:
    stage = make_stage()
    return {"Quick-Change v2 - Flexure Stage": (stage, PRINT_POSE * stage)}


def labelled_compound(items: list, label: str) -> Compound:
    children = []
    for item in items:
        shape = item.shape.moved(Location())
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
        print(f"  {name:34s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:6.1f} mm (print orientation),"
              f" z from {bb.min.Z:.2f}")
    asm = labelled_compound(assembly(), "UTRA 6-1000 quick-change pen holder v2")
    export_step(asm, out_dir / "STEP" / "Quick-Change v2 - Assembly.step")
    export_gltf(asm, out_dir / "Quick-Change v2 - Assembly.glb", binary=True, linear_deflection=0.08,
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
