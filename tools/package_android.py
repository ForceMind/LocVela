"""Package already-built debug APKs; this script does not run device tests."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]

def main() -> None:
    output = ROOT / "artifacts/android"
    output.mkdir(parents=True, exist_ok=True)
    files = {
        "LocVela-0.1.0-alpha.1-debug.apk": "apps/android/controller/build/outputs/apk/debug/controller-debug.apk",
        "LocVela-Probe-0.1.0-alpha.1-debug.apk": "probes/android/build/outputs/apk/debug/probe-debug.apk",
    }
    checksums = {}
    for name, relative in files.items():
        source = ROOT / relative
        if not source.is_file():
            raise FileNotFoundError(relative)
        shutil.copyfile(source, output / name)
        checksums[name] = hashlib.sha256(source.read_bytes()).hexdigest()
    tests = {"tests": 0, "failures": 0, "errors": 0, "skipped": 0}
    results = list((ROOT / "apps/android/model/build/test-results/test").glob("TEST-*.xml"))
    if not results:
        raise RuntimeError("Missing model JUnit XML results")
    for path in results:
        suite = ET.parse(path).getroot()
        for key in tests:
            tests[key] += int(suite.get(key, "0"))
    if not tests["tests"] or tests["failures"] or tests["errors"]:
        raise RuntimeError("Model tests did not pass")
    info = {
        "version": "0.1.0-alpha.1", "source_sha": os.environ.get("SOURCE_SHA", "unknown"),
        "build_type": "debug", "compile_sdk": 36, "target_sdk": 36, "min_sdk": 31,
        "jvm_model_tests": tests, "hardware_validation": "not_performed",
        "wechat_compatibility": "unverified", "sha256": checksums,
        "warning": "Ephemeral debug signing; not a production release. Stop and clean up before uninstalling an older differently signed build."
    }
    (output / "build-info.json").write_text(json.dumps(info, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "SHA256SUMS.txt").write_text("".join(f"{value}  {name}\n" for name, value in checksums.items()), encoding="utf-8")
    shutil.copyfile(ROOT / "docs/ANDROID-QUICKSTART.zh-CN.md", output / "ANDROID-QUICKSTART.zh-CN.md")
    print(json.dumps(info, ensure_ascii=False, indent=2))

if __name__ == "__main__":
    main()
