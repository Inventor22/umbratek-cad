# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["build123d>=0.9,<0.14", "pyvista>=0.43", "numpy", "pillow"]
# ///
"""
Render the quick-change pen holder v2, leaf-spring version (quick_change_v2_leaf.py), to PNG images.

    uv run render_quick_change_v2_leaf.py      # -> <repo>/Renders/Quick-Change Pen Holder v2 Leaf Spring Render N.png
    uv run render_quick_change_v2_leaf.py --hero-glb hero.glb  # for ../Quick-Change Pen Holder/blender_hero_quick_change.py
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
sys.path.insert(0, str(HERE.parent / "Quick-Change Pen Holder"))
import quick_change_v2_leaf as lf  # noqa: E402
import render_quick_change as rqc  # noqa: E402  (v1 materials)
from render_pen_holder import INK, Scene, annotate, font, footer, title  # noqa: E402

qc, ph = lf.qc, lf.ph
OUT_DIR = HERE.parents[1] / "Renders"
PREFIX = "Quick-Change Pen Holder v2 Leaf Spring Render"
FOOT = "umbratek-cad / End Effectors / Quick-Change Pen Holder v2 Leaf Spring  -  build123d"
rqc.rph.MATERIALS["spring_petg"] = ("#f26b1d", 0.0, 0.42, "#ff9d5c")
RED = (200, 60, 20)


def add(sc: Scene, its) -> None:
    for it in its:
        if "housing" not in it.name:
            sc.add(it.shape, it.material)


def render_overview(path: Path) -> None:
    sc = Scene(2100, 1700)
    add(sc, lf.assembly())
    sc.camera((0, -30, -25), (0.55, -1.0, 0.3), zoom=1.0)
    img = sc.render()
    s, p = lf.SPRING, lf.PRELOAD
    z0 = lf.Z_C1 - lf.CROWN_POCKET
    zc = s.crown_z(p)
    yf = lf.ROD_Y - s.depth / 2
    notes = [
        ((30, 13, 30), "R", 0, "UTRA 6-1000 tool flange\nreference"),
        ((lf.STAGE_HW, -18, lf.Z_CAP0 + 6), "R", 0, "Top cap\nclamped to the rods"),
        ((lf.ROD_X + 4, yf, z0 + (zc[5] + zc[6]) / 2), "R", 0, f"Bow-spring stack\n{s.n} bows threaded on the rods"),
        ((lf.ROD_X, lf.ROD_Y, lf.Z_CAP1 + 2), "R", 0, f"2x Ø6 x {lf.ROD_LEN:g} rod"),
        ((lf.STAGE_HW, -20, lf.Z_C0 + 20), "R", 0, "Carriage\nslides on the rods"),
        ((-lf.STAGE_HW, -18, lf.Z_BB0 + 8), "L", 0, "Base\nbottom block = rest stop"),
        ((0, -40, qc.Z_U1 - 4), "L", 0, "v1 cartridge\nunchanged"),
        ((0, qc.PEN_Y, qc.Z_TIP + 18), "L", 0, f"Pen tip\nTCP X {qc.TCP_F[0]:.0f}, Z +{-qc.PEN_Y:.0f} (as v1)"),
    ]
    annotate(img, sc, notes, left_x=0.25, right_x=0.76, halo=3)
    title(img, "Quick-change pen holder v2 - leaf-spring version",
          "v1 with the coil springs replaced by a printed bow-spring stack  |  15 mm of travel, then the stack closes up")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_compliance(path: Path) -> None:
    travels = [0.0, lf.STROKE / 2, lf.STROKE]
    pw, ph_px, cap_h, head_h = 860, 1250, 120, 150
    panels = []
    for t in travels:
        sc = Scene(pw, ph_px)
        add(sc, lf.assembly(travel=t))
        z_table = qc.Z_TIP + t
        sc.add_pv(pv.Cube(center=(0, -60, z_table - 7.2), x_length=170, y_length=150, z_length=14), "table")
        sc.add_pv(pv.Cube(center=(0, -60, z_table - 0.1), x_length=150, y_length=120, z_length=0.2), "paper")
        sc.pl.enable_parallel_projection()
        zc = -30.0
        sc.pl.camera_position = [(0, -1000, zc), (0, -30, zc), (0, 0, 1)]
        sc.pl.camera.parallel_scale = 92
        img = sc.render()
        d = ImageDraw.Draw(img)
        (_, y_free), (_, y_tab) = sc.project([(0, qc.PEN_Y, qc.Z_TIP), (0, qc.PEN_Y, z_table)])
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
        dc.text((30, 14), "Pen touches the paper" if t == 0 else ("Stack closed up = hard stop" if t == lf.STROKE
                                                                    else f"Over-reach {t:g} mm"), font=font(30, True),
                fill=INK)
        dc.text((32, 60), f"{lf.SPRING.rate * sq:.1f} N  |  leaves {lf.SPRING.stress(sq):.0f} MPa", font=font(24),
                fill=RED if t else (88, 94, 104))
        panel = Image.new("RGB", (pw, ph_px + cap_h))
        panel.paste(cap, (0, 0))
        panel.paste(img, (0, cap_h))
        panels.append(panel)
    out = Image.new("RGB", (pw * len(panels), ph_px + cap_h + head_h), (251, 252, 253))
    for i, p in enumerate(panels):
        out.paste(p, (i * pw, head_h))
    title(out, "Quick-change leaf-spring version - compliance",
          f"The bows flatten instead of the pen: {lf.SPRING.rate:.2f} N/mm, {lf.PRELOAD:g} mm preload "
          "(+ the cartridge's weight when the pen points down)")
    footer(out, FOOT)
    out.save(path)


def render_spring(path: Path) -> None:
    s = lf.SPRING
    sc = Scene(1900, 1150)
    shapes = [("As printed", 0.0, -32.0), ("Closed up = hard stop", lf.PRELOAD + lf.STROKE, 32.0)]
    for _, sq, x in shapes:
        sc.add(Pos(x, 0, 0) * s.shape(sq), "spring_petg")
    sc.camera((0, 0, s.free_len / 2), (0.1, -1.0, 0.06), zoom=1.2)
    img = sc.render()
    zc = s.crown_z(0.0)
    notes = [
        ((-32, -6.5, zc[-1]), "L", 0, "Crown tab\npushes on the cap"),
        ((-32 - s.x_joint, -6.5, (zc[4] + zc[5]) / 2), "L", 0, f"Joint tab\nØ{s.joint_hole:g} hole for a Ø6 rod"),
        ((-32 + s.crown_w / 2 + s.leaf_len / 2, -6.5, zc[2] + 0.6), "R", 0,
         f"Half-leaf {s.leaf_len:g} x {s.t:g} x {s.b:g} mm\nbends like a fixed-guided beam"),
        ((32 + s.x_joint, -6.5, s.length(lf.PRELOAD + lf.STROKE) / 2), "R", 0,
         f"{s.n} bows in series\nthe tabs touch at {lf.PRELOAD + lf.STROKE:g} mm"),
    ]
    annotate(img, sc, notes, left_x=0.2, right_x=0.8, halo=3)
    d = ImageDraw.Draw(img)
    for label, _, x in shapes:
        (px, py), = sc.project([(x, -6.5, -5)])
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
    layout = {"Quick-Change v2 Leaf - Base": (-55, 10, "printed"), "Quick-Change v2 Leaf - Carriage": (25, 35, "accent"),
              "Quick-Change v2 Leaf - Top Cap": (25, -5, "printed"),
              "Quick-Change v2 Leaf - Bow Spring": (80, 10, "spring_petg")}
    for name, (x, y, mat) in layout.items():
        p = parts[name][1]
        c = p.bounding_box().center()
        sc.add(Pos(x - c.X, y - c.Y, 0) * p, mat)
    sc.add_pv(pv.Cube(center=(12, 10, -0.8), x_length=230, y_length=110, z_length=1.6), "bed")
    sc.camera((12, 10, 30), (0.3, -1.0, 0.7), zoom=1.1)
    img = sc.render()
    title(img, "Quick-change leaf-spring version - print layout",
          "PETG, no supports  |  cartridge parts: the v1 STLs")
    footer(img, FOOT)
    img.save(path)
    sc.close()


VIEWS = {1: render_overview, 2: render_compliance, 3: render_spring, 4: render_print_layout}


def export_hero_glb(path: Path, travel: float = 3.0) -> None:
    """Scene for blender_hero_quick_change.py: pen pressed into the paper, spare cartridges in their gauges."""
    its = lf.assembly(travel=travel)
    for it in its:
        if "housing" in it.name:
            it.shape = lf.F2M * ph.make_arm_housing(170.0)
    z_desk = qc.Z_TIP + travel
    gauge = qc.make_gauge()
    for label, pen, (x, y, spin) in (("Spare A ", "Ballpoint 8 mm", (-118, 18, 200)),
                                     ("Spare B ", "Whiteboard marker 16 mm", (-170, 66, 225))):
        place = Pos(x, y, z_desk + qc.GAUGE_FLOOR - qc.Z_TIP) * Rot(0, 0, spin) * Pos(0, -qc.PEN_Y, 0)
        its += qc.cartridge_items(pen, place=place, label=label)
        its.append(qc.Item(f"{label}Stick-out gauge", Pos(x, y, z_desk) * gauge, "printed"))
    asm = lf.labelled_compound(its, "UTRA 6-1000 quick-change pen holder v2, leaf spring (hero)")
    lf.export_gltf(asm, path, binary=True, linear_deflection=0.01, angular_deflection=0.1)
    print(f"wrote {path}")


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Render the leaf-spring quick-change pen holder")
    ap.add_argument("views", nargs="*", type=int, default=sorted(VIEWS), help="view numbers to render")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--hero-glb", type=Path, help="only export the GLB used by blender_hero_quick_change.py")
    args = ap.parse_args()
    if args.hero_glb:
        export_hero_glb(args.hero_glb)
        return
    args.out.mkdir(parents=True, exist_ok=True)
    for n in args.views:
        p = args.out / f"{PREFIX} {n}.png"
        VIEWS[n](p)
        print(f"wrote {p}")


if __name__ == "__main__":
    main()
