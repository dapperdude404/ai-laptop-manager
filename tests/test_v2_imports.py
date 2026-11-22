"""Packaging and import regression tests without opening the GUI."""
import importlib
import unittest

class V2ImportTests(unittest.TestCase):
    def test_real_entrypoint_imports(self):
        module = importlib.import_module("ai_laptop_manager_v2")
        self.assertTrue(callable(module.FutureLaptopManager))
        self.assertTrue(callable(module.FutureLaptopManager.__init__))

    def test_v2_ui_compatibility(self):
        from app import LaptopManager
        from ai_laptop_manager_v2 import FutureLaptopManager
        from ui_compat import label, button, SURFACE, SURFACE2
        self.assertTrue(issubclass(FutureLaptopManager, LaptopManager))
        self.assertTrue(all(callable(x) for x in (label, button)))
        self.assertTrue(SURFACE and SURFACE2)
        self.assertTrue(hasattr(FutureLaptopManager, "show_directory_files"))
        self.assertEqual(FutureLaptopManager.show_files, LaptopManager.show_files)
