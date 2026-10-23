# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = ["build123d>=0.9,<0.14", "pyvista>=0.43", "numpy", "pillow"]
# ///
"""
Render the UTRA 6-1000 pen-holder end effector (pen_holder.py) to PNG images.

    uv run render_pen_holder.py          # -> <repo>/Renders/Pen Holder End Effector Render N.png

Needs an OpenGL-capable GPU/driver (VTK off-screen rendering).
"""

from __future__ import annotations

import math
import sys
import tempfile
from pathlib import Path

import numpy as np
import pyvista as pv
import vtk
from build123d import Box, GeomType, Pos, Shape
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import pen_holder as ph  # noqa: E402

OUT_DIR = HERE.parents[1] / "Renders"
PREFIX = "Pen Holder End Effector Render"
INK = (29, 31, 35)

# material: (base colour, metallic, roughness, section-cut colour)
MATERIALS = {
    "printed": ("#3a3d43", 0.0, 0.55, "#8a9099"),
    "accent": ("#f26b1d", 0.0, 0.42, "#ff9d5c"),
    "steel_black": ("#2a2c30", 0.6, 0.35, "#6f747b"),
    "steel": ("#c6cacf", 1.0, 0.28, "#e3e5e8"),
    "spring": ("#d7dbe0", 1.0, 0.2, "#eef0f2"),
    "aluminum": ("#d2d6db", 0.85, 0.32, "#e8eaed"),
    "arm_dark": ("#454a52", 0.25, 0.45, "#767c85"),
    "pen_body": ("#e6e8eb", 0.0, 0.32, "#f4f5f6"),
    "pen_black": ("#1b1c1f", 0.0, 0.35, "#55595f"),
    "pen_nib": ("#22305c", 0.0, 0.6, "#53639a"),
    "table": ("#c79d70", 0.0, 0.62, "#c79d70"),
    "bed": ("#c4a062", 0.35, 0.5, "#c4a062"),
    "paper": ("#fbfbf8", 0.0, 0.85, "#fbfbf8"),
    "ink": ("#1d2c63", 0.0, 0.5, "#1d2c63"),
}
NO_EDGES = {"spring", "table", "paper", "ink"}


# -----------------------------------------------------------------------------
# Fonts
# -----------------------------------------------------------------------------
def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    names = ["segoeuib.ttf", "arialbd.ttf", "DejaVuSans-Bold.ttf"] if bold else ["segoeui.ttf", "arial.ttf", "DejaVuSans.ttf"]
    for name in names:
        for folder in (Path("C:/Windows/Fonts"), Path("/usr/share/fonts/truetype/dejavu"), Path("/Library/Fonts")):
            if (folder / name).exists():
                return ImageFont.truetype(str(folder / name), size)
    return ImageFont.load_default(size=size)


# -----------------------------------------------------------------------------
# build123d -> pyvista
# -----------------------------------------------------------------------------
def to_polydata(shape: Shape, caps: list[tuple[int, float]] | None = None, tol: float = 0.02, ang: float = 0.15):
    """Tessellate per B-rep face (crisp edges, smooth curved faces).

    Returns (body, cap); cap holds planar faces lying on a section plane, given as
    (axis index, coordinate) pairs, e.g. [(1, 0.0)] for the plane y = 0.
    """
    shape.tessellate(tol, ang)
    buckets = {False: ([], []), True: ([], [])}
    count = {False: 0, True: 0}
    for face in shape.faces():
        verts, tris = face.tessellate(tol, ang)
        if not tris:
            continue
        is_cap = False
        if caps and face.geom_type == GeomType.PLANE:
            n, c = face.normal_at(), face.center()
            nv, cv = (n.X, n.Y, n.Z), (c.X, c.Y, c.Z)
            is_cap = any(abs(abs(nv[i]) - 1) < 1e-6 and abs(cv[i] - v) < 1e-3 for i, v in caps)
        pts, cells = buckets[is_cap]
        pts.append(np.array([(v.X, v.Y, v.Z) for v in verts], dtype=float))
        t = np.asarray(tris, dtype=np.int64) + count[is_cap]
        cells.append(np.hstack([np.full((len(t), 1), 3), t]).ravel())
        count[is_cap] += len(verts)
    out = []
    for key in (False, True):
        pts, cells = buckets[key]
        if not pts:
            out.append(None)
            continue
        mesh = pv.PolyData(np.vstack(pts), np.concatenate(cells))
        out.append(mesh.compute_normals(cell_normals=False, split_vertices=False, consistent_normals=False,
                                        auto_orient_normals=False))
    return out[0], out[1]


