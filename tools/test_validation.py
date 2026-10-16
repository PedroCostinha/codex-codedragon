"""Regression tests: reject corrupt release assets without changing the release."""
import tempfile
import unittest
import json
import shutil
from pathlib import Path

from PIL import Image

from build_v2 import ROOT, ART, SHEET, original_bytes, verify_sources
from validate_v2 import validate, evidence_matches


class ReleaseValidation(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = original_bytes()
        cls.release = Image.open(ROOT/SHEET).copy()
        cls.manifest = ROOT/"pets/codedragon/pet-manifest.json"

    def rejects(self, image, expected_error):
        with tempfile.TemporaryDirectory(prefix="codedragon-qa-") as directory:
            target = Path(directory)/"spritesheet.png"
            image.save(target)
            manifest = Path(directory)/"pet-manifest.json"
            shutil.copyfile(self.manifest, manifest)
            result = validate(target, manifest, self.source)
            self.assertFalse(result["ok"])
            self.assertTrue(any(expected_error in e for e in result["errors"]), result["errors"])

    def test_release_passes(self):
        self.assertTrue(validate(ROOT/SHEET, self.manifest, self.source)["ok"])

    def test_wrong_dimensions_rejected(self):
        self.rejects(self.release.crop((0, 0, 1536, 1872)), "v2 dimensions")

    def test_missing_alpha_rejected(self):
        self.rejects(self.release.convert("RGB"), "RGBA")

    def test_missing_pose_rejected(self):
        image = self.release.copy()
        image.paste((0, 0, 0, 0), (0, 0, 192, 208))
        self.rejects(image, "Required frame 0/0 is empty")

    def test_unused_cell_occupied_rejected(self):
        image = self.release.copy()
        image.putpixel((7*192+70, 100), (20, 80, 255, 255))
        self.rejects(image, "Unused cell 0/7")

    def test_changed_look_rejected(self):
        image = self.release.copy()
        image.putpixel((80, 9*208+100), (255, 0, 0, 255))
        self.rejects(image, "Approved artwork differs at 9/0")

    def test_old_horned_look_rejected(self):
        import io
        previous = Image.open(io.BytesIO(self.source))
        image = self.release.copy()
        image.paste(previous.crop((0, 9*208, 192, 10*208)), (0, 9*208))
        self.rejects(image, "Approved artwork differs at 9/0")

    def test_old_work_without_computer_rejected(self):
        import io
        previous = Image.open(io.BytesIO(self.source))
        image = self.release.copy()
        image.paste(previous.crop((0, 7*208, 192, 8*208)), (0, 7*208))
        self.rejects(image, "Approved artwork differs at 7/0")

    def test_reversed_locomotion_rejected(self):
        image = self.release.copy()
        image.paste(self.release.crop((0, 2*208, 192, 3*208)), (0, 208))
        self.rejects(image, "Approved artwork differs at 1/0")

    def test_stale_success_report_rejected(self):
        self.assertFalse(evidence_matches({"ok": True, "sha256": "0"*64}, ROOT/SHEET))

    def test_source_art_tampering_rejected(self):
        with tempfile.TemporaryDirectory(prefix="codedragon-source-") as directory:
            art = Path(directory)
            shutil.copytree(ART, art, dirs_exist_ok=True)
            (art/"running.png").write_bytes(b"replaced art")
            with self.assertRaisesRegex(ValueError, "Source checksum mismatch"):
                verify_sources(art)

    def test_manifest_look_order_rejected(self):
        with tempfile.TemporaryDirectory(prefix="codedragon-manifest-") as directory:
            manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
            manifest["lookDirections"][0]["degrees"] = 90
            path = Path(directory)/"pet-manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            result = validate(ROOT/SHEET, path, self.source)
            self.assertIn("Look positions/order changed", result["errors"])

    def test_clipping_rejected(self):
        image = self.release.copy()
        image.putpixel((0, 80), (20, 80, 255, 255))
        self.rejects(image, "safety margin")

    def test_hidden_rgb_rejected(self):
        image = self.release.copy()
        image.putpixel((0, 0), (255, 255, 255, 0))
        self.rejects(image, "Hidden RGB")

    def test_opaque_background_rejected(self):
        image = self.release.copy()
        image.putalpha(255)
        self.rejects(image, "safety margin")


if __name__ == "__main__":
    unittest.main(verbosity=2)
