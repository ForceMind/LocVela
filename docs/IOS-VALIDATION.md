# iOS developer alpha validation

## Initial implementation: 08a66ca9421452a194a364de145cec5120fce56d

- Local cloud container: 88 Python tests passed, Python compileall and git diff --check passed. New tests use explicit synthetic transports, not device simulation presented as hardware evidence.
- iOS workflow 40206548761: Python tests and installed pymobiledevice3 11.31.0 API checks passed on Linux, Windows and macOS. Independent Swift Probe compiled for simulator and unsigned device targets on the hosted macOS runner.
- Foundation workflow 40206548693: 21 Rust tests, Clippy, 88 Python tests and initial-report validation passed on all three hosts.
- First Swift build succeeded but revealed a CLLocationManagerDelegate actor-conformance warning and an iPad orientation warning. The follow-up uses nonisolated delegates with explicit MainActor.assumeIsolated assertions, following Apple's documented initialization-thread callback contract; it enables Swift 6 with compiler warnings treated as errors and declares supported orientations.

The callback pattern is documented by Apple in https://developer.apple.com/videos/play/wwdc2024/10169/ (39:32–40:06) and https://developer.apple.com/documentation/corelocation/cllocationmanagerdelegate . This is a checked runtime assumption for the manager constructed on MainActor, not an unchecked Sendable declaration.

## Follow-up validation requirements

The additional concurrency contract test increases Python coverage to 89 tests. Follow-up commits must run their own complete CI; historical success is not a later-head result. PR #6 records the final reviewed head and final workflow runs.

Swift compilation is not simulator execution, real-device installation or UI review. A generic unsigned device build is not an installable IPA. API signature checks never open a device connection. No S25/iPhone or WeChat behavior has been validated.

## Important evidence boundary

Reviewed upstream stopLocationSimulation explicitly expects no reply. A completed clear call is recorded as sent_unconfirmed, with the recovery journal still set. Explicit user confirmation is labeled user_confirmation_only, not automatic recovery proof. Current report v1 cannot represent this distinction sufficiently and must not be populated with fabricated cleanup=confirmed values.

Android application behavior is unchanged by this iOS increment; Google Play services FLP remains pending. Android CI still rebuilds and regression-checks the existing source. No owner's Mac, phone or VPN configuration was operated on.