def feature_edges(meshes: list, angle: float = 40.0) -> pv.PolyData | None:
    meshes = [m for m in meshes if m is not None]
    if not meshes:
        return None
    merged = pv.merge(meshes).clean(tolerance=1e-4)
    return merged.extract_feature_edges(feature_angle=angle, boundary_edges=False, non_manifold_edges=False,
                                        manifold_edges=False, feature_edges=True)


def cut_away(shape: Shape, quarter: bool = False) -> Shape | None:
    """Section a shape: remove the half y < 0, or (quarter=True) only the quadrant x > 0, y < 0."""
    big = 2000.0
    cutter = Pos(big / 2 if quarter else 0, -big / 2, 0) * Box(big, big, big)
    try:
        cut = shape - cutter
    except Exception:
        return shape
    return cut if cut.volume > 1e-6 else None


# -----------------------------------------------------------------------------
# Scene
# -----------------------------------------------------------------------------
_ENV = None


def studio_environment() -> pv.Texture:
    """Soft light-grey studio cube map so metallic PBR surfaces have something to reflect."""
    global _ENV
    if _ENV is None:
        tmp = Path(tempfile.mkdtemp(prefix="penholder_env_"))
        n = 128
        u = np.linspace(-1, 1, n)
        uu, vv = np.meshgrid(u, u)
        paths = []
        for i, base in enumerate([95, 70, 165, 40, 85, 80]):  # +X -X +Y(up) -Y +Z -Z
            img = np.full((n, n), float(base))
            if i in (0, 4):  # soft boxes
                img += 90 * np.exp(-((uu * 1.6) ** 4 + (vv * 2.2) ** 4))
            rgb = np.clip(np.stack([img, img * 1.0, img * 1.02], axis=-1), 0, 255).astype(np.uint8)
            p = tmp / f"env{i}.png"
            Image.fromarray(rgb).save(p)
            paths.append(str(p))
        _ENV = pv.cubemap_from_filenames(paths)
    return _ENV


