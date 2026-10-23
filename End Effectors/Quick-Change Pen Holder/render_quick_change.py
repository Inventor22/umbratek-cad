# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["build123d>=0.9,<0.14", "pyvista>=0.43", "numpy", "pillow"]
# ///
"""
Render the quick-change pen holder (quick_change_pen_holder.py) to PNG images.

    uv run render_quick_change.py                    # -> <repo>/Renders/Quick-Change Pen Holder Render N.png
    uv run render_quick_change.py --hero-glb hero.glb   # scene for blender_hero_quick_change.py
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import numpy as np
import pyvista as pv
from build123d import Box, Location, Pos, Rot, Shape
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "Pen Holder"))
import quick_change_pen_holder as qc  # noqa: E402
import render_pen_holder as rph  # noqa: E402
from render_pen_holder import INK, Scene, annotate, font, footer, title  # noqa: E402

OUT_DIR = HERE.parents[1] / "Renders"
PREFIX = "Quick-Change Pen Holder Render"
FOOT = "umbratek-cad / End Effectors / Quick-Change Pen Holder  -  build123d"
rph.MATERIALS.update({
    "cartridge": ("#d9dce0", 0.0, 0.45, "#eef0f2"),
    "pen_blue": ("#2152b0", 0.0, 0.3, "#6d8fd6"),
    "pen_red": ("#bf2330", 0.0, 0.3, "#e0747c"),
})


def cut_x(shape: Shape) -> Shape | None:
    """Remove the half x > 0 (the section plane x = 0 contains the pen axis and the dock)."""
    big = 2000.0
    try:
        out = shape - Pos(big / 2, 0, 0) * Box(big, big, big)
    except Exception:
        return shape
    return out if out.volume > 1e-6 else None


def add_items(sc: Scene, items, section: bool = False, skip=("housing",)) -> None:
    for it in items:
        if any(k in it.name for k in skip):
            continue
        s = it.shape
        if section and "flange (ref)" not in it.name:
            s = cut_x(s)
        if s is not None:
            sc.add(s, it.material, caps=[(0, 0.0)] if section else None)


def arrow(d: ImageDraw.ImageDraw, p0, p1, colour=(200, 60, 20), width=4, head=16) -> None:
    d.line([p0, p1], fill=colour, width=width)
    ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0])
    for s in (-1, 1):
        a = ang + math.pi + s * math.radians(28)
        d.line([p1, (p1[0] + head * math.cos(a), p1[1] + head * math.sin(a))], fill=colour, width=width)


# -----------------------------------------------------------------------------
# Views
# -----------------------------------------------------------------------------
def render_cutaway(path: Path) -> None:
    sc = Scene(2200, 1700)
    add_items(sc, qc.assembly(travel=0.0), section=True)
    sc.camera((0, -24, -26), (1.0, -0.42, 0.2), zoom=1.05)
    img = sc.render()
    y_pen, zc0 = qc.PEN_Y, qc.Z_C0
    notes = [
        ((30, 13, 30), "R", 0, "UTRA 6-1000 tool flange\nreference"),
        ((0, -6, 38), "R", 0, "Base\nbolts on once: 6x M5, pilot, dowel"),
        ((0, -9.5, 32), "R", 0, "M5x12 SHCS"),
        ((-12, qc.ROD_Y - 4, -5), "R", 0, f"2x spring {qc.STAGE_SPRING_WIRE:g} x {qc.STAGE_SPRING_OD:g} x "
                                           f"{qc.STAGE_SPRING_L0:g} on 6 mm rods"),
        ((0, -18.5, qc.Z_TB0 + 4), "R", 0, f"Top block = hard stop\n{qc.STROKE:g} mm of travel"),
        ((0, -16, zc0 + 17), "R", 0, "Hex-key access\nto the lowest M5"),
        ((0, -20, zc0 + 28), "R", 0, "Carriage\nslides on the rods"),
        ((0, -24, zc0 + qc.PLUNGER_Z), "R", 0, "M6 ball spring plunger\ndetent + dovetail preload"),
        ((0, -35, -30), "L", 0, "Cartridge\nslides onto the dovetail rail"),
        ((0, y_pen - 22.5, qc.Z_U1 + 2), "L", 0, "Upper twist chuck\nsecond grip point on the pen"),
        ((0, y_pen - 11, (qc.Z_JS1 + qc.Z_FLARE0) / 2), "L", 0, "Pen tube\njoins the two chucks"),
        ((0, y_pen + 23, qc.Z_W0 + 2), "L", 0, "Lower twist ring\nspiral slots drive 3 jaws"),
        ((0, y_pen - 7.5, qc.Z_JS0 + 8), "L", 0, "Self-centring jaws\nany pen 6-17 mm"),
        ((0, y_pen, -82), "L", 0, "Pen\n11 mm gel pen shown"),
    ]
    annotate(img, sc, notes, left_x=0.27, right_x=0.75, halo=3)
    title(img, "Quick-change pen holder - section",
          f"Pen perpendicular to the flange  |  two chucks grip it over {qc.GRIP_SPAN:.0f} mm  |  pen in free air")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_exploded(path: Path) -> None:
    sc = Scene(1600, 2000)
    items = [it for it in qc.assembly(travel=0.0, explode=True) if "housing" not in it.name]
    for it in items:
        sc.add(Pos(*it.explode) * it.shape, it.material)
    ex_c = qc.EX_CARTRIDGE
    sc.pl.add_mesh(pv.Line((0, qc.PEN_Y + ex_c[1], qc.Z_TIP + ex_c[2] - 80), (0, qc.PEN_Y + ex_c[1], 80)),
                   color="#9aa1ab", line_width=1.5, lighting=False)
    sc.camera((0, -60, -60), (1.0, -1.1, 0.5), zoom=1.12)
    img = sc.render()
    off = {it.name: it.explode for it in items}

    def at(name, x, y, z):
        o = off[name]
        return x + o[0], y + o[1], z + o[2]

    y_pen, zc0 = qc.PEN_Y, qc.Z_C0
    notes = [
        (at("UTRA 6-1000 tool flange (ref)", 30, 13, 30), "R", 0, "UTRA 6-1000 tool flange\nreference"),
        (at("Dowel pin 3x8", 0, 1, 26), "R", 0, "Dowel pin 3 x 8"),
        (at("Base", 30, -6, -20), "R", 0, "Base\nprinted"),
        (at("M5x12 SHCS 4", 0, -9, -32), "L", 0, "6x M5x12 SHCS"),
        (at("Rod L", -12, qc.ROD_Y - 3, 0), "L", 0, "2x 6 x 80 mm steel rod"),
        (at("M3x3 set screw R", 12, -24, qc.Z_TB1 - 3), "R", 0, "2x M3x3 set screw\nlocks the rods"),
        (at("Stage spring L", -12, qc.ROD_Y - 4, zc0 + 50), "L", 0, f"2x spring {qc.STAGE_SPRING_WIRE:g} x "
                                                                    f"{qc.STAGE_SPRING_OD:g} x {qc.STAGE_SPRING_L0:g} mm"),
        (at("Carriage", 17, -20, zc0 + 18), "R", 0, "Carriage\nprinted"),
        (at("M6 ball spring plunger", 3, -20, zc0 + qc.PLUNGER_Z), "R", 0, "M6 ball spring plunger"),
        (at("Cartridge body", 12.5, -30, -25), "R", 0, "Cartridge\nprinted, no hardware"),
        (at("Twist ring (lower)", 24.2 * 0.7, y_pen - 24.2 * 0.7, qc.Z_W0 + 2), "R", 0, "2x twist ring\nprinted"),
        (at("Jaw 1 (lower)", 0, y_pen - 10, qc.Z_JS0 + 7), "L", 0, "6x jaw\nprinted, 3 per chuck"),
        (at("Gel pen 11 mm barrel", -5.5, y_pen, -64), "L", 0, "Pen\n6-17 mm"),
    ]
    annotate(img, sc, notes, left_x=0.25, right_x=0.75, halo=3)
    title(img, "Exploded view", "Base and stage stay on the robot; cartridges slide on and off")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_chuck(path: Path) -> None:
    panels = []
    pw, phh, cap_h = 760, 760, 110
    for pen in qc.PENS:
        sc = Scene(pw, phh)
        sc.pl.add_light(pv.Light(position=(250, -500, -600), focal_point=(0, qc.PEN_Y, -70), intensity=0.85,
                                 light_type="scene light"))
        for it in qc.cartridge_items(pen):
            sc.add(it.shape, it.material)
        sc.camera((0, qc.PEN_Y, qc.Z_W0 + 8), (0.42, -0.62, -1.0), zoom=1.9)
        img = sc.render()
        sc.close()
        cap = Image.new("RGB", (pw, cap_h), (251, 252, 253))
        d = ImageDraw.Draw(cap)
        d.text((30, 14), pen, font=font(30, True), fill=INK)
        d.text((32, 58), f"ring turned {qc.ring_angle(qc.PENS[pen][0]):.0f} deg from open", font=font(23),
               fill=(84, 90, 100))
        panel = Image.new("RGB", (pw, phh + cap_h))
        panel.paste(cap, (0, 0))
        panel.paste(img, (0, cap_h))
        panels.append(panel)
    head = 150
    out = Image.new("RGB", (pw * len(panels), phh + cap_h + head), (251, 252, 253))
    for i, p in enumerate(panels):
        out.paste(p, (i * pw, head))
    title(out, "Self-centring twist chuck", f"Spiral slots in the ring move three jaws together: up to a third of a "
                                            f"turn clamps any pen from {qc.PEN_D_MIN:g} to {qc.PEN_D_MAX:g} mm on the "
                                            f"same axis. A second chuck, upside down, grips it higher up")
    footer(out, FOOT)
    out.save(path)


def render_compliance(path: Path) -> None:
    travels = [0.0, qc.STROKE / 2, qc.STROKE]
    pw, ph_px, half_h, cap_h, head_h = 860, 1200, 100.0, 120, 150
    z_mid, y_mid = -32.0, -27.0
    y_dim = qc.RAIL_FRONT_Y - 2.0  # just in front of the rail, above the cartridge spine
    panels = []
    for t in travels:
        sc = Scene(pw, ph_px)
        items = [it for it in qc.assembly(travel=t) if "housing" not in it.name]
        add_items(sc, items, section=True)
        z_table = qc.Z_TIP + t
        sc.add_pv(pv.Cube(center=(0, -45, z_table - 7.2), x_length=150, y_length=150, z_length=14), "table")
        sc.add_pv(pv.Cube(center=(0, -45, z_table - 0.1), x_length=130, y_length=120, z_length=0.2), "paper")
        sc.pl.enable_parallel_projection()
        sc.pl.camera_position = [(1000, y_mid, z_mid), (0, y_mid, z_mid), (0, 0, 1)]
        sc.pl.camera.parallel_scale = half_h
        img = sc.render()
        d = ImageDraw.Draw(img)
        (_, y_free), (_, y_tab), (x_d, y_c1), (_, y_tb0), (_, y_tb), (x_rail, _) = sc.project(
            [(0, qc.PEN_Y, qc.Z_TIP), (0, qc.PEN_Y, z_table), (0, y_dim, qc.Z_C1 + t), (0, y_dim, qc.Z_TB0),
             (0, qc.PEN_Y, z_table - 14), (0, qc.STAGE_FRONT_Y, 0)])
        red = (200, 60, 20)
        for x in range(30, pw - 30, 18):
            d.line([(x, y_free), (x + 9, y_free)], fill=(120, 126, 136), width=2)
        d.text((30, max(y_free, y_tb) + 8), "pen tip in free air", font=font(20), fill=(110, 116, 126))
        if t > 0:
            xd = 70
            d.line([(xd, y_free), (xd, y_tab)], fill=red, width=3)
            for y, s in ((y_free, 1), (y_tab, -1)):
                d.polygon([(xd, y), (xd - 8, y - 14 * s), (xd + 8, y - 14 * s)], fill=red)
            d.text((xd + 14, (y_free + y_tab) / 2 - 16), f"{t:g} mm", font=font(24, True), fill=red)
        gap = qc.STROKE - t
        for y in (y_c1, y_tb0):  # extension lines from the carriage top and the top block
            d.line([(x_d - 8, y), (x_rail, y)], fill=INK, width=2)
        f_b, f_r = font(24, True), font(20)
        if gap > 0:
            d.line([(x_d, y_tb0), (x_d, y_c1)], fill=INK, width=2)
            for y, s in ((y_tb0, 1), (y_c1, -1)):
                d.polygon([(x_d, y), (x_d - 6, y + 11 * s), (x_d + 6, y + 11 * s)], fill=INK)
            ym = (y_c1 + y_tb0) / 2
            for txt, fn, dy in ((f"{gap:g} mm", f_b, -30), ("to stop", f_r, 2)):
                d.text((x_d - 12 - d.textlength(txt, font=fn), ym + dy), txt, font=fn, fill=INK,
                       stroke_width=3, stroke_fill=(251, 252, 253))
        else:
            txt = "hard stop"
            d.text((x_d - 12 - d.textlength(txt, font=f_b), y_tb0 - 34), txt, font=f_b, fill=INK,
                   stroke_width=3, stroke_fill=(251, 252, 253))
        sc.close()
        cap = Image.new("RGB", (pw, cap_h), (251, 252, 253))
        dc = ImageDraw.Draw(cap)
        force = qc.STAGE_RATE * (qc.SPRING_PRELOAD + t)
        dc.text((36, 18), "Pen touches the table" if t == 0 else f"Arm over-reaches {t:g} mm", font=font(32, True),
                fill=INK)
        dc.text((38, 66), f"pen force {force:.1f} N", font=font(26), fill=red if t else (88, 94, 104))
        panel = Image.new("RGB", (pw, ph_px + cap_h))
        panel.paste(cap, (0, 0))
        panel.paste(img, (0, cap_h))
        panels.append(panel)
    out = Image.new("RGB", (pw * len(panels), ph_px + cap_h + head_h), (251, 252, 253))
    for i, p in enumerate(panels):
        out.paste(p, (i * pw, head_h))
    d = ImageDraw.Draw(out)
    for i in range(1, len(panels)):
        d.line([(i * pw, head_h + 20), (i * pw, head_h + cap_h - 10)], fill=(205, 210, 216), width=2)
    title(out, "Spring compliance", f"The carriage rides up to {qc.STROKE:g} mm on its rods instead of driving the pen "
                                    f"into the table  |  ~{qc.STAGE_RATE:.2f} N/mm, {qc.SPRING_PRELOAD:g} mm preload")
    footer(out, FOOT)
    out.save(path)


def robot_side(travel: float = 0.0) -> list:
    return [it for it in qc.assembly(travel=travel, pen=None)
            if not any(k in it.name for k in ("Cartridge", "Twist ring", "Jaw", "housing"))]


def render_swap(path: Path) -> None:
    sc = Scene(1800, 1500)
    add_items(sc, robot_side())
    drop = -48.0
    add_items(sc, qc.cartridge_items("Gel pen 11 mm", place=Pos(0, 0, drop)))
    spares = {"Ballpoint 8 mm": Pos(-82, -20, -40), "Whiteboard marker 16 mm": Pos(82, -20, -40)}
    for pen, loc in spares.items():
        add_items(sc, qc.cartridge_items(pen, place=loc))
    sc.camera((0, -40, -50), (0.9, -1.25, 0.42), zoom=1.08)
    img = sc.render()
    d = ImageDraw.Draw(img)
    (x0, y0), (x1, y1) = sc.project([(13.5, qc.SPINE_BACK_Y - 6, qc.Z_C0 + drop + 8),
                                      (13.5, qc.SPINE_BACK_Y - 6, qc.Z_C0 - 6)])
    arrow(d, (x0 + 40, y0), (x1 + 40, y1), width=5, head=20)
    arrow(d, (x1 + 70, y1), (x0 + 70, y0), colour=(110, 116, 126), width=5, head=20)
    notes = [
        ((0, qc.RAIL_FRONT_Y, qc.Z_C0 + 25), "R", 0, "Dovetail rail on the carriage"),
        ((0, qc.PLUNGER_FACE_Y - 0.3, qc.Z_C0 + qc.PLUNGER_Z), "R", 0, "Ball plunger clicks into the\ncartridge's detent"),
        ((12.5, -35, qc.Z_C0 + drop + 20), "R", 0, "Slide up until it clicks\npull down to release"),
        ((-82 + 0, -20 + qc.PEN_Y - 24, -40 + qc.Z_W0 + 4), "L", 0, "Spare cartridges\npens stay clamped"),
        ((0, -6, 38), "L", 0, "Base stays bolted\nto the arm"),
    ]
    annotate(img, sc, notes, left_x=0.2, right_x=0.8)
    title(img, "Quick pen swap", "No tools: the base and spring stage stay on the robot")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_print_layout(path: Path) -> None:
    sc = Scene(1700, 1050)
    sc.add_pv(pv.Cube(center=(0, 0, -0.8), x_length=250, y_length=210, z_length=1.6), "bed")
    parts = qc.printed_parts()
    layout = {
        "Quick-Change - Base": (-62, 40, "printed"),
        "Quick-Change - Carriage": (10, 60, "accent"),
        "Quick-Change - Cartridge": (62, 40, "cartridge"),
        "Quick-Change - Twist Ring (print 2)": (-95, -58, "accent"),
        "Quick-Change - Stick-out Gauge": (95, -58, "printed"),
    }
    anchors = []
    for name, (x, y, mat) in layout.items():
        p = parts[name][1]
        c = p.bounding_box().center()
        shape = Pos(x - c.X, y - c.Y, 0) * p
        sc.add(shape, mat)
        bb = shape.bounding_box()
        anchors.append(((bb.center().X, bb.min.Y + 2, bb.max.Z * 0.7), name, p.bounding_box().size))
    ring = parts["Quick-Change - Twist Ring (print 2)"][1]
    c = ring.bounding_box().center()
    sc.add(Pos(-42 - c.X, -58 - c.Y, 0) * ring, "accent")
    jaw = parts["Quick-Change - Jaw (print 6)"][1]
    for i in range(6):
        c = jaw.bounding_box().center()
        sc.add(Pos(4 + 15 * (i % 3) - c.X, -46 - 19 * (i // 3) - c.Y, 0) * jaw, "printed")
    sc.camera((8, 0, 30), (0.35, -1.0, 0.66), zoom=1.12)
    img = sc.render()
    sides = {"Base": "L", "Carriage": "R", "Cartridge": "R", "Twist Ring (print 2)": "L", "Stick-out Gauge": "R"}
    notes = []
    for pt, name, s in anchors:
        short = name.split(" - ")[1]
        notes.append((pt, sides[short], 0, f"{short.replace(' (print 2)', '')}\n{s.X:.0f} x {s.Y:.0f} x {s.Z:.0f} mm"
                                           + ("  -  print 2" if "print 2" in short else "")))
    notes.append(((34, -65, 4), "R", 0, "6x jaw\non their side"))
    annotate(img, sc, notes, left_x=0.16, right_x=0.84, top=170, halo=3)
    title(img, "Print layout", "No supports needed  |  PETG, 0.2 mm layers, 4 perimeters, 40 % infill")
    footer(img, FOOT)
    img.save(path)
    sc.close()


def render_detent(path: Path) -> None:
    """Lower chuck cut just above the ring's wheel, seen from above: spring fingers clicking into the ring's flutes."""
    pitch = 360 / qc.DETENT_FLUTES
    psi = round(qc.ring_angle(11.0) / pitch) * pitch  # an 11 mm pen, ring settled on a click
    r_tip = qc.R_TIP_MAX - (qc.R_TIP_MAX - qc.R_TIP_MIN) * psi / qc.SLOT_SWEEP
    z_cut = qc.Z_JS0 + 1.4
    keep = Pos(0, qc.PEN_Y, z_cut - 10) * Box(80, 80, 20)
    _, _, barrel = qc.make_pen(2 * r_tip, 140.0)
    jaw = qc.make_jaw()
    shapes = [(qc.make_cartridge(), "cartridge"), (qc.at_pen(Rot(0, 0, psi) * qc.make_ring()), "accent"),
              (Pos(0, qc.PEN_Y, qc.Z_TIP) * barrel, "pen_black")]
    shapes += [(qc.at_pen(Rot(0, 0, a) * Pos(r_tip, 0, 0) * jaw), "printed") for a in qc.JAW_ANGLES]
    cut = [(s & keep, m) for s, m in shapes]

    def pt(r: float, deg: float) -> tuple[float, float, float]:
        return r * math.cos(math.radians(deg)), qc.PEN_Y + r * math.sin(math.radians(deg)), z_cut

    a_f = qc.DETENT_ANGLES[1]
    r_bore = (qc.CHUCK_D + qc.RING_CLEARANCE) / 2
    views = [
        ("Lower chuck, cut just above the ring's slotted wheel", (0, qc.PEN_Y, z_cut), 1.0, [
            (pt(23.0, 300), "R", 0, "Twist ring"),
            (pt(20.1, a_f), "R", 0, "Spring finger"),
            (pt(12.0, qc.JAW_ANGLES[0]), "L", 0, "Jaw"),
            (pt(2.0, 180), "L", 0, "Pen"),
        ]),
        ("Close-up of one finger", pt(21.0, a_f), 4.0, [
            (pt(r_bore + 0.15, a_f), "R", 0, "Bump sits\nin a flute"),
            (pt(r_bore + 0.25, a_f - 2 * pitch), "R", 0, f"{qc.DETENT_FLUTES} ratchet flutes:\ngentle ramp to tighten,\n"
                                                           f"steep wall against loosening"),
            (pt(20.1, a_f + 5), "L", 0, f"Spring finger\nflexes {qc.DETENT_DEPTH:g} mm"),
        ]),
    ]
    pw, phh, cap_h, head, foot = 1100, 1000, 90, 150, 70
    out = Image.new("RGB", (pw * 2, phh + cap_h + head + foot), (251, 252, 253))
    for i, (caption, focal, zoom, notes) in enumerate(views):
        sc = Scene(pw, phh)
        for s, m in cut:
            sc.add(s, m, caps=[(2, z_cut)])
        sc.camera(focal, (0.12, -0.22, 1.0), zoom=zoom, up=(0, 1, 0))
        img = sc.render()
        annotate(img, sc, notes, left_x=0.2, right_x=0.72, halo=3)
        sc.close()
        d = ImageDraw.Draw(out)
        d.text((30 + i * pw, head + 22), caption, font=font(26, True), fill=INK)
        out.paste(img, (i * pw, head + cap_h))
    title(out, "Ratchet clicks", f"Two spring fingers per chuck click into flutes inside its ring every {pitch:g}°: "
                                 "light to tighten, a steep wall against loosening. The shallow spiral holds the clamp")
    footer(out, FOOT)
    out.save(path)


VIEWS = {1: render_cutaway, 2: render_exploded, 3: render_chuck, 4: render_compliance, 5: render_swap,
         6: render_print_layout, 7: render_detent}


def export_hero_glb(path: Path, travel: float = 3.0) -> None:
    """Scene for blender_hero_quick_change.py: pen pressed into the paper, spare cartridges in their gauges."""
    items = qc.assembly(travel=travel)
    for it in items:
        if "housing" in it.name:
            it.shape = qc.F2M * qc.ph.make_arm_housing(170.0)
    z_desk = qc.Z_TIP + travel
    gauge = qc.make_gauge()
    for label, pen, (x, y, spin) in (("Spare A ", "Ballpoint 8 mm", (-118, 18, 200)),
                                     ("Spare B ", "Whiteboard marker 16 mm", (-170, 66, 225))):
        place = Pos(x, y, z_desk + qc.GAUGE_FLOOR - qc.Z_TIP) * Rot(0, 0, spin) * Pos(0, -qc.PEN_Y, 0)
        items += qc.cartridge_items(pen, place=place, label=label)
        items.append(qc.Item(f"{label}Stick-out gauge", Pos(x, y, z_desk) * gauge, "printed"))
    asm = qc.labelled_compound(items, "UTRA 6-1000 quick-change pen holder (hero)")
    qc.export_gltf(asm, path, binary=True, linear_deflection=0.01, angular_deflection=0.1)
    print(f"wrote {path} (pen tip / desk at z = {z_desk:.2f} mm, frame M)")


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Render the quick-change pen holder")
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
