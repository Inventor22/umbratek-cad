# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["build123d>=0.9,<0.14"]
# ///
"""
Pen holder v2, leaf-spring version, for the Umbratek UTRA 6-1000 (build123d)
============================================================================

    uv run pen_holder_v2_leaf.py      # prints a design report and writes STEP / STL / GLB

The v1 pen holder with its steel coil spring replaced by a printed PETG bow-spring stack: twelve bows (pairs of
0.5 mm leaves joined at their ends) in series, threaded on the pen. Everything else works as in v1: the carriage
slides in the barrel on two set-screw guide pins, the nose shoulder is the 15 mm hard stop, and the same tool adapter
bolts to the arm.

A PETG leaf can only bend about a tenth as far as spring steel for its length, so the stack is wider than the coil
spring: the barrel gets a Ø53 spring housing above the v1 guide bore, and the carriage's piston is 11 mm longer to
reach it.

Frame (mm), as in v1: origin = centre of the arm's flange face, +Z into the arm (the tool hangs along -Z), +X towards
the Ø3 dowel. The stack's leaves lie in the XZ plane.
"""

from __future__ import annotations

import argparse
import math
import sys
from dataclasses import dataclass
from pathlib import Path

from build123d import Box, Color, Compound, Part, Pos, Rot, Shape, export_gltf, export_step, export_stl

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "Pen Holder"))
sys.path.insert(0, str(HERE))
import pen_holder as ph  # noqa: E402  (flange, adapter, hardware and pen models)
from bow_spring import PETG_STRENGTH, BowStack  # noqa: E402
from pen_holder import cut_all, polar, radial_cyl, revolved, zcyl  # noqa: E402

# =============================================================================
# Spring
# =============================================================================
STROKE = ph.STROKE  # 15 mm, then the nose shoulder lands on the barrel
PRELOAD = 4.5  # stack squeeze with the pen in free air
SPRING = BowStack(
    n=12,  # bows in series
    leaf_len=10.0,  # each half-leaf, crown tab to joint tab
    t=0.5,  # leaf thickness: one 0.5 mm extrusion line
    b=11.0,  # leaf depth
    crown_w=16.0,  # crown tab: a ring around the pen
    joint_w=2.5,
    tab_t=2.5,
    depth=18.0,  # crown tab depth
    pitch=5.0,
    crown_hole=ph.PEN_D + 1.4,
)

# =============================================================================
# Module: v1 flange and guide barrel, with a spring housing between them
# =============================================================================
HOUSING_D = ph.MODULE_FLANGE_D  # outside, as wide as the flange (inside the M5 counterbores)
HOUSING_BORE = 46.0
CROWN_POCKET = 2.0  # the stack's top crown sits in a pocket under the flange, which keys it
CONE_H = (HOUSING_BORE - ph.BARREL_BORE) / 2  # 45° cone from the housing bore down to the guide bore
GUIDED = ph.PISTON_L - ph.STROKE  # guided length of the piston at rest, as v1
PISTON_L = GUIDED + STROKE + CONE_H  # the piston reaches up through the cone to the stack

# =============================================================================
# Derived (Z positions for the "pen in free air" state)
# =============================================================================
Z_FLANGE_BOTTOM = ph.Z_FLANGE_BOTTOM
Z_STACK_TOP = Z_FLANGE_BOTTOM + CROWN_POCKET
Z_CARRIAGE_TOP = Z_STACK_TOP - SPRING.length(PRELOAD)  # piston top = stack bottom
Z_GUIDE_TOP = Z_CARRIAGE_TOP - CONE_H  # top of the guide bore
Z_NOSE_TOP = Z_CARRIAGE_TOP - PISTON_L
Z_NOSE_BOTTOM = Z_NOSE_TOP - ph.NOSE_L
Z_BARREL_BOTTOM = Z_NOSE_TOP + STROKE  # the nose shoulder lands here at full stroke
Z_PIN = Z_BARREL_BOTTOM + ph.SLOT_BOTTOM_RING
Z_CLAMP = Z_NOSE_TOP - ph.NOSE_L / 2
Z_TIP = Z_NOSE_BOTTOM - ph.PEN_STICKOUT
TCP_Z = -Z_TIP