class Scene:
    def __init__(self, width: int, height: int, *, shadows: bool = False, ssao: bool = True,
                 background: tuple[str, str] = ("#fbfcfd", "#d3d8df")):
        pl = pv.Plotter(off_screen=True, window_size=(width, height), lighting="none")
        pl.set_background(background[0], top=background[1])
        try:
            pl.set_environment_texture(studio_environment(), is_srgb=True)
            pl.renderer.SetEnvironmentUp(0, 0, 1)
            pl.renderer.SetEnvironmentRight(1, 0, 0)
        except Exception:
            pass
        lights = [((450, -520, 640), 1.25, "#fff4ea"), ((-560, -260, 160), 0.4, "#e8efff"),
                  ((90, 620, 420), 0.7, "#ffffff"), ((0, -60, -700), 0.12, "#ffffff")]
        for pos, intensity, colour in lights:
            pl.add_light(pv.Light(position=pos, focal_point=(0, 0, -60), color=colour, intensity=intensity,
                                  light_type="scene light"))
        self.pl, self.width, self.height = pl, width, height
        self._shadows, self._ssao = shadows, ssao

    def add(self, shape: Shape, material: str, *, caps: list[tuple[int, float]] | None = None, edges: bool = True,
            edge_angle: float = 40.0, edge_width: float = 1.3) -> None:
        body, cap = to_polydata(shape, caps)
        base, metallic, rough, cap_colour = MATERIALS[material]
        if body is not None:
            self.pl.add_mesh(body, color=base, pbr=True, metallic=metallic, roughness=rough, smooth_shading=True)
        if cap is not None:
            self.pl.add_mesh(cap, color=cap_colour, pbr=True, metallic=0.0, roughness=0.9, smooth_shading=False)
        if edges and material not in NO_EDGES:
            fe = feature_edges([body, cap], edge_angle)
            if fe is not None and fe.n_points:
                self.pl.add_mesh(fe, color="#1b1d21", line_width=edge_width, lighting=False)

    def add_pv(self, mesh: pv.PolyData, material: str, smooth: bool = True) -> None:
        base, metallic, rough, _ = MATERIALS[material]
        self.pl.add_mesh(mesh, color=base, pbr=True, metallic=metallic, roughness=rough, smooth_shading=smooth)

    def camera(self, focal, direction, *, zoom: float = 1.0, view_angle: float = 18.0, up=(0, 0, 1)) -> None:
        d = np.asarray(direction, float)
        d /= np.linalg.norm(d)
        focal = np.asarray(focal, float)
        self.pl.camera_position = [tuple(focal + d * 1000.0), tuple(focal), up]
        self.pl.camera.view_angle = view_angle
        self.pl.reset_camera()
        self.pl.camera.focal_point = tuple(focal)
        self.pl.camera.position = tuple(focal + d * np.linalg.norm(np.array(self.pl.camera.position) - focal))
        self.pl.camera.zoom(zoom)

    def project(self, points) -> list[tuple[float, float]]:
        coord = vtk.vtkCoordinate()
        coord.SetCoordinateSystemToWorld()
        out = []
        for p in points:
            coord.SetValue(*map(float, p))
            x, y = coord.GetComputedDoubleDisplayValue(self.pl.renderer)
            out.append((x, self.height - y))
        return out

    def render(self) -> Image.Image:
        if self._shadows:
            self.pl.enable_shadows()
        if self._ssao:
            # scale the occlusion kernel with the scene, otherwise distant views band
            b = self.pl.bounds
            diag = math.dist((b[0], b[2], b[4]), (b[1], b[3], b[5]))
            self.pl.enable_ssao(radius=0.02 * diag, bias=0.006 * diag, kernel_size=128, blur=True)
        self.pl.enable_anti_aliasing("ssaa")
        self.pl.render()
        img = Image.fromarray(self.pl.screenshot(return_img=True))
        return img

    def close(self) -> None:
        self.pl.close()


# -----------------------------------------------------------------------------
# 2-D annotation (PIL)
# -----------------------------------------------------------------------------
def title(img: Image.Image, text: str, sub: str | None = None) -> None:
    d = ImageDraw.Draw(img)
    d.text((52, 40), text, font=font(42, bold=True), fill=INK)
    if sub:
        d.text((54, 98), sub, font=font(26), fill=(88, 94, 104))


def _spread(ys: list[float], gaps: list[float], lo: float, hi: float) -> list[float]:
    """Push label centres apart (1-D) so neighbouring blocks don't overlap."""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    out = list(ys)
    prev = None
    for i in order:
        if prev is not None:
            out[i] = max(out[i], out[prev] + (gaps[prev] + gaps[i]) / 2)
        prev = i
    nxt = None
    for i in reversed(order):
        limit = hi - gaps[i] / 2 if nxt is None else out[nxt] - (gaps[nxt] + gaps[i]) / 2
        out[i] = min(out[i], limit)
        nxt = i
    return [max(y, lo) for y in out]


def annotate(img: Image.Image, sc: Scene, notes: list, *, size: int = 25, left_x: float = 0.27,
             right_x: float = 0.73, top: int = 150, halo: int = 0) -> None:
    """notes: (anchor xyz, 'L' | 'R', dy px, 'Bold first line\\nsecond line'). halo = text outline px."""
    w, h = img.size
    d = ImageDraw.Draw(img)
    f_b, f_r = font(size, bold=True), font(size - 3)
    anchors = sc.project([n[0] for n in notes])
    blocks = []
    for (ax, ay), (_, side, dy, text) in zip(anchors, notes):
        lines = text.split("\n")
        fonts = [f_b] + [f_r] * (len(lines) - 1)
        heights = [fn.getbbox("Ag")[3] + 4 for fn in fonts]
        blocks.append([ax, ay, ay + dy, side, lines, fonts, heights])
    for side in ("L", "R"):
        idx = [i for i, b in enumerate(blocks) if b[3] == side]
        ys = _spread([blocks[i][2] for i in idx], [sum(blocks[i][6]) + 18 for i in idx], top, h - 80)
        for i, y in zip(idx, ys):
            blocks[i][2] = y
    for ax, ay, ly, side, lines, fonts, heights in blocks:
        edge = w * (left_x if side == "L" else right_x)
        shoulder = edge + (22 if side == "L" else -22)
        d.line([(ax, ay), (shoulder, ly), (edge, ly)], fill=INK, width=2)
        d.ellipse([ax - 5, ay - 5, ax + 5, ay + 5], fill=INK, outline="white", width=2)
        y = ly - sum(heights) / 2 - 2
        for line, fn, hh in zip(lines, fonts, heights):
            tw = d.textlength(line, font=fn)
            x = edge - 10 - tw if side == "L" else edge + 10
            d.text((x, y), line, font=fn, fill=INK if fn is f_b else (84, 90, 100),
                   stroke_width=halo, stroke_fill=(251, 252, 253))
            y += hh


