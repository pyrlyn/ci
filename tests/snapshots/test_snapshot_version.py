import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "tools" / "snapshots"))
import snapshot_version as sv  # noqa: E402


class KeyTests(unittest.TestCase):
    def test_parse_xcode(self):
        self.assertEqual(sv.parse_xcode("Xcode 27.1\nBuild version 27A9275\n"), ("27.1", "27A9275"))

    def test_key(self):
        self.assertEqual(
            sv.compute_key("Xcode 27.1\nBuild version 27A9275\n", "27.0.1"),
            "xcode27.1-27A9275-macos27.0.1",
        )

    def test_macos_patch_is_padded(self):
        self.assertEqual(sv.normalise_macos("27.0"), "27.0.0")
        self.assertEqual(sv.normalise_macos("27"), "27.0.0")

    def test_garbage_raises(self):
        with self.assertRaises(ValueError):
            sv.parse_xcode("nope")


if __name__ == "__main__":
    unittest.main()
