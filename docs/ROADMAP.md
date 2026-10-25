# Roadmap and delivery gates

## M0 — foundation and feasibility (in progress)

- [x] Product specification, architecture, recovery and privacy rules.
- [x] Bilingual README and contribution guidance.
- [x] Dependency-free coordinate/route/session core source and automated test suite.
- [x] Strict compatibility-report tooling and unverified device baselines.
- [ ] Independent Android/iOS native system-location probes.
- [ ] Minimal Android fixed-point backend and cleanup.
- [ ] iOS persistent development-service session and cleanup.
- [ ] Actual device evidence on S25 and iPhone 16.

Automated source checks are not the M0 hardware exit gate. Consult CI for the exact revision; checkboxes above describe implemented source, not device support.

## M1 — Android closed loop

Kotlin/Compose application, permission onboarding, foreground service and notification stop, provider capability detection, separately optional Google FLP, native probe, installable APK, S25 regression evidence. No Root requirement.

## M2 — iPhone desktop closed loop

Tauri device management, pinned development-service adapter, trust/developer support setup, persistent connection, fixed point and route, cleanup/error handling, signed/packaged desktop distribution where available. iPhone 16 / iOS 18.4.1 device gate.

## M3 — compatibility and everyday controls

Map-provider abstraction, search/favorites, bounded GPX parser, route editor, speed/stop/repeat controls and complete per-feature WeChat records. Real-time sharing must be checked at the receiving device.

## M4 — iPhone standalone mode

Native SwiftUI app, pairing and local development transport, actual signing/distribution workflow, background/VPN-conflict/failure tests. No claim of permanent background execution.

## M5 — release engineering

Build metadata, checksums, dependency notices, SBOM, application rollback, redacted support reports and bilingual setup guides. Do not ship a “WeChat all features supported” claim while any scoped feature lacks evidence.