def footer(img: Image.Image, text: str = "umbratek-cad / End Effectors / Pen Holder  -  build123d") -> None:
    w, h = img.size
    d = ImageDraw.Draw(img)
    fn = font(20)
    d.text((w - 40 - d.textlength(text, font=fn), h - 50), text, font=fn, fill=(130, 136, 146))


# -----------------------------------------------------------------------------
# Views
# -----------------------------------------------------------------------------
def tool_items(travel: float = 0.0) -> list:
    """Assembly without the J6 housing stub (technical views)."""
    return [it for it in ph.assembly(travel=travel) if "housing" not in it.name]


def render_cutaway(path: Path) -> None:
    sc = Scene(1800, 1800)
    for it in tool_items():
        s = it.shape if "flange (ref)" in it.name else cut_away(it.shape, quarter=True)
        if s is not None:
            sc.add(s, it.material, caps=[(1, 0.0), (0, 0.0)])
    sc.camera((0, 0, -64), (1.0, -1.2, 0.28), zoom=0.93)
    img = sc.render()
    z_pin, z_cl = ph.Z_PIN, ph.Z_CLAMP
    notes = [
        ((-30, -30, 14), "L", 0, "UTRA 6-1000 tool flange\nreference, per Quick Start Guide"),
        ((32, 0, -3.5), "R", 0, "6x M5x12 SHCS\nPCD 64, 5 mm thread engagement"),
        ((26, 0, 1.0), "R", 0, "3 mm dowel pin\nPCD 52, sets tool orientation"),
        ((40.5, 0, -8), "R", 0, "Tool adapter\nre-usable mounting plate"),
        ((0, -21.5, -9), "L", 0, "3x M3x14 + captive nuts\nmodule -> adapter"),
        ((0, -14, -44), "L", 0, "Pen module\nflange + barrel"),
        ((0, -9.5, -28), "L", 0, f"Compression spring\n{ph.SPRING_WIRE:g} x {ph.SPRING_OD:g} x {ph.SPRING_FREE_LEN:g} mm"),
        ((0, -13.5, z_pin), "L", 0, "Guide pin in slot\nM3x6 set screw, anti-rotation"),
        ((0, -11.8, ph.Z_NOSE_TOP + 7), "L", 0, f"{ph.STROKE:g} mm compliant travel\nnose shoulder = hard stop"),
        ((10.5, 0, ph.Z_CARRIAGE_TOP - 20), "R", 0, "Pen carriage\nslides in the barrel"),
        ((17, 0, z_cl), "R", 0, "Thumb screw + captive nut\nclamps the pen"),
        ((3.5, 0, ph.Z_TIP + 12), "R", 0, "Pen\nSharpie Fine Point shown"),
    ]
    annotate(img, sc, notes, left_x=0.225, right_x=0.8)
    title(img, "Compliant pen holder - cutaway", f"Pen in free air  |  TCP {ph.TCP_Z:.0f} mm below the flange face")
    footer(img)
    img.save(path)
    sc.close()


