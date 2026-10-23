# Quick-Change Pen Holder (UTRA 6-1000)

![Quick-change pen holder drawing on paper](../../Renders/Quick-Change%20Pen%20Holder%20Render%200.png)

A second version of the [compliant pen holder](../Pen%20Holder/README.md). Here the pen sits **perpendicular to the
flange axis**, takes **any pen from 6 to 17 mm**, and pens are swapped by sliding **cartridges** in and out
without tools. Each cartridge grips its pen with **two twist chucks 56 mm apart**, so the pen can't rock. A base
stays bolted to the arm and carries a spring stage with **15 mm of compliant travel**.

| | |
|---|---|
| Mounting | UTRA 6-1000 tool flange: 6x M5 on PCD 64, Ø73 h7 pilot, Ø3 H7 dowel on PCD 52 (same as v1) |
| Pen | any diameter from 6 to 17 mm, held by two self-centring 3-jaw twist chucks whose jaws span 56 mm of the pen |
| Pen swap | slide the cartridge up onto the dovetail rail until it clicks; pull it down to remove |
| Compliant travel | 15 mm along the pen, then a hard stop |
| Pen force | 1.5 N at first touch, 4.6 N at full travel (2 springs 0.5 x 8 x 40 mm, ~0.21 N/mm, 7 mm preload) |
| TCP | 56 mm out from the flange face, 95 mm off the flange axis (opposite the dowel pin). Same for every pen. |
| Mass | about 215 g including hardware and an 11 mm gel pen |

## Renders

| | |
|---|---|
| ![Section](../../Renders/Quick-Change%20Pen%20Holder%20Render%201.png) | ![Exploded view](../../Renders/Quick-Change%20Pen%20Holder%20Render%202.png) |
| ![Twist chuck](../../Renders/Quick-Change%20Pen%20Holder%20Render%203.png) | ![Spring compliance](../../Renders/Quick-Change%20Pen%20Holder%20Render%204.png) |
| ![Quick pen swap](../../Renders/Quick-Change%20Pen%20Holder%20Render%205.png) | ![Print layout](../../Renders/Quick-Change%20Pen%20Holder%20Render%206.png) |
| ![Ratchet clicks](../../Renders/Quick-Change%20Pen%20Holder%20Render%207.png) | |

## How it works

- **Base** (printed): bolts to the arm once with the same flange interface as v1. It sits on the Ø73 pilot,
  clamps on the boss face, and clears the tool-I/O cover. A frame below the flange holds two Ø6 mm steel rods,
  locked with M3 set screws.
  - The top block is the 15 mm hard stop and the bottom block is the rest stop.
  - Two side walls tie the blocks together, so the top block prints as a bridge.
- **Carriage** (printed, orange): slides on the rods. A spring around each rod pushes it down onto the rest
  stop. It carries the dovetail rail and an M6 ball spring plunger. The lowest M5 screw is behind the carriage;
  a Ø9 hole through the carriage gives hex-key access to it.
- **Cartridge** (printed, light grey): holds one pen and needs no hardware. The pen runs through a tube up the
  front of the cartridge, with a twist chuck at each end. Slide the cartridge up onto the rail until the
  plunger's ball clicks into its detent. The plunger also pushes the dovetail flanks together, so it seats
  without play. When the pen pushes back it drives the cartridge into its seat, so the detent only has to stop
  the cartridge falling off. To remove it, pull it straight down.
