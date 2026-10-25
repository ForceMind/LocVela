import hashlib
from pathlib import Path
import unittest

class LicenseIntegrity(unittest.TestCase):
    def test_canonical_agpl_text(self):
        raw = (Path(__file__).resolve().parents[1] / "LICENSE").read_bytes()
        candidates = (raw, raw + b"\n", raw.rstrip(b"\n"))
        hashes = {
            hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()
            for data in candidates
        }
        self.assertIn("0c97efd25b5974b974ed9a8a18207bc4f55bb338", hashes,
                      "LICENSE must match the canonical SPDX text; do not paraphrase license terms")
