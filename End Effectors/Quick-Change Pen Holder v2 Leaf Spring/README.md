# Quick-Change Pen Holder v2, leaf-spring version (UTRA 6-1000)

![Leaf-spring quick-change pen holder drawing on paper](../../Renders/Quick-Change%20Pen%20Holder%20v2%20Leaf%20Spring%20Render%200.png)

The [v1 quick-change pen holder](../Quick-Change%20Pen%20Holder/README.md) with its two steel coil springs replaced
by a **printed PETG bow-spring stack** threaded on the two guide rods. Everything else works as in v1: the carriage
slides on the rods, the cartridges, rings, jaws and stick-out gauge are the v1 parts, and **the pen tip is exactly
where v1 puts it**. For the version where printed beams also guide the carriage, with no rods, see
[Quick-Change Pen Holder v2](../Quick-Change%20Pen%20Holder%20v2/README.md).

| | |
|---|---|
| Mounting | as v1: 6x M5 on PCD 64, Ø73 h7 pilot, Ø3 dowel |
| Pens | v1 cartridges, rings, jaws and stick-out gauge, unchanged |
| Spring | 8 printed bows in series, threaded on the rods: 49 x 13 mm, 43 mm long as printed |
| Compliant travel | 15 mm along the pen, then the stack closes up (the hard stop) |
| Pen force | 1.1 N at first touch, 1.8 N at 3 mm over-reach, 4.3 N at the hard stop (0.21 N/mm, 5.5 mm preload) |
| Leaf stress | 7 MPa at rest, 25 MPa at the hard stop (PETG: ~45 MPa) |
| TCP | X -95, Y 0, Z +56 mm in the flange frame, the same as v1 |
| Stage | 51 mm wide with Ø6 x 100 rods at ±19.5 mm (v1: 43 mm wide, Ø6 x 80 rods at ±12 mm) |

## Renders

| | |
|---|---|
| ![Overview](../../Renders/Quick-Change%20Pen%20Holder%20v2%20Leaf%20Spring%20Render%201.png) | ![Compliance](../../Renders/Quick-Change%20Pen%20Holder%20v2%20Leaf%20Spring%20Render%202.png) |
| ![Bow-spring stack](../../Renders/Quick-Change%20Pen%20Holder%20v2%20Leaf%20Spring%20Render%203.png) | ![Print layout](../../Renders/Quick-Change%20Pen%20Holder%20v2%20Leaf%20Spring%20Render%204.png) |

## How it works

- **Bow-spring stack** (printed): each bow is two 0.5 mm leaves joined at their ends, like an eye. Eight bows sit
  in series, crown tab to crown tab. The tabs where each bow's leaves meet carry holes for the two rods, so the rods
  keep the stack straight. The bottom crown tab sits in a pocket on the carriage, the top one in a pocket under the
  cap.
  - Each half-leaf bends like a fixed-guided beam through half of its bow's squeeze. The 20.5 mm squeeze is
    shared between eight bows, 2.6 mm each, which keeps the leaves at about half of PETG's strength.
  - It prints lying flat, so each leaf is a thin vertical wall and its bending stress runs along the extrusion
    lines.
- **Hard stop**: after 15 mm of travel every tab touches its neighbour and the stack closes up, so the leaves are
  never bent further.
- **Rods moved out**: a PETG leaf needs about 12.5 mm of length per side for this travel, so the rods move from
  ±12 mm to ±19.5 mm and the stage grows from 43 to 51 mm wide. The carriage, bottom block and cap grow with them.
- **Separate top cap**: the top block is no longer printed with the base. It is a separate cap that slides onto the
  rods and is clamped by two M3 set screws. Without side walls, the base prints upright without supports and every
  M5 screw stays reachable. The base's bottom block is the rest stop, as in v1, and also clamps the rods.

