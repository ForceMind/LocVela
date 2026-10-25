"""Host-only archive/manifest invariants, not Android runtime or hardware tests."""
import io
import os
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET
import zipfile
from tools.android_gradle import SHA256, VERSION, validate_members

ROOT = Path(__file__).resolve().parents[1]
ANDROID = "{http://schemas.android.com/apk/res/android}"


def manifest(relative):
    return ET.parse(ROOT / relative).getroot()


def archive_bytes(name, symlink=False):
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        # Construct the same raw header on every host; ZipInfo(name) normalizes
        # backslashes on Windows before writing and would invalidate this fixture.
        info = zipfile.ZipInfo("placeholder")
        info.filename = name
        info.orig_filename = name
        if symlink:
            info.external_attr = 0o120777 << 16
        archive.writestr(info, b"test")
    return buffer.getvalue()


def archive_with(name, symlink=False):
    return zipfile.ZipFile(io.BytesIO(archive_bytes(name, symlink)))


class AndroidBuildContracts(unittest.TestCase):
    def test_pinned_distribution_checksum(self):
        self.assertEqual(VERSION, "8.13")
        self.assertEqual(SHA256, "20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78")

    def test_expected_archive_path(self):
        with archive_with("gradle-8.13/bin/gradle") as archive:
            validate_members(archive)

    def test_rejects_traversal_and_foreign_roots(self):
        for name in ("../escape", "/tmp/file", "gradle-8.13/../escape", "other/file",
                     "gradle-8.13\\escape", "gradle-8.13/C:escape", "gradle-8.13/ok\0hidden"):
            with self.subTest(name=name), archive_with(name) as archive, self.assertRaises(ValueError):
                validate_members(archive)

    def test_windows_name_normalization_does_not_hide_raw_header(self):
        raw = archive_bytes("gradle-8.13\\escape")
        with patch.object(os, "sep", "\\"), zipfile.ZipFile(io.BytesIO(raw)) as archive:
            info = archive.infolist()[0]
            self.assertEqual(info.filename, "gradle-8.13/escape")
            self.assertEqual(info.orig_filename, "gradle-8.13\\escape")
            with self.assertRaises(ValueError):
                validate_members(archive)

    def test_rejects_symlink(self):
        with archive_with("gradle-8.13/link", symlink=True) as archive, self.assertRaises(ValueError):
            validate_members(archive)

    def test_probe_cannot_request_mock_or_network_permissions(self):
        root = manifest("probes/android/src/main/AndroidManifest.xml")
        names = {item.get(ANDROID + "name") for item in root.findall("uses-permission")}
        self.assertNotIn("android.permission.ACCESS_MOCK_LOCATION", names)
        self.assertNotIn("android.permission.INTERNET", names)
        self.assertIsNone(root.get(ANDROID + "sharedUserId"))

    def test_control_service_private_and_location_typed(self):
        root = manifest("apps/android/controller/src/main/AndroidManifest.xml")
        service = root.find("application/service")
        self.assertEqual(service.get(ANDROID + "exported"), "false")
        self.assertEqual(service.get(ANDROID + "foregroundServiceType"), "location")
        names = {item.get(ANDROID + "name") for item in root.findall("uses-permission")}
        self.assertNotIn("android.permission.INTERNET", names)
        self.assertIn("android.permission.FOREGROUND_SERVICE_LOCATION", names)

    def test_neither_app_has_boot_receiver_or_backup(self):
        for path in ("apps/android/controller", "probes/android"):
            app = manifest(path + "/src/main/AndroidManifest.xml").find("application")
            self.assertEqual(app.get(ANDROID + "allowBackup"), "false")
            self.assertEqual(app.findall("receiver"), [])

    def test_bilingual_resource_keys_match(self):
        for path in ("apps/android/controller", "probes/android"):
            base = ROOT / path / "src/main/res"
            english = {item.get("name") for item in ET.parse(base / "values/strings.xml").getroot()}
            chinese = {item.get("name") for item in ET.parse(base / "values-zh-rCN/strings.xml").getroot()}
            self.assertEqual(english, chinese)


if __name__ == "__main__":
    unittest.main()