- **Twist chucks**: in each chuck, three jaws slide in radial grooves in the cartridge. Each jaw has a pin that
  runs in a spiral slot in the knurled ring, so turning the ring moves all three jaws together.
  - The two chucks grip the pen at points 56 mm apart, so it can't rock in the cartridge. A single short chuck
    would let it pivot, because each jaw bears hardest at its pinned end.
  - The upper chuck is the lower one turned upside down, so both use the same ring and jaws. Pens shorter than
    about 95 mm only reach the lower chuck.
  - About 120° of rotation takes the jaws from open to closed: roughly 20° for a 16 mm marker, 70° for an 11 mm
    gel pen, 100° for an 8 mm ballpoint.
  - Two things stop a ring turning back and releasing the pen:
    - The spiral is shallow: its slope is at most 0.24, under PETG's friction of about 0.3, so pressure from the
      pen can't turn the ring back. This is what holds the clamp, like the friction in a screw thread.
    - Ratchet clicks: two spring fingers, printed as part of each chuck, click into 60 flutes inside the ring, a
      click every 6°. Each flute has a gentle ramp on the tightening side and a steep wall on the loosening side,
      so tightening is light, and a ring that gets knocked is caught at the next click. A seated click holds
      the ring even if the friction were only 0.2.
  - The jaws, not the clicks, decide where a ring stops, so it often rests between two clicks. A finger resting on
    a ramp barely pushes the ring back, because the ramp is about as shallow as the friction angle. At worst, a
    knocked ring slips back to the previous click and opens the jaws about 0.3 mm, so tighten firmly.
  - The fingers print standing up, with a layer line at the root, so they are sized for low stress there: about
    a third of PETG's strength across layers while riding on a land between clicks, and none when seated in a
    flute. Notches in each ring's snap ridge line up with the fingers when the ring is fully open, so pushing a
    ring on doesn't bend them.
  - Because the jaws are self-centring, every pen ends up on the same axis and the TCP doesn't change.
  - The jaw pins are Ø3.6 mm and print with their layers running along them, so they have no weak layer line at
    the root. A hard 1 N·m twist loads them to about 60 % of PETG's strength. Finger-tight (about 0.1 N·m)
    already holds the pen against the full spring force.
- **Stick-out gauge** (printed): sets the pen at the stick-out the TCP assumes. Stand the cartridge on it with the
  pen down through the hole, then clamp.

## Files

| File | |
|---|---|
| `quick_change_pen_holder.py` | Parametric model, design-rule checks, STEP/STL/GLB export. Imports the shared flange interface from `../Pen Holder/pen_holder.py`. |
| `render_quick_change.py` | Technical renders 1-7 (pyvista/VTK), reusing the v1 renderer |
| `blender_hero_quick_change.py` | Photoreal render 0 (Blender Cycles) |
| `STLs/` | Printable parts, already in print orientation |
| `STEP/` | Each part plus the full assembly (arm flange included as a reference) |
| `Quick-Change - Assembly.glb` | Assembly for quick viewing |

## Bill of materials

| Qty | Part | Notes |
|---|---|---|
| 1 | Base | printed, stands upright on the print bed |
| 1 | Carriage | printed |
| 1 per pen | Cartridge, 2 twist rings, 6 jaws | printed; make as many cartridges as you have pens |
| 1 | Stick-out gauge | printed |
| 2 | Ø6 x 80 mm steel rod | h6 linear shaft or ISO 8734 dowel pins |
| 2 | Compression spring, 0.5 mm wire x 8 mm OD x 40 mm free length | ID must be at least 6.5 mm |
| 1 | M6 ball spring plunger, 14 mm long, Ø3.5 ball, hex socket | needs about 0.8-1 mm of ball travel, e.g. GN 615 / Kipp K0322 style |
| 2 | M3 x 3 set screw, ISO 4026 | locks the rods |
| 6 | M5 x 12 socket head cap screw, ISO 4762 | 3 (every other hole) is enough |
| 1 | Ø3 x 8 dowel pin, ISO 8734 | optional, fixes the tool orientation |

## Printing

PETG (or ASA/PLA+), 0.2 mm layers, 4 perimeters, 40 % infill, **no supports**. The STLs are already in print
orientation:

