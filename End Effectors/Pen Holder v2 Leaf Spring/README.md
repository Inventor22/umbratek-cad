# Pen Holder v2, leaf-spring version (UTRA 6-1000)

![Leaf-spring pen holder drawing on paper](../../Renders/Pen%20Holder%20v2%20Leaf%20Spring%20Render%200.png)

The [v1 coaxial pen holder](../Pen%20Holder/README.md) with its steel coil spring replaced by a **printed PETG
bow-spring stack**. Everything else works as in v1: the carriage slides in the barrel on two set-screw guide pins,
the nose shoulder is the 15 mm hard stop, and the same tool adapter bolts to the arm. For the version where printed
beams also guide the pen, with no sliding fit, see [Pen Holder v2](../Pen%20Holder%20v2/README.md).

| | |
|---|---|
| Mounting | the v1 tool adapter, unchanged |
| Spring | 12 printed bows in series, threaded on the pen: 41 x 18 mm, 62.5 mm long as printed |
| Compliant travel | 15 mm, then the nose shoulder lands on the barrel |
| Pen force | 1.0 N at first touch, 1.7 N at 3 mm over-reach, 4.5 N at the hard stop (0.23 N/mm, 4.5 mm preload) |
| Leaf stress | 6 MPa at rest, 24 MPa at the hard stop (PETG: ~45 MPa) |
| TCP | X 0, Y 0, Z +189 mm from the flange face (Sharpie Fine Point), 30 mm further out than v1 |
| Size | module Ø53 x 109 mm (v1: Ø32 barrel, 79 mm) |

## Renders

| | |
|---|---|
| ![Cutaway](../../Renders/Pen%20Holder%20v2%20Leaf%20Spring%20Render%201.png) | ![Compliance](../../Renders/Pen%20Holder%20v2%20Leaf%20Spring%20Render%202.png) |
| ![Bow-spring stack](../../Renders/Pen%20Holder%20v2%20Leaf%20Spring%20Render%203.png) | ![Print layout](../../Renders/Pen%20Holder%20v2%20Leaf%20Spring%20Render%204.png) |

## How it works

- **Bow-spring stack** (printed): each bow is two 0.5 mm leaves joined at their ends, like an eye. Pushing its
  crown tabs together flattens the leaves. Twelve bows sit in series, crown tab to crown tab, and every crown tab is
  a ring the pen passes through, so the pen keeps the stack straight.
  - Each half-leaf bends like a fixed-guided beam through half of its bow's squeeze. The full 19.5 mm squeeze is
    shared between twelve bows, 1.6 mm each, which keeps the leaves at about half of PETG's strength.
  - It prints lying flat, so each leaf is a thin vertical wall and its bending stress runs along the extrusion
    lines.
  - The top crown tab sits in a pocket under the module's flange, which keys the stack. The bottom one sits on the
    carriage's piston.
- **Why it is bigger than v1**: at a safe stress, spring steel stores about six times as much energy per cubic
  centimetre as PETG, so the printed spring needs much more room than the Ø20 coil spring it replaces. The leaves
  need about 10 mm of length per side, plus a ring around
  the pen, so the stack is 41 mm wide. The module grows a Ø53 spring housing, as wide as its flange. A 45° cone
  joins it to the v1 guide bore, so the module still prints flange-down without supports.
- **Carriage**: v1's carriage, with the piston 11 mm longer so it reaches up through the cone to the stack, and a flat
  top instead of the coil spring's spigot. The guided length (35 mm at rest), guide pins, travel ticks, pen clamp
  and nose-shoulder hard stop are unchanged.
- The stack never closes up: at the hard stop it still has 0.9 mm of room.

