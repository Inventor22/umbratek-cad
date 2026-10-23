# Chess Gripper end effector (UTRA 6-1000)

![How the chess gripper works](../../Renders/Chess%20Gripper%20Animation.gif)

A three-claw gripper that lifts chess pieces by the neck, just under the collar. An SG90 micro servo
pushes the claws open. A broccoli rubber band closes them and does all of the holding.
Full-resolution video: [Chess Gripper Animation.mp4](../../Renders/Chess%20Gripper%20Animation.mp4).

## How it works

- **Base** (`Gripper Base v3`): a hex plate with three angled forks. The tabs on top of the forks have
  M5 clearance holes on a 64 mm PCD, matching the UTRA 6-1000 tool flange. The SG90 sits upside down in
  a pocket in the plate, with its output shaft on the gripper axis.
- **Claws** (`Gripper Claw v3`, x3): hang from Ø2.5 pins in the forks, 26 mm off the axis. Each one ends
  in a 3 mm hook with a concave tip.
- **Horn wheel and pushers** (`Gripper Servo Wheel v1`, `Gripper Claw Pusher` x3): the wheel on the servo
  spline has three Ø2.5 pin holes on a 7.5 mm radius. Each pusher is a C-shaped clevis that runs from one
  of those pins to a Ø4 peg, which passes loosely through a Ø6 hole in its claw. The peg points straight
  back at the pin, so the pusher works as a push rod. The C shape lets it curl round the servo hub, which
  sits right on that line when the pushers are fully back.
- **Broccoli band**: the wide produce band (PLU 4060) that comes round a head of broccoli, stretched
  round the three claws. It slides up them into the valley where the angled faces of the forks meet the
  claws, just under the pivots, and settles there with its lower edge on the plate. It is not in the CAD.

The servo only pushes the claws open. The band closes them:

1. Turning the horn about 100° swings the pusher pins round. The pushers drive their shoulders against
   the claws and spread the hook tips from about Ø13 to Ø65, stretching the band.
2. Turning the horn back retracts the pushers. The band pulls the claws in behind them until the hooks
   land on the piece's neck, under the collar.
3. The pushers keep going, sliding their pegs back through the oversized holes. On a Ø19 neck they end
   up about 1 mm clear of the claws, so from then on the band is the only thing squeezing the piece.

Because the grip comes from the band rather than the servo, the servo carries no load while it holds a
piece and cannot crush one. The hooks sit inboard of the pivots, so the weight of the piece tries to open
the claws; the band's tension keeps them shut. With no piece in the claws, the band pulls them back onto
the pushers.

## Animation

`animate_chess_gripper.py` builds the assembly from the STLs and solves the mechanism from the part
geometry for every frame. The servo angle sets the wheel, each pusher's peg is aimed through its claw's
hole, and each claw sits wherever the band holds it: against its pusher's shoulder, or against the piece.
The band is solved every 0.5° of claw travel and thins as it stretches. `--check` prints the key angles
and clearances, checks the moving parts for collisions with each other and with the other pieces at
frames spread across the whole cycle, and checks the camera never sees its subject through a piece.

The gripper plays a real move. The board is set up in the Traxler Counterattack after
1.e4 e5 2.Nf3 Nc6 3.Bc4 Nf6 4.Ng5 Bc5 5.Nxf7 Bxf2+, with the two captured pawns beside the board. White's
king is in check, and the gripper plays 6.Kf1: it picks the king up off e1, carries it over the bishop on
f2 and sets it down on f1. The claws are turned so they straddle the queen on d1 and the bishop next to
f1. Change the position with `POSITION` (a FEN board) and the move with `GRIP_SQUARE` and `DROP_SQUARE`.

The edit is cut like a product film: nine shots joined by hard cuts, each one a single slow push-in,
slide or crane. It opens wide on the board, then cuts to the band, to the pushers opening the claws, to
the descent, to the band closing the claws, and to the hooks catching the collar. A high shot follows the
carry, then come the set-down and release, and a slow pull-back ends it. Each shot is a line in `SHOTS`
with its own camera, switched by timeline markers.

The servo and the king only exist as SolidWorks parts (`Parts/*.SLDPRT`), which Blender can't read, and
the band isn't modelled at all, so the animation uses stand-ins:

- SG90 servo: modelled from TowerPro's published dimensions.
- Chess set: a turned Staunton set in boxwood and ebony with a 96 mm king, modelled in the script. The
  king's neck is Ø19, so the hooks land just under its collar.
- Band: a #81 PLU 4060 produce band, 12 mm wide with a 50 mm lay-flat length and a 0.8 mm wall. Round
  the claws it stretches to about 1.63x its free length (1.71x with them open) and narrows to about
  9.4 mm. Each strip of the band takes the shortest way round the parts at its own height, and the band
  sits where its stretch is lowest with the claws open, which is the valley between the forks and the
  claws. Set its size with `BAND_REST`, `BAND_W0` and `BAND_T0`.

## Files

| File | |
|---|---|
| `animate_chess_gripper.py` | Blender scene, kinematics, timeline and frame rendering (Cycles) |
| `make_video.py` | Encodes the frames as `Renders/Chess Gripper Animation.mp4` and `.gif` |
| `STLs/` | Printable parts |
| `Parts/` | SolidWorks parts and assemblies |

## Regenerating

Needs Blender (made with 5.2), [uv](https://docs.astral.sh/uv/) and ffmpeg on the PATH:

```
blender -b --factory-startup --python animate_chess_gripper.py -- --check
blender -b --factory-startup --python animate_chess_gripper.py -- --out frames
uv run make_video.py frames
```

The 630 frames take about 40 minutes at 1920x1080 and 96 samples on an RTX 3080 Ti. For a quick look,
`--stills 1,150,300` renders single frames and `--res 960x540 --samples 32` renders a fast preview.
`--save scene.blend` keeps the scene for editing.
