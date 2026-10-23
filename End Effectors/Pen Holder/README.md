# Pen Holder end effector (UTRA 6-1000)

![Pen holder drawing on paper](../../Renders/Pen%20Holder%20End%20Effector%20Render%200.png)

A spring-loaded pen holder for the Umbratek UTRA 6-1000 arm, modelled in
[build123d](https://github.com/gumyr/build123d). The pen is clamped in a carriage that slides in a
barrel, with a compression spring along the pen axis. If the arm over-reaches toward the surface, the
carriage slides up the barrel (up to 15 mm) instead of driving the pen into the table.

For a holder that takes any pen from 6 to 17 mm, mounts it perpendicular to the flange and swaps pens
without tools, see the [Quick-Change Pen Holder](../Quick-Change%20Pen%20Holder/README.md).

| | |
|---|---|
| Mounting | UTRA 6-1000 tool flange: 6x M5 on PCD 64, Ø73 h7 pilot, Ø3 H7 dowel on PCD 52 |
| Compliant travel | 15 mm, then a hard stop |
| Pen force | 1.8 N at first touch, 4.5 N at full travel (spring 1.0 x 20 x 50 mm, ~0.18 N/mm, 10 mm preload) |
| TCP | X 0, Y 0, Z +159 mm from the flange face (Sharpie Fine Point, 35 mm stick-out) |
| Mass | about 150 g including hardware and pen |

## Renders

| | |
|---|---|
| ![Cutaway](../../Renders/Pen%20Holder%20End%20Effector%20Render%201.png) | ![Exploded view](../../Renders/Pen%20Holder%20End%20Effector%20Render%202.png) |
| ![Spring compliance](../../Renders/Pen%20Holder%20End%20Effector%20Render%203.png) | ![Mounting interface](../../Renders/Pen%20Holder%20End%20Effector%20Render%204.png) |
| ![Print layout](../../Renders/Pen%20Holder%20End%20Effector%20Render%205.png) | |

## How it works

- **Tool adapter** (printed): bolts to the arm's tool flange and centres on the Ø73 pilot boss. It seats on
  the boss face, where the M5 holes are, and leaves a 0.5 mm gap at the shoulder. A Ø50 x 1 mm pocket keeps it
  off the tool-I/O connector cover. Future tools can reuse it through its 3x M3 interface (captive nuts on
  PCD 43). The module flange stays inside the M5 counterbores, so the adapter can be unbolted with the pen
  module still attached.
- **Pen module** (printed): flange and barrel. The spring sits in a pocket under the flange.
- **Pen carriage** (printed, orange): slides in the barrel (0.4 mm diametral clearance, 35 to 50 mm of guided
  length). Two M3 set screws ride in slots in the barrel. They stop the carriage rotating or falling out and
  line up with tick marks every 5 mm, so you can see how far the pen has been pushed. At 15 mm the nose
  shoulder lands on the end of the barrel, a solid hard stop, before the spring can go solid.
- **Pen clamp**: an M3 thumb screw into a captive nut, slid into the nose from its end face.

## Files

| File | |
|---|---|
| `pen_holder.py` | Parametric model, design-rule checks and STEP/STL/GLB export |
| `render_pen_holder.py` | Technical renders 1-5 (pyvista/VTK) |
| `blender_hero.py` | Photoreal render 0 (Blender Cycles) |
| `STLs/` | Printable parts, already in print orientation |
| `STEP/` | Each part plus the full assembly (with the arm flange as a reference) |
| `Pen Holder - Assembly.glb` | Assembly for quick viewing (Windows 3D Viewer, browser glTF viewers) |

## Bill of materials

| Qty | Part | Notes |
|---|---|---|
| 1 | Tool adapter | printed |
| 1 | Pen module | printed |
| 1 | Pen carriage | printed |
| 1 | Compression spring, 1.0 mm wire x 20 mm OD x 50 mm free length | any rate from ~0.1 to 0.3 N/mm works; ID must be at least 15 mm |
| 6 | M5 x 12 socket head cap screw, ISO 4762 | 3 (every other hole) is plenty for a pen |
| 1 | Ø3 x 8 dowel pin, ISO 8734 | optional, fixes the tool orientation |
| 3 | M3 x 14 socket head cap screw, ISO 4762 | module to adapter |
| 4 | M3 hex nut, ISO 4032 | 3 in the adapter, 1 for the pen clamp |
| 2 | M3 x 6 set screw, flat point, ISO 4026 | guide pins |
| 1 | M3 x 10 knurled thumb screw, DIN 464 / DIN 653 | an M3 x 10 cap screw also works |

## Printing

PETG (or ASA/PLA+), 0.2 mm layers, 4 perimeters, 40 % infill, **no supports**. The STLs are already in
print orientation: adapter with the arm side up, module flange down, carriage nose down.

If the carriage binds or rattles, change `SLIDE_CLEARANCE` and reprint only the carriage. If the adapter
is tight or loose on the Ø73 pilot, change `PILOT_CLEARANCE`. For a machined aluminium adapter, set it to 0
and make the recess Ø73 H7.

## Assembly

1. Press the three M3 nuts into the hex pockets on the arm side of the adapter, and press the dowel pin
   into its hole so 4.5 mm stands proud.
2. Bolt the module to the adapter with 3x M3 x 14 from the barrel side.
3. Drop the spring into the barrel. Push the carriage in, spigot first, until its two side holes line up
   with the slots, then drive the M3 x 6 set screws in until they bottom out. They end just below the
   barrel surface. Release, and the carriage settles with the pins at the bottom of the slots.
4. Slide an M3 nut into the slot in the nose face and thread in the thumb screw.
5. Fit the adapter to the arm: dowel in the Ø3 hole, recess over the Ø73 pilot. Tighten the M5 screws snug
   only, about 2 N·m in plastic.
6. Insert the pen from below until its wide barrel reaches the nose face (35 mm stick-out for a Sharpie
   Fine Point), then tighten the thumb screw.

## Robot setup

- Set the tool TCP to **X 0, Y 0, Z +159 mm** in the flange frame (pen tip, spring relaxed). +X points to
  the dowel side, marked by the groove on the adapter rim. Re-teach the tip after re-clamping a pen.
- Command the pen-down height 2 to 5 mm below the paper, giving roughly 2.2 to 2.7 N of drawing force.
  Keep over-reach well under the 15 mm hard stop.
- Payload: about 0.15 kg, with the centre of mass roughly 35 mm below the flange face.

## Using a different pen

Edit the pen block near the top of `pen_holder.py`:

- `PEN_D`: diameter of the part of the pen that sits in the carriage.
- `PEN_LEN`: pen length.
- `PEN_STICKOUT`: how far the tip protrudes below the nose.

Then re-run the script and reprint just the carriage. The design checks fail loudly if the pen would not
pass through the spring or would hit the arm at full travel. The TCP is printed in the report.

## Regenerating

The scripts declare their dependencies inline (PEP 723), so [uv](https://docs.astral.sh/uv/) needs no setup:

```
uv run pen_holder.py                  # design report + STEP / STL / GLB
uv run render_pen_holder.py           # renders 1-5 into ../../Renders
uv run render_pen_holder.py --hero-glb hero.glb
blender --background --factory-startup --python blender_hero.py -- hero.glb "../../Renders/Pen Holder End Effector Render 0.png"
```

`blender_hero.py` takes optional arguments after the output path: samples (default 256), width, height.
It enables GPU rendering for that Blender process only.

## Flange reference

The tool-flange dimensions come from `Quick_Start_Guide_UTRA_6-1000.pdf`, page 1:

- Ø86 body with a Ø73 h7 pilot boss 3 mm high.
- 6x M5, 6 mm deep, on PCD 64 at a 60° pitch, with one hole on the dowel axis.
- Ø3 H7 dowel hole, 5 mm deep, on PCD 52.
- Two 8-pin tool-I/O connectors in a Ø47 centre cover.

Check the hole pattern with calipers before committing to a metal adapter.
