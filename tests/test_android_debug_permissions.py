"""Development-only mock permission must be scoped to the alpha debug variant."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
A = "{http://schemas.android.com/apk/res/android}"

class DebugPermissions(unittest.TestCase):
    def test_mock_permission_is_debug_only(self):
        base = ROOT / "apps/android/controller/src"
        names = {}
        for source in ("main", "debug"):
            document = ET.parse(base / source / "AndroidManifest.xml").getroot()
            names[source] = {item.get(A + "name") for item in document.findall("uses-permission")}
        self.assertNotIn("android.permission.ACCESS_MOCK_LOCATION", names["main"])
        self.assertIn("android.permission.ACCESS_MOCK_LOCATION", names["debug"])
        self.assertNotIn("android.permission.INTERNET", names["debug"])

if __name__ == "__main__":
    unittest.main()