def render_exploded(path: Path) -> None:
    sc = Scene(1400, 2000)
    items = tool_items()
    offset = {it.name: it.explode for it in items}
    for it in items:
        sc.add(Pos(*it.explode) * it.shape, it.material)
    z_lo = ph.Z_CLAMP + offset["M3 nut (pen clamp)"][2] - 40
    sc.pl.add_mesh(pv.Line((0, 0, 115), (0, 0, z_lo)), color="#9aa1ab", line_width=1.5, lighting=False)
    px, _, pz = offset["Pen nib"]
    sc.pl.add_mesh(pv.Line((px, 0, ph.Z_TIP + pz - 20), (px, 0, ph.Z_TIP + ph.PEN_LEN + pz + 20)),
                   color="#9aa1ab", line_width=1.5, lighting=False)
    sc.camera((0, 0, (115 + z_lo) / 2 + 6), (1.0, -1.25, 0.42), zoom=1.26)
    img = sc.render()

    def at(name: str, x: float, y: float, z: float) -> tuple[float, float, float]:
        ox, oy, oz = offset[name]
        return x + ox, y + oy, z + oz

    notes = [
        (at("UTRA 6-1000 tool flange (ref)", -30, -30, 14), "L", 0, "UTRA 6-1000 tool flange\nreference"),
        (at("Dowel pin 3x8", 26, 0, 4.5), "R", 0, "Dowel pin 3 x 8\nISO 8734"),
        (at("M3 nut 3", 0, -21.5, -3), "L", 0, "3x M3 hex nut\ncaptive, arm side"),
        (at("Tool adapter", 30.4, -30.4, -5), "R", 0, "Tool adapter\nprinted"),
        (at("M5x12 SHCS 6", 16, -27.7, ph.Z_M5_SEAT - 3), "R", 0, "6x M5x12 SHCS\nISO 4762"),
        (at("Pen module", 11.3, -11.3, -60), "R", 0, "Pen module\nprinted"),
        (at("M3x14 SHCS 3", 0, -21.5, ph.Z_M3_SEAT - 2), "L", 0, "3x M3x14 SHCS\nISO 4762"),
        (at("Compression spring", -7, -7, ph.Z_SPRING_TOP - ph.SPRING_INSTALLED / 2), "L", 0,
         f"Compression spring\n{ph.SPRING_WIRE:g} x {ph.SPRING_OD:g} x {ph.SPRING_FREE_LEN:g} mm, "
         f"~{ph.SPRING_RATE:.2f} N/mm"),
        (at("Pen carriage", 8.3, -8.3, ph.Z_CARRIAGE_TOP - 22), "R", 0, "Pen carriage\nprinted"),
        (at("M3x6 set screw (guide pin, -Y)", 0, -14.3, ph.Z_PIN), "L", 0, "2x M3x6 set screw\nISO 4026 - guide pins"),
        (at("M3x10 thumb screw", ph.PEN_D / 2 + 15, 0, ph.Z_CLAMP), "R", 0,
         "M3x10 knurled thumb screw\nDIN 464 / DIN 653"),
        (at("M3 nut (pen clamp)", 10.5, -2, ph.Z_CLAMP), "R", 0, "M3 hex nut\ncaptive pen clamp"),
        (at("Pen barrel", 0, -6.5, ph.Z_TIP + 60), "L", 0, "Pen\nSharpie Fine Point shown"),
    ]
    annotate(img, sc, notes)
    title(img, "Exploded view", "3 printed parts + off-the-shelf hardware")
    footer(img)
    img.save(path)
    sc.close()


