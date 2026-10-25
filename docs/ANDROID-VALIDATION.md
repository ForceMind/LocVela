# Android alpha validation history

These records distinguish compiler/host checks from physical-device evidence. No Samsung S25 or iPhone has been connected to these builds.

## Initial implementation — 3194c65

Android Actions run 40192074238: all 23 JVM transaction tests passed, but controller compilation failed because a wildcard import resolved `Target` to Kotlin's annotation type. Fixed with explicit model imports, not by changing test expectations.

## Import/package follow-up — d186ca0

Android run 40192549489: controller and independent Probe both compiled and assembled; 23 JVM tests passed. Android Lint blocked the workflow because ACCESS_MOCK_LOCATION was declared in the main manifest. No APK delivery artifact was published by this failed run.

Foundation run 40192549480: Linux/macOS passed; Windows exposed ZipInfo's normalization of backslashes. The archive reader now validates raw header names, rejects hidden NUL/drive/path forms, and tests preserve the original fixture on every OS.

## Raw-path regression — def3152

Foundation run 40192729475 passed across Linux, Windows and macOS: 21 Rust tests, Clippy, and 30 Python tests per host. The debug permission and backup tests increase the Python suite to 32 in later revisions.

## Debug permission and backup scope — c7ceac1

Foundation run 40193047546 passed on all three hosts (21 Rust, 32 Python, Clippy). Android run 40193047585 again assembled both APKs and passed the 23 JVM tests, but the pinned Lint still reported MockLocation, now pointing directly to `controller/src/debug/AndroidManifest.xml`. No delivery APK artifact was published by that failed run.

This is a dedicated developer-selected mock-location test application, so the debug variant requires this permission. The follow-up adds a **narrow documented `tools:ignore="ProtectedPermissions,MockLocation"` on that one debug-only uses-permission element**. It does not disable Lint globally, remove user AppOps selection, change mock flags, or grant the Probe mock privileges. Regression tests enforce that the exception exists only there and the main/release manifest has no mock permission. Production distribution remains a separate explicit decision.

Other Lint errors still abort the build. Nonblocking warnings about deliberately pinned historical dependencies, target SDK and UI modernization may remain; a successful Lint task is not a claim of zero warnings. Debug builds are not production releases.

## Delivery evidence

The current successful run, if available, is recorded in PR #5 and its Actions checks. Do not infer that a historical run applies to a later commit. APK artifacts must include the exact source commit, matching source archive, legal notices and SHA-256 values; signature/alignment verification runs before packaging.

Device tests, actual install/launch, lock-screen behavior, recovery and WeChat compatibility remain unverified regardless of build success.
