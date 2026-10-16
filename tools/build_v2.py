"""Rebuild V2 revision 2 from versioned ImageGen strips using the Pets pipeline.

Never calls a generative service during build. Source PNGs and the pinned
pipeline are verified before extraction; re-running cannot accumulate edits.
"""
from __future__ import annotations
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_COMMIT = "6b3add420b52e307a664ca30985257791ebcc4f1"
SOURCE_SHA256 = "3648d95700b376609ffd0b63225d6dc255a2986b5c97b2b11be044a303f5f490"
SHEET = "pets/codedragon/spritesheet.png"
ART = ROOT / "assets/source/v2-r2"
PIPELINE = ROOT / "tools/pet_pipeline"
NAMES = ["idle", "running-right", "running-left", "waving", "jumping",
         "failed", "waiting", "running", "review", "look-1", "look-2"]
COUNTS = [6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8]
DURATIONS = [160, 85, 85, 180, 150, 150, 220, 140, 200, 160, 160]
W, H = 192, 208


def digest(data):
    return hashlib.sha256(data).hexdigest()


def original_bytes(source=None):
    """Previous published V2, exclusively for comparisons (not an art input)."""
    data = Path(source).read_bytes() if source else subprocess.check_output(
        ["git", "show", f"{ORIGINAL_COMMIT}:{SHEET}"], cwd=ROOT)
    if digest(data) != SOURCE_SHA256:
        raise ValueError("Comparison source must be the previous published V2")
    return data


def cell(image, row, column):
    return image.crop((column*W, row*H, (column+1)*W, (row+1)*H))


def verify_sources(art=ART):
    manifest = json.loads((art / "sources.json").read_text(encoding="utf-8"))
    required = {f"{name}.png" for name in NAMES[:9]} | {"look-row-9.png", "look-row-10.png", "canonical-base.png", "look-cardinals.png"}
    if not required.issubset(manifest["files"]):
        raise ValueError("Source manifest is missing required artwork")
    for name, expected in manifest["files"].items():
        if Path(name).name != name or digest((art/name).read_bytes()) != expected:
            raise ValueError(f"Source checksum mismatch: {name}")
    pinned = json.loads((PIPELINE/"provenance.json").read_text(encoding="utf-8"))
    for name, expected in pinned["files"].items():
        if digest((PIPELINE/name).read_bytes()) != expected:
            raise ValueError(f"Pinned pipeline checksum mismatch: {name}")
    return manifest


def run_pipeline(name, *args):
    subprocess.run([sys.executable, str(PIPELINE/name), *map(str, args)],
                   check=True, cwd=ROOT, stdout=subprocess.DEVNULL)