def render_compliance(path: Path) -> None:
    travels = [0.0, ph.STROKE / 2, ph.STROKE]
    pw, ph_px, half_h, cap_h, head_h = 760, 1380, 118.0, 120, 150
    z_mid = -76.0
    panels = []
    for t in travels:
        sc = Scene(pw, ph_px)
        for it in tool_items(t):
            s = it.shape if "flange (ref)" in it.name else cut_away(it.shape)
            if s is not None:
                sc.add(s, it.material, caps=[(1, 0.0)])
        z_table = ph.Z_TIP + t
        sc.add_pv(pv.Cube(center=(0, 40, z_table - 7.2), x_length=170, y_length=80, z_length=14), "table")
        sc.add_pv(pv.Cube(center=(0, 40, z_table - 0.1), x_length=150, y_length=80, z_length=0.2), "paper")
        sc.pl.enable_parallel_projection()
        sc.pl.camera_position = [(0, -1000, z_mid), (0, 0, z_mid), (0, 0, 1)]
        sc.pl.camera.parallel_scale = half_h
        img = sc.render()
        d = ImageDraw.Draw(img)
        (_, y_free), (_, y_tab), (_, y_bb), (_, y_nt), (x_r, _), (_, y_tb) = sc.project(
            [(0, 0, ph.Z_TIP), (0, 0, z_table), (0, 0, ph.Z_BARREL_BOTTOM), (0, 0, ph.Z_NOSE_TOP + t), (27, 0, 0),
             (0, 0, z_table - 14)])
        red = (200, 60, 20)
        for x in range(30, pw - 30, 18):  # free-air tip height
            d.line([(x, y_free), (x + 9, y_free)], fill=(120, 126, 136), width=2)
        d.text((30, max(y_free, y_tb) + 8), "pen tip in free air", font=font(20), fill=(110, 116, 126))
        if t > 0:
            xd = pw - 110
            d.line([(xd, y_free), (xd, y_tab)], fill=red, width=3)
            for y, s in ((y_free, 1), (y_tab, -1)):
                d.polygon([(xd, y), (xd - 8, y - 14 * s), (xd + 8, y - 14 * s)], fill=red)
            label = f"{t:g} mm"
            d.text((xd - 14 - d.textlength(label, font=font(24, True)), (y_free + y_tab) / 2 - 16), label,
                   font=font(24, True), fill=red)
        gap = ph.STROKE - t
        for y in (y_bb, y_nt):
            d.line([(x_r, y), (x_r + 28, y)], fill=INK, width=2)
        ym = (y_bb + y_nt) / 2
        if gap > 0:
            d.line([(x_r + 14, y_bb), (x_r + 14, y_nt)], fill=INK, width=2)
            d.text((x_r + 38, ym - 30), f"{gap:g} mm", font=font(24, True), fill=INK)
            d.text((x_r + 38, ym + 2), "to hard stop", font=font(20), fill=(84, 90, 100))
        else:
            d.text((x_r + 38, ym - 15), "hard stop", font=font(24, True), fill=INK)
        sc.close()
        cap = Image.new("RGB", (pw, cap_h), (251, 252, 253))
        dc = ImageDraw.Draw(cap)
        force = ph.SPRING_RATE * (ph.SPRING_PRELOAD + t)
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
    title(out, "Spring compliance", f"The carriage slides up to {ph.STROKE:g} mm instead of driving the pen into the "
                                    f"table  |  spring ~{ph.SPRING_RATE:.2f} N/mm, {ph.SPRING_PRELOAD:g} mm preload")
    footer(out)
    out.save(path)


def render_interface(path: Path) -> None:
    size, w = 1000, 1200
    a = Scene(w, size)
    a.add(ph.make_arm_flange(), "aluminum")
    a.camera((0, 0, 10), (0.22, -0.6, -1.0), zoom=0.92)
    img_a = a.render()
    annotate(img_a, a, [
        ((16, -27.7, 0), "R", 0, "6x M5, 6 deep\nPCD 64, 60 deg pitch"),
        ((26, 0, 0), "R", 0, "3 mm H7 dowel, 5 deep\nPCD 52, in line with an M5"),
        ((-26.2, -25.5, 1.5), "L", 0, "73 h7 pilot boss\n3 mm high"),
        ((-7.5, 3, 0), "L", 0, "Tool I/O\n2x 8-pin connectors"),
        ((-39, -18, 12), "L", 0, "86 mm flange"),
    ], size=21, left_x=0.19, right_x=0.765, top=170)
    a.close()

    b = Scene(w, size)
    b.add(ph.make_adapter(), "printed")
    b.camera((0, 0, -4), (0.22, -0.6, 1.0), zoom=0.86)
    img_b = b.render()
    r_p = (ph.PILOT_D + ph.PILOT_CLEARANCE) / 2
    annotate(img_b, b, [
        ((-r_p * 0.7071, -r_p * 0.7071, 1.2), "L", 0, f"Pilot recess {ph.PILOT_D + ph.PILOT_CLEARANCE:g} x "
                                                     f"{ph.PILOT_RECESS_DEPTH:g}\nseats on the boss face"),
        ((16, -27.7, 0), "R", 0, "6x 5.5 thru\n10 c'bore from below"),
        ((26, 0, 0), "R", 0, "Dowel hole"),
        ((ph.ADAPTER_OD / 2, 0, -5), "R", 0, "Index groove\ndowel side"),
        ((-14, -12, -1), "L", 0, f"{ph.RELIEF_D:g} x {ph.RELIEF_DEPTH:g} relief\nclears the I/O cover"),
        ((-18.6, 10.75, -1), "L", 0, "M3 nut pockets (3x)\ntool-module interface"),
        ((0, -8, -6), "R", 0, f"{ph.CENTER_HOLE_D:g} mm pass-through"),
    ], size=21, left_x=0.19, right_x=0.81, top=170)
    b.close()

    d0 = ImageDraw.Draw(img_a)
    d0.text((40, 40), "Arm: UTRA 6-1000 tool flange", font=font(30, True), fill=INK)
    d0.text((40, 84), "Quick Start Guide, page 1", font=font(22), fill=(88, 94, 104))
    d1 = ImageDraw.Draw(img_b)
    d1.text((40, 40), "Tool adapter: arm side", font=font(30, True), fill=INK)
    d1.text((40, 84), "printed, bolts on with 6x M5x12", font=font(22), fill=(88, 94, 104))
    out = Image.new("RGB", (2 * w, size), (251, 252, 253))
    out.paste(img_a, (0, 0))
    out.paste(img_b, (w, 0))
    ImageDraw.Draw(out).line([(w, 60), (w, size - 60)], fill=(200, 205, 212), width=2)
    footer(out)
    out.save(path)


