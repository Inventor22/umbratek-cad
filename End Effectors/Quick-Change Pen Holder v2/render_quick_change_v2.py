# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["build123d>=0.9,<0.14", "pyvista>=0.43", "numpy", "pillow"]
# ///
"""
Render the quick-change pen holder v2 (quick_change_v2.py) to PNG images.

    uv run render_quick_change_v2.py                     # -> <repo>/Renders/Quick-Change Pen Holder v2 Render N.png
    uv run render_quick_change_v2.py --hero-glb hero.glb  # scene for ../Quick-Change Pen Holder/blender_hero_quick_change.py
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
import quick_change_v2 as v2  # noqa: E402
import render_quick_change as rqc  # noqa: E402  (v1 views: materials, helpers)
from render_pen_holder import INK, Scene, annotate, font, footer, title  # noqa: E402

qc = v2.qc
OUT_DIR = HERE.parents[1] / "Renders"
PREFIX = "Quick-Change Pen Holder v2 Render"
FOOT = "umbratek-cad / End Effectors / Quick-Change Pen Holder v2  -  build123d"
RED = (200, 60, 20)


def items(travel: float = 0.0, pen: str | None = "Gel pen 11 mm", **kw) -> list:
    return [it for it in v2.assembly(travel=travel, pen=pen, split_stage=True, **kw) if "housing" not in it.name]


def add(sc: Scene, its) -> None:
    for it in its:
        sc.add(it.shape, it.material)


def stage_only(travel: float = 0.0) -> list:
    return [it for it in items(travel, pen=None)
            if not any(k in it.name for k in ("Cartridge", "Twist ring", "Jaw"))]


# -----------------------------------------------------------------------------
# Views
# -----------------------------------------------------------------------------
def render_overview(path: Path) -> None:
    sc = Scene(2200, 1700)
    add(sc, items())
    sc.camera((0, -30, -30), (0.55, -1.0, 0.32), zoom=1.0)
    img = sc.render()
    f, p, dz = v2.FLEX, v2.PRELOAD, v2.DZ
    xb, yf = 22.0, f.y0  # a point along the beams; their front face
    notes = [
        ((30, 13, 30), "R", 0, "UTRA 6-1000 tool flange\nreference"),
        ((38, -6, 14), "R", 0, "Tool adapter (v1, unchanged)"),
        ((v2.PAD1_X, v2.FRAME_FRONT_Y, v2.PAD1_Z), "R", 0, "M3 x 20 into the adapter's nuts\n(2 of its 3) + washers"),
        ((xb, yf, v2.Z_P1T + f.rise_p1(xb, p)), "R", 0, "Ground beams\n2 pairs"),
        ((xb, yf, v2.Z_P2T + f.rise_p2(xb, p)), "R", 0, f"Carriage beams\n2 pairs, {f.beam_len:g} x {f.t:g} x {f.b:g} mm"),
        ((f.x_bar + 3, yf, (v2.Z_P2B + v2.Z_P1T) / 2 + p / 2), "R", 0, "Intermediate bar\nmoves half as far"),
        ((v2.X_OUT_R, v2.Y_MID, v2.Z_BB0 + 8), "R", 0, "Frame\none print with the beams"),
        ((0, -40, qc.Z_U1 + dz - 4), "L", 0, "v1 cartridge\nunchanged, swaps without tools"),
        ((0, qc.PEN_Y, v2.Z_TIP + 18), "L", 0, f"Pen tip\nTCP X {v2.TCP_F[0]:.0f}, Z +{-qc.PEN_Y:.0f}"),
    ]
    annotate(img, sc, notes, left_x=0.25, right_x=0.76, halo=3)
    title(img, "Quick-change pen holder v2 - printed flexure stage",
          f"One PETG part replaces the rods and coil springs  |  {v2.X_OUT_R - v2.X_OUT_L:.0f} mm wide  |  "
          f"{v2.STROKE:g} mm along the pen")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_stage(path: Path) -> None:
    sc = Scene(2100, 1600)
    add(sc, stage_only())
    sc.camera((0, -18, -22), (0.25, -1.0, 0.2), zoom=1.0)
    img = sc.render()
    f, p = v2.FLEX, v2.PRELOAD
    xb, yf = 22.0, f.y0
    notes = [
        ((v2.PAD1_X, v2.FRAME_FRONT_Y, v2.PAD1_Z), "R", 0, "Mount pad on a ground arm\nM3 x 20 + washer"),
        ((v2.PAD3_X, v2.FRAME_FRONT_Y, v2.PAD3_Z), "L", 0, "Mount pad in the ground anchor\nM3 x 20 + washer"),
        ((v2.X_ROOT - 3, v2.FRAME_FRONT_Y, v2.Z_AB), "L", 0, f"Hard stop\n{v2.STROKE:g} mm above the carriage member"),
        ((xb, yf, v2.Z_P1T + f.rise_p1(xb, p)), "R", 0, "Ground beams"),
        ((xb, yf, v2.Z_P2T + f.rise_p2(xb, p)), "R", 0, f"Carriage beams\nbent {p:g} mm at rest (preload)"),
        ((f.x_bar + 3, yf, (v2.Z_P2B + v2.Z_P1T) / 2 + p / 2), "R", 0, "Intermediate bar"),
        ((0, qc.RAIL_FRONT_Y, v2.Z_RAIL1 - 8), "L", 0, "Dovetail rail\nsame as v1"),
        ((0, qc.PLUNGER_FACE_Y, v2.Z_RAIL0 + qc.PLUNGER_Z), "L", 0, "M6 ball plunger\nholds the cartridge"),
        ((v2.X_STOP, v2.Y_MID, v2.Z_BB0), "L", 0, "M3 x 12 stop screw\nthe carriage rests on its tip"),
    ]
    annotate(img, sc, notes, left_x=0.25, right_x=0.75, halo=3)
    title(img, "Quick-change pen holder v2 - flexure stage", "Cartridge removed  |  first touch (stage on its stop "
                                                               "screws)")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_compliance(path: Path) -> None:
    travels = [0.0, v2.STROKE / 2, v2.STROKE]
    pw, ph_px, cap_h, head_h = 900, 1250, 130, 150
    panels = []
    for t in travels:
        sc = Scene(pw, ph_px)
        add(sc, items(t))
        z_table = v2.Z_TIP + t
        sc.add_pv(pv.Cube(center=(0, -60, z_table - 7.2), x_length=170, y_length=150, z_length=14), "table")
        sc.add_pv(pv.Cube(center=(0, -60, z_table - 0.1), x_length=150, y_length=120, z_length=0.2), "paper")
        sc.pl.enable_parallel_projection()
        zc, yc = -40.0, -30.0
        sc.pl.camera_position = [(0, -1000, zc), (0, yc, zc), (0, 0, 1)]
        sc.pl.camera.parallel_scale = 100
        img = sc.render()
        d = ImageDraw.Draw(img)
        (_, y_free), (_, y_tab) = sc.project([(0, qc.PEN_Y, v2.Z_TIP), (0, qc.PEN_Y, z_table)])
        for x in range(30, pw - 30, 18):
            d.line([(x, y_free), (x + 9, y_free)], fill=(120, 126, 136), width=2)
        if t > 0:
            xd = 70
            d.line([(xd, y_free), (xd, y_tab)], fill=RED, width=3)
            for y, s in ((y_free, 1), (y_tab, -1)):
                d.polygon([(xd, y), (xd - 8, y - 14 * s), (xd + 8, y - 14 * s)], fill=RED)
            d.text((xd + 14, (y_free + y_tab) / 2 - 16), f"{t:g} mm", font=font(24, True), fill=RED)
        sc.close()
        lift = v2.PRELOAD + t
        cap = Image.new("RGB", (pw, cap_h), (251, 252, 253))
        dc = ImageDraw.Draw(cap)
        dc.text((36, 14), "Pen touches the paper" if t == 0 else
                ("Hard stop" if t == v2.STROKE else f"Arm over-reaches {t:g} mm"), font=font(32, True), fill=INK)
        dc.text((38, 62), f"pen force {v2.FLEX.rate * lift:.1f} N   |   beam stress {v2.FLEX.stress(lift):.0f} MPa",
                font=font(25), fill=RED if t else (88, 94, 104))
        panel = Image.new("RGB", (pw, ph_px + cap_h))
        panel.paste(cap, (0, 0))
        panel.paste(img, (0, cap_h))
        panels.append(panel)
    out = Image.new("RGB", (pw * len(panels), ph_px + cap_h + head_h), (251, 252, 253))
    for i, p in enumerate(panels):
        out.paste(p, (i * pw, head_h))
    title(out, "Quick-change v2 - compliance", f"The beams bend instead of the pen: {v2.FLEX.rate:.2f} N/mm, "
                                               f"{v2.PRELOAD:g} mm preload, hard stop at {v2.STROKE:g} mm  "
                                               f"(+ the cartridge's weight when the pen points down)")
    footer(out, FOOT)
    out.save(path)


def render_exploded(path: Path) -> None:
    sc = Scene(1700, 2000)
    its = [it for it in v2.assembly(travel=0.0, explode=True) if "housing" not in it.name]
    for it in its:
        sc.add(Pos(*it.explode) * it.shape, it.material)
    sc.camera((0, -60, -55), (1.0, -1.1, 0.5), zoom=1.1)
    img = sc.render()
    off = {it.name: it.explode for it in its}

    def at(name, x, y, z):
        o = off[name]
        return x + o[0], y + o[1], z + o[2]

    dz, y_pen = v2.DZ, qc.PEN_Y
    notes = [
        (at("UTRA 6-1000 tool flange (ref)", 30, 13, 30), "R", 0, "UTRA 6-1000 tool flange\nreference"),
        (at("Tool adapter (v1)", 30, -6, -20), "R", 0, "Tool adapter (v1)\n6x M5 x 12, dowel"),
        (at("Flexure stage", v2.X_OUT_R, v2.Y_MID, -40), "R", 0, "Flexure stage\none print, no springs"),
        (at("M3 washer (F 270 deg)", -21.5, v2.BACK_Y, 0), "L", 0, "2x M3 washer"),
        (at("M3x20 SHCS (mount, F 270 deg)", -21.5, -26, 0), "L", 0, "2x M3 x 20"),
        (at("M3x12 SHCS (preload stop)", v2.X_STOP, v2.Y_MID, v2.Z_STOP_SEAT), "L", 0, "M3 x 12 stop screw"),
        (at("M6 ball spring plunger", 3, -20, v2.Z_RAIL0 + qc.PLUNGER_Z), "R", 0, "M6 ball spring plunger"),
        (at("Cartridge body", 12.5, -30, -25 + dz), "R", 0, "v1 cartridge\nrings, jaws unchanged"),
        (at("Gel pen 11 mm barrel", -5.5, y_pen, -64 + dz), "L", 0, "Pen\n6-17 mm"),
    ]
    annotate(img, sc, notes, left_x=0.25, right_x=0.75, halo=3)
    title(img, "Quick-change v2 - exploded", "The stage replaces v1's base, rods, carriage and coil springs")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_print_layout(path: Path) -> None:
    sc = Scene(1900, 1250)
    stage = v2.PRINT_POSE * v2.make_stage()
    sc.add(stage, "accent")
    bb = stage.bounding_box()
    sc.add_pv(pv.Box((bb.min.X - 25, bb.max.X + 25, bb.min.Y - 25, bb.max.Y + 25, -2, 0)), "bed")
    sc.camera((0, (bb.min.Y + bb.max.Y) / 2, 4), (0.35, -0.8, 0.85), zoom=1.12)
    img = sc.render()
    f = v2.FLEX
    notes = [
        ((22, v2.Z_P1B, f.b), "R", 0, "Beams print as 0.8 mm walls\nbending runs along the lines"),
        ((0, (v2.Z_RAIL0 + v2.Z_RAIL1) / 2 - v2.PRELOAD, v2.BACK_Y - qc.RAIL_FRONT_Y), "L", 0,
         "Dovetail rail on top\nflanks lean 32°"),
        ((v2.X_OUT_R, -40, (v2.BACK_Y - v2.FRAME_FRONT_Y)), "R", 0, "Back face on the bed"),
    ]
    annotate(img, sc, notes, left_x=0.25, right_x=0.75, halo=3)
    title(img, "Quick-change v2 - print layout",
          f"PETG, back face down, no supports  |  {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm  |  "
          "cartridge parts: v1 STLs")
    footer(img, FOOT)
    img.save(path)
    sc.close()


VIEWS = {1: render_overview, 2: render_stage, 3: render_compliance, 4: render_exploded, 5: render_print_layout}


def export_hero_glb(path: Path, travel: float = 3.0) -> None:
    """Scene for blender_hero_quick_change.py: pen pressed into the paper, spare cartridges in their gauges."""
    its = v2.assembly(travel=travel)
    # blender_hero_quick_change.py picks materials by name: "carriage" -> orange PETG, "base" -> charcoal PETG
    names = {"Flexure stage": "Flexure stage (carriage, frame and beams)", "Tool adapter (v1)": "Tool adapter base"}
    for it in its:
        it.name = names.get(it.name, it.name)
        if "housing" in it.name:
            it.shape = v2.F2M * v2.ph.make_arm_housing(170.0)
    z_desk = v2.Z_TIP + travel
    gauge = qc.make_gauge()
    for label, pen, (x, y, spin) in (("Spare A ", "Ballpoint 8 mm", (-128, 18, 200)),
                                     ("Spare B ", "Whiteboard marker 16 mm", (-180, 66, 225))):
        place = Pos(x, y, z_desk + qc.GAUGE_FLOOR - qc.Z_TIP) * Rot(0, 0, spin) * Pos(0, -qc.PEN_Y, 0)
        its += qc.cartridge_items(pen, place=place, label=label)
        its.append(qc.Item(f"{label}Stick-out gauge", Pos(x, y, z_desk) * gauge, "printed"))
    asm = v2.labelled_compound(its, "UTRA 6-1000 quick-change pen holder v2 (hero)")
    v2.export_gltf(asm, path, binary=True, linear_deflection=0.01, angular_deflection=0.1)
    print(f"wrote {path} (pen tip / desk at z = {z_desk:.2f} mm, frame M)")


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Render the quick-change pen holder v2")
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
    _ = rqc  # materials registered on import
    main()
