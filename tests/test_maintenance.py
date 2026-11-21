import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch
from maintenance import human_bytes, largest_files, temp_candidates, _strict_descendant, recycle_selected_temp_files

class MaintenanceTests(unittest.TestCase):
    def test_human_bytes(self):
        self.assertEqual(human_bytes(1024), "1.0 KiB")
        self.assertEqual(human_bytes(1024 ** 3), "1.0 GiB")
        self.assertEqual(human_bytes(None), "Unknown")

    def test_large_files_ranked_and_non_destructive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "small.txt").write_bytes(b"a" * 10)
            (root / "large.txt").write_bytes(b"a" * 250)
            ranked, count, truncated = largest_files(root, limit=1)
            self.assertEqual(count, 2)
            self.assertFalse(truncated)
            self.assertEqual(Path(ranked[0]["path"]).name, "large.txt")
            self.assertTrue((root / "large.txt").exists())

    def test_age_filtering_and_path_protection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            old = root / "older.tmp"
            fresh = root / "today.tmp"
            old.write_bytes(b"old")
            fresh.write_bytes(b"new")
            t = time.time() - 30 * 86400
            os.utime(old, (t, t))
            candidates, count, _ = temp_candidates(root=root)
            self.assertEqual(count, 2)
            self.assertEqual([Path(c["path"]).name for c in candidates], ["older.tmp"])
            self.assertFalse(_strict_descendant(root / ".." / "outside", root))

    def test_recycle_requires_old_file_under_temp_root(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as outside:
            root = Path(temp)
            allowed = root / "old.tmp"
            fresh = root / "recent.tmp"
            external = Path(outside) / "outside.tmp"
            for file in (allowed, fresh, external):
                file.write_bytes(b"data")
            t = time.time() - 18 * 86400
            for old in (allowed, external): os.utime(old, (t, t))
            with patch("send2trash.send2trash") as recycle:
                moved, failed = recycle_selected_temp_files([str(allowed), str(fresh), str(external)], root=root)
                self.assertEqual(moved, [str(allowed)])
                self.assertEqual(len(failed), 2)
                recycle.assert_called_once_with(str(allowed))

if __name__ == "__main__":
    unittest.main()
