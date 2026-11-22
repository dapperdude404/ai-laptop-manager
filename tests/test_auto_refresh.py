"""Pure scheduling policy tests; do not perform system repair or scanning."""
import unittest
from auto_refresh import valid_interval, should_refresh

class AutoRefreshTests(unittest.TestCase):
    def test_intervals(self):
        self.assertEqual(valid_interval("30"), 30)
        for invalid in ("1","0","5","999","abc",None):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                valid_interval(invalid)

    def test_paused_does_not_run(self):
        self.assertFalse(should_refresh(enabled=False, elapsed=120, interval=10, busy=False))

    def test_no_overlap(self):
        self.assertFalse(should_refresh(enabled=True, elapsed=120, interval=10, busy=True))

    def test_respects_interval(self):
        self.assertFalse(should_refresh(enabled=True, elapsed=9, interval=10, busy=False))
        self.assertTrue(should_refresh(enabled=True, elapsed=10, interval=10, busy=False))
