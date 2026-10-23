# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["build123d>=0.9,<0.14"]
# ///
"""
Quick-change pen holder v2, leaf-spring version, for the UTRA 6-1000 (build123d)
================================================================================

    uv run quick_change_v2_leaf.py      # prints a design report, writes STEP / STL / GLB

The v1 quick-change pen holder with its two steel coil springs replaced by a printed PETG bow-spring stack: eight
bows (pairs of 0.5 mm leaves joined at their ends) in series, threaded on the two guide rods through the tabs where
their leaves meet. Everything else works as in v1: the carriage slides on the rods, the cartridges, rings, jaws and
gauge are the v1 parts, and the pen tip is where v1 puts it.

* The rods move out to ±19.5 mm to make room for leaves long enough for 15 mm of travel in PETG.
* The stack is the hard stop: its tabs close up when the carriage has travelled 15 mm.
* The top block is a separate cap clamped to the rods, so the base needs no side walls: it prints without supports
  and every M5 screw stays reachable.

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
sys.path.insert(0, str(HERE.parent / "Quick-Change Pen Holder"))
sys.path.insert(0, str(HERE.parent / "Pen Holder v2 Leaf Spring"))
import pen_holder as ph  # noqa: E402  (flange, hardware)
import quick_change_pen_holder as qc  # noqa: E402  (cartridge, rings, jaws, gauge, pens, plunger)
from bow_spring import PETG_STRENGTH, BowStack  # noqa: E402
from pen_holder import cut_all, polar, revolved, zcyl  # noqa: E402

F2M = qc.F2M
box, ycyl = qc.box, qc.ycyl

# =============================================================================
# Spring
# =============================================================================
STROKE = qc.STROKE  # 15 mm along the pen, then the stack closes up
PRELOAD = 5.5  # stack squeeze at rest
_N, _TAB = 8, 2.5
SPRING = BowStack(
    n=_N,
    leaf_len=12.5,
    t=0.5,  # one 0.5 mm extrusion line
    b=13.0,  # leaf depth = stage depth
    crown_w=4.0,
    joint_w=10.0,  # joint tabs carry the rod holes
    tab_t=_TAB,
    depth=13.0,
    pitch=_TAB + (PRELOAD + STROKE) / _N,  # the tabs close up exactly at the end of the stroke: the hard stop
    joint_hole=qc.ROD_D + 0.8,
)

# =============================================================================
# Stage (v1 layout with the rods moved out)
# =============================================================================
ROD_X = SPRING.x_joint  # rods through the stack's joint tabs
ROD_Y = qc.ROD_Y
ROD_LEN = 100.0  # Ø6 x 100 steel rods
STAGE_HW = ROD_X + qc.BUSHING_D / 2 + 3.0  # carriage, bottom block and cap half-width
CAP_SET_Z = 4.0  # rod set screws, above the cap's underside
CROWN_POCKET = 1.0  # keys the stack's crown tabs in the carriage and the cap
Z_C0, Z_C1 = qc.Z_C0, qc.Z_C1  # carriage bottom (rest stop) and top, as v1
Z_BB0 = qc.Z_BB0  # bottom block, as v1
Z_CAP0 = Z_C1 - CROWN_POCKET + SPRING.length(PRELOAD) - CROWN_POCKET  # cap underside
Z_CAP1 = Z_BB0 + ROD_LEN  # cap top = rod ends


# =============================================================================
# Printed part 1: base (v1 plate and chin; the bottom block is the rest stop and holds the rods)
# =============================================================================
def make_base() -> Part:
    r_out, r_pilot = ph.ADAPTER_OD / 2, (ph.PILOT_D + ph.PILOT_CLEARANCE) / 2
    zt = ph.PILOT_RECESS_DEPTH
    plate = F2M * revolved(
        [
            (0, -qc.BASE_T),
            (r_out - 1.0, -qc.BASE_T),
            (r_out, -qc.BASE_T + 1.0),
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
    yb, yf = -qc.BASE_T + 0.01, qc.STAGE_FRONT_Y
    chin = r_out * math.sin(math.radians(45))  # carries the disc's lower rim: no overhang over 45° upright
    body = plate + box(-chin, chin, -qc.BASE_T, 0.0, Z_BB0, -30.0)
    body += box(-STAGE_HW, STAGE_HW, yf, yb, Z_BB0, Z_C0)  # bottom block (rest stop)
    tools = []
    for i in range(ph.BOLT_COUNT):
        x, y = polar(ph.BOLT_PCD / 2, i * 360 / ph.BOLT_COUNT)
        tools.append(F2M * (Pos(x, y, 0) * zcyl(ph.M5_CLEAR_D, -qc.BASE_T - 1, 1)))
        tools.append(F2M * (Pos(x, y, 0) * zcyl(ph.M5_CBORE_D, -qc.BASE_T - 1, ph.Z_M5_SEAT)))
    tools.append(F2M * (Pos(ph.DOWEL_PCD / 2, 0, 0) * zcyl(ph.DOWEL_HOLE_D, -qc.BASE_T - 1, 1)))
    for s in (-1, 1):
        x = s * ROD_X
        tools.append(Pos(x, ROD_Y, 0) * zcyl(qc.ROD_HOLE_D, Z_BB0 - 1, Z_C0 + 1))
        tools.append(ycyl(2.5, x, Z_BB0 + 7.0, yf - 1, ROD_Y))  # M3 set screw locks the rod
    return cut_all(body, tools)


# =============================================================================
# Printed part 2: carriage (local z = 0 at its bottom face)
# =============================================================================
def crown_pocket(z0: float, z1: float) -> Part:
    return box(-SPRING.crown_w / 2 - 0.2, SPRING.crown_w / 2 + 0.2, ROD_Y - SPRING.depth / 2 - 0.2,
               ROD_Y + SPRING.depth / 2 + 0.2, z0, z1)


def make_carriage() -> Part:
    yf, yb = qc.CARRIAGE_Y
    body = box(-STAGE_HW, STAGE_HW, yf, yb, 0, qc.CARRIAGE_L) + qc.prism_xy(qc.rail_profile(), 0, qc.CARRIAGE_L)
    tools = [Pos(s * ROD_X, ROD_Y, 0) * zcyl(qc.BUSHING_D, -1, qc.CARRIAGE_L + 1) for s in (-1, 1)]
    tools.append(ycyl(qc.PLUNGER_TAP_D, 0, qc.PLUNGER_Z, qc.RAIL_FRONT_Y - 1, yb + 1))
    m5 = polar(ph.BOLT_PCD / 2, 180.0)  # lowest M5 screw (F frame) sits behind the carriage
    tools.append(ycyl(qc.ACCESS_HOLE_D, 0, m5[0] - Z_C0, qc.RAIL_FRONT_Y - 1, yb + 1))
    tools.append(crown_pocket(qc.CARRIAGE_L - CROWN_POCKET, qc.CARRIAGE_L + 1))
    return cut_all(body, tools)


# =============================================================================
# Printed part 3: cap (top block, clamped to the rods; local z = 0 at its underside)
# =============================================================================
def make_cap() -> Part:
    yf, yb = qc.STAGE_FRONT_Y, -qc.BASE_T - 0.5
    h = Z_CAP1 - Z_CAP0
    body = box(-STAGE_HW, STAGE_HW, yf, yb, 0, h)
    tools = [crown_pocket(-1, CROWN_POCKET)]
    for s in (-1, 1):
        x = s * ROD_X
        tools.append(Pos(x, ROD_Y, 0) * zcyl(qc.ROD_HOLE_D, -1, h + 1))
        tools.append(ycyl(2.5, x, CAP_SET_Z, yf - 1, ROD_Y))
    return cut_all(body, tools)


def make_rod() -> Part:
    r, c = qc.ROD_D / 2, 0.5
    return revolved([(0, 0), (r - c, 0), (r, c), (r, ROD_LEN - c), (r - c, ROD_LEN), (0, ROD_LEN)])

# =============================================================================
# Assembly
# =============================================================================
COLORS = {**qc.COLORS, "spring_petg": "#f26b1d"}
EX_CARRIAGE, EX_STACK, EX_CAP = (0.0, -40.0, 0.0), (0.0, -40.0, 45.0), (0.0, 0.0, 90.0)


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


def stack_at(travel: float) -> Shape:
    sq = round(PRELOAD + travel, 3)
    return Pos(0, ROD_Y, Z_C1 - CROWN_POCKET + travel) * _cached(("stack", sq), lambda: SPRING.shape(sq))


def assembly(travel: float = 0.0, pen: str | None = "Gel pen 11 mm", arm: bool = True, hardware: bool = True,
             explode: bool = False) -> list:
    if not 0.0 <= travel <= STROKE:
        raise ValueError(f"travel must be within 0..{STROKE} mm")
    up = travel
    items: list = []
    if arm:
        items.append(Item("UTRA 6-1000 tool flange (ref)", F2M * _cached("arm_flange", ph.make_arm_flange),
                          "aluminum", (0, 60, 0)))
        items.append(Item("UTRA 6-1000 J6 housing (ref)", F2M * _cached("arm_housing", ph.make_arm_housing),
                          "arm_dark", (0, 60, 0)))
    items.append(Item("Base", _cached("base", make_base), "printed"))
    items.append(Item("Carriage", Pos(0, 0, Z_C0 + up) * _cached("carriage", make_carriage), "accent", EX_CARRIAGE))
    items.append(Item("Bow-spring stack", stack_at(travel), "spring_petg", EX_STACK))
    items.append(Item("Top cap", Pos(0, 0, Z_CAP0) * _cached("cap", make_cap), "printed", EX_CAP))
    for s in (-1, 1):
        items.append(Item(f"Rod {'L' if s < 0 else 'R'}", Pos(s * ROD_X, ROD_Y, Z_BB0) * _cached("rod", make_rod),
                          "steel", (0, 0, 150)))
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
            for tag, z, ex in (("bottom", Z_BB0 + 7.0, (0, -20, 0)), ("cap", Z_CAP0 + CAP_SET_Z, (0, -20, EX_CAP[2]))):
                items.append(Item(f"M3x3 set screw ({tag} {'L' if s < 0 else 'R'})",
                                  Pos(s * ROD_X, ROD_Y - qc.ROD_D / 2, z) * Rot(0, 0, -90) * set_screw, "steel_black", ex))
        items.append(Item("M6 ball spring plunger", Pos(0, qc.PLUNGER_FACE_Y, Z_C0 + up + qc.PLUNGER_Z)
                          * _cached("plunger", qc.make_plunger), "steel", (EX_CARRIAGE[0], EX_CARRIAGE[1] - 35, 0)))
    items += qc.cartridge_items(pen, up, explode=explode)
    return items


# =============================================================================
# Design checks and report
# =============================================================================
MOVING_WEIGHT = 0.90  # N: carriage, plunger, about half the stack, cartridge, rings, jaws and an 11 mm gel pen


def design_checks() -> list[tuple[str, bool, str]]:
    s = SPRING
    full = PRELOAD + STROKE
    sf = PETG_STRENGTH / s.stress(full)
    closes = s.n * (s.pitch - s.tab_t)
    m5_side_z = ph.BOLT_PCD / 2 * math.cos(math.radians(60))  # the four side M5 screws sit at z = ±16 (frame M)
    access_z = -ph.BOLT_PCD / 2 - Z_C0
    return [
        ("M5 engagement within the 6 mm arm thread", ph.M5_ENGAGEMENT <= ph.BOLT_THREAD_DEPTH - 0.5,
         f"{ph.M5_ENGAGEMENT:.1f} mm"),
        ("Leaf stress at the hard stop (SF >= 1.8 on PETG)", sf >= 1.8, f"{s.stress(full):.1f} MPa, SF {sf:.1f}"),
        ("Leaf stress at rest is low enough to limit creep (<= 8 MPa)", s.stress(PRELOAD) <= 8.0,
         f"{s.stress(PRELOAD):.1f} MPa"),
        ("Leaves are at least one 0.45 mm extrusion line", s.t >= 0.45, f"{s.t} mm"),
        ("The stack closes up exactly at the end of the stroke (it is the hard stop)", abs(closes - full) < 0.05,
         f"closes after {closes:.2f} mm of squeeze"),
        ("Rods pass the joint tabs, which keep >= 1.2 mm walls", s.joint_hole >= qc.ROD_D + 0.6
         and (s.joint_w - s.joint_hole) / 2 >= 1.2 and (s.b - s.joint_hole) / 2 >= 1.2, ""),
        ("Stack fits inside the stage", s.width / 2 <= STAGE_HW - 0.5, f"{s.width / 2:.1f} <= {STAGE_HW - 0.5:.1f}"),
        ("Rods span the bottom block and the cap", abs((Z_CAP1 - Z_BB0) - ROD_LEN) < 1e-6, f"{ROD_LEN:g} mm"),
        ("Cap thick enough for its set screws", Z_CAP1 - Z_CAP0 >= 2 * CAP_SET_Z + 2.0, f"{Z_CAP1 - Z_CAP0:.1f} mm"),
        ("Carriage bushings keep >= 2.5 mm walls", STAGE_HW - ROD_X - qc.BUSHING_D / 2 >= 2.5, ""),
        ("Preload holds the moving parts on the rest stop even with the pen pointing up (x1.25)",
         s.rate * PRELOAD >= 1.25 * MOVING_WEIGHT, f"{s.rate * PRELOAD:.2f} N vs {MOVING_WEIGHT:.2f} N"),
        ("Lowest M5 reachable through the carriage",
         qc.ACCESS_HOLE_D / 2 + 1 <= access_z <= qc.CARRIAGE_L - qc.ACCESS_HOLE_D / 2 - 1, ""),
        ("Side M5 screws stay reachable: nothing on the base stands in front of them",
         Z_C0 <= -m5_side_z - ph.M5_HEAD_D / 2 - 1.0, f"bottom block up to z = {Z_C0:g}, screws at z = ±{m5_side_z:.0f}"),
        ("Rings clear the base's bottom block and the cap", qc.PEN_Y + qc.RING_OD / 2 <= qc.STAGE_FRONT_Y - 1.0, ""),
        ("Pen tip well below the base", -qc.Z_TIP + Z_BB0 >= STROKE + 15.0, f"{-qc.Z_TIP + Z_BB0:.0f} mm"),
    ]


def design_report() -> str:
    lines = ["UTRA 6-1000 quick-change pen holder v2, leaf spring", "=" * 51]
    for label, ok, detail in design_checks():
        lines.append(f"  [{'ok' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))
    lines += [
        "",
        f"  TCP (pen tip, spring relaxed): X {qc.TCP_F[0]:.1f}, Y 0, Z +{-qc.PEN_Y:.0f} mm in the flange frame, as v1",
        f"  Compliant travel {STROKE:g} mm along the pen, then the stack closes up; squeezed {PRELOAD:g} mm at rest",
        *SPRING.report(PRELOAD, STROKE),
        f"  Stage: {2 * STAGE_HW:.0f} mm wide, rods {ROD_LEN:g} mm (v1: {qc.STAGE_W:g} mm wide, {qc.ROD_LEN:g} mm rods)",
        "  Cartridges, rings, jaws and the stick-out gauge are the v1 parts (../Quick-Change Pen Holder/STLs)",
    ]
    return "\n".join(lines)


# =============================================================================
# Export
# =============================================================================
def printed_parts() -> dict[str, tuple[Part, Part]]:
    base, carriage, cap, stack = make_base(), make_carriage(), make_cap(), SPRING.shape(0.0)
    h_cap = Z_CAP1 - Z_CAP0
    return {
        "Quick-Change v2 Leaf - Base": (base, Pos(0, 0, -Z_BB0) * base),
        "Quick-Change v2 Leaf - Carriage": (Pos(0, 0, Z_C0) * carriage, Pos(0, -sum(qc.CARRIAGE_Y) / 2, 0) * carriage),
        "Quick-Change v2 Leaf - Top Cap": (Pos(0, 0, Z_CAP0) * cap, Pos(0, 0, h_cap) * Rot(180, 0, 0) * cap),
        "Quick-Change v2 Leaf - Bow Spring": (Pos(0, ROD_Y, Z_C1 - CROWN_POCKET - PRELOAD) * stack,
                                              Pos(0, 0, SPRING.depth / 2) * Rot(90, 0, 0) * stack),
    }


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
        print(f"  {name:36s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:6.1f} mm (print orientation),"
              f" z from {bb.min.Z:.2f}")
    asm = labelled_compound(assembly(), "UTRA 6-1000 quick-change pen holder v2, leaf spring")
    export_step(asm, out_dir / "STEP" / "Quick-Change v2 Leaf - Assembly.step")
    export_gltf(asm, out_dir / "Quick-Change v2 Leaf - Assembly.glb", binary=True, linear_deflection=0.08,
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
