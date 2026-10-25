# Third-party register

Original LocVela source is AGPL-3.0-only. The Rust core and Python report tools use their standard libraries. No source from the reference location projects below is vendored or linked.

## Android alpha dependencies

Direct build/runtime selections are pinned in `apps/android/*.gradle.kts` and the module files:

| Component | Version | Role / upstream |
| --- | --- | --- |
| Android Gradle Plugin | 8.13.0 | Build tooling; https://developer.android.com/build/releases/agp-8-13-0-release-notes |
| Gradle | 8.13 | Build tooling; official binary archive SHA-256 pinned in tools/android_gradle.py |
| Kotlin / Compose compiler plugin | 2.2.10 | Compiler and Kotlin runtime; https://github.com/JetBrains/kotlin |
| AndroidX Compose BOM | 2025.08.01 | Compose UI/material/foundation version alignment; https://developer.android.com/develop/ui/compose/bom |
| AndroidX Activity Compose | 1.10.1 | Activity/UI integration |
| AndroidX Core KTX | 1.16.0 | Android support APIs |
| JUnit | 4.13.2 | JVM tests only; https://github.com/junit-team/junit4 |
| JDK | 17 | Build toolchain, not bundled as an Android runtime |

AndroidX sources/licenses are maintained at https://android.googlesource.com/platform/frameworks/support/ . Preserve package notices and per-file licenses when redistributing. Direct-version pinning is not a complete transitive dependency lock or finished SBOM. Resolve and audit the complete dependency/license inventory before a production release; no map SDK or Google Play services runtime is bundled in this alpha.

## Reference projects, not adopted dependencies

| Candidate | Planned role | Adoption gate |
| --- | --- | --- |
| https://github.com/ZCShou/GoGoGo | Android implementation reference | Pin revision; review exact files and license |
| https://github.com/doronz88/pymobiledevice3 | iOS desktop protocol backend | Pin version/dependencies; preserve notices; verify API |
| https://github.com/jkcoxson/idevice | Optional Rust transport | Verify services and license at pinned revision |
| https://github.com/StikDebug/StikDebug | iOS on-device reference | Review file licenses and lifecycle behavior |
| https://github.com/laatortuejaune/anole | Cross-transport architecture reference | Review provenance and file licenses |

An upstream mention is not a license review or compatibility certification. Do not assume a top-level license covers all binaries, map SDKs or services.

CI uses pinned GitHub actions/checkout, actions/setup-java and actions/upload-artifact commits. These are CI tools, not Android application code. Rust remains pinned to 1.85.1.
