# LocVela · 位航

[简体中文](README.zh-CN.md)

Local-first location simulation and route control for Android and iOS, with explicit recovery states and verifiable compatibility records.

**Status: M0 engineering foundation, not an installable phone application.** No APK, IPA, device injection backend, desktop GUI, or WeChat compatibility has been delivered yet. Unit tests and successful CI do not certify hardware support.

## Implemented in this baseline

- Dependency-free Rust core: validated WGS-84 coordinates, spherical interpolation, bounded deterministic route playback, and a conservative session state machine.
- Strict Python compatibility-report validation: evidence levels, cleanup status, version scoping, input limits, duplicate-key rejection, and stale-version detection.
- Initial unverified device records and product, architecture, testing, privacy, recovery, and handoff documentation.
- CI for the core and report tooling. Check the actual workflow result for the commit you use.

## First target devices

| Device | Target OS | Planned backend | Device validation |
| --- | --- | --- | --- |
| Samsung Galaxy S25 | Android 16 | Native mock-location app; optional separate Google FLP adapter | Not tested |
| iPhone 16 | iOS 18.4.1 | Desktop development-service session first | Not tested |

Root, jailbreak, external positioning hardware, and a self-hosted server are not baseline prerequisites. iPhone standalone operation is a separately gated later milestone. WeChat versions and OS build numbers are not yet recorded.

## Developer quick start

Rust 1.85.1 (pinned), Python 3.10+; no third-party runtime dependencies in this baseline.

```sh
cargo test --workspace --all-targets --locked
cargo clippy --workspace --all-targets --locked -- -D warnings
cargo run -p locvela-core --example replay --locked
python -m unittest discover -s tests -v
python -m tools.report compatibility/android.unverified.json compatibility/ios.unverified.json
```

The replay example only prints synthetic coordinates. It does not connect to or modify a device. `VALID ... unverified` means a report has valid structure, not that a device test passed. The validator checks consistency, not the authenticity of supplied evidence.

## Documentation

- [Product specification](docs/SPEC.zh-CN.md)
- [Architecture](docs/ARCHITECTURE.zh-CN.md)
- [Compatibility matrix](docs/COMPATIBILITY.zh-CN.md)
- [Device test plan](docs/TEST-PLAN.zh-CN.md)
- [Recovery](docs/RECOVERY.zh-CN.md) · [Privacy](docs/PRIVACY.zh-CN.md)
- [Roadmap](docs/ROADMAP.md) · [Development handoff](docs/HANDOFF.zh-CN.md)
- [Third-party register](THIRD_PARTY_NOTICES.md) · [Contributor rules](AGENTS.md)

## Evidence and scope

Submission, independent system observation, and target-application observation are separate evidence levels. A disconnect is an unknown state, not proof of restored location. System simulation may affect other apps; this is not an app-isolation feature. Device coordinates do not change public IP or server-side account regions. Use test devices/accounts with participant consent.

## License

Original LocVela code: **AGPL-3.0-only**, see [LICENSE](LICENSE). Preserve upstream notices for any future imported code. Reference projects are not bundled dependencies in this baseline. LocVela is independent of and not endorsed by WeChat, Samsung, or Apple.
