# Foundation validation record

## Initial branch revision

Revision: `146315944523091bce04f8fd53af239450b607b0`.
PR run: https://github.com/ForceMind/LocVela/actions/runs/40166279234

- Rust 1.85.1: 21 core tests and Clippy with warnings denied passed on Linux, macOS and Windows.
- Python: 20 report-validator tests passed on all three hosts.
- Canonical AGPL integrity check passed on Linux/macOS but failed on Windows, where Git's default checkout converted LF to CRLF.
- The follow-up adds `.gitattributes` to preserve LF for canonical text on all platforms. The expected license checksum is not weakened or changed.

The new revision requires its own successful CI run; see PR #1 / Actions for the actual current result. These are desktop-host core/tooling checks, not Android/iOS builds or hardware evidence. No device or WeChat feature has been tested.
