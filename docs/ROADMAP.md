# Roadmap and delivery gates

## M0 — foundation and feasibility (in progress)

- [x] Product, architecture, recovery/privacy, bilingual README and contributor rules.
- [x] Rust geometry/route/session core and strict Python evidence tooling.
- [x] Android fixed-point backend with write-ahead cleanup journal.
- [x] Independent Android read-only location Probe source.
- [x] Android build/test/lint pipeline and debug artifact packaging.
- [ ] Independent iOS native location Probe.
- [ ] iOS persistent development-service session and cleanup.
- [ ] Actual S25 and iPhone hardware acceptance.

Source implementation, successful CI and actual device tests are separate gates. Check the specific workflow run; no hardware pass is inferred from these checkboxes.

## M1 — Android closed loop (alpha implemented, device gate pending)

Implemented: Kotlin/Compose control screen, permission/mock-app onboarding, framework provider detection, fixed-point service, hold/resume, notification stop, transactional cleanup and crash recovery; independent foreground Probe; JVM failure tests; APK artifact pipeline.

Remaining: S25 installation and runtime validation; 20 start/stop cycles; lock-screen/network/permission-revocation cases; energy measurements; a separately optional Google FLP adapter; production packaging/signing. Android 12+ is a build minimum, not a validated fleet. No Root requirement.

## M2 — iPhone desktop closed loop (not implemented)

Tauri device management, pinned development-service adapter, trust/developer support setup, persistent connection, fixed point and route, cleanup/error handling and independent Swift Probe. First device: iPhone 16 / iOS 18.4.1. No operations on the owner's Mac or phone without explicit authorization.

## M3 — compatibility and everyday controls

Map abstraction, search/favorites, bounded GPX parsing, route editor, shared Rust integration, speed/stop/repeat controls and complete per-feature WeChat evidence. Receiving-device observations required for live sharing.

## M4 — iPhone standalone mode

Native SwiftUI app, pairing/local development transport, actual signing/distribution process, background/VPN-conflict/failure tests. No claim of permanent background execution.

## M5 — release engineering

Dependency locks and notices, SBOM, production signing, checksums, build provenance, update/rollback and bilingual setup guides. Do not ship an all-WeChat-features claim while any scoped feature lacks evidence.
