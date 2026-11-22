import unittest
from smart_engine import SCHEMA, advice, validate_profile, profile_from_snapshot, compare_profiles

def p(**kw):
    d=dict(schema=SCHEMA,cpu_logical_cores=8,ram_gib=16,
           system_drive_free_pct=11.5,cpu_utilization_pct=15,
           ram_utilization_pct=75)
    d.update(kw)
    return d

class SmartEngineTests(unittest.TestCase):
    def test_low_disk_evidence(self):
        alerts=advice(p())
        self.assertEqual(alerts[0]["severity"],"Medium")
        self.assertFalse(alerts[0]["automatic_change"])
    def test_high_ram_is_review_not_proven_leak(self):
        self.assertEqual(advice(p(ram_utilization_pct=92))[-1]["severity"],"Review")
    def test_no_fake_composite_score(self):
        out=advice(p(system_drive_free_pct=50,ram_utilization_pct=40))
        self.assertEqual(out[0]["severity"],"Info")
    def test_profile_export_strips_identifiers(self):
        d=p(serial_number="sensitive",hostname="private",username="secret",email="x@y.z")
        v=validate_profile(d)
        self.assertEqual(set(v),{SCHEMA and "schema","cpu_logical_cores","ram_gib",
                                  "system_drive_free_pct","cpu_utilization_pct","ram_utilization_pct"})
        self.assertNotIn("hostname",v)
    def test_bad_numbers_rejected(self):
        for invalid in (float("nan"),float("inf"),-20,120):
            with self.subTest(value=invalid):
                with self.assertRaises(ValueError): validate_profile(p(system_drive_free_pct=invalid))
    def test_derived_drive_is_c(self):
        snapshot={"drives":[{"name":"D:\\","free":900,"total":1000},
                            {"name":"C:\\","free":125,"total":1000}],
                  "cpu_percent":7,"ram_percent":66}
        v=profile_from_snapshot(snapshot,logical_cores=8,ram_total_bytes=16*1024**3)
        self.assertEqual(v["system_drive_free_pct"],12.5)
    def test_compare_requires_two_to_four(self):
        with self.assertRaises(ValueError):compare_profiles(p(),[p()])
        v=compare_profiles(p(),[p(ram_gib=8),p(ram_gib=32)])
        self.assertEqual(v["count"],2)
        self.assertEqual(next(x for x in v["rows"] if x["metric"]=="ram_gib")["peer_median"],20)
