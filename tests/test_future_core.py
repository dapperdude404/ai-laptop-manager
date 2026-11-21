"""Future Tools safety contracts; no Windows or real disk needed for tests."""
from pathlib import Path
import tempfile
import unittest

from future_core import (
    RECOVERY_EXTENSIONS, REPAIR_PRESETS, copy_file_no_overwrite,
    list_directory, recovery_plan, repair_command
)

class V2SafetyTests(unittest.TestCase):
    def test_no_same_volume_recovery(self):
        with self.assertRaises(ValueError):
            recovery_plan("E:", "E:", "Photos")
        with self.assertRaises(ValueError):
            recovery_plan("E: & del *", "D:", "Photos")
        with self.assertRaises(ValueError):
            recovery_plan("E:", "D:", "invalid")
    
    def test_recovery_command_valid(self):
        plan = recovery_plan("f:", "g:", "Photos + videos")
        self.assertEqual(plan["source"], "F:")
        self.assertIn("*.mp4", plan["command"])
        self.assertIn("*.jpg", plan["command"])
        self.assertNotIn("format", plan["command"].lower())

    def test_repair_allowlist(self):
        for name, item in REPAIR_PRESETS.items():
            self.assertEqual(repair_command(name)["read_only"], item["read_only"])
        self.assertEqual(repair_command("CHKDSK read-only", drive="E:")["args"],
                         ["chkdsk.exe", "E:"])
        with self.assertRaises(ValueError):
            repair_command("format c:")

    def test_no_overwrite_and_original_preserved(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            src = Path(first) / "family-photo.jpg"
            src.write_bytes(b"test data")
            path, entries, clipped = list_directory(first)
            self.assertEqual(len(entries), 1)
            self.assertFalse(clipped)
            created = copy_file_no_overwrite(src, second)
            self.assertEqual(created.read_bytes(), b"test data")
            self.assertEqual(src.read_bytes(), b"test data")
            with self.assertRaises(FileExistsError):
                copy_file_no_overwrite(src, second)

    def test_no_symlink_copy(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as other:
            f = Path(root) / "target"
            f.write_bytes(b"data")
            link = Path(root) / "link"
            try:
                link.symlink_to(f)
            except (OSError, NotImplementedError):
                self.skipTest("OS disallows symlinks")
            with self.assertRaises(ValueError):
                copy_file_no_overwrite(link, other)

if __name__ == "__main__":
    unittest.main()
