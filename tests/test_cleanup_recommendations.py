"""Safety tests for V2.2 read-only recommendations."""
import unittest
from cleanup_recommendations import classify_folder, make_recommendations

class RecommendationTests(unittest.TestCase):
    def sample(self):
        return {"complete": True, "unreadable": 0, "reason": None, "folders": [
            {"path": r"C:\\Users\\Me\\Videos", "size": 4_000_000_000},
            {"path": r"C:\\Windows", "size": 2_000_000_000},
            {"path": r"C:\\Users\\Me\\Projects\\.git", "size": 3_000_000},
        ]}

    def test_low_space(self):
        result = make_recommendations(self.sample(), free_bytes=13, total_bytes=235)
        self.assertTrue(result["low_space"])
        self.assertIsNone(result["reclaimable_bytes"])

    def test_non_destructive(self):
        result = make_recommendations(self.sample())
        self.assertTrue(all(not x["can_auto_clean"] for x in result["folders"]))
        self.assertEqual(result["folders"][0]["category"], "personal")

    def test_system_protection(self):
        self.assertEqual(classify_folder(r"C:\\Windows\\System32")[0], "system-managed")
        self.assertEqual(classify_folder(r"C:\\Program Files\\MyApp")[0], "system-managed")

    def test_developer_data(self):
        self.assertEqual(classify_folder("/home/me/.venv")[0], "development")

    def test_incomplete_scan(self):
        scan = self.sample()
        scan["complete"] = False
        scan["reason"] = "file limit reached"
        output = make_recommendations(scan)
        self.assertFalse(output["scan_complete"])
        self.assertEqual(output["scan_reason"], "file limit reached")

    def test_bad_drive_values(self):
        with self.assertRaises(ValueError):
            make_recommendations(self.sample(), free_bytes=500, total_bytes=235)
        with self.assertRaises(ValueError):
            make_recommendations(self.sample(), free_bytes=1)
        with self.assertRaises(ValueError):
            make_recommendations(self.sample(), limit=0)

    def test_not_claiming_recovery(self):
        result = make_recommendations(self.sample(), free_bytes=100, total_bytes=235)
        self.assertFalse(result["low_space"])
        self.assertIn("NOT reclaimable", result["disclaimer"])