# =============================================================================
# Printed part 1: module (flange + spring housing + guide barrel)
# =============================================================================
def make_module() -> Part:
    r_fl, r_h, r_o, r_b = HOUSING_D / 2, HOUSING_BORE / 2, ph.BARREL_OD / 2, ph.BARREL_BORE / 2
    zt, zf, zc, zb = ph.Z_ADAPTER_BOTTOM, Z_FLANGE_BOTTOM, Z_CARRIAGE_TOP, Z_BARREL_BOTTOM
    cone_out = r_fl - r_o  # outer 45° cone, flange diameter down to the barrel
    body = revolved(
        [
            (ph.MODULE_CENTER_HOLE_D / 2, zt),
            (r_fl - 0.6, zt),
            (r_fl, zt - 0.6),
            (r_fl, zc),
            (r_o, zc - cone_out),
            (r_o, zb + 0.8),
            (r_o - 0.8, zb),
            (r_b + 1.0, zb),  # lead-in for the carriage
            (r_b, zb + 1.0),
            (r_b, Z_GUIDE_TOP),
            (r_h, zc),  # inner 45° cone: prints without support with the flange on the bed
            (r_h, zf),
            (ph.MODULE_CENTER_HOLE_D / 2, zf),
        ]
    )
    tools = []
    for a in ph.MODULE_SCREW_ANGLES:  # v1 interface: 3x M3 x 14 up into the adapter's captive nuts
        x, y = polar(ph.MODULE_SCREW_PCD / 2, a)
        tools.append(Pos(x, y, 0) * zcyl(ph.M3_CLEAR_D, zf - 1, zt + 1))
        tools.append(Pos(x, y, 0) * zcyl(ph.M3_CBORE_D, zf - 1, ph.Z_M3_SEAT))
    # pocket that keys the stack's top crown tab
    cw, cd = SPRING.crown_w + 0.4, SPRING.depth + 0.4
    tools.append(Pos(0, 0, zf + CROWN_POCKET / 2 - 0.5) * Box(cw, cd, CROWN_POCKET + 1))
    # guide slots and travel ticks, as v1
    z_lo = Z_PIN + (ph.GUIDE_SLOT_W - ph.GUIDE_PIN_D) / 2
    z_hi = Z_PIN + STROKE + ph.SLOT_OVERTRAVEL
    span = ph.BARREL_OD + 4
    tools.append(Pos(0, 0, (z_lo + z_hi) / 2) * Box(ph.GUIDE_SLOT_W, span, z_hi - z_lo))
    for z in (z_lo, z_hi):
        tools.append(Pos(0, 0, z) * Rot(90, 0, 0) * ph.Cylinder(ph.GUIDE_SLOT_W / 2, span))
    for side in (1, -1):
        for dz in ph.TICKS:
            length = 4.0 if dz in (0.0, STROKE) else 2.5
            gap = ph.GUIDE_SLOT_W / 2 + 0.8 + length / 2
            theta = side * (90 - math.degrees(gap / r_o))
            tools.append(Rot(0, 0, theta) * Pos(r_o, 0, Z_PIN + dz) * Box(1.2, length, 0.6))
    return cut_all(body, tools)


# =============================================================================
# Printed part 2: pen carriage (local frame: z = 0 is the stack seat, tool along -Z)
# =============================================================================
def carriage_z(z_global: float) -> float:
    return z_global - Z_CARRIAGE_TOP