- base upright on its foot;
- carriage on its bottom face;
- cartridge on its lower chuck face;
- rings on their slotted face;
- jaws on their side, pin teardrop down (this keeps layer lines out of the pin's root).

The ratchet fingers print in place as part of the cartridge, standing free in their pockets. Check that they
flex freely after printing; trim any stringing between a finger and its pocket wall.

**Fit tuning:**

- **Rod bushings:** if the carriage binds, ream the carriage bushings to 6.05-6.1 mm.
- **Dovetail:** if it is too tight or too loose, change `DOVETAIL_CLEARANCE`. The flanks locate the cartridge, so
  the pen stays where it is; the design report prints the new plunger setting.
- **Twist rings:** if they are too stiff or too loose on the chucks, change `RING_CLEARANCE`.
- **Ratchet clicks:** if they are too weak or too stiff, change `DETENT_DEPTH` (0.3 mm by default).

Each ring snaps over a 0.5 mm ridge onto its chuck, with a 45° lead-in on both sides so it can come off again.
Push it on with the jaws in their grooves and their pins in the slot ends.

## Assembly

1. Press the dowel into the base. From behind the carriage, screw the ball plunger in through its through-hole
   until its face stands about 0.6 mm proud of the rail (a little over half a turn past flush). Slide a cartridge
   on: it should click and sit without play. If it rattles, turn the plunger in a quarter turn; if it is stiff,
   back it out. Then bolt the base to the arm (6x M5x12, snug, about 2 N·m in
   plastic). The lowest M5 is reached through the Ø9 hole in the carriage, with the carriage pushed up or not
   yet fitted.
2. Put a spring into each spring pocket in the top of the carriage. Hold the carriage between the blocks with
   the springs compressed, then push the rods down through the top block, springs, carriage and bottom block.
   Lock them with the M3 set screws.
3. Cartridge: drop three jaws into the lower chuck's grooves with the pins down, turn a ring to fully open and
   snap it on from below. Do the same at the upper chuck with the pins up and the ring snapped on from above.
4. Load a pen: open both rings, push the pen down through both chucks, and stand the cartridge on the stick-out
   gauge with the tip on the bottom. Turn the lower ring clockwise, as seen from its own end of the cartridge,
   until its jaws grip (up to a third of a turn; this is the light, clicking direction). Then do the same with the
   upper ring. Finger-tight is plenty; there is no need to crank them.
5. Slide the cartridge up onto the rail until it clicks. To change pens, pull it down and slide on another.

## Robot setup

- **TCP:** in a flange frame with Z pointing out of the flange and X towards the dowel pin, the pen tip is at
  **X -95, Y 0, Z +56 mm**. The pen points along -X, so set the tool orientation to **(0, -90°, 0)** if your
  tool Z axis should point along the pen. Confirm the dowel direction with a slow jog test before drawing.
- **Pen-down height:** command it 2 to 5 mm below the paper, about 1.9 to 2.5 N of drawing force. Keep
  over-reach well under the 15 mm hard stop.
- **Payload:** about 0.21 kg, with the centre of mass at about **X -21, Y 0, Z +23 mm** in the same flange frame.
- **Drawing pose:** the holder works in any orientation. It is designed for the flange axis horizontal and the
  pen vertical, which is the pose shown.

## Changing the design

Every dimension is a named parameter at the top of `quick_change_pen_holder.py`. Some useful ones:

| Parameter | Controls |
|---|---|
| `STROKE` | compliant travel |
| `PEN_D_MIN`, `PEN_D_MAX` | chuck range |
| `PEN_Y` | how far the pen sits in front of the flange |
| `PEN_STICKOUT` | stick-out the TCP assumes, and the gauge height |
| `SLOT_SWEEP` | ring rotation from open to closed |
| `DETENT_*` | spacing, shape and strength of the ring's ratchet clicks |
| `STAGE_SPRING_*` | spring size and stiffness |

The script runs its design checks on every export and stops with an error if a change makes parts collide or a
mechanism stop working.

## Regenerating

```
uv run quick_change_pen_holder.py              # design report + STEP / STL / GLB
uv run render_quick_change.py                  # renders 1-7 into ../../Renders
uv run render_quick_change.py --hero-glb hero.glb
blender --background --factory-startup --python blender_hero_quick_change.py -- hero.glb "../../Renders/Quick-Change Pen Holder Render 0.png"
```
