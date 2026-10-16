"""Check the encoded release, original-art invariants, manifest and previews.

This is local artifact QA, not a replacement for the Pets official preflight or
human motion review. Exits nonzero on failure and writes reproducible evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence

from build_v2 import ROOT, SHEET, COUNTS, NAMES, ORIGINAL_COMMIT, cell, original_bytes


def digest(data):
    return hashlib.sha256(data).hexdigest()


def validate(sheet_path, manifest_path, source_data):
    errors = []
    def check(condition, message):
        if not condition:
            errors.append(message)

    data = sheet_path.read_bytes()
    with Image.open(io.BytesIO(data)) as probe:
        check(probe.format == "PNG", "Release must be PNG")
        probe.verify()
    image = Image.open(io.BytesIO(data))
    check(image.mode == "RGBA", "Release must have RGBA channels")
    check(image.size == (1536, 2288), "Release must retain v2 dimensions")
    check(0 < len(data) <= 20*1024*1024, "Release exceeds Pets size limit")
    if image.mode != "RGBA" or image.size != (1536, 2288):
        return {"ok": False, "errors": errors}
    source = Image.open(io.BytesIO(source_data))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    layout = manifest["spritesheetLayout"]
    check(layout == {"columns": 8, "rows": 11, "cellWidth": 192, "cellHeight": 208,
                     "lookDirectionCount": 16, "neutralLookFrame": {"rowIndex": 0, "columnIndex": 0}},
          "Manifest geometry or neutral cell changed")
    check((manifest_path.parent/manifest["spritesheetPath"]).resolve() == sheet_path.resolve(),
          "Manifest does not point at validated sheet")
    check(manifest["lookDirections"] == [
        {"degrees": i*22.5, "rowIndex": 9+i//8, "columnIndex": i%8}
        for i in range(16)], "Look positions/order changed")
    check(np.array_equal(np.asarray(image)[9*208:], np.asarray(source)[9*208:]),
          "The original sixteen look poses must be preserved exactly")
    pixels = np.asarray(image)
    check(not np.any(pixels[pixels[:, :, 3] == 0, :3]), "Hidden RGB under zero alpha")
    occupied, empty, changed = 0, 0, 0
    rows = []
    for row, count in enumerate(COUNTS):
        frames = []
        for col in range(8):
            frame = cell(image, row, col)
            alpha = np.asarray(frame)[:, :, 3]
            if col >= count:
                check(not np.any(alpha), f"Unused cell {row}/{col} is occupied")
                empty += 1
                continue
            occupied += 1
            bbox = frame.getbbox()
            check(bbox is not None, f"Required frame {row}/{col} is empty")
            if bbox is None:
                continue
            margin = min(bbox[0], bbox[1], 192-bbox[2], 208-bbox[3])
            check(margin >= 4, f"Frame {row}/{col} touches safety margin")
            check(np.count_nonzero(alpha) > 400, f"Frame {row}/{col} is too sparse")
            old_col = [0, 1, 3, 2, 4][col] if row == 4 else col
            old = cell(source, row, old_col)
            different = not np.array_equal(np.asarray(frame), np.asarray(old))
            changed += int(row < 9 and different)
            # Register only the vertical baseline, then ensure the work contains
            # articulated pixel changes rather than translating an old frame.
            aligned = Image.new("RGBA", (192, 208))
            aligned.alpha_composite(old, (0, bbox[3]-old.getbbox()[3]))
            nonrigid_difference = int(np.count_nonzero(np.any(
                np.abs(np.asarray(frame).astype(int)-np.asarray(aligned).astype(int)) > 8, axis=2)))
            if row < 9:
                check(nonrigid_difference > 50, f"Frame {row}/{col} has no material articulated change")
            frames.append({"frame": col, "bbox": list(bbox), "margin_pixels": margin,
                           "visible_pixels": int(np.count_nonzero(alpha)),
                           "pixel_changes_after_baseline_registration": nonrigid_difference})
        # No repeated poses within an animation. Alpha-aware temporal difference
        # is evidence to review, not a claim of motion quality by itself.
        sequence = [np.asarray(cell(image, row, c)).astype(float) for c in range(count)]
        signatures = {digest(frame.astype(np.uint8).tobytes()) for frame in sequence}
        check(len(signatures) == count, f"Duplicated frames in {NAMES[row]}")
        for frame in sequence:
            frame[:, :, :3] *= frame[:, :, 3:4]/255
        deltas = [float(np.abs(sequence[c]-sequence[(c+1)%count]).mean()) for c in range(count)]
        rows.append({"state": NAMES[row], "frames": frames,
                     "successive_mean_absolute_differences_including_loop": deltas})
    check(occupied == 73 and empty == 15, "Incorrect occupied/unused frame count")
    check(changed == 57, "All 57 animation frames must have actual changes")
    if any(cell(image, r, c).getbbox() is None for r, n in enumerate(COUNTS) for c in range(n)):
        return {"ok": False, "sha256": digest(data), "errors": errors, "rows": rows}
    jump_baselines = [cell(image, 4, c).getbbox()[3] for c in range(5)]
    original_baselines = [cell(source, 4, c).getbbox()[3] for c in range(5)]
    idle_baselines = [cell(image, 0, c).getbbox()[3] for c in range(6)]
    lift = max(jump_baselines)-min(jump_baselines)
    check(lift > max(original_baselines)-min(original_baselines), "Jump lift did not improve")
    check(jump_baselines[0] == jump_baselines[-1] == idle_baselines[0],
          "Jump does not return to the resting baseline")
    check(jump_baselines[0] > jump_baselines[1] > jump_baselines[2] < jump_baselines[3] < jump_baselines[4],
          "Jump ascent/descent is not coherent")
    previews = ROOT/"assets/previews"
    for row, count in enumerate(COUNTS):
        with Image.open(previews/f"{NAMES[row]}.gif") as gif:
            check(gif.n_frames == count, f"Preview count differs from atlas: {NAMES[row]}")
            check(gif.size == (192, 208), f"Preview cell size mismatch: {NAMES[row]}")
            check(gif.info.get("loop") == 0, f"Preview does not loop: {NAMES[row]}")
            for c, gf in enumerate(ImageSequence.Iterator(gif)):
                check(gf.info.get("duration", 0) > 0, "Missing preview timing")
                # GIF is lossy indexed color, so compare the decoded motion pose
                # to the matching sheet composite with a bounded palette error.
                bg = Image.new("RGBA", (192, 208), (29, 36, 49, 255))
                bg.alpha_composite(cell(image, row, c))
                error = float(np.abs(np.asarray(gf.convert("RGB")).astype(float)
                                    -np.asarray(bg.convert("RGB")).astype(float)).mean())
                check(error < 3, f"GIF does not reflect encoded sheet: {NAMES[row]}/{c}")
    return {"ok": not errors, "sheet": SHEET, "sha256": digest(data),
            "source_commit": ORIGINAL_COMMIT, "source_sha256": digest(source_data),
            "format": image.format, "mode": image.mode, "dimensions": list(image.size),
            "encoded_bytes": len(data), "occupied_cells": occupied, "transparent_unused_cells": empty,
            "modified_animation_frames": changed, "unchanged_look_frames": 16,
            "jump": {"original_baselines": original_baselines, "v2_baselines": jump_baselines,
                     "original_lift_pixels": max(original_baselines)-min(original_baselines),
                     "v2_lift_pixels": lift, "landing_delta_pixels": abs(jump_baselines[-1]-idle_baselines[0])},
            "rows": rows, "errors": errors,
            "limitations": ["Does not test the installed native player or account import",
                            "Pixel and continuity metrics do not replace visual inspection"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sheet", type=Path, default=ROOT/SHEET)
    parser.add_argument("--source", type=Path)
    parser.add_argument("--json-out", type=Path, default=ROOT/"assets/qa/local-validation.json")
    args = parser.parse_args()
    try:
        result = validate(args.sheet, ROOT/"pets/codedragon/pet-manifest.json", original_bytes(args.source))
    except (OSError, ValueError, KeyError, TypeError) as exc:
        result = {"ok": False, "errors": [str(exc)]}
    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(result, indent=2)+"\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "rows"}, indent=2))
    raise SystemExit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