def make_carriage() -> Part:
    """v1's carriage with a longer piston and a flat top for the stack instead of the coil spring's spigot."""
    r_b, r_p, r_n = ph.PEN_BORE / 2, ph.PISTON_D / 2, ph.NOSE_D / 2
    zn, zbot = -PISTON_L, -PISTON_L - ph.NOSE_L
    body = revolved(
        [
            (r_b, 0.0),
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
    tools = [radial_cyl(ph.GUIDE_PIN_HOLE_D, r_p - ph.GUIDE_PIN_HOLE_DEPTH, r_p + 1, z_pin, a) for a in (90, -90)]
    tools.append(radial_cyl(ph.M3_CLEAR_D + 0.1, r_b - 0.5, r_n + 1, z_cl, 0))
    x0, x1 = ph.CLAMP_NUT_X0, ph.CLAMP_NUT_X0 + ph.CLAMP_NUT_POCKET_T
    z_top = z_cl + ph.NUT_POCKET_AF / math.sqrt(3)
    tools.append(Pos((x0 + x1) / 2, 0, (zbot - 1 + z_top) / 2) * Box(x1 - x0, ph.NUT_POCKET_AF, z_top - zbot + 1))
    tools.append(Pos(ph.CLAMP_SPOT_FACE_X + 5, 0, z_cl) * Box(10, 14, 10))
    return cut_all(body, tools)

# =============================================================================
# Assembly
# =============================================================================
COLORS = {**ph.COLORS, "spring_petg": "#f26b1d"}


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
    return Pos(0, 0, Z_CARRIAGE_TOP + travel) * _cached(("stack", sq), lambda: SPRING.shape(sq))


def assembly(travel: float = 0.0, arm: bool = True, hardware: bool = True, pen: bool = True) -> list[Item]:
    """Every part in place. `travel` = how far the carriage has been pushed up (0..STROKE)."""
    if not 0.0 <= travel <= STROKE:
        raise ValueError(f"travel must be within 0..{STROKE} mm")
    up = travel
    ex_carriage = (0.0, 0.0, -150.0)
    items: list[Item] = []
    if arm:
        items.append(Item("UTRA 6-1000 tool flange (ref)", _cached("arm_flange", ph.make_arm_flange), "aluminum", (0, 0, 70)))
        items.append(Item("UTRA 6-1000 J6 housing (ref)", _cached("arm_housing", ph.make_arm_housing), "arm_dark", (0, 0, 70)))
    items.append(Item("Tool adapter (v1)", _cached("adapter", ph.make_adapter), "printed"))
    items.append(Item("Pen module", _cached("module", make_module), "printed", (0, 0, -50)))
    items.append(Item("Pen carriage", Pos(0, 0, Z_CARRIAGE_TOP + up) * _cached("carriage", make_carriage), "accent",
                      ex_carriage))
    items.append(Item("Bow-spring stack", stack_at(travel), "spring_petg", (0, 0, -100)))
    if hardware:
        m5 = _cached("m5", lambda: ph.make_shcs(5.0, ph.M5_SCREW_LEN, ph.M5_HEAD_D, ph.M5_HEAD_H, 4.0))
        for i in range(ph.BOLT_COUNT):
            x, y = polar(ph.BOLT_PCD / 2, i * 360 / ph.BOLT_COUNT)
            items.append(Item(f"M5x12 SHCS {i + 1}", Pos(x, y, ph.Z_M5_SEAT) * m5, "steel_black", (0, 0, -28)))
        z_dowel = ph.DOWEL_HOLE_DEPTH - 0.5 - ph.DOWEL_LEN
        items.append(Item("Dowel pin 3x8", Pos(ph.DOWEL_PCD / 2, 0, z_dowel) * _cached("dowel", ph.make_dowel), "steel",
                          (0, 0, 32)))
        m3 = _cached("m3", lambda: ph.make_shcs(3.0, ph.MODULE_SCREW_LEN, ph.M3_HEAD_D, ph.M3_HEAD_H, 2.5))
        nut = _cached("nut", ph.make_nut)
        for i, a in enumerate(ph.MODULE_SCREW_ANGLES):
            x, y = polar(ph.MODULE_SCREW_PCD / 2, a)
            items.append(Item(f"M3x14 SHCS {i + 1}", Pos(x, y, ph.Z_M3_SEAT) * m3, "steel_black", (0, 0, -95)))
            z_nut = ph.Z_NUT_POCKET_BOTTOM + ph.M3_NUT_T / 2
            items.append(Item(f"M3 nut {i + 1}", Pos(x, y, z_nut) * Rot(0, 0, a - 30) * nut, "steel", (0, 0, 24)))
        pin = _cached("set_screw", lambda: ph.make_set_screw(ph.GUIDE_PIN_D, ph.GUIDE_PIN_LEN, 1.5))
        r_pin = ph.PISTON_D / 2 - ph.GUIDE_PIN_HOLE_DEPTH
        for a in (90, -90):
            ex = (0.0, math.copysign(16.0, a), ex_carriage[2])
            items.append(Item(f"M3x6 set screw (guide pin, {'+' if a > 0 else '-'}Y)",
                              Rot(0, 0, a) * Pos(r_pin, 0, Z_PIN + up) * pin, "steel_black", ex))
        items.append(Item("M3x10 thumb screw", Pos(ph.PEN_D / 2, 0, Z_CLAMP + up) * _cached("thumb", ph.make_thumb_screw),
                          "steel", (20.0, 0.0, ex_carriage[2])))
        x_nut = ph.CLAMP_NUT_X0 + ph.CLAMP_NUT_POCKET_T - ph.M3_NUT_T / 2
        items.append(Item("M3 nut (pen clamp)", Pos(x_nut, 0, Z_CLAMP + up) * Rot(0, 90, 0) * nut, "steel",
                          (0.0, 0.0, ex_carriage[2] - 22)))
    if pen:
        for name, shape, material in _cached("pen", ph.make_pen):
            items.append(Item(name, Pos(0, 0, Z_TIP + up) * shape, material, (-70, 0, -140)))
    return items


# =============================================================================
# Design checks and report
# =============================================================================
def design_checks() -> list[tuple[str, bool, str]]:
    s = SPRING
    full = PRELOAD + STROKE
    sf = PETG_STRENGTH / s.stress(full)
    joint_r = math.hypot(s.width / 2, s.depth / 2)  # joint tabs sit at the leaves' depth, inside the crown's
    crown_r = math.hypot(s.crown_w / 2, s.depth / 2)
    m3_tip = ph.Z_M3_SEAT + ph.MODULE_SCREW_LEN
    nut_top = ph.Z_NUT_POCKET_BOTTOM + ph.M3_NUT_T
    pen_end_full = Z_TIP + STROKE + ph.PEN_LEN
    slot_top = Z_PIN + STROKE + ph.SLOT_OVERTRAVEL + ph.GUIDE_SLOT_W
    cone_foot = Z_CARRIAGE_TOP - (HOUSING_D - ph.BARREL_OD) / 2  # where the outer cone meets the barrel
    cone_wall = (HOUSING_D / 2 - HOUSING_BORE / 2) / math.sqrt(2)
    return [
        ("M5 engagement within the 6 mm arm thread", ph.M5_ENGAGEMENT <= ph.BOLT_THREAD_DEPTH - 0.5,
         f"{ph.M5_ENGAGEMENT:.1f} mm"),
        ("Module screws pass through their nuts but stay below the relief floor",
         nut_top <= m3_tip <= -ph.RELIEF_DEPTH - 0.5, f"tip at z = {m3_tip:.1f}"),
        ("Module (flange and housing) clears the M5 counterbores", HOUSING_D / 2 <= ph.BOLT_PCD / 2 - ph.M5_CBORE_D / 2,
         f"{HOUSING_D / 2:.1f} <= {ph.BOLT_PCD / 2 - ph.M5_CBORE_D / 2:.1f}"),
        ("Leaf stress at the hard stop (SF >= 1.8 on PETG)", sf >= 1.8, f"{s.stress(full):.1f} MPa, SF {sf:.1f}"),
        ("Leaf stress at rest is low enough to limit creep (<= 8 MPa)", s.stress(PRELOAD) <= 8.0,
         f"{s.stress(PRELOAD):.1f} MPa"),
        ("Leaves are at least one 0.45 mm extrusion line", s.t >= 0.45, f"{s.t} mm"),
        ("The stack never closes up before the hard stop", s.max_squeeze >= full + 0.5,
         f"room for {s.max_squeeze:.1f} mm, needs {full:.1f}"),
        ("Stack fits the housing bore with the pen through it", max(joint_r, crown_r) <= HOUSING_BORE / 2 - 0.4,
         f"r {max(joint_r, crown_r):.1f} <= {HOUSING_BORE / 2 - 0.4:.1f}"),
        ("Pen passes the crown tabs, which keep >= 0.7 mm walls", s.crown_hole >= ph.PEN_D + 1.0
         and (s.crown_w - s.crown_hole) / 2 >= 0.7 and (s.depth - s.crown_hole) / 2 >= 1.5, ""),
        ("Bottom crown sits on the piston", crown_r <= ph.PISTON_D / 2 + 0.5, f"r {crown_r:.1f}"),
        ("Housing walls >= 3 mm, also across the cones", HOUSING_D / 2 - HOUSING_BORE / 2 >= 3.0 and cone_wall >= 2.0,
         f"{HOUSING_D / 2 - HOUSING_BORE / 2:.1f} mm, {cone_wall:.1f} mm across the cones"),
        ("Engaged length / piston dia >= 1.4 (no jamming)", GUIDED / ph.PISTON_D >= 1.4, f"{GUIDED / ph.PISTON_D:.2f}"),
        ("Guide slots stay in the plain barrel, below the cone", slot_top <= cone_foot - 1.0,
         f"{cone_foot - slot_top:.1f} mm below"),
        ("Pen end stays clear of the arm at full stroke", pen_end_full <= -ph.RELIEF_DEPTH - 3,
         f"pen end at z = {pen_end_full:.1f}"),
    ]


def design_report() -> str:
    lines = ["UTRA 6-1000 pen holder v2, leaf spring", "=" * 38]
    for label, ok, detail in design_checks():
        lines.append(f"  [{'ok' if ok else 'FAIL'}] {label}" + (f"  ({detail})" if detail else ""))
    lines += [
        "",
        f"  TCP (pen tip, spring relaxed): X 0, Y 0, Z +{TCP_Z:.1f} mm along the flange axis",
        f"  Compliant over-travel: {STROKE:g} mm, then a hard stop; stack squeezed {PRELOAD:g} mm at rest",
        *SPRING.report(PRELOAD, STROKE),
        f"  Module: Ø{HOUSING_D:g} spring housing, {ph.Z_ADAPTER_BOTTOM - Z_BARREL_BOTTOM:.0f} mm long",
    ]
    return "\n".join(lines)


# =============================================================================
# Export
# =============================================================================
def printed_parts() -> dict[str, tuple[Part, Part]]:
    """name -> (part in the assembly frame, part in its print orientation)."""
    module, carriage, stack = make_module(), make_carriage(), SPRING.shape(0.0)
    return {
        "Pen Holder v2 Leaf - Module": (module, Pos(0, 0, ph.Z_ADAPTER_BOTTOM) * Rot(180, 0, 0) * module),
        "Pen Holder v2 Leaf - Carriage": (Pos(0, 0, Z_CARRIAGE_TOP) * carriage,
                                          Pos(0, 0, PISTON_L + ph.NOSE_L) * carriage),
        "Pen Holder v2 Leaf - Bow Spring": (Pos(0, 0, Z_CARRIAGE_TOP - PRELOAD) * stack,
                                            Pos(0, 0, SPRING.depth / 2) * Rot(90, 0, 0) * stack),
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
        print(f"  {name:32s} {bb.size.X:6.1f} x {bb.size.Y:6.1f} x {bb.size.Z:6.1f} mm (print orientation),"
              f" z from {bb.min.Z:.2f}")
    asm = labelled_compound(assembly(), "UTRA 6-1000 pen holder v2, leaf spring")
    export_step(asm, out_dir / "STEP" / "Pen Holder v2 Leaf - Assembly.step")
    export_gltf(asm, out_dir / "Pen Holder v2 Leaf - Assembly.glb", binary=True, linear_deflection=0.08,
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
