import copy
import json
from pathlib import Path
import tempfile
import unittest
from tools.report import MAX_BYTES, ReportError, load, validate

ROOT = Path(__file__).resolve().parents[1]

def blank():
    return load(ROOT / "compatibility/android.unverified.json")

def complete():
    # Synthetic validator fixture, never a real device compatibility report.
    r = blank()
    r["device"]["os_build"] = "TEST-ONLY"
    r["software"] = dict.fromkeys(r["software"], "TEST-ONLY")
    r["result"] = "passed"
    r["evidence"] = {"submitted": True, "system_observed": True,
                     "target_observed": True, "reference": "synthetic-test-case"}
    r["cleanup"] = "confirmed"
    r["tested_at"] = "2000-01-01T00:00:00Z"
    return r

class Reports(unittest.TestCase):
    def test_device_baselines(self):
        for path in (ROOT / "compatibility").glob("*.json"):
            r = load(path)
            validate(r)
            self.assertEqual(r["result"], "unverified")
    def test_complete_synthetic_record(self):
        validate(complete())
    def test_missing_target_not_passed(self):
        r = complete(); r["evidence"]["target_observed"] = False
        with self.assertRaises(ReportError): validate(r)
    def test_cannot_skip_system(self):
        r = complete(); r["evidence"]["system_observed"] = False
        with self.assertRaises(ReportError): validate(r)
    def test_cleanup_unknown_not_passed(self):
        r = complete(); r["cleanup"] = "unknown"
        with self.assertRaises(ReportError): validate(r)
    def test_every_version_required(self):
        for key in complete()["software"]:
            r = complete(); r["software"][key] = None
            with self.assertRaises(ReportError): validate(r)
    def test_unverified_cannot_claim_evidence(self):
        r = blank(); r["evidence"]["submitted"] = True
        with self.assertRaises(ReportError): validate(r)
    def test_boolean_is_not_version(self):
        r = blank(); r["schema_version"] = True
        with self.assertRaises(ReportError): validate(r)
    def test_unknown_fields_rejected(self):
        for target in ("root", "device", "software", "evidence"):
            r = blank(); (r if target == "root" else r[target])["secret"] = "test"
            with self.assertRaises(ReportError): validate(r)
    def test_missing_timezone(self):
        r = complete(); r["tested_at"] = "2000-01-01T00:00:00"
        with self.assertRaises(ReportError): validate(r)
    def test_stale_version(self):
        with self.assertRaises(ReportError): validate(complete(), expected_wechat_version="OTHER")
    def test_reference_is_not_remote_url(self):
        r = complete(); r["evidence"]["reference"] = "https://example.invalid/private"
        with self.assertRaises(ReportError): validate(r)
    def test_flags_require_bool(self):
        r = complete(); r["evidence"]["submitted"] = 1
        with self.assertRaises(ReportError): validate(r)
    def test_invalid_document_types(self):
        for value in (None, [], 1, "string"):
            with self.assertRaises(ReportError): validate(value)
    def test_duplicate_nan_and_bad_encoding(self):
        for payload in (b'{"x":1,"x":2}', b'{"x":NaN}', b'\xff'):
            with tempfile.TemporaryDirectory() as d:
                path = Path(d)/"report.json"; path.write_bytes(payload)
                with self.assertRaises(ReportError): load(path)
    def test_size_limit(self):
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"report.json"; path.write_bytes(b" "*(MAX_BYTES+1))
            with self.assertRaises(ReportError): load(path)
    def test_no_mutation(self):
        r = complete(); before = copy.deepcopy(r); validate(r); self.assertEqual(r,before)
    def test_blocked_needs_attempt_timestamp(self):
        r=blank(); r["result"]="blocked"
        with self.assertRaises(ReportError): validate(r)
    def test_missing_field(self):
        r=blank(); del r["notes"]
        with self.assertRaises(ReportError): validate(r)
    def test_unknown_feature(self):
        r=blank(); r["feature"]="wechat.ip_region"
        with self.assertRaises(ReportError): validate(r)

if __name__ == "__main__":
    unittest.main()
