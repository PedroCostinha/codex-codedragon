"""Regression tests: reject corrupt release assets without changing the release."""
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from build_v2 import ROOT, SHEET, original_bytes
from validate_v2 import validate


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
            result = validate(target, self.manifest, self.source)
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
        self.rejects(image, "sixteen look poses")

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
