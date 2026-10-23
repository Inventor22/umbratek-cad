# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["build123d>=0.9,<0.14", "pyvista>=0.43", "numpy", "pillow"]
# ///
"""
Render pen holder v2 (pen_holder_v2.py) to PNG images.

    uv run render_pen_holder_v2.py              # -> <repo>/Renders/Pen Holder v2 Render N.png
    uv run render_pen_holder_v2.py 3            # just view 3
    uv run render_pen_holder_v2.py --hero-glb hero.glb   # scene for ../Pen Holder/blender_hero.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pyvista as pv
from build123d import Box, Pos
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "Pen Holder"))
import pen_holder_v2 as v2  # noqa: E402
import render_pen_holder as rph  # noqa: E402
from render_pen_holder import INK, Scene, annotate, font, footer, title  # noqa: E402

OUT_DIR = HERE.parents[1] / "Renders"
PREFIX = "Pen Holder v2 Render"
FOOT = "umbratek-cad / End Effectors / Pen Holder v2  -  build123d"
FRONT = (0.42, 1.0, 0.22)  # 3/4 view from the front (+Y)


def cut_front(shape):
    """Stepped section: through the pen axis (y = 0) right of the beam roots, through the plate's mid-plane (stop screw,
    carriage member, ground anchor) left of them."""
    big = 2000.0
    cutter = Pos(v2.X_ROOT + big / 2, big / 2, 0) * Box(big, big, big)
    cutter += Pos(v2.X_ROOT - big / 2, v2.Y_MID + big / 2, 0) * Box(big, big, big)
    try:
        out = shape - cutter
    except Exception:
        return shape
    return out if out.volume > 1e-6 else None


def items(travel: float = 0.0, **kw) -> list:
    return [it for it in v2.assembly(travel=travel, split_module=True, **kw) if "housing" not in it.name]


def add_items(sc: Scene, its, section: bool = False) -> None:
    for it in its:
        s = it.shape
        if section and "flange (ref)" not in it.name:
            s = cut_front(s)
        if s is not None:
            sc.add(s, it.material, caps=[(1, 0.0), (1, v2.Y_MID)] if section else None)


def arrow(d: ImageDraw.ImageDraw, p0, p1, colour=(200, 60, 20), width=4, head=16) -> None:
    import math

    d.line([p0, p1], fill=colour, width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s in (-1, 1):
        a = ang + math.pi + s * math.radians(28)
        d.line([p1, (p1[0] + head * math.cos(a), p1[1] + head * math.sin(a))], fill=colour, width=width)


# -----------------------------------------------------------------------------
# Views
# -----------------------------------------------------------------------------
def render_overview(path: Path) -> None:
    sc = Scene(2200, 1800)
    add_items(sc, items())
    sc.camera((0, 0, -60), FRONT, zoom=0.95)
    img = sc.render()
    f, p = v2.FLEX, v2.PRELOAD
    xb, yf = 18.0, v2.PLATE_Y[1]  # a point along the beams, right of the pen block; front face of the plate
    notes = [  # the camera looks from +Y, so +X is on the left of the image
        ((-30, 25, 10), "R", 0, "UTRA 6-1000 tool flange\nreference"),
        ((-40, 20, -6), "R", 0, "Tool adapter (v1, unchanged)\n6x M5, Ø73 pilot, dowel"),
        ((22, 14.5, -15), "L", 0, "Mount block\n2x M3 from the arm side"),
        ((xb, yf, v2.Z_P2T + f.rise_p2(xb, p)), "L", 0, f"Carriage beams\n{f.beam_len:g} x {f.t:g} x {f.b:g} mm PETG"),
        ((xb, yf, v2.Z_P1T + f.rise_p1(xb, p)), "L", 0, "Ground beams\nanchored to the frame"),
        ((f.x_bar + 3, yf, (v2.Z_P2B + v2.Z_P1T) / 2 + p / 2), "L", 0, "Intermediate bar\nmoves half as far"),
        ((v2.X_OUT, yf, v2.Z_BB0 + 10), "L", 0, "Frame\none print with the beams"),
        ((v2.X_ROOT - 3, yf, v2.Z_M1 + p), "R", 0, f"Carriage member\nhits the frame after {v2.STROKE:g} mm"),
        ((-v2.BLOCK_HW, v2.BLOCK_FRONT_Y, v2.Z_CLAMP + p + 8), "R", 0, "Pen block\nin front of the beams"),
        ((0, 22, v2.Z_CLAMP + p), "R", 0, "M3 thumb screw\npen clamp"),
        ((v2.X_STOP, v2.Y_MID, v2.Z_BB0), "R", 0, f"M3 x 40 stop screw\nscrewed home = {p:g} mm preload"),
        ((0, 0, v2.Z_TIP + 20), "L", 0, f"Pen\nTCP Z +{v2.TCP_Z:.0f} mm"),
    ]
    annotate(img, sc, notes, left_x=0.25, right_x=0.76, halo=3)
    title(img, "Pen holder v2 - printed flexure spring",
          f"One PETG part replaces the coil spring and sliding fit  |  {2 * v2.X_OUT:.0f} mm wide  |  "
          f"{v2.STROKE:g} mm over-travel")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_section(path: Path) -> None:
    sc = Scene(2000, 1800)
    add_items(sc, items(), section=True)
    sc.camera((0, 0, -64), (0.30, 1.0, 0.16), zoom=0.9)
    img = sc.render()
    p = v2.PRELOAD
    f = v2.FLEX
    xm, yf = v2.X_ROOT - v2.MEMBER_W / 2, v2.PLATE_Y[1]
    notes = [  # +X is on the left of the image
        ((xm, v2.Y_MID, v2.Z_HS), "R", 0, f"Hard stop\nthe carriage member lands here after {v2.STROKE:g} mm"),
        ((xm, v2.Y_MID, v2.Z_M1 + p - 12), "R", 0, "Carriage member\nthe carriage beams root here"),
        ((v2.X_STOP, v2.Y_MID, v2.Z_REST0 - 0.5), "R", 0, "Stop screw tip\nthe carriage rests here"),
        ((xm, v2.Y_MID, v2.Z_A1 - 12), "R", 0, "Ground anchor\nthe ground beams root here"),
        ((v2.X_STOP, v2.Y_MID, v2.Z_STOP_SEAT - 1), "R", 0, f"Head seated = carriage lifted {p:g} mm\n"
                                                            f"= {f.rate * p:.1f} N preload"),
        ((14, yf, v2.Z_P2T + f.rise_p2(14, p)), "L", 0, f"Carriage beams\nbent {p:g} mm at rest (preload)"),
        ((14, yf, v2.Z_P1T + f.rise_p1(14, p)), "L", 0, "Ground beams"),
        ((0, 0, v2.Z_CLAMP + p + 10), "L", 0, f"Pen\nSharpie Fine Point, Ø{v2.PEN_D:g} mm"),
        ((0, 0, v2.Z_BB0 - 10), "L", 0, "Pen runs in front\nof the plate"),
    ]
    annotate(img, sc, notes, left_x=0.27, right_x=0.73, halo=3)
    title(img, "Pen holder v2 - section", "Stepped cut: through the pen axis, and through the plate at the stop screw"
                                          "  |  pen at first touch")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_compliance(path: Path) -> None:
    states = [(0.0, "First touch"), (v2.STROKE / 2, f"{v2.STROKE / 2:g} mm over-reach"),
              (v2.STROKE, f"{v2.STROKE:g} mm: hard stop")]
    w, h = 1000, 1250
    canvas = Image.new("RGB", (3 * w, h + 470), (251, 252, 253))
    d = ImageDraw.Draw(canvas)
    for i, (travel, label) in enumerate(states):
        sc = Scene(w, h)
        add_items(sc, [it for it in items(travel, hardware=True) if "thumb" not in it.name])
        # paper: in the tool's frame it rises as the arm keeps descending, so the camera rises with it
        z_paper = v2.Z_TIP + travel
        sc.pl.add_mesh(pv.Box((-70, 70, -50, 50, z_paper - 2, z_paper)), color="#fbfbf8", pbr=True, roughness=0.9)
        sc.camera((0, 0, -68 + travel), (0.0, 1.0, 0.0), zoom=1.0, view_angle=14)
        sc.pl.camera.parallel_projection = True
        sc.pl.camera.parallel_scale = 112
        img = sc.render()
        canvas.paste(img, (i * w, 170))
        lift = v2.PRELOAD + travel
        f = v2.FLEX.rate * lift
        s = v2.FLEX.stress(lift)
        cx = i * w + w / 2
        for j, (txt, fn) in enumerate([(label, font(40, True)), (f"{f:.1f} N on the paper", font(32)),
                                       (f"beam stress {s:.0f} MPa", font(28))]):
            tw = d.textlength(txt, font=fn)
            d.text((cx - tw / 2, h + 200 + j * 48), txt, font=fn, fill=INK if j == 0 else (84, 90, 100))
        sc.close()
    title(canvas, "Pen holder v2 - compliance",
          f"The arm keeps descending after first touch; the beams bend and the pen force rises "
          f"{v2.FLEX.rate:.2f} N/mm")
    footer(canvas, FOOT)
    canvas.save(path)


def render_exploded(path: Path) -> None:
    ph_m5 = v2.ph.Z_M5_SEAT
    sc = Scene(1700, 2100)
    for it in v2.assembly(travel=0.0):
        if "housing" in it.name:
            continue
        sc.add(Pos(*it.explode) * it.shape, it.material)
    sc.camera((0, 0, -112), FRONT, zoom=1.0)
    img = sc.render()
    ex = (0, 0, -45)
    p = v2.PRELOAD
    notes = [  # the camera looks from +Y, so +X is on the left of the image
        ((-40, 0, 85), "R", 0, "UTRA 6-1000 tool flange\nreference"),
        ((26, 0, 32), "L", 0, "Dowel pin 3 x 8"),
        ((32, 0, -5), "L", 0, "Tool adapter (v1)"),
        ((-32, 0, ph_m5 - 28), "R", 0, "4x M5 x 12"),
        ((-18.6, 10.75, -4.4 + 40), "R", 0, "2x M3 x 14\nfrom the arm side"),
        ((v2.X_OUT, v2.PLATE_Y[1], -70 + ex[2]), "L", 0, "Flexure module\none print"),
        ((0, 40, v2.Z_CLAMP + p + ex[2]), "R", 0, "M3 x 10 thumb screw"),
        ((0, 10, v2.Z_CLAMP + p + ex[2] - 60), "R", 0, "M3 nut"),
        ((v2.X_STOP, v2.Y_MID, v2.Z_STOP_SEAT - 95), "R", 0, "M3 x 40 stop screw"),
        ((-95, 0, v2.Z_TIP - 110 + 60), "R", 0, "Pen\nSharpie Fine Point"),
    ]
    annotate(img, sc, notes, left_x=0.25, right_x=0.75, halo=3)
    title(img, "Pen holder v2 - exploded", "2 printed parts (adapter reused from v1), no springs")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_print_layout(path: Path) -> None:
    sc = Scene(2000, 1400)
    module = v2.PRINT_POSE * v2.make_module()
    sc.add(module, "accent")
    bb = module.bounding_box()
    sc.pl.add_mesh(pv.Box((bb.min.X - 25, bb.max.X + 25, bb.min.Y - 25, bb.max.Y + 25, -2, 0)), color="#c4a062",
                   pbr=True, metallic=0.35, roughness=0.5)
    sc.camera((0, (bb.min.Y + bb.max.Y) / 2, 10), (0.35, -0.75, 0.75), zoom=1.0)
    img = sc.render()
    lift0 = -v2.PLATE_Y[0]  # print pose: (x, y, z) -> (x, -z, y + lift0)
    notes = [
        ((18, -v2.Z_P2T, v2.PLATE_Y[1] + lift0), "R", 0, "Beams print as 0.8 mm walls\nbending runs along the lines"),
        ((0, -(v2.Z_C0 + 12), v2.BLOCK_FRONT_Y + lift0), "L", 0, "Pen block\npen bore with a teardrop roof"),
        ((0, -(v2.Z_HS + 3), v2.MOUNT_BLOCK[1] + lift0), "L", 0, "Mount block"),
    ]
    annotate(img, sc, notes, left_x=0.25, right_x=0.75, halo=3)
    title(img, "Pen holder v2 - print layout",
          f"PETG, lying on its back, no supports  |  {bb.size.X:.0f} x {bb.size.Y:.0f} x {bb.size.Z:.0f} mm")
    footer(img, FOOT)
    img.save(path)
    sc.close()


VIEWS = {1: render_overview, 2: render_section, 3: render_compliance, 4: render_exploded, 5: render_print_layout}


def export_hero_glb(path: Path, travel: float = 3.0, housing: float = 170.0) -> None:
    """Tool at `travel`, pen tip on z = Z_TIP (paper), with a tall J6 housing for the Blender hero shot."""
    from build123d import export_gltf

    its = [it for it in v2.assembly(travel=travel) if "housing" not in it.name]
    its.append(v2.Item("UTRA 6-1000 J6 housing (ref)", v2.ph.make_arm_housing(housing), "arm_dark"))
    # blender_hero.py picks materials by name: "carriage" -> orange PETG
    names = {"Flexure module": "Flexure module (carriage, frame and beams)"}
    asm = v2.labelled_compound([v2.Item(names.get(it.name, it.name), Pos(0, 0, -travel) * it.shape, it.material)
                                for it in its], "pen holder v2")
    export_gltf(asm, str(path), binary=True, linear_deflection=0.05, angular_deflection=0.2)


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Render pen holder v2")
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
    main()
