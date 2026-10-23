# Quick-Change Pen Holder v2: printed flexure stage (UTRA 6-1000)

![Quick-change pen holder v2 drawing on paper](../../Renders/Quick-Change%20Pen%20Holder%20v2%20Render%200.png)

Version 2 of the [quick-change pen holder](../Quick-Change%20Pen%20Holder/README.md). The pen still sits
perpendicular to the flange, in the same tool-free cartridges with two twist chucks, with 15 mm of compliant travel
along the pen. What changed is the stage the cartridges ride on: **v1's steel rods, sliding carriage and two coil
springs are replaced by one printed PETG part**, a folded-beam flexure. Thin beams guide the carriage on a straight
line and provide the spring force, with no sliding friction or play. The stage is **71 mm wide**, narrower than
the Ø86 flange.

For the coaxial holder with the same kind of flexure, see [Pen Holder v2](../Pen%20Holder%20v2/README.md).

| | |
|---|---|
| Mounting | the v1 tool adapter from [Pen Holder](../Pen%20Holder/README.md), unchanged (6x M5 on PCD 64, Ø73 h7 pilot, Ø3 dowel) |
| Pens | v1 cartridges, rings, jaws and stick-out gauge, unchanged: any pen from 6 to 17 mm, swapped without tools |
| Compliant travel | 15 mm along the pen, then a printed hard stop |
| Pen force | 1.2 N at first touch, 1.9 N at 3 mm over-reach, 4.6 N at the hard stop (0.23 N/mm, 5 mm preload) |
| Beam stress | 6 MPa at rest, 9 MPa while drawing, 23 MPa at the hard stop (PETG: ~45 MPa) |
| TCP | 56 mm out from the flange face, 116 mm off the flange axis (opposite the dowel pin), for every pen |
| Size, mass | stage 71 x 17 x 137 mm; about 190 g including the adapter, hardware and an 11 mm gel pen |

## Renders

| | |
|---|---|
| ![Overview](../../Renders/Quick-Change%20Pen%20Holder%20v2%20Render%201.png) | ![Flexure stage](../../Renders/Quick-Change%20Pen%20Holder%20v2%20Render%202.png) |
| ![Compliance](../../Renders/Quick-Change%20Pen%20Holder%20v2%20Render%203.png) | ![Exploded view](../../Renders/Quick-Change%20Pen%20Holder%20v2%20Render%204.png) |
| ![Print layout](../../Renders/Quick-Change%20Pen%20Holder%20v2%20Render%205.png) | |

## How it works

- **Flexure stage** (printed, one part): a frame, the carriage and eight 46 x 0.8 x 11 mm beams in four pairs.
  - The beams span the stage. The two lower pairs (the carriage parallelogram) run from the carriage member, on the
    left as seen from the front, across to an intermediate bar on the right. The two upper pairs (the ground
    parallelogram) run from that bar back to a ground anchor above the carriage member. This is a folded double
    parallelogram, a standard compliant linear guide.
  - The carriage can only move along the pen, and the bar moves half as far, so each beam bends through only half
    the travel. The bar slides inward slightly as the beams bend, so the beams never stretch and the force rises
    linearly.
  - Sideways, the beams are edge-on and stiff. A 1 N drag at the pen tip moves it about 0.3 mm towards or away
    from the flange, and under 0.1 mm sideways, with no play.
  - The carriage carries v1's dovetail rail and M6 ball plunger, so v1 cartridges slide on and click in as before.
    The frame's front face stays 1 mm behind the carriage, so a cartridge never rubs on the frame.
- **Why it is this size**: each beam has to be about 46 mm long to bend through 10 mm while staying at half of
  PETG's strength. The beams cross behind the cartridge, so the stage is one beam length wide instead of two. The
  ground beams go above the carriage, because below it the stage must stay 25 mm clear of the paper.
- **Preload stop screw** (M3 x 12): the stage is printed with the beams straight. Screwed home from below, the stop
  screw lifts the carriage member 5 mm, so it rests on the screw's tip with 1.2 N of preload, half as much again as
  the weight of the moving parts. The rest position, and so the TCP, is set by where the head seats.
- **Hard stop**: after 15 mm the carriage member lands under the ground anchor, with the beams at about half of
  PETG's strength.
- **Mount**: the stage bolts to the v1 tool adapter with two M3 x 20 screws into the adapter's captive nuts at 270°
  and 30°. The first pad sits in the ground anchor, the second on a ground arm inside the ground parallelogram. The
  third nut sits behind the carriage's path and isn't used. An M3 washer under each pad keeps the moving parts
  0.5 mm clear of the adapter.
- **Why the pen is 21 mm further out than v1**: the left mount pad is level with the flange's centre and must sit
  in the ground anchor, above the carriage's travel, so the cartridge seat moves down along the pen.