With the pen pointing down, the weight of the carriage, cartridge and pen (about 0.9 N) adds to every force above.
Spring numbers use PETG at E = 2 GPa. Brands vary by about ±20 %, and the force goes with the cube of the leaf
thickness, so measure it (see [Tuning](#tuning)).

## Files

| File | |
|---|---|
| `quick_change_v2_leaf.py` | Parametric model, 15 design checks, STEP/STL/GLB export. Imports the cartridge from `../Quick-Change Pen Holder` and the flange interface from `../Pen Holder`. |
| `render_quick_change_v2_leaf.py` | Technical renders 1-4 (pyvista/VTK) |
| `../Pen Holder v2 Leaf Spring/bow_spring.py` | The bow-spring stack (shared with the coaxial leaf version) |
| `STLs/` | Base, carriage, cap and spring, in print orientation |
| `STEP/` | Each part and the full assembly (arm flange included as a reference) |
| `Quick-Change v2 Leaf - Assembly.glb` | Assembly for quick viewing |

Print the cartridge, twist rings, jaws and stick-out gauge from `../Quick-Change Pen Holder/STLs`.

## Bill of materials

| Qty | Part | Notes |
|---|---|---|
| 1 | Base | printed, upright on its foot |
| 1 | Carriage | printed |
| 1 | Top cap | printed |
| 1 | Bow-spring stack | printed |
| 1 per pen | Cartridge, 2 twist rings, 6 jaws | printed, the v1 parts |
| 1 | Stick-out gauge | printed, the v1 part |
| 2 | Ø6 x 100 mm steel rod | h6 linear shaft or ISO 8734 dowel pins |
| 4 | M3 x 3 set screw, ISO 4026 | lock the rods in the base and the cap |
| 1 | M6 ball spring plunger, 14 mm long, Ø3.5 ball | as v1 |
| 6 | M5 x 12 socket head cap screw, ISO 4762 | 3 (every other hole) is enough |
| 1 | Ø3 x 8 dowel pin, ISO 8734 | optional |

No coil springs.

## Printing

PETG, 0.2 mm layers, **no supports**. The STLs are in print orientation: base upright on its foot, carriage on its
bottom face, cap upside down, spring lying flat.

- **Spring leaves**: they are 0.5 mm walls, which a 0.4 mm nozzle prints as one extrusion line. Turn on your
  slicer's thin-wall/Arachne option and check in the preview that every leaf is one continuous line from tab to tab.
- Clean any stringing between the bows, then squeeze the stack by hand: every bow should flatten evenly.
- If the carriage binds on the rods, ream its bushings to 6.05-6.1 mm, as in v1.

## Assembly

1. Press the dowel into the base and bolt the base to the arm (6x M5 x 12, snug, about 2 N·m in plastic). Every
   screw is reachable now; later the cap covers the top one.
2. Screw the ball plunger into the carriage from behind until its face stands about 0.6 mm proud of the rail, as in
   v1.
3. Push the two rods into the bottom block and lock them with two set screws. Slide on the carriage until it rests
   on the bottom block, then the stack, through its joint tabs, with its bottom crown tab in the carriage's pocket.
4. Slide the cap onto the rods, squeezing the stack, until its top is flush with the rod ends. Lock it with its two
   set screws: the stack is now squeezed 5.5 mm.
5. Load pens into cartridges with the stick-out gauge and slide a cartridge up onto the rail until it clicks, as in
   v1.

To take the base off the arm, remove the cap and the stack first.

## Robot setup

As v1: the pen tip is at **X -95, Y 0, Z +56 mm** in the flange frame (Z out of the flange, X towards the dowel).
Command the pen-down height 2 to 5 mm below the paper: about 1.6 to 2.2 N from the spring, plus the moving parts'
0.9 N when the pen points down.

## Tuning

- **Measuring the force**: point the pen down onto a kitchen scale and lower the arm. The reading where the carriage
  starts to move is the preload plus the moving parts' weight, about 2 N. 5 mm lower it should have risen by about
  1 N.
- **Too light or too heavy**: reprint only the spring with a different leaf thickness `t` (force goes with its cube)
  or leaf depth `b` (proportional, up to the 13 mm stage depth). The design checks recompute the stress.

## Regenerating

```
uv run quick_change_v2_leaf.py              # design report + STEP / STL / GLB
uv run render_quick_change_v2_leaf.py       # renders 1-4 into ../../Renders
uv run render_quick_change_v2_leaf.py --hero-glb hero.glb
blender --background --factory-startup --python "../Quick-Change Pen Holder/blender_hero_quick_change.py" -- hero.glb "../../Renders/Quick-Change Pen Holder v2 Leaf Spring Render 0.png"
```
