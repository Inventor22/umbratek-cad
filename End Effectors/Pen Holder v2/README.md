# Pen Holder v2: printed flexure spring (UTRA 6-1000)

![Pen holder v2 drawing on paper](../../Renders/Pen%20Holder%20v2%20Render%200.png)

Version 2 of the [coaxial pen holder](../Pen%20Holder/README.md). The pen still sits on the flange axis with 15 mm
of compliant over-travel, but the **coil spring, sliding carriage and guide pins are replaced by one printed PETG
part**: a folded-beam flexure. Four thin beams hold the pen carriage on a straight line and provide the spring
force, so there is no friction, no sliding clearance and no spring to buy. The module is **70 mm wide**, narrower
than the Ø86 flange.

For the perpendicular quick-change holder with the same kind of flexure, see
[Quick-Change Pen Holder v2](../Quick-Change%20Pen%20Holder%20v2/README.md).

| | |
|---|---|
| Mounting | the v1 tool adapter, unchanged (6x M5 on PCD 64, Ø73 h7 pilot, Ø3 dowel) |
| Compliant travel | 15 mm, then a printed hard stop |
| Pen force | 1.1 N at first touch, 1.8 N at 3 mm over-reach, 4.5 N at the hard stop (0.22 N/mm, 5 mm preload) |
| Beam stress | 6 MPa at rest, 10 MPa while drawing, 24 MPa at the hard stop (PETG: ~45 MPa) |
| TCP | X 0, Y 0, Z +159 mm from the flange face (Sharpie Fine Point), the same as v1 |
| Size, mass | flexure module 70 x 43 x 117 mm; about 170 g including the adapter, hardware and pen |

## Renders

| | |
|---|---|
| ![Overview](../../Renders/Pen%20Holder%20v2%20Render%201.png) | ![Section](../../Renders/Pen%20Holder%20v2%20Render%202.png) |
| ![Compliance](../../Renders/Pen%20Holder%20v2%20Render%203.png) | ![Exploded view](../../Renders/Pen%20Holder%20v2%20Render%204.png) |
| ![Print layout](../../Renders/Pen%20Holder%20v2%20Render%205.png) | |

## How it works

