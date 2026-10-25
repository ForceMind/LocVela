# Security and sensitive data

Never attach pairing records, device identifiers, signing keys, precise personal routes, access tokens or chat logs to public issues. Start with a minimal redacted description; do not assume a private advisory channel is enabled.

The baseline has no device backend, network service or telemetry. Future control transports must authenticate commands, reject stale session receipts and fail closed on unknown cleanup status. Reports validate structure, not evidence authenticity.

Supported security scope currently covers the source in main, not unpublished APK/IPA downloads or third-party builds. Supply-chain imports require version pins, provenance and license records.
