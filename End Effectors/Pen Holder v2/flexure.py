"""
Printed cross-span flexure (PETG), shared by the v2 pen holders.

The stage is a 2.5D profile in the XZ plane, extruded along Y and printed flat, so every beam is a thin vertical
wall: it bends in the plane of the print and its bending stress runs along the extrusion lines, PETG's strong
direction. Motion is along +Z.

One folded double parallelogram spans the whole width of the stage:

    carriage member --P2: 2 levels of beams--> intermediate bar (far end)
    ground anchor   --P1: 2 levels of beams--> intermediate bar

The carriage member and the ground anchor sit at the same end, one above the other, so both parallelograms have the
same beam length. The carriage moves d, the bar d/2, so each beam bends through only d/2. Both parallelograms shorten
equally as they bend, so the bar slides inward and the carriage stays on its line without the beams stretching: the
force rises linearly. Because the beams span the stage instead of sitting on both sides of the carriage, the stage is
one beam length wide rather than two. Each level is one deep beam or a pair of thinner-depth twin beams.

The stage is printed in its relaxed ("neutral") position. A stop screw then lifts the carriage PRELOAD mm, so it
rests on it with a defined force and position; over-travel lifts it off the screw until it hits a printed hard stop.
Motion is therefore always one way (+Z) from the printed position, which sets the gaps (`rise_*` give the shapes).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from build123d import Box, Face, Part, Pos, Wire, extrude

# PETG, printed (typical datasheet values; brands vary by about +-20 %)
PETG_E = 2000.0  # MPa, along the extrusion lines
PETG_STRENGTH = 45.0  # MPa, along the extrusion lines
PETG_DENSITY = 1.27e-3  # g/mm³


def box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Part:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))


def prism_xz(pts: list[tuple[float, float]], y0: float, y1: float) -> Part:
    """Closed (x, z) polygon extruded along +Y from y0 to y1."""
    face = Face(Wire.make_polygon([(x, y0, z) for x, z in pts], close=True))
    return extrude(face, y1 - y0, dir=(0, 1, 0))


def s_curve(xi: float) -> float:
    """Deflected shape of a fixed-guided beam (0 at the root, 1 at the guided end, flat at both)."""
    return xi * xi * (3 - 2 * xi)


@dataclass
class CrossDP:
    x_root: float  # x of the beam roots: the carriage member's and the ground anchor's inner face
    beam_len: float  # free length of every beam
    t: float  # beam thickness (in the plane, along the motion)
    b: float  # beam depth (extrusion, Y)
    y0: float  # beams extrude from y0 to y0 + b
    z_p2: tuple[float, float]  # carriage <-> bar: centres of the upper and lower twin pairs
    z_p1: tuple[float, float]  # ground <-> bar: centres of the upper and lower twin pairs
    travel: float  # preload + stroke: the largest lift above the printed position
    direction: int = 1  # the beams run from the root towards +x (1) or -x (-1)
    twin_gap: float = 2.0  # gap between the two beams of a pair
    bar_w: float = 6.0
    bar_ext: float = 2.0  # bar reaches this far past the outermost beams

    # ---------------------------------------------------------------- layout
    @property
    def n_twin(self) -> int:
        """Beams per level: 2 (twin pair) or 1 (twin_gap <= 0)."""
        return 2 if self.twin_gap > 0 else 1

    @property
    def pitch(self) -> float:
        return self.t + self.twin_gap if self.n_twin == 2 else 0.0

    def twins(self, zc: float) -> tuple[float, ...]:
        return (zc + self.pitch / 2, zc - self.pitch / 2) if self.n_twin == 2 else (zc,)

    @property
    def x_bar(self) -> float:
        """x of the bar's inner face (printed position)."""
        return self.x_root + self.direction * self.beam_len

    @property
    def x_far(self) -> float:
        """x of the bar's outer face (printed position)."""
        return self.x_bar + self.direction * self.bar_w

    def xi(self, x: float) -> float:
        return (x - self.x_root) * self.direction / self.beam_len

    def rise_p2(self, x: float, lift: float | None = None) -> float:
        """How far a carriage (P2) beam has risen at x."""
        d = self.travel if lift is None else lift
        return d - d / 2 * s_curve(self.xi(x))

    def rise_p1(self, x: float, lift: float | None = None) -> float:
        """How far a ground (P1) beam has risen at x."""
        d = self.travel if lift is None else lift
        return d / 2 * s_curve(self.xi(x))

    # ---------------------------------------------------------------- mechanics
    @property
    def k_beam(self) -> float:
        """Fixed-guided beam, N/mm."""
        return PETG_E * self.b * self.t**3 / self.beam_len**3

    @property
    def rate(self) -> float:
        """Stage rate, N/mm: 2 x n_twin beams per parallelogram, two parallelograms in series."""
        return self.n_twin * self.k_beam

    def stress(self, lift: float) -> float:
        """Peak bending stress (MPa) with the carriage `lift` mm above its printed position."""
        return 3 * PETG_E * self.t * (lift / 2) / self.beam_len**2

    def shortening(self, lift: float) -> float:
        """How far each beam's ends draw together (the bar slides inward this much)."""
        return 0.6 * (lift / 2) ** 2 / self.beam_len

    @property
    def k_y_beam(self) -> float:
        return PETG_E * self.t * self.b**3 / self.beam_len**3

    @property
    def k_out_of_plane(self) -> float:
        """Stage stiffness along Y (N/mm)."""
        return self.n_twin * self.k_y_beam

    @property
    def k_tilt(self) -> float:
        """Stage stiffness against tilting about X (N·mm/rad): beams bending out of plane, torsion ignored."""
        h2 = self.z_p2[0] - self.z_p2[1]
        h1 = self.z_p1[0] - self.z_p1[1]
        k2, k1 = (self.n_twin * self.k_y_beam * h**2 / 2 for h in (h2, h1))
        return k1 * k2 / (k1 + k2)

    def k_turn(self, lever: float) -> float:
        """In-plane stiffness (N/mm) at `lever` mm from the beam roots, from the beams' axial stiffness."""
        k_ax = PETG_E * self.t * self.b / self.beam_len
        h2 = self.z_p2[0] - self.z_p2[1]
        h1 = self.z_p1[0] - self.z_p1[1]
        k2, k1 = (self.n_twin * k_ax * h**2 / 2 for h in (h2, h1))
        return k1 * k2 / (k1 + k2) / lever**2

    # ---------------------------------------------------------------- geometry
    def _beam(self, x0: float, x1: float, z: float, w0: float, w1: float, n: int = 24) -> Part:
        """Beam centreline from (x0, z + w0) to (x1, z + w1), S-shaped, flat at both ends."""
        t2, ext = self.t / 2, 0.4
        if abs(w1 - w0) < 1e-9:
            lo, hi = sorted((x0, x1))
            return box(lo - ext, hi + ext, self.y0, self.y0 + self.b, z + w0 - t2, z + w0 + t2)
        top, bot = [], []
        sgn = 1 if x1 > x0 else -1
        for i in range(n + 1):
            xi = i / n
            x = x0 + (x1 - x0) * xi
            w = w0 + (w1 - w0) * s_curve(xi)
            th = math.atan((w1 - w0) * 6 * xi * (1 - xi) / (x1 - x0))
            dx, dz = -math.sin(th) * t2, math.cos(th) * t2
            if i == 0:
                x -= sgn * ext
            if i == n:
                x += sgn * ext
            top.append((x + dx, z + w + dz))
            bot.append((x - dx, z + w - dz))
        return prism_xz(top + bot[::-1], self.y0, self.y0 + self.b)

    def beams(self, lift: float = 0.0) -> list[Part]:
        """All eight beams with the carriage `lift` mm above its printed position."""
        xb = self.x_root + self.direction * (self.beam_len - self.shortening(lift))
        out = []
        for zc in self.z_p2:
            out += [self._beam(self.x_root, xb, z, lift, lift / 2) for z in self.twins(zc)]
        for zc in self.z_p1:
            out += [self._beam(self.x_root, xb, z, 0.0, lift / 2) for z in self.twins(zc)]
        return out

    def bar_z(self, lift: float = 0.0) -> tuple[float, float]:
        zs = [*self.z_p2, *self.z_p1]
        reach = self.pitch / 2 + self.t / 2 + self.bar_ext
        return min(zs) - reach + lift / 2, max(zs) + reach + lift / 2

    def bar(self, lift: float = 0.0) -> Part:
        """The intermediate bar: it rises lift/2 and slides inward as the beams shorten."""
        sh = self.direction * self.shortening(lift)
        x0, x1 = sorted((self.x_bar - sh, self.x_far - sh))
        return box(x0, x1, self.y0, self.y0 + self.b, *self.bar_z(lift))

    def report(self, preload: float, stroke: float, drawing: float = 3.0) -> list[str]:
        r = self.rate
        return [
            f"  Flexure: {4 * self.n_twin} printed beams {self.beam_len:g} x {self.t:g} x {self.b:g} mm, rate {r:.3f} N/mm"
            f" (PETG, E = {PETG_E / 1000:g} GPa)",
            f"  Pen force: {r * preload:.2f} N at first touch, {r * (preload + drawing):.2f} N at {drawing:g} mm"
            f" over-reach, {r * (preload + stroke):.2f} N at the {stroke:g} mm hard stop",
            f"  Beam stress: {self.stress(preload):.1f} MPa at rest, {self.stress(preload + drawing):.1f} MPa"
            f" drawing, {self.stress(preload + stroke):.1f} MPa at the hard stop (PETG ~{PETG_STRENGTH:g} MPa)",
        ]
