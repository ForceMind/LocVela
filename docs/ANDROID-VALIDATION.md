# Android alpha validation history

These records distinguish compiler/host checks from physical-device evidence. No Samsung S25 or iPhone has been connected to these builds.

## Initial implementation — 3194c65

Android Actions run 40192074238: all 23 JVM transaction tests passed, but controller compilation failed because a wildcard import resolved `Target` to Kotlin's annotation type. Fixed with explicit model imports, not by changing test expectations.

## Import/package follow-up — d186ca0

Android run 40192549489: controller and independent Probe both compiled and assembled; 23 JVM tests passed. Android Lint correctly blocked the workflow because ACCESS_MOCK_LOCATION was declared in the main manifest. No APK delivery artifact was published by this failed run.

Foundation run 40192549480: Linux/macOS passed; Windows exposed ZipInfo's normalization of backslashes. The archive reader now validates raw header names, rejects hidden NUL/drive/path forms, and tests preserve the original malicious fixture on every OS.

## Raw-path regression — def3152

Foundation run 40192729475 passed across Linux, Windows and macOS: 21 Rust tests, Clippy, and 30 Python tests per host. The separate mock-manifest fix adds one further Python test and requires its own new run.

## Debug permission scope

The Alpha mock permission is moved to `controller/src/debug/AndroidManifest.xml`, with a regression test. The ordinary main/release manifest has no mock permission; a production location-tool variant requires a separate explicit distribution/security decision and is not delivered by this alpha. Lint remains enabled with errors aborting the build.

The current successful run, if available, is recorded in PR #5 and its Actions checks. Do not infer that a historical run applies to a later commit. APK artifacts must include the exact source commit, matching source archive, legal notices and SHA-256 values; signature/alignment verification runs before packaging.

Device tests, actual install/launch, lock-screen behavior, recovery and WeChat compatibility remain unverified regardless of build success.