def register_frames(frames):
    """Fit generated pixels with one scale per row, retaining the prior pet size.

    This only resizes/places approved art, never paints anatomy or props. The
    five jump baselines retain the previous revision's 55px celebration lift.
    """
    for row, (name, count) in enumerate(zip(NAMES[:9], COUNTS[:9])):
        paths = [frames/name/f"{c:02d}.png" for c in range(count)]
        images = [Image.open(p).convert("RGBA") for p in paths]
        if any(im.getbbox() is None for im in images):
            raise ValueError(f"Extraction produced an empty frame in {name}; repair the source strip")
        height = max(im.getbbox()[3]-im.getbbox()[1] for im in images)
        scale = min(1., (148 if row == 7 else 132)/height)
        size = (round(W*scale), round(H*scale))
        for col, (path, image) in enumerate(zip(paths, images)):
            resized = image.resize(size, Image.Resampling.LANCZOS)
            bbox = resized.getbbox()
            baseline = [200, 171, 145, 169, 200][col] if row == 4 else 200
            if row in (1, 2):
                baseline = [200, 198, 196, 198, 200, 198, 196, 198][col]
            target = Image.new("RGBA", (W, H))
            target.alpha_composite(resized, ((W-size[0])//2, baseline-bbox[3]))
            target.save(path)


def build(destination, workdir):
    verify_sources()
    workdir.mkdir(parents=True, exist_ok=True)
    frames = workdir/"frames"
    run_pipeline("extract_strip_frames.py", "--decoded-dir", ART,
                 "--output-dir", frames, "--method", "components", "--chroma-key", "#FF00FF")
    register_frames(frames)
    run_pipeline("compose_atlas.py", "--frames-root", frames, "--output", workdir/"standard.png")
    run_pipeline("assemble_extended_atlas.py", "--base-atlas", workdir/"standard.png",
                 "--look-row-9", ART/"look-row-9.png", "--chroma-key", "#FF00FF",
                 "--registered-row-output", workdir/"registered-row-9.png",
                 "--registration-manifest-output", workdir/"registration.json")
    run_pipeline("assemble_extended_atlas.py", "--base-atlas", workdir/"standard.png",
                 "--registered-row-9", workdir/"registered-row-9.png",
                 "--row-9-registration", workdir/"registration.json",
                 "--look-row-10", ART/"look-row-10.png", "--chroma-key", "#FF00FF",
                 "--output", workdir/"assembled.png")
    destination.parent.mkdir(parents=True, exist_ok=True)
    run_pipeline("despill_chroma_edges.py", workdir/"assembled.png", "--output", destination,
                 "--chroma-key", "#FF00FF", "--json-out", workdir/"chroma.json")
    return Image.open(destination)


def background(frame, light=False):
    bg = Image.new("RGBA", (W, H), (232, 236, 242, 255) if light else (29, 36, 49, 255))
    bg.alpha_composite(frame)
    return bg.convert("RGB")


def preview(source, output, destination):
    destination.mkdir(parents=True, exist_ok=True)
    font = ImageFont.load_default(size=15)
    contact = Image.new("RGB", (W*8, (H+30)*11), (29, 36, 49))
    all_frames, all_durations = [], []
    for row, count in enumerate(COUNTS):
        frames, compare = [], []
        for col in range(count):
            frame = background(cell(output, row, col))
            contact.paste(frame, (col*W, row*(H+30)+30))
            ImageDraw.Draw(contact).text((col*W+6, row*(H+30)+7),
                                         f"{NAMES[row]} {col}", fill="white", font=font)
            frames.append(frame)
            pair = Image.new("RGB", (W*2, H+28), (29, 36, 49))
            pair.paste(background(cell(source, row, col)), (0, 28))
            pair.paste(frame, (W, 28))
            ImageDraw.Draw(pair).text((8, 6), "V2 anterior             V2 rev.2", fill="white", font=font)
            compare.append(pair)
        frames[0].save(destination/f"{NAMES[row]}.gif", save_all=True,
                       append_images=frames[1:], duration=DURATIONS[row], loop=0, disposal=2)
        if row < 9:
            compare[0].save(destination/f"{NAMES[row]}-comparison.gif", save_all=True,
                            append_images=compare[1:], duration=DURATIONS[row], loop=0, disposal=2)
            for frame in frames:
                labeled = Image.new("RGB", (W, H+32), (29, 36, 49))
                labeled.paste(frame, (0, 32))
                ImageDraw.Draw(labeled).text((8, 8), NAMES[row], fill="white", font=font)
                all_frames.append(labeled)
                all_durations.append(DURATIONS[row])
    contact.save(destination/"contact-sheet.png")
    directions = Image.new("RGB", (W*8, (H+32)*3), (29, 36, 49))
    directions.paste(background(cell(output, 0, 0)), (0, 32))
    ImageDraw.Draw(directions).text((8, 8), "Neutral (idle 0)", fill="white", font=font)
    look_frames = []
    for index in range(16):
        c, r = index % 8, 1+index//8
        look = background(cell(output, 9+index//8, c))
        look_frames.append(look)
        directions.paste(look, (c*W, r*(H+32)+32))
        ImageDraw.Draw(directions).text((c*W+8, r*(H+32)+8),
                                        f"{index*22.5:05.1f} deg", fill="white", font=font)
    directions.save(destination/"look-directions.png")
    look_frames[0].save(destination/"look-directions.gif", save_all=True,
                        append_images=look_frames[1:], duration=160, loop=0, disposal=2)
    all_frames[0].save(destination/"all-states.gif", save_all=True, append_images=all_frames[1:],
                       duration=all_durations, loop=0, disposal=2)
    bridge = [background(cell(output, 0, c)) for c in range(6)]
    bridge += [background(cell(output, 4, c)) for c in range(5)]
    bridge += [background(cell(output, 0, 0))]
    bridge[0].save(destination/"idle-success-idle.gif", save_all=True,
                   append_images=bridge[1:], duration=[160]*6+[150]*5+[320], loop=0, disposal=2)
    # Ordered contact strip gives concrete evidence even without GIF playback.
    stills = Image.new("RGB", (W*5, H+32), (29, 36, 49))
    labels = ["1. Prepare", "2. Lift", "3. Hover", "4. Celebrate", "5. Land"]
    for col, label in enumerate(labels):
        stills.paste(background(cell(output, 4, col)), (col*W, 32))
        ImageDraw.Draw(stills).text((col*W+7, 8), label, fill="white", font=font)
    stills.save(destination/"success-frames.png")
    # Alpha/fringe evidence on both dark and light mattes (PNG, not the pet).
    mattes = Image.new("RGB", (W*8, H*2), (232, 236, 242))
    for row in range(2):
        for col, (r, c) in enumerate([(0, 3), (1, 3), (2, 3), (3, 1), (4, 2), (5, 4), (7, 1), (8, 1)]):
            mattes.paste(background(cell(output, r, c), light=row == 1), (col*W, row*H))
    mattes.save(destination/"alpha-mattes.png")
    # The video is encoded from the decoded final-sheet GIF, with no audio.
    import imageio_ffmpeg
    subprocess.run([imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
                    "-i", str(destination/"all-states.gif"), "-an", "-c:v", "libx264",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(destination/"all-states.mp4")], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="previous V2 PNG for comparisons without Git history")
    parser.add_argument("--output", type=Path, default=ROOT/SHEET)
    parser.add_argument("--work-dir", type=Path, default=ROOT/"tmp/build-v2-r2")
    parser.add_argument("--skip-previews", action="store_true")
    args = parser.parse_args()
    output = build(args.output, args.work_dir)
    if not args.skip_previews:
        source_data = original_bytes(args.source)
        preview(Image.open(io.BytesIO(source_data)), output, ROOT/"assets/previews")
    print(json.dumps({"output_sha256": digest(args.output.read_bytes()),
                      "revision": "V2 revision 2", "generated_animation_frames": 57,
                      "regenerated_look_frames": 16}, indent=2))


if __name__ == "__main__":
    main()
