# LocVela · 位航

[简体中文](README.zh-CN.md)

Local-first location simulation and route control for Android and iOS, with explicit cleanup states and verifiable compatibility records.

**Status: Android fixed-point alpha; physical-device and WeChat acceptance remain unverified.** The controller and independent Probe are implemented as separate Android applications. Downloadable debug APKs are produced only by a successful `android-alpha` Actions run. An iOS desktop JSONL helper and independent Swift Probe are now implemented as developer source; no signed IPA or desktop GUI is delivered.

## Android alpha

| Application | Purpose |
| --- | --- |
| `app.locvela.controller` | WGS-84 fixed point; detected framework GPS/network/fused; foreground control; hold/resume; explicit stop; crash-recovery journal |
| `app.locvela.probe` | Independent read-only system callbacks; freshness, mock flags, baseline distance and post-cleanup observation |

Android 12+ is the installation floor, **not** a device-support certification. First physical target: Samsung Galaxy S25 / Android 16. No Root, network permission, account, telemetry, stored coordinates, hooks or mock-flag concealment. The Probe does not share a UID, code dependency, target cache or private storage with the controller.

**Read [Android setup and recovery](docs/ANDROID-QUICKSTART.zh-CN.md) before installing.** Debug builds are not production releases and may be signed with a different key on each clean CI run. Clean up and verify recovery before uninstalling an old build. Artifacts contain checksums and source/build metadata.

Not in this alpha: map search, GPX/route UI, Google Play services FLP, Rust FFI, or verified WeChat behavior. Framework `fused` is not Google FLP. A live service has a 60-minute cap; process death can prevent cleanup, so pending provider names survive restart and require explicit recovery.

## iOS developer path

The [iOS developer guide](docs/IOS-DEVELOPER-QUICKSTART.zh-CN.md) covers the persistent Python helper and independent foreground-only SwiftUI Probe. The helper pins pymobiledevice3 11.31.0, targets an explicit device and iOS version, defaults to an in-process userspace tunnel without automatic pairing/native fallback, and provides strict local JSONL commands with a lease and durable recovery intent.

**DVT clear is send-only in the reviewed upstream.** `CLEAR_SENT` is not an acknowledgement or restoration proof. Recovery remains pending until an explicit user confirmation after independent observation; this never creates a WeChat pass. CI checks Python failure paths, installed dependency signatures and Swift compilation, not hardware operation. No signed/installable IPA, automatic device-setup wizard, map GUI or on-iPhone controller is provided.

## Other implemented components

- Dependency-free Rust core: validated WGS-84 geometry, deterministic bounded timelines and a conservative abstract session state machine.
- Strict Python compatibility-report tooling: version scope, evidence levels, cleanup status, duplicate-key/input limits and stale-version checks.
- Transactional Android adapter model and automated failure-path tests. These JVM tests do not exercise Samsung firmware.
- Bilingual documentation, CI, initial unverified device records and implementation tasks.

## First target devices

| Device | Target OS | Route | Hardware validation |
| --- | --- | --- | --- |
| Samsung Galaxy S25 | Android 16 | Native no-root Android alpha; optional Google FLP later | Not tested |
| iPhone 16 | iOS 18.4.1 | Persistent desktop development-service helper; signing/device setup still manual | Not tested |

## Build and test

Rust 1.85.1 and Python 3.10+ for the foundation:

```sh
cargo test --workspace --all-targets --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
python -m unittest discover -s tests -v
python -m tools.report compatibility/android.unverified.json compatibility/ios.unverified.json
```

For Android, also install JDK 17, SDK platform 36 and build-tools 35.0.0, then set `ANDROID_HOME`:

```sh
python tools/android_gradle.py :model:test :controller:assembleDebug :probe:assembleDebug :controller:lintDebug :probe:lintDebug --no-daemon
```

The bootstrap verifies a pinned official Gradle archive. No standard `gradlew` is committed yet. The Rust replay example remains a terminal-only dry run; report `VALID` means structural consistency, not compatibility success. Consult the actual Actions run for the revision being used.

## Evidence and documentation

Submission, independent OS observation, target-app behavior and real-location recovery remain separate. Cleanup acknowledgement is not proof of real location. System simulation may affect other apps; it does not alter public IP or server-side account regions. Use your own devices and consenting test participants.

[Product specification](docs/SPEC.zh-CN.md) · [Architecture](docs/ARCHITECTURE.zh-CN.md) · [Compatibility](docs/COMPATIBILITY.zh-CN.md) · [Device tests](docs/TEST-PLAN.zh-CN.md) · [Recovery](docs/RECOVERY.zh-CN.md) · [Roadmap](docs/ROADMAP.md) · [Handoff](docs/HANDOFF.zh-CN.md)

## License

Original LocVela code: **AGPL-3.0-only**, see [LICENSE](LICENSE). See [third-party notices](THIRD_PARTY_NOTICES.md) for platform/build dependencies and reference projects. LocVela is independent of WeChat, Samsung and Apple, and carries no warranty.
