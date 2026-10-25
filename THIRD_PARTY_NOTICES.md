# Third-party register

The M0 core and report validator are original LocVela source and use only the Rust/Python standard libraries. No code from the candidate projects below is vendored or linked yet. An upstream mention is not a dependency, license review, or compatibility certification.

| Candidate | Planned role | Adoption gate |
| --- | --- | --- |
| https://github.com/ZCShou/GoGoGo | Android implementation reference | Pin revision; review exact files and license |
| https://github.com/doronz88/pymobiledevice3 | iOS desktop protocol backend | Pin revision/package and dependencies; preserve notices; verify API |
| https://github.com/jkcoxson/idevice | Optional Rust transport | Pin revision; verify required services and license |
| https://github.com/StikDebug/StikDebug | iOS on-device reference | Review per-file licensing and background behavior |
| https://github.com/laatortuejaune/anole | Cross-transport architecture reference | Review per-file licensing and provenance |

Original project code is AGPL-3.0-only. Preserve all upstream notices if any code is imported. Do not assume a project-level license covers every bundled file, map SDK, binary or service.

CI uses GitHub's checkout action at a pinned commit; it is a build tool, not bundled application code. Rust is pinned to 1.85.1. Target-platform dependencies are not selected yet.
