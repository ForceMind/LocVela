"""Development mock permission and device-local storage rules are explicit."""
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
A = "{http://schemas.android.com/apk/res/android}"
T = "{http://schemas.android.com/tools}"

class DebugPermissions(unittest.TestCase):
    def test_mock_permission_is_debug_only(self):
        base = ROOT / "apps/android/controller/src"
        names = {}
        documents = {}
        for source in ("main", "debug"):
            document = ET.parse(base / source / "AndroidManifest.xml").getroot()
            documents[source] = document
            names[source] = {item.get(A + "name") for item in document.findall("uses-permission")}
        self.assertNotIn("android.permission.ACCESS_MOCK_LOCATION", names["main"])
        self.assertIn("android.permission.ACCESS_MOCK_LOCATION", names["debug"])
        self.assertNotIn("android.permission.INTERNET", names["debug"])
        # A documented exception is permitted only on the dedicated debug permission.
        ignored = [(source, node) for source, document in documents.items()
                   for node in document.iter() if node.get(T + "ignore")]
        self.assertEqual(len(ignored), 1)
        source, node = ignored[0]
        self.assertEqual(source, "debug")
        self.assertEqual(node.tag, "uses-permission")
        self.assertEqual(node.get(A + "name"), "android.permission.ACCESS_MOCK_LOCATION")
        self.assertEqual(set(node.get(T + "ignore").split(",")), {"ProtectedPermissions", "MockLocation"})

    def test_no_backup_or_transfer_and_explicit_launcher(self):
        domains = {"root", "file", "database", "sharedpref", "external", "device_root",
                   "device_file", "device_database", "device_sharedpref"}
        for relative in ("apps/android/controller", "probes/android"):
            main = ROOT / relative / "src/main"
            app = ET.parse(main / "AndroidManifest.xml").getroot().find("application")
            self.assertEqual(app.get(A + "dataExtractionRules"), "@xml/no_backup")
            self.assertEqual(app.get(A + "icon"), "@mipmap/ic_launcher")
            rules = ET.parse(main / "res/xml/no_backup.xml").getroot()
            for mode in ("cloud-backup", "device-transfer"):
                entries = rules.find(mode).findall("exclude")
                self.assertEqual({entry.get("domain") for entry in entries}, domains)
                self.assertTrue(all(entry.get("path") == "." for entry in entries))

if __name__ == "__main__":
    unittest.main()
