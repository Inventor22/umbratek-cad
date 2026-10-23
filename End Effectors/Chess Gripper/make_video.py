# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""
Encode the rendered frames of the chess-gripper animation as an MP4 and a GIF.

    uv run make_video.py frames                      # -> ../../Renders/Chess Gripper Animation.mp4 / .gif
    uv run make_video.py frames --gif-width 800 --gif-fps 15

Reads frames/frame_####.png and frames/timeline.json written by animate_chess_gripper.py.
Needs ffmpeg on PATH.
"""

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RENDERS = os.path.normpath(os.path.join(HERE, "..", "..", "Renders"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames", nargs="?", default=os.path.join(HERE, "frames"))
    ap.add_argument("--mp4", default=os.path.join(RENDERS, "Chess Gripper Animation.mp4"))
    ap.add_argument("--gif", default=os.path.join(RENDERS, "Chess Gripper Animation.gif"))
    ap.add_argument("--gif-width", type=int, default=560)
    ap.add_argument("--gif-fps", type=int, default=10)
    ap.add_argument("--gif-colors", type=int, default=112)
    ap.add_argument("--crf", type=int, default=19)
    args = ap.parse_args()

    if not shutil.which("ffmpeg"):
        sys.exit("ffmpeg not found on PATH")
    with open(os.path.join(args.frames, "timeline.json")) as fh:
        fps = json.load(fh)["fps"]
    if not any(p.startswith("frame_") and p.endswith(".png") for p in os.listdir(args.frames)):
        sys.exit(f"no frame_####.png in {args.frames}")
    frames = os.path.join(args.frames, "frame_%04d.png")

    os.makedirs(os.path.dirname(args.mp4), exist_ok=True)
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", frames,
                    "-c:v", "libx264", "-preset", "slow", "-crf", str(args.crf), "-pix_fmt", "yuv420p",
                    "-movflags", "+faststart", args.mp4], check=True)
    # a light denoise and an ordered (Bayer) dither keep the GIF small with a camera that never stops
    vf = f"scale={args.gif_width}:-2:flags=lanczos,hqdn3d=2:2:6:6,fps={args.gif_fps}"
    with tempfile.TemporaryDirectory() as tmp:
        palette = os.path.join(tmp, "palette.png")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", frames,
                        "-vf", f"{vf},palettegen=max_colors={args.gif_colors}:stats_mode=full", palette], check=True)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", frames, "-i", palette,
                        "-lavfi", f"{vf}[v];[v][1:v]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle",
                        "-loop", "0", args.gif], check=True)
    for path in (args.mp4, args.gif):
        print(f"{path}  {os.path.getsize(path) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