With the pen pointing down, the weight of the carriage, cartridge and pen (about 0.8 N) adds to every force above.
Flexure numbers use PETG at E = 2 GPa. Brands vary by about ±20 %, and the force goes with the cube of the beam
thickness, so measure it (see [Tuning](#tuning)).

## Files

| File | |
|---|---|
| `quick_change_v2.py` | Parametric model, 19 design checks, STEP/STL/GLB export. Imports the cartridge from `../Quick-Change Pen Holder` and the adapter from `../Pen Holder`. |
| `render_quick_change_v2.py` | Technical renders 1-5 (pyvista/VTK) |
| `../Pen Holder v2/flexure.py` | The cross-span flexure (shared with Pen Holder v2) |
| `STLs/` | The flexure stage, in print orientation |
| `STEP/` | The stage and the full assembly (arm flange included as a reference) |
| `Quick-Change v2 - Assembly.glb` | Assembly for quick viewing |

Print the other parts from the v1 folders: `../Pen Holder/STLs/Pen Holder - Tool Adapter.stl`, and the cartridge,
twist rings, jaws and stick-out gauge from `../Quick-Change Pen Holder/STLs`.

## Bill of materials

| Qty | Part | Notes |
|---|---|---|
| 1 | Tool adapter | printed, the v1 part |
| 1 | Flexure stage | printed |
| 1 per pen | Cartridge, 2 twist rings, 6 jaws | printed, the v1 parts |
| 1 | Stick-out gauge | printed, the v1 part |
| 6 | M5 x 12 socket head cap screw, ISO 4762 | 3 (every other hole) is enough |
| 1 | Ø3 x 8 dowel pin, ISO 8734 | optional, fixes the tool orientation |
| 2 | M3 hex nut, ISO 4032 | in the adapter's pockets at 270° and 30° |
| 2 | M3 x 20 socket head cap screw, ISO 4762 | stage to adapter |
| 2 | M3 washer, DIN 125 (0.5 mm) | under the stage's mount pads |
| 1 | M3 x 12 socket head cap screw, ISO 4762 | preload stop screw |
| 1 | M6 ball spring plunger, 14 mm long, Ø3.5 ball | as v1, holds the cartridge on the rail |

No rods, coil springs or set screws. The ball plunger is the only purchased spring, and it only holds the cartridge
on.

## Printing

PETG, 0.2 mm layers, **no supports**. The STL lies on its back face, already in print orientation, with the
dovetail rail on top (its flanks lean 32°).

- **Beams**: they are 0.8 mm walls, which slicers print as two 0.4 mm perimeters with nothing between them. Check
  in the preview that every beam is two continuous lines from end to end.
- Each beam's bending stress runs along its extrusion lines, PETG's strong direction.
- 4 perimeters and 40 % infill for the rest. No brim is needed.
- Clean any stringing between the beams, then push the carriage along by hand. It should move smoothly, with
  nothing rubbing.

## Assembly

1. Adapter: press in the dowel pin if used, and push two M3 nuts into the pockets at 270° and 30° from the arm
   side. Bolt the adapter to the arm with the M5 x 12 screws, snug only (about 2 N·m in plastic).
2. Ball plunger: before the stage goes on, screw it in from behind the carriage until its face stands about 0.6 mm
   proud of the rail, then check that a cartridge clicks on without play (as in v1).
3. Stop screw: screw the M3 x 12 up into the bottom of the frame, under the carriage member, until its head seats.
   The last 5 mm lift the carriage and preload the beams.
4. Bolt the stage to the adapter: an M3 x 20 through each mount pad from the front, with a washer between the pad
   and the adapter.
5. Load pens into cartridges with the stick-out gauge and slide a cartridge up onto the rail until it clicks, as in
   v1.

## Robot setup

- **TCP:** in a flange frame with Z pointing out of the flange and X towards the dowel pin, the pen tip is at
  **X -116, Y 0, Z +56 mm**. The pen points along -X, so set the tool orientation to **(0, -90°, 0)** if your tool
  Z axis should point along the pen.
- **Pen-down height:** command it 2 to 5 mm below the paper: about 1.6 to 2.3 N from the beams, plus the moving
  parts' 0.8 N when the pen points down. Keep over-reach well under the 15 mm hard stop.
- **Payload:** about 0.19 kg, with the centre of mass at about **X -26, Y 0, Z +24 mm** in the same flange frame.

## Tuning

- **Measuring the force**: point the pen down onto a kitchen scale and lower the arm. The reading where the carriage
  starts to move is the preload plus the moving parts' weight, about 2 N. 5 mm lower it should have risen by about
  1.2 N.
- **Too light or too heavy**: change `BEAM_T` (force goes with its cube) or `BEAM_B` (proportional) and reprint the
  stage. The design checks recompute stress and preload.
- **Creep**: PETG relaxes a little under constant load, so the preload may fall by 10-20 % over the first weeks.
  The TCP and travel don't change, because the stop screw and hard stop set them.

## Regenerating

```
uv run quick_change_v2.py              # design report + STEP / STL / GLB
uv run render_quick_change_v2.py       # renders 1-5 into ../../Renders
uv run render_quick_change_v2.py --hero-glb hero.glb
blender --background --factory-startup --python "../Quick-Change Pen Holder/blender_hero_quick_change.py" -- hero.glb "../../Renders/Quick-Change Pen Holder v2 Render 0.png"
```