- **Flexure module** (printed, one part): a 20 mm plate behind the pen holds a frame, the carriage and four
  45 x 0.8 x 20 mm beams. A pen block on the carriage stands in front of the plate and clamps the pen.
  - The beams span the plate. Two of them (the carriage parallelogram) run from the carriage member, on the right
    as seen from the front, across to an intermediate bar on the far side. Two more (the ground parallelogram) run
    from that bar back to a ground anchor under the carriage member. This is a folded double parallelogram, a
    standard compliant linear guide.
  - The carriage can only move along the pen. The bar moves half as far, so each beam bends through only half the
    travel. As the beams bend they draw their ends together slightly, and the bar slides inward to absorb it. The
    beams never stretch, so the force rises linearly.
  - Sideways the beams are stiff: a 1 N drag at the pen tip moves it about 0.2 mm towards or away from the plate,
    and under 0.1 mm along it, with no play at all (v1's sliding fit had 0.4 mm of clearance).
- **Why it is this size**: each beam has to be about 45 mm long to bend through 10 mm while staying at half of
  PETG's strength. The beams cross behind the pen, so the module is one beam length wide instead of two.
- **Preload stop screw** (M3 x 40): the module is printed with the beams straight. The stop screw runs up through
  the ground anchor; screwed home, it lifts the carriage member 5 mm, so the carriage rests on its tip with 1.1 N of
  preload. The rest position, and so the TCP, is set by where the head seats, not by how tightly it is turned.
- **Hard stop**: after 15 mm the carriage member lands on the frame's top bar. The beams are then at about half of
  PETG's strength, with 2 mm still to spare.
- **Relief that follows the beams**: the top bar's underside follows the upper beam's bent shape at full travel,
  and the carriage body's top slopes the same way, so nothing rubs.
- **Pen clamp**: an M3 thumb screw from the front, into a captive nut slid in from the pen block's bottom face.
  The pen runs in front of the plate, clear of the frame.
- **Mount**: two M3 x 14 screws go in from the arm side of the adapter, with their heads in two of the adapter's
  nut pockets, and thread into the module. The plate covers the two M5 holes on -Y, so four of the six M5 screws are
  used, which is plenty for a pen.

Flexure numbers use PETG at E = 2 GPa. PETG brands vary by about ±20 %, and the force goes with the cube of the
beam thickness, so expect the real force to differ from the numbers above. Check it with a kitchen scale (see
[Tuning](#tuning)).

## Files

| File | |
|---|---|
| `pen_holder_v2.py` | Parametric model, 20 design checks, STEP/STL/GLB export. Imports the flange interface, adapter and hardware from `../Pen Holder/pen_holder.py`. |
| `flexure.py` | The cross-span flexure: geometry at any travel, rate, stress, stiffness. Shared with Quick-Change v2. |
| `render_pen_holder_v2.py` | Technical renders 1-5 (pyvista/VTK), reusing the v1 renderer |
| `STLs/` | The flexure module, in print orientation. The adapter is `../Pen Holder/STLs/Pen Holder - Tool Adapter.stl`. |
| `STEP/` | The module and the full assembly (arm flange included as a reference) |
| `Pen Holder v2 - Assembly.glb` | Assembly for quick viewing |

## Bill of materials

| Qty | Part | Notes |
|---|---|---|
| 1 | Tool adapter | printed, the v1 part (`../Pen Holder/STLs`) |
| 1 | Flexure module | printed |
| 4 | M5 x 12 socket head cap screw, ISO 4762 | the four the plate doesn't cover |
| 1 | Ø3 x 8 dowel pin, ISO 8734 | optional, fixes the tool orientation |
| 2 | M3 x 14 socket head cap screw, ISO 4762 | module to adapter, from the arm side |
| 1 | M3 x 40 socket head cap screw, ISO 4762 | preload stop screw |
| 1 | M3 hex nut, ISO 4032 | pen clamp |
| 1 | M3 x 10 knurled thumb screw, DIN 464 / DIN 653 | an M3 x 10 cap screw also works |

No springs, rods, bushings or set screws.

## Printing

PETG, 0.2 mm layers, **no supports**. The STL lies on its back (the plate) and is 43 mm tall, already in print
orientation.

- **Beams**: they are 0.8 mm walls, which slicers print as two 0.4 mm perimeters with nothing between them. Check
  in the preview that every beam is two continuous lines from end to end, with no gap fill or infill.
- Each beam's bending stress runs along its extrusion lines, PETG's strong direction. The layer lines only cross
  the beams' depth, which carries almost no stress.
- 4 perimeters and 40 % infill for the rest. A brim isn't needed: the beams are held at both ends.
- Clean any stringing between the beams and the frame, then push the carriage up and down by hand. It should move
  smoothly, with nothing rubbing.

## Assembly

1. Press the dowel pin into the adapter (4.5 mm proud on the arm side), if used.
2. Bolt the module to the adapter: two M3 x 14 from the arm side, through the nut pockets at 30° and 150°. They
   thread into the module's mount block.
3. Bolt the adapter to the arm with the four M5 x 12 screws the plate doesn't cover. Snug only, about 2 N·m in
   plastic.
4. Screw the M3 x 40 stop screw up into the bottom of the frame, under the carriage member, until its head seats.
   The last 5 mm lift the carriage off its printed position and preload the beams.
5. Slide an M3 nut into the slot in the pen block's bottom face and thread in the thumb screw.
6. Push the pen up through the pen block until its tip is 30 mm below the frame's bottom face, then tighten the
   thumb screw.

## Robot setup

- Set the tool TCP to **X 0, Y 0, Z +159 mm** in the flange frame (Z out of the flange, X towards the dowel).
  Re-teach the tip after re-clamping a pen.
- Command the pen-down height 2 to 5 mm below the paper, giving about 1.6 to 2.2 N of drawing force. Keep
  over-reach well under the 15 mm hard stop.
- Payload: about 0.17 kg, centre of mass about 42 mm out from the flange face.
- The preload holds the carriage on its stop in any orientation: the moving parts weigh about 0.3 N.

## Tuning

- **Measuring the force**: point the pen down onto a kitchen scale and lower the arm. The reading where the carriage
  starts to move is the preload. 5 mm lower it should have risen by about 1.1 N.
- **Too light or too heavy**: change `BEAM_T` (force goes with its cube: 0.75 mm is about 18 % lighter, 0.85 mm
  about 20 % heavier) or `BEAM_B` (proportional), and reprint the module.
- **Lighter first touch**: put washers under the stop-screw head. Each 0.5 mm of washer lowers the preload by
  about 0.11 N and moves the pen tip 0.5 mm further out, so re-teach the TCP.
- **Creep**: PETG relaxes a little under constant load, so the preload may fall by 10-20 % over the first weeks.
  The TCP and travel don't change, because the stop screw and hard stop set them.

## Changing the design

Every dimension is a named parameter at the top of `pen_holder_v2.py`:

| Parameter | Controls |
|---|---|
| `STROKE`, `PRELOAD` | compliant travel, and how far the stop screw lifts the carriage |
| `BEAM_L`, `BEAM_T`, `BEAM_B` | beam length, thickness and depth: stiffness and stress |
| `H_CARRIAGE`, `H_GROUND` | spacing of each parallelogram's beams: how stiffly the pen resists tilting |
| `TIP_BELOW_FRAME` | pen stick-out below the frame, which sets the TCP |

The script runs its design checks on every export and stops with an error if a change overstresses the beams,
makes parts collide or breaks an assembly rule.

## Regenerating

```
uv run pen_holder_v2.py                  # design report + STEP / STL / GLB
uv run render_pen_holder_v2.py           # renders 1-5 into ../../Renders
uv run render_pen_holder_v2.py --hero-glb hero.glb
blender --background --factory-startup --python "../Pen Holder/blender_hero.py" -- hero.glb "../../Renders/Pen Holder v2 Render 0.png"
```
