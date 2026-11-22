"""No device access: synthetic inventory and recovery triage tests."""
import unittest
from usb_diagnostics import normalize_inventory, recovery_triage, inventory_windows

class USBInventoryTests(unittest.TestCase):
    def test_partition_volume_mapping(self):
        payload = {
            "disks":[{"Number":0,"FriendlyName":"SSD","BusType":"RAID","HealthStatus":"Healthy",
                      "OperationalStatus":"Online","Size":512000000000,"PartitionStyle":"GPT",
                      "IsOffline":False,"IsReadOnly":False}],
            "partitions":[{"DiskNumber":0,"PartitionNumber":1,"DriveLetter":"C","Size":300000000000},
                          {"DiskNumber":0,"PartitionNumber":2,"DriveLetter":"D","Size":200000000000}],
            "volumes":[{"DriveLetter":"C","FileSystem":"NTFS","SizeRemaining":14000000000,
                        "HealthStatus":"Healthy"}]}
        result=normalize_inventory(payload)
        self.assertTrue(result["read_only"])
        self.assertEqual(len(result["disks"]),1)
        self.assertEqual(result["disks"][0]["partitions"][0]["letter"],"C:")
        self.assertEqual(result["disks"][0]["partitions"][1]["filesystem"],"Unknown")

    def test_removable_unmapped_and_offline_warning(self):
        data={"disks":[{"Number":3,"BusType":"USB","HealthStatus":"Warning",
                         "OperationalStatus":"Offline","IsOffline":True}],
              "partitions":[{"DiskNumber":3,"PartitionNumber":1,"DriveLetter":None}],
              "volumes":[]}
        row=normalize_inventory(data)["disks"][0]
        self.assertIsNone(row["partitions"][0]["letter"])
        self.assertGreaterEqual(len(row["alerts"]),3)

    def test_single_object_provider_response(self):
        out=normalize_inventory({"disks":{"Number":1,"BusType":"NVMe","HealthStatus":"Healthy",
                                          "OperationalStatus":"Online"},
                                 "partitions":None,"volumes":None})
        self.assertEqual(out["disks"][0]["disk_number"],1)

    def test_invalid_payload(self):
        with self.assertRaises(ValueError):
            normalize_inventory(["unexpected"])

    def test_unmapped_partition_reported(self):
        report=normalize_inventory({"disks":[],"partitions":[{"DiskNumber":8}],"volumes":[]})
        self.assertEqual(report["unmapped_partition_disks"],[8])

    def test_failing_media_never_auto_repair(self):
        result=recovery_triage(drive_visible=True,disconnecting=True)
        self.assertEqual(result["risk"],"critical")
        self.assertFalse(result["run_command"])

    def test_data_loss_no_guarantee(self):
        self.assertIn("no guarantee",recovery_triage(drive_visible=True)["guidance"].lower())

    def test_inventory_requires_windows(self):
        import os
        if os.name != "nt":
            with self.assertRaises(RuntimeError):
                inventory_windows()
