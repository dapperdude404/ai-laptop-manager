import unittest
from unittest.mock import patch
from power_center import parse_power_plans, change_power_plan, _norm_guid, battery_report

A="381b4222-f694-41f0-9685-ff5bb260df2e"
B="8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c"
LIST=f"""Existing schemes (* Active)
Power Scheme GUID: {A}  (Balanced) *
Power Scheme GUID: {B}  (High performance)
"""

class PowerSafetyTests(unittest.TestCase):
    def test_plan_parser(self):
        plans=parse_power_plans(LIST,f"Power Scheme GUID: {A}  (Balanced)")
        self.assertEqual(len(plans["plans"]),2)
        self.assertTrue(plans["plans"][0]["active"])
    def test_untrusted_guid_rejected(self):
        with self.assertRaises(ValueError):
            _norm_guid("x & format C:")
    def test_requires_confirmation(self):
        with self.assertRaises(PermissionError):
            change_power_plan(B,confirmed=False)
    def test_only_enumerated_plan_allowed(self):
        with patch("power_center.list_power_plans",return_value=parse_power_plans(LIST,A)):
            with self.assertRaises(ValueError):
                change_power_plan("00000000-0000-0000-0000-000000000000",confirmed=True)
    def test_can_revert_by_original_guid(self):
        state={"active":A,"calls":[]}
        def list_fake():
            return parse_power_plans(LIST,"Power Scheme GUID: "+state["active"])
        def run_fake(args):
            self.assertEqual(args[0],"/setactive")
            state["active"]=args[1]
            state["calls"].append(args)
        with patch("power_center.list_power_plans",side_effect=list_fake):
            with patch("power_center._run",side_effect=run_fake):
                first=change_power_plan(B,confirmed=True)
                back=change_power_plan(first["previous"],confirmed=True)
        self.assertTrue(first["changed"])
        self.assertTrue(back["changed"])
        self.assertEqual(state["active"],A)
    def test_battery_report_opt_in(self):
        with self.assertRaises(PermissionError):
            battery_report("C:/Users/test/report.html",confirmed=False)
