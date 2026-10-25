# Upstream adoption status

See [THIRD_PARTY_NOTICES.md](../THIRD_PARTY_NOTICES.md) for candidate projects. The optional iOS development helper now imports separately installed pymobiledevice3 11.31.0; no upstream source is vendored. See the third-party register and iOS developer guide for its exact revision, reviewed API and remaining dependency-lock limits. Before implementation, record the exact version/commit, license of adopted files, dependency tree, API signature and device test evidence.

The complete LICENSE text is copied from the SPDX license-list-data AGPL-3.0-only text. Its canonical Git blob is `0c97efd25b5974b974ed9a8a18207bc4f55bb338`; the integrity test permits only a terminal-newline difference. Project licensing is version 3 only, as stated in COPYRIGHT and package metadata.

Android API and iOS development-service references are in docs/SPEC.zh-CN.md. Documentation compatibility claims must be rechecked when choosing actual platform dependencies; do not copy them into the device matrix as a pass.
