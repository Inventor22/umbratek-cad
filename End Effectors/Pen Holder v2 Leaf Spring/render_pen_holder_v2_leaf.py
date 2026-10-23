# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["build123d>=0.9,<0.14", "pyvista>=0.43", "numpy", "pillow"]
# ///
"""
Render pen holder v2, leaf-spring version (pen_holder_v2_leaf.py), to PNG images.

    uv run render_pen_holder_v2_leaf.py              # -> <repo>/Renders/Pen Holder v2 Leaf Spring Render N.png
    uv run render_pen_holder_v2_leaf.py --hero-glb hero.glb   # scene for ../Pen Holder/blender_hero.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pyvista as pv
from build123d import Pos, Rot
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "Pen Holder"))
import pen_holder_v2_leaf as lf  # noqa: E402
import render_pen_holder as rph  # noqa: E402
from render_pen_holder import INK, Scene, annotate, cut_away, font, footer, title  # noqa: E402

ph = lf.ph
OUT_DIR = HERE.parents[1] / "Renders"
PREFIX = "Pen Holder v2 Leaf Spring Render"
FOOT = "umbratek-cad / End Effectors / Pen Holder v2 Leaf Spring  -  build123d"
rph.MATERIALS["spring_petg"] = ("#f26b1d", 0.0, 0.42, "#ff9d5c")
RED = (200, 60, 20)


def add_section(sc: Scene, items, keep=("Bow-spring", "Pen nib", "Pen front", "Pen barrel", "Pen end")) -> None:
    """Cut away y < 0, except the spring and the pen, which stay whole inside the cut barrel."""
    for it in items:
        if "housing" in it.name:
            continue
        s = it.shape if any(k in it.name for k in keep) or "flange (ref)" in it.name else cut_away(it.shape)
        if s is not None:
            sc.add(s, it.material, caps=[(1, 0.0)])


def render_cutaway(path: Path) -> None:
    sc = Scene(1800, 2000)
    add_section(sc, lf.assembly(travel=0.0))
    sc.camera((0, 0, -95), (0.35, -1.0, 0.18), zoom=1.0)
    img = sc.render()
    s, p = lf.SPRING, lf.PRELOAD
    z0 = lf.Z_CARRIAGE_TOP
    zc = s.crown_z(p)
    xj = s.x_joint
    notes = [
        ((30, -10, 10), "R", 0, "UTRA 6-1000 tool flange\nreference"),
        ((40, -5, -6), "R", 0, "Tool adapter (v1)"),
        ((0, -9, z0 + zc[-1]), "L", 0, "Top crown tab\nkeyed in a pocket under the flange"),
        ((xj, -9, z0 + (zc[8] + zc[9]) / 2), "R", 0, f"Bow-spring stack\n{s.n} bows, 0.5 mm PETG leaves"),
        ((s.crown_w / 2 + s.leaf_len / 2, -9, z0 + zc[5] - 1.0), "L", 0, "Leaves bend like the\nflexure's beams"),
        ((lf.HOUSING_D / 2, 0, -40), "R", 0, f"Spring housing\nØ{lf.HOUSING_D:g}, prints without support"),
        ((0, -6.6, z0 + zc[2]), "L", 0, "The pen runs through\nevery crown tab"),
        ((ph.PISTON_D / 2, 0, z0 - 25), "R", 0, f"Carriage\npiston {lf.PISTON_L:g} mm, slides as in v1"),
        ((0, -ph.BARREL_OD / 2, lf.Z_PIN), "R", 0, "M3 set-screw guide pins\nin slots, as v1"),
        ((ph.NOSE_D / 2, 0, lf.Z_NOSE_TOP), "R", 0, f"Nose shoulder = hard stop\nafter {lf.STROKE:g} mm"),
        ((0, 0, lf.Z_TIP + 15), "L", 0, f"Pen\nTCP Z +{lf.TCP_Z:.0f} mm"),
    ]
    annotate(img, sc, notes, left_x=0.25, right_x=0.74, halo=3)
    title(img, "Pen holder v2 - leaf-spring version", "v1 with the coil spring replaced by a printed bow-spring stack"
                                                       "  |  pen in free air")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_compliance(path: Path) -> None:
    travels = [0.0, lf.STROKE / 2, lf.STROKE]
    pw, ph_px, cap_h, head_h = 760, 1500, 120, 150
    panels = []
    for t in travels:
        sc = Scene(pw, ph_px)
        add_section(sc, [it for it in lf.assembly(travel=t) if "thumb" not in it.name])
        z_table = lf.Z_TIP + t
        sc.add_pv(pv.Cube(center=(0, 0, z_table - 7.2), x_length=120, y_length=120, z_length=14), "table")
        sc.add_pv(pv.Cube(center=(0, 0, z_table - 0.1), x_length=110, y_length=110, z_length=0.2), "paper")
        sc.pl.enable_parallel_projection()
        zc = -95.0
        sc.pl.camera_position = [(0, -1000, zc), (0, 0, zc), (0, 0, 1)]
        sc.pl.camera.parallel_scale = 118
        img = sc.render()
        d = ImageDraw.Draw(img)
        (_, y_free), (_, y_tab) = sc.project([(0, 0, lf.Z_TIP), (0, 0, z_table)])
        for x in range(20, pw - 20, 18):
            d.line([(x, y_free), (x + 9, y_free)], fill=(120, 126, 136), width=2)
        if t > 0:
            xd = 60
            d.line([(xd, y_free), (xd, y_tab)], fill=RED, width=3)
            for y, s in ((y_free, 1), (y_tab, -1)):
                d.polygon([(xd, y), (xd - 8, y - 14 * s), (xd + 8, y - 14 * s)], fill=RED)
            d.text((xd + 14, (y_free + y_tab) / 2 - 16), f"{t:g} mm", font=font(24, True), fill=RED)
        sc.close()
        sq = lf.PRELOAD + t
        cap = Image.new("RGB", (pw, cap_h), (251, 252, 253))
        dc = ImageDraw.Draw(cap)
        dc.text((30, 14), "Pen touches the paper" if t == 0 else ("Hard stop" if t == lf.STROKE else
                                                                    f"Over-reach {t:g} mm"), font=font(30, True), fill=INK)
        dc.text((32, 60), f"{lf.SPRING.rate * sq:.1f} N  |  leaves {lf.SPRING.stress(sq):.0f} MPa", font=font(24),
                fill=RED if t else (88, 94, 104))
        panel = Image.new("RGB", (pw, ph_px + cap_h))
        panel.paste(cap, (0, 0))
        panel.paste(img, (0, cap_h))
        panels.append(panel)
    out = Image.new("RGB", (pw * len(panels), ph_px + cap_h + head_h), (251, 252, 253))
    for i, p in enumerate(panels):
        out.paste(p, (i * pw, head_h))
    title(out, "Leaf-spring version - compliance", f"The bows flatten instead of the pen: {lf.SPRING.rate:.2f} N/mm, "
                                                    f"{lf.PRELOAD:g} mm preload, nose shoulder stops it at {lf.STROKE:g} mm")
    footer(out, FOOT)
    out.save(path)


def render_spring(path: Path) -> None:
    s = lf.SPRING
    sc = Scene(1900, 1300)
    shapes = [("As printed", 0.0, -40.0), (f"Squeezed {lf.PRELOAD + lf.STROKE:g} mm (hard stop)",
                                          lf.PRELOAD + lf.STROKE, 40.0)]
    for _, sq, x in shapes:
        sc.add(Pos(x, 0, 0) * s.shape(sq), "spring_petg")
    sc.camera((0, 0, s.free_len / 2), (0.1, -1.0, 0.06), zoom=1.15)
    img = sc.render()
    zc = s.crown_z(0.0)
    xl = s.crown_w / 2 + s.leaf_len / 2
    notes = [
        ((-40, -9, zc[-1]), "L", 0, f"Crown tab\na ring around the pen, Ø{s.crown_hole:.1f} hole"),
        ((-40 + s.x_joint, -9, (zc[6] + zc[7]) / 2), "L", 0, "Joint tab\nwhere the two leaves of a bow meet"),
        ((-40 - xl, -9, zc[3] + 0.6), "L", 0, f"Half-leaf {s.leaf_len:g} x {s.t:g} x {s.b:g} mm\nbends like a fixed-guided beam"),
        ((40 + s.x_joint, -9, s.length(lf.PRELOAD + lf.STROKE) / 2), "R", 0,
         f"{s.n} bows in series\neach flattens {(lf.PRELOAD + lf.STROKE) / s.n:.1f} mm"),
    ]
    annotate(img, sc, notes, left_x=0.22, right_x=0.78, halo=3)
    d = ImageDraw.Draw(img)
    for (label, sq, x) in shapes:
        (px, py), = sc.project([(x, -9, -6)])
        f = font(30, True)
        d.text((px - d.textlength(label, font=f) / 2, py), label, font=f, fill=INK)
    title(img, "Bow-spring stack", f"Printed lying flat in PETG: {s.free_len:.1f} mm long, {s.width:.0f} mm wide, "
                                   f"{s.depth:g} mm deep  |  {s.rate:.2f} N/mm")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_print_layout(path: Path) -> None:
    sc = Scene(1800, 1100)
    parts = lf.printed_parts()
    layout = {"Pen Holder v2 Leaf - Module": (-50, 0, "printed"), "Pen Holder v2 Leaf - Carriage": (15, 0, "accent"),
              "Pen Holder v2 Leaf - Bow Spring": (65, 0, "spring_petg")}
    for name, (x, y, mat) in layout.items():
        p = parts[name][1]
        c = p.bounding_box().center()
        sc.add(Pos(x - c.X, y - c.Y, 0) * p, mat)
    sc.add_pv(pv.Cube(center=(5, 0, -0.8), x_length=190, y_length=120, z_length=1.6), "bed")
    sc.camera((5, 0, 30), (0.3, -1.0, 0.7), zoom=1.1)
    img = sc.render()
    title(img, "Leaf-spring version - print layout", "PETG, no supports  |  module flange down, carriage nose down, "
                                                     "spring lying flat (adapter: the v1 part)")
    footer(img, FOOT)
    img.save(path)
    sc.close()


VIEWS = {1: render_cutaway, 2: render_compliance, 3: render_spring, 4: render_print_layout}


def export_hero_glb(path: Path, travel: float = 3.0, housing: float = 170.0) -> None:
    from build123d import export_gltf

    its = [it for it in lf.assembly(travel=travel) if "housing" not in it.name]
    its.append(lf.Item("UTRA 6-1000 J6 housing (ref)", ph.make_arm_housing(housing), "arm_dark"))
    asm = lf.labelled_compound([lf.Item(it.name, Pos(0, 0, -travel) * it.shape, it.material) for it in its],
                               "pen holder v2 leaf")
    export_gltf(asm, str(path), binary=True, linear_deflection=0.05, angular_deflection=0.2)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Render the leaf-spring pen holder")
    ap.add_argument("views", nargs="*", type=int, default=sorted(VIEWS), help="view numbers to render")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--hero-glb", type=Path, help="only export the GLB used by blender_hero.py")
    args = ap.parse_args()
    if args.hero_glb:
        export_hero_glb(args.hero_glb)
        return
    args.out.mkdir(parents=True, exist_ok=True)
    for n in args.views:
        p = args.out / f"{PREFIX} {n}.png"
        VIEWS[n](p)
        print("wrote", p)


if __name__ == "__main__":
    _ = Rot
    main()
