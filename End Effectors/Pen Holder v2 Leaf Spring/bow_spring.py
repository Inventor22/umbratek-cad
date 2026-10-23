"""
Printed bow-spring stack (PETG), shared by the leaf-spring pen holders.

A bow is two leaves joined at their ends, like an eye: pushing its two crown tabs together flattens the leaves. A
stack of bows in series, crown tab to crown tab, makes a printable spring that replaces a steel coil spring:

        crown tab ═══╗                    ╔═══ crown tab
                      ╲__ leaf     leaf __╱
       joint tab ▬▬▬▬▬     (one bow)       ▬▬▬▬▬ joint tab
                      ╱‾‾ leaf     leaf ‾‾╲
        crown tab ═══╝                    ╚═══ crown tab   (shared with the next bow)

Each half-leaf bends like a fixed-guided beam through half of its bow's compression, so the stack is n bows tall
for n times the travel of one bow. The stack is a 2.5D profile (axis Z, width X) extruded along Y and printed lying
flat: every leaf is a thin vertical wall whose bending stress runs along the extrusion lines, PETG's strong
direction. Holes through the crown tabs (for a pen) or the joint tabs (for guide rods) run along the axis, so the
part the stack is threaded on keeps it straight.

Local frame: axis Z, the bottom crown tab's bottom face at z = 0, crown holes on the Z axis, tabs from y = -depth/2.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from build123d import Box, Cylinder, Face, Part, Pos, Wire, extrude

PETG_E = 2000.0  # MPa, along the extrusion lines (brands vary by about +-20 %)
PETG_STRENGTH = 45.0  # MPa, along the extrusion lines


def _box(x0: float, x1: float, y0: float, y1: float, z0: float, z1: float) -> Part:
    return Pos((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2) * Box(abs(x1 - x0), abs(y1 - y0), abs(z1 - z0))


def _s(xi: float) -> float:
    return xi * xi * (3 - 2 * xi)


@dataclass
class BowStack:
    n: int  # bows in series
    leaf_len: float  # free length of each half-leaf, crown tab to joint tab
    t: float  # leaf thickness
    b: float  # leaf depth (print height); the leaves and joint tabs start at the bed with the crown tabs
    crown_w: float  # crown tab width (X)
    joint_w: float  # joint tab width (X)
    tab_t: float  # tab thickness along the axis
    depth: float  # crown tab depth (Y)
    pitch: float  # crown-to-crown spacing as printed
    crown_hole: float = 0.0  # hole through every crown tab, on the axis (0 = none)
    joint_hole: float = 0.0  # hole through every joint tab, at its centre (0 = none)

    # ---------------------------------------------------------------- mechanics
    @property
    def k_half(self) -> float:
        """One half-leaf as a fixed-guided beam, N/mm."""
        return PETG_E * self.b * self.t**3 / self.leaf_len**3

    @property
    def rate(self) -> float:
        """N/mm: per bow, 2 half-leaves in parallel above and 2 below, in series; n bows in series."""
        return self.k_half / self.n

    def stress(self, squeeze: float) -> float:
        """Peak leaf stress (MPa) with the stack squeezed `squeeze` mm shorter than printed."""
        return 3 * PETG_E * self.t * (squeeze / self.n / 2) / self.leaf_len**2

    @property
    def free_len(self) -> float:
        return self.n * self.pitch + self.tab_t

    @property
    def max_squeeze(self) -> float:
        """Squeeze at which neighbouring tabs would touch (0.8 mm left)."""
        return self.n * (self.pitch - self.tab_t - 0.8)

    @property
    def width(self) -> float:
        return self.crown_w + 2 * (self.leaf_len + self.joint_w)

    @property
    def x_joint(self) -> float:
        """|x| of the joint tabs' centres."""
        return self.crown_w / 2 + self.leaf_len + self.joint_w / 2

    def crown_z(self, squeeze: float = 0.0) -> list[float]:
        p = self.pitch - squeeze / self.n
        return [self.tab_t / 2 + i * p for i in range(self.n + 1)]

    def length(self, squeeze: float = 0.0) -> float:
        return self.free_len - squeeze

    # ---------------------------------------------------------------- geometry
    def _leaf(self, x0: float, z0: float, x1: float, z1: float, y0: float, n: int = 16) -> Part:
        """S-shaped leaf of thickness t from (x0, z0) to (x1, z1), flat at both ends, extruded from y0 by b."""
        t2, ext = self.t / 2, 0.3
        top, bot = [], []
        sgn = 1 if x1 > x0 else -1
        for i in range(n + 1):
            xi = i / n
            x = x0 + (x1 - x0) * xi
            z = z0 + (z1 - z0) * _s(xi)
            th = math.atan((z1 - z0) * 6 * xi * (1 - xi) / (x1 - x0))
            dx, dz = -math.sin(th) * t2, math.cos(th) * t2
            if i == 0:
                x -= sgn * ext
            if i == n:
                x += sgn * ext
            top.append((x + dx, z + dz))
            bot.append((x - dx, z - dz))
        face = Face(Wire.make_polygon([(x, y0, z) for x, z in top + bot[::-1]], close=True))
        return extrude(face, self.b, dir=(0, 1, 0))

    def shape(self, squeeze: float = 0.0) -> Part:
        """The stack squeezed `squeeze` mm shorter than printed (bottom crown fixed)."""
        y0 = -self.depth / 2
        cz = self.crown_z(squeeze)
        h, t2 = self.tab_t / 2, self.t / 2
        x_in, x_out = self.crown_w / 2, self.crown_w / 2 + self.leaf_len
        parts = []
        for z in cz:
            crown = _box(-x_in, x_in, y0, y0 + self.depth, z - h, z + h)
            if self.crown_hole:
                crown -= Pos(0, 0, z) * Cylinder(self.crown_hole / 2, self.tab_t + 2)
            parts.append(crown)
        for j in range(self.n):
            zj = (cz[j] + cz[j + 1]) / 2
            for s in (-1, 1):
                joint = _box(s * x_out, s * (x_out + self.joint_w), y0, y0 + self.b, zj - h, zj + h)
                if self.joint_hole:
                    joint -= Pos(s * self.x_joint, y0 + self.b / 2, zj) * Cylinder(self.joint_hole / 2, self.tab_t + 2)
                parts.append(joint)
                # lower leaf: from the lower crown's top face up to the joint's bottom face; upper leaf mirrored
                parts.append(self._leaf(s * x_in, cz[j] + h - t2, s * x_out, zj - h + t2, y0))
                parts.append(self._leaf(s * x_in, cz[j + 1] - h + t2, s * x_out, zj + h - t2, y0))
        return parts[0].fuse(*parts[1:]).clean()

    def report(self, preload: float, stroke: float) -> list[str]:
        r = self.rate
        return [
            f"  Bow stack: {self.n} bows, half-leaves {self.leaf_len:g} x {self.t:g} x {self.b:g} mm, "
            f"{self.width:.0f} mm wide, {self.free_len:.1f} mm long as printed, rate {r:.3f} N/mm",
            f"  Pen force: {r * preload:.2f} N at first touch, {r * (preload + 3):.2f} N at 3 mm over-reach, "
            f"{r * (preload + stroke):.2f} N at the {stroke:g} mm hard stop",
            f"  Leaf stress: {self.stress(preload):.1f} MPa at rest, {self.stress(preload + stroke):.1f} MPa at the "
            f"hard stop (PETG ~{PETG_STRENGTH:g} MPa)",
        ]
