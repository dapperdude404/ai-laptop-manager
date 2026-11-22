"""Read-only storage tests; safe to run without Windows or real disks."""
import os
from pathlib import Path
import tempfile
import threading
import unittest
from storage_insights import scan_sizes, find_duplicates

class StorageInsightsTests(unittest.TestCase):
    def test_count_folder_and_rank_files(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "Apps").mkdir()
            (root / "Apps" / "large").write_bytes(b"x" * 2000)
            (root / "small").write_bytes(b"y" * 12)
            result = scan_sizes(root)
            self.assertTrue(result["complete"])
            self.assertEqual(result["files"], 2)
            self.assertEqual(result["bytes"], 2012)
            self.assertEqual(result["folders"][0]["size"], 2000)
            self.assertEqual(Path(result["largest"][0]["path"]).name, "large")

    def test_cancel(self):
        with tempfile.TemporaryDirectory() as temp:
            event = threading.Event()
            event.set()
            result = scan_sizes(temp, cancel=event)
            self.assertFalse(result["complete"])
            self.assertEqual(result["reason"], "cancelled")

    def test_scan_limit_reports_incomplete(self):
        with tempfile.TemporaryDirectory() as temp:
            for index in range(3):
                (Path(temp) / str(index)).write_text("data")
            result = scan_sizes(temp, max_files=1)
            self.assertEqual(result["files"], 1)
            self.assertFalse(result["complete"])

    def test_no_reparse_symlink_following(self):
        with tempfile.TemporaryDirectory() as root, tempfile.TemporaryDirectory() as out:
            (Path(root) / "real").write_text("safe")
            (Path(out) / "outside").write_text("hidden")
            try:
                (Path(root) / "linked").symlink_to(out, target_is_directory=True)
            except OSError:
                self.skipTest("symlink permission restricted")
            result = scan_sizes(root)
            self.assertEqual(result["files"], 1)
            self.assertEqual(result["links"], 1)

    def test_duplicate_detection(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            for name in ("x","y"):
                (root / name).write_bytes(b"same"*300)
            (root / "z").write_bytes(b"other"*300)
            result = find_duplicates(root, min_size=100)
            self.assertTrue(result["complete"])
            self.assertEqual(len(result["groups"]), 1)
            self.assertEqual(len(result["groups"][0]["paths"]), 2)
            self.assertTrue((root/"x").exists())

    def test_hard_link_not_a_duplicate(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"one").write_bytes(b"x"*1200)
            try:
                os.link(root/"one",root/"two")
            except OSError:
                self.skipTest("hard links restricted")
            result=find_duplicates(root,min_size=100)
            self.assertEqual(result["groups"],[])

    def test_hash_limit(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            (root/"one").write_bytes(b"x"*1200)
            (root/"two").write_bytes(b"x"*1200)
            result=find_duplicates(root,min_size=100,hash_limit=100)
            self.assertFalse(result["complete"])
            self.assertEqual(result["reason"],"hash budget reached")
