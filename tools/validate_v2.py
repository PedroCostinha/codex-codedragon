"""Check encoded bytes, approved artwork, manifest and derived previews.

Frame hashes pin visually reviewed pixels; they cannot recognize horns or typing.
"""
from __future__ import annotations
import argparse
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageSequence

from build_v2 import ROOT, ART, SHEET, COUNTS, NAMES, ORIGINAL_COMMIT, cell, original_bytes, digest


def validate(sheet_path, manifest_path, source_data, *, previews_dir=None, approved_path=None):
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
        return {"ok": False, "sha256": digest(data), "errors": errors}
    source = Image.open(io.BytesIO(source_data))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    check(manifest["spritesheetLayout"] == {
        "columns": 8, "rows": 11, "cellWidth": 192, "cellHeight": 208,
        "lookDirectionCount": 16, "neutralLookFrame": {"rowIndex": 0, "columnIndex": 0}},
        "Manifest geometry or neutral cell changed")
    check((manifest_path.parent/manifest["spritesheetPath"]).resolve() == sheet_path.resolve(),
          "Manifest does not point at validated sheet")
    check(manifest["lookDirections"] == [
        {"degrees": i*22.5, "rowIndex": 9+i//8, "columnIndex": i%8} for i in range(16)],
        "Look positions/order changed")
    approved = json.loads((approved_path or ART/"approved-frames.json").read_text(encoding="utf-8"))
    pixels = np.asarray(image)
    check(not np.any(pixels[pixels[:, :, 3] == 0, :3]), "Hidden RGB under zero alpha")
    occupied, empty, changed = 0, 0, 0
    rows = []
    for row, count in enumerate(COUNTS):
        frames, signatures = [], set()
        for col in range(8):
            frame = cell(image, row, col)
            rgba = np.asarray(frame)
            alpha = rgba[:, :, 3]
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
            signature = digest(frame.tobytes())
            check(signature == approved["frames"].get(f"{row}/{col}"),
                  f"Approved artwork differs at {row}/{col}")
            signatures.add(signature)
            changed += int(not np.array_equal(rgba, np.asarray(cell(source, row, col))))
            cyan = (rgba[:, :, 2] > 150) & (rgba[:, :, 1] > 85) & (rgba[:, :, 0] < 120) & (alpha > 32)
            frames.append({"frame": col, "bbox": list(bbox), "margin_pixels": margin,
                           "visible_pixels": int(np.count_nonzero(alpha)),
                           "bright_blue_pixels": int(np.count_nonzero(cyan))})
        check(len(signatures) == count, f"Duplicated frames in {NAMES[row]}")
        sequence = [np.asarray(cell(image, row, c)).astype(float) for c in range(count)]
        for frame in sequence:
            frame[:, :, :3] *= frame[:, :, 3:4]/255
        deltas = [float(np.abs(sequence[c]-sequence[(c+1)%count]).mean()) for c in range(count)]
        rows.append({"state": NAMES[row], "frames": frames, "loop_deltas": deltas})
    if any(cell(image, r, c).getbbox() is None for r, n in enumerate(COUNTS) for c in range(n)):
        return {"ok": False, "sha256": digest(data), "errors": errors, "rows": rows}
    jump = [cell(image, 4, c).getbbox()[3] for c in range(5)]
    idle = cell(image, 0, 0).getbbox()[3]
    check(max(jump)-min(jump) >= 8, "Jump must visibly leave the ground")
    check(abs(jump[0]-idle) <= 12 and abs(jump[-1]-idle) <= 12,
          "Jump landing does not match idle baseline")
    check(jump[2] < jump[0] and jump[2] < jump[-1], "Jump apex must be airborne")
    previews = previews_dir or ROOT/"assets/previews"
    for row, count in enumerate(COUNTS):
        with Image.open(previews/f"{NAMES[row]}.gif") as gif:
            check(gif.n_frames == count, f"Preview count differs from atlas: {NAMES[row]}")
            check(gif.size == (192, 208), f"Preview cell size mismatch: {NAMES[row]}")
            check(gif.info.get("loop") == 0, f"Preview does not loop: {NAMES[row]}")
            for c, gf in enumerate(ImageSequence.Iterator(gif)):
                check(gf.info.get("duration", 0) > 0, "Missing preview timing")
                bg = Image.new("RGBA", (192, 208), (29, 36, 49, 255))
                bg.alpha_composite(cell(image, row, c))
                error = float(np.abs(np.asarray(gf.convert("RGB")).astype(float)
                                    -np.asarray(bg.convert("RGB")).astype(float)).mean())
                check(error < 3, f"GIF does not reflect encoded sheet: {NAMES[row]}/{c}")
    return {"ok": not errors, "sheet": SHEET, "sha256": digest(data),
            "comparison_commit": ORIGINAL_COMMIT, "comparison_sha256": digest(source_data),
            "format": image.format, "mode": image.mode, "dimensions": list(image.size),
            "encoded_bytes": len(data), "occupied_cells": occupied, "transparent_unused_cells": empty,
            "modified_frames": changed, "regenerated_look_frames": 16,
            "jump": {"baselines": jump, "idle_baseline": idle, "lift_pixels": max(jump)-min(jump)},
            "rows": rows, "errors": errors,
            "limitations": ["Native player and installation not tested in this revision",
                            "Frame signatures pin reviewed art; they do not infer visual semantics"]}


def evidence_matches(report, sheet_path):
    return report.get("sha256") == digest(sheet_path.read_bytes())


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
