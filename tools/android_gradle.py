"""Run the pinned Gradle distribution in an isolated cache; no system installation.

Usage: python tools/android_gradle.py :model:test :controller:assembleDebug :probe:assembleDebug
Requires JDK 17 and an Android SDK with platform 36 / build-tools 35.0.0.
"""
from __future__ import annotations
import hashlib
import os
from pathlib import Path, PurePosixPath
import shutil
import subprocess
import sys
import tempfile
import urllib.request
import zipfile

VERSION = "8.13"
SHA256 = "20f1b1176237254a6fc204d8434196fa11a4cfb387567519c61556e8710aed78"
URL = f"https://services.gradle.org/distributions/gradle-{VERSION}-bin.zip"
MAX_DOWNLOAD = 250 * 1024 * 1024
MAX_EXPANDED = 500 * 1024 * 1024
ROOT = Path(__file__).resolve().parents[1]


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate_members(archive: zipfile.ZipFile) -> None:
    members = archive.infolist()
    if sum(item.file_size for item in members) > MAX_EXPANDED:
        raise ValueError("Gradle archive exceeds expanded-size limit")
    seen = set()
    for item in members:
        # ZipInfo.filename can already be normalized on Windows or truncated at NUL.
        # Inspect the original header name before trusting any host-specific rewrite.
        raw = item.orig_filename
        path = PurePosixPath(raw)
        mode = (item.external_attr >> 16) & 0o170000
        if (raw != item.filename or "\0" in raw or raw in seen
                or path.is_absolute() or ".." in path.parts or not path.parts
                or path.parts[0] != f"gradle-{VERSION}" or "\\" in raw
                or any(":" in part for part in path.parts) or mode == 0o120000):
            raise ValueError("Unsafe Gradle archive entry")
        seen.add(raw)


def bootstrap(cache: Path) -> Path:
    cache.mkdir(parents=True, exist_ok=True)
    target = cache / f"gradle-{VERSION}-bin.zip"
    if not target.exists() or checksum(target) != SHA256:
        fd, temporary = tempfile.mkstemp(dir=cache, suffix=".download")
        try:
            with os.fdopen(fd, "wb") as out, urllib.request.urlopen(URL, timeout=60) as response:
                size = 0
                while chunk := response.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_DOWNLOAD:
                        raise ValueError("Gradle download exceeds size limit")
                    out.write(chunk)
            if checksum(Path(temporary)) != SHA256:
                raise ValueError("Gradle SHA-256 mismatch")
            os.replace(temporary, target)
        finally:
            Path(temporary).unlink(missing_ok=True)
    # Fresh extraction from the verified archive; no trust in a stale extracted executable.
    work = Path(tempfile.mkdtemp(prefix="gradle-", dir=cache))
    try:
        with zipfile.ZipFile(target) as archive:
            validate_members(archive)
            archive.extractall(work)
        executable = work / f"gradle-{VERSION}" / "bin" / ("gradle.bat" if os.name == "nt" else "gradle")
        if os.name != "nt":
            executable.chmod(0o755)
        return executable
    except Exception:
        shutil.rmtree(work)
        raise


def main() -> int:
    cache = Path(os.environ.get("LOCVELA_BUILD_CACHE", str(Path.home() / ".cache" / "locvela-build")))
    executable = bootstrap(cache)
    try:
        args = sys.argv[1:] or [":model:test", ":controller:assembleDebug", ":probe:assembleDebug"]
        return subprocess.call([str(executable), "-p", str(ROOT / "apps" / "android"), *args])
    finally:
        shutil.rmtree(executable.parents[2])


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, zipfile.BadZipFile) as error:
        print(f"Android build bootstrap failed: {error}", file=sys.stderr)
        raise SystemExit(1)