def render_print_layout(path: Path) -> None:
    sc = Scene(1600, 1000)
    sc.add_pv(pv.Cube(center=(0, 0, -0.8), x_length=250, y_length=210, z_length=1.6), "bed")
    placements = {"Pen Holder - Tool Adapter": (-72, 10), "Pen Holder - Module": (22, 10),
                  "Pen Holder - Carriage": (82, 10)}
    material = {"Pen Holder - Carriage": "accent"}
    anchors = []
    for name, (_, printable) in ph.printed_parts().items():
        x, y = placements[name]
        shape = Pos(x, y, 0) * printable
        sc.add(shape, material.get(name, "printed"))
        bb = shape.bounding_box()
        anchors.append(((bb.center().X, bb.min.Y + 3, bb.max.Z * 0.8), name, printable.bounding_box().size))
    sc.camera((5, 0, 20), (0.3, -1.0, 0.62), zoom=1.3)
    img = sc.render()
    notes = []
    for (pt, name, s), side in zip(anchors, ("L", "R", "R")):
        notes.append((pt, side, 0, f"{name.split(' - ')[1]}\n{s.X:.0f} x {s.Y:.0f} x {s.Z:.0f} mm"))
    annotate(img, sc, notes, left_x=0.16, right_x=0.84, top=170)
    title(img, "Print layout", "All three parts print without supports  |  PETG, 0.2 mm layers, 4 perimeters, "
                               "40 % infill")
    footer(img)
    img.save(path)
    sc.close()


VIEWS = {
    1: render_cutaway,
    2: render_exploded,
    3: render_compliance,
    4: render_interface,
    5: render_print_layout,
}


def export_hero_glb(path: Path, travel: float = 3.0, housing: float = 170.0) -> None:
    """Assembly for blender_hero.py: pen pressed `travel` mm into the paper, tall J6 housing stub."""
    items = ph.assembly(travel=travel)
    for it in items:
        if "housing" in it.name:
            it.shape = ph.make_arm_housing(housing)
    asm = ph.labelled_compound(items, "UTRA 6-1000 pen holder (hero)")
    ph.export_gltf(asm, path, binary=True, linear_deflection=0.01, angular_deflection=0.1)
    print(f"wrote {path} (pen tip at z = {ph.Z_TIP + travel:.2f} mm)")


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Render the pen-holder end effector")
    ap.add_argument("views", nargs="*", type=int, default=sorted(VIEWS), help="view numbers to render")
    ap.add_argument("--out", type=Path, default=OUT_DIR)
    ap.add_argument("--hero-glb", type=Path, help="only export the GLB used by blender_hero.py")
    args = ap.parse_args()
    if args.hero_glb:
        export_hero_glb(args.hero_glb)
        return
    args.out.mkdir(parents=True, exist_ok=True)
    for n in args.views:
        path = args.out / f"{PREFIX} {n}.png"
        VIEWS[n](path)
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
