"""Articulate the approved V1 artwork without redrawing the character.

Authoring only. Source pixels come from the immutable original Git commit, or
an explicit --source PNG. Every output frame is sampled once in premultiplied
alpha. No sprite mirroring, facial repainting, or procedural replacement art.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ORIGINAL_COMMIT = "cd9aad5"
SOURCE_SHA256 = "f81bdbb0d2701f21602a1b4cf5950026e46895235f680aa401d58d48e49753bd"
SHEET = "pets/codedragon/spritesheet.png"
NAMES = ["idle", "running-right", "running-left", "waving", "jumping",
         "failed", "waiting", "running", "review", "look-1", "look-2"]
COUNTS = [6, 8, 8, 4, 5, 8, 6, 6, 6, 8, 8]
# Demonstration timing only. The native player controls its own cadence.
DURATIONS = [160, 85, 85, 180, 150, 150, 220, 95, 200, 160, 160]
W, H = 192, 208
Y, X = np.mgrid[:H, :W].astype(float)


def original_bytes(source=None):
    if source:
        data = Path(source).read_bytes()
    else:
        data = subprocess.check_output(
            ["git", "show", f"{ORIGINAL_COMMIT}:{SHEET}"], cwd=ROOT)
    if hashlib.sha256(data).hexdigest() != SOURCE_SHA256:
        raise ValueError("Source must be the original sheet; do not articulate V2 a second time")
    return data


def cell(image, row, column):
    return image.crop((column*W, row*H, (column+1)*W, (row+1)*H))


def smooth(a, b, value):
    t = np.clip((value-a)/(b-a), 0, 1)
    return t*t*(3-2*t)


def region(cx, cy, rx, ry):
    """Compact support, zero displacement beyond each anatomical region."""
    radius = np.sqrt(((X-cx)/rx)**2 + ((Y-cy)/ry)**2)
    return 1-smooth(0.25, 1, radius)


def sample_once(image, dx, dy):
    """Inverse map with bilinear filtering in premultiplied RGBA.

    Sampling RGB independently from alpha creates dark fringes. Multiplying
    before sampling and unpremultiplying afterward keeps the original edge color.
    """
    rgba = np.asarray(image, dtype=float)/255
    rgba[:, :, :3] *= rgba[:, :, 3:4]
    sx, sy = X-dx, Y-dy
    x0, y0 = np.floor(sx).astype(int), np.floor(sy).astype(int)
    fx, fy = sx-x0, sy-y0
    result = np.zeros((H, W, 4), dtype=float)
    for ox, oy, weight in [(0, 0, (1-fx)*(1-fy)), (1, 0, fx*(1-fy)),
                            (0, 1, (1-fx)*fy), (1, 1, fx*fy)]:
        xx, yy = x0+ox, y0+oy
        inside = (xx >= 0) & (xx < W) & (yy >= 0) & (yy < H)
        result[inside] += rgba[yy[inside], xx[inside]]*weight[inside, None]
    np.divide(result[:, :, :3], result[:, :, 3:4],
              out=result[:, :, :3], where=result[:, :, 3:4] > 0)
    output = np.clip(np.rint(result*255), 0, 255).astype(np.uint8)
    output[output[:, :, 3] == 0] = 0
    return Image.fromarray(output)


def articulate(image, *, breath=0, tilt=0, tail=0, wings=0, hands=0,
               wave=0, lean=0, gaze=0, stride=0, head_drop=0, wing_open=0):
    """Local motion around neck, shoulders and tail root; hoodie logo stays rigid."""
    dx, dy = np.zeros_like(X), np.zeros_like(Y)
    # Feet stay anchored while rib cage, neck and head rise with breathing.
    upper = 1-smooth(166, 199, Y)
    dy -= breath*upper
    dx += breath*0.22*(X-96)/24*region(96, 159, 34, 29)
    head = 1-smooth(130, 143, Y)
    angle = np.deg2rad(tilt)
    # Rigid head turn, feathered only at the neck; no head rescaling.
    dx += ((np.cos(angle)-1)*(X-96)-np.sin(angle)*(Y-135))*head
    dy += (np.sin(angle)*(X-96)+(np.cos(angle)-1)*(Y-135))*head
    dx += lean*head
    dy += head_drop*head
    # Closed/half-closed frames retain their existing eyelid artwork.
    for ex in (82, 113):
        dx += gaze*region(ex, 117, 9, 8)
    tail_weight = smooth(91, 119, X)*smooth(173, 188, Y)
    dy += tail*tail_weight
    dx += tail*0.32*tail_weight
    left_wing = (1-smooth(65, 80, X))*smooth(126, 141, Y)*(1-smooth(166, 179, Y))
    right_wing = smooth(115, 130, X)*smooth(126, 141, Y)*(1-smooth(166, 179, Y))
    dy += wings*(left_wing+right_wing)
    dx += wing_open*(right_wing-left_wing)
    # Alternating typing hands, attached by a taper along the sleeves.
    dx -= hands*0.35*region(77, 156, 15, 17)
    dy += hands*region(77, 156, 15, 17)
    dx += hands*0.35*region(116, 156, 15, 17)
    dy -= hands*region(116, 156, 15, 17)
    # Waving paw and forearm from the approved waving row.
    dx += wave*region(62, 126, 20, 24)
    dy -= wave*0.55*region(62, 126, 20, 24)
    # Separate foot controls strengthen existing alternating directional poses.
    dx += stride*region(75, 186, 20, 19)
    dx -= stride*region(123, 186, 20, 19)
    # Preserve the chest emblem's geometry; no horizontal flip or stretching.
    logo = region(96, 155, 17, 16)
    dx *= 1-logo
    dy *= 1-logo
    return sample_once(image, dx, dy)


def place(image, baseline):
    bbox = image.getbbox()
    offset = round(baseline-bbox[3])
    # Reject overflow instead of silently discarding anatomy.
    if bbox[1]+offset < 5 or bbox[3]+offset > H-4:
        raise ValueError(f"Unsafe vertical placement: {bbox}, offset {offset}")
    output = Image.new("RGBA", (W, H))
    output.alpha_composite(image, (0, offset))
    return output


def build(source):
    output = source.copy()
    for row, count in enumerate(COUNTS[:9]):
        for col in range(count):
            phase = 2*np.pi*col/count
            sine, cosine = np.sin(phase), np.cos(phase)
            src_col = [0, 1, 3, 2, 4][col] if row == 4 else col
            frame = cell(source, row, src_col)
            baseline = 200
            if row == 0:
                frame = articulate(frame, breath=1.8*sine, tail=2.8*np.sin(phase-0.5),
                                   wings=2.1*sine, tilt=0.7*sine, gaze=0.55*sine)
            elif row in (1, 2):
                sign = 1 if row == 1 else -1
                # Use each direction's original artwork, never mirror the emblem.
                frame = articulate(frame, wings=4.2*sine, tail=3.7*np.sin(phase-0.6),
                                   stride=sign*3.1*sine, lean=sign*0.8)
                baseline = 198+2*np.cos(2*phase)
            elif row == 3:
                frame = articulate(frame, wave=[-2.5, 4.5, -4.5, 2.5][col],
                                   tilt=[-1.5, 1, -1, 0][col], tail=3*sine, wings=1.8*sine)
            elif row == 4:
                # Anticipation -> lift -> held apex -> attached flame -> landing.
                # Swap original poses 2/3 to put the blue breath on the descent.
                frame = articulate(frame, wing_open=[-1, 5, 9, 5, -1][col],
                                   wings=[2, -4, -7, 1, 2][col],
                                   tail=[2, -3, -6, -2, 1][col],
                                   tilt=[-1, -2, -3, -1, 0][col])
                baseline = [200, 171, 145, 169, 200][col]
            elif row == 5:
                frame = articulate(frame, head_drop=[-0.7, 1, 3, 4, 4, 2, 1, 0][col],
                                   tilt=[-1.3, 1, 2, 3, 2, 1, 0, 0][col],
                                   wings=[0, 1, 3, 4, 4, 3, 1, 0][col],
                                   tail=[0, 2, 4, 6, 6, 4, 2, 0][col], breath=0.6*sine)
                # Tint only the original neutral gray nose smoke, not the dragon.
                pixels = np.asarray(frame).copy()
                rgb = pixels[:, :, :3].astype(float)
                smoke = (X > 114) & (Y > 115) & (Y < 151) & (rgb.min(2) > 95) & ((rgb.max(2)-rgb.min(2)) < 38)
                rgb[smoke] *= [0.73, 0.84, 1.0]
                pixels[:, :, :3] = np.clip(rgb, 0, 255).astype(np.uint8)
                frame = Image.fromarray(pixels)
            elif row == 6:
                frame = articulate(frame, breath=1.1*sine, wings=1.8*sine,
                                   tail=2.8*np.sin(phase-0.6), tilt=0.8*sine, gaze=0.45*sine)
            elif row == 7:
                frame = articulate(frame, hands=[-4, 4, -3.5, 4, -4, 3.5][col],
                                   head_drop=1.8, lean=0.7, tilt=0.5*sine,
                                   wings=2.5*sine, tail=2.8*np.sin(phase-0.6), breath=0.65*cosine)
            else:
                frame = articulate(frame, tilt=[-2, -3, -2, 0.6, 1, -1][col],
                                   gaze=0.65*sine, hands=0.8*sine,
                                   tail=2.2*sine, wings=0.8*sine, breath=0.7*sine)
            frame = place(frame, baseline)
            output.paste(frame, (col*W, row*H))
    # Rows 9 and 10 and all unused cells remain byte-for-byte identical pixels.
    return output


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
            ImageDraw.Draw(pair).text((8, 6), "Original                 V2", fill="white", font=font)
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path)
    args = parser.parse_args()
    data = original_bytes(args.source)
    source = Image.open(io.BytesIO(data))
    if source.mode != "RGBA" or source.size != (1536, 2288):
        raise SystemExit("Expected the original RGBA v2 sheet")
    output = build(source)
    output.save(ROOT/SHEET, optimize=True)
    encoded = Image.open(ROOT/SHEET)
    preview(source, encoded, ROOT/"assets/previews")
    print(json.dumps({"source_sha256": hashlib.sha256(data).hexdigest(),
                      "output_sha256": hashlib.sha256((ROOT/SHEET).read_bytes()).hexdigest(),
                      "modified_animation_frames": 57, "preserved_look_frames": 16}, indent=2))


if __name__ == "__main__":
    main()