Spring numbers use PETG at E = 2 GPa. Brands vary by about ±20 %, and the force goes with the cube of the leaf
thickness, so measure it (see [Tuning](#tuning)).

## Files

| File | |
|---|---|
| `pen_holder_v2_leaf.py` | Parametric model, 14 design checks, STEP/STL/GLB export. Imports the adapter, hardware and pen from `../Pen Holder/pen_holder.py`. |
| `bow_spring.py` | The bow-spring stack: geometry at any squeeze, rate, stress. Shared with the quick-change leaf version. |
| `render_pen_holder_v2_leaf.py` | Technical renders 1-4 (pyvista/VTK), reusing the v1 renderer |
| `STLs/` | Module, carriage and spring, in print orientation. The adapter is `../Pen Holder/STLs/Pen Holder - Tool Adapter.stl`. |
| `STEP/` | Each part and the full assembly (arm flange included as a reference) |
| `Pen Holder v2 Leaf - Assembly.glb` | Assembly for quick viewing |

## Bill of materials

As [v1](../Pen%20Holder/README.md#bill-of-materials), without the coil spring:

| Qty | Part | Notes |
|---|---|---|
| 1 | Tool adapter | printed, the v1 part |
| 1 | Module | printed |
| 1 | Carriage | printed |
| 1 | Bow-spring stack | printed |
| 6 | M5 x 12 socket head cap screw, ISO 4762 | 3 (every other hole) is plenty for a pen |
| 1 | Ø3 x 8 dowel pin, ISO 8734 | optional |
| 3 | M3 x 14 socket head cap screw, ISO 4762 | module to adapter |
| 4 | M3 hex nut, ISO 4032 | 3 in the adapter, 1 for the pen clamp |
| 2 | M3 x 6 set screw, flat point, ISO 4026 | guide pins |
| 1 | M3 x 10 knurled thumb screw, DIN 464 / DIN 653 | |

## Printing

PETG, 0.2 mm layers, **no supports**. The STLs are in print orientation: module flange down, carriage nose down,
spring lying flat.

- **Spring leaves**: they are 0.5 mm walls, which a 0.4 mm nozzle prints as one extrusion line. Turn on your
  slicer's thin-wall/Arachne option and check in the preview that every leaf is one continuous line from tab to tab.
  Each leaf's bending stress runs along that line.
- Clean any stringing between the bows, then squeeze the stack by hand: every bow should flatten evenly.
- 4 perimeters and 40 % infill for the module and carriage.

## Assembly

As v1, with the stack in place of the coil spring:

1. Press the three M3 nuts and the dowel pin into the adapter, and bolt the module to it with 3x M3 x 14.
2. Push the stack up into the housing from below until its top crown tab drops into the pocket under the flange.
3. Push the carriage in, flat top first, squeezing the stack, until its two side holes line up with the slots. Drive
   the M3 x 6 set screws in until they bottom out. Release: the carriage settles with the pins at the bottom of the
   slots, with the stack squeezed 4.5 mm.
4. Fit the pen clamp (nut and thumb screw), bolt the adapter to the arm, and insert the pen from below through the
   carriage and the stack until its barrel step reaches the nose face (35 mm stick-out).

## Robot setup

- Set the tool TCP to **X 0, Y 0, Z +189 mm** in the flange frame (Z out of the flange). Re-teach the tip after
  re-clamping a pen.
- Command the pen-down height 2 to 5 mm below the paper, about 1.5 to 2.2 N of drawing force.

## Tuning

- **Measuring the force**: point the pen down onto a kitchen scale and lower the arm. The reading where the carriage
  starts to move is the preload. 5 mm lower it should have risen by about 1.1 N.
- **Too light or too heavy**: reprint only the spring with a different leaf thickness `t` (force goes with its cube:
  0.45 mm is about 27 % lighter, 0.55 mm about 33 % heavier) or leaf depth `b` (proportional). The design checks
  recompute the stress.

## Regenerating

```
uv run pen_holder_v2_leaf.py                  # design report + STEP / STL / GLB
uv run render_pen_holder_v2_leaf.py           # renders 1-4 into ../../Renders
uv run render_pen_holder_v2_leaf.py --hero-glb hero.glb
blender --background --factory-startup --python "../Pen Holder/blender_hero.py" -- hero.glb "../../Renders/Pen Holder v2 Leaf Spring Render 0.png"
```
