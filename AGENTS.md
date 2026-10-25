# LocVela engineering rules

1. Read README, docs/SPEC.zh-CN.md, docs/ARCHITECTURE.zh-CN.md, docs/ROADMAP.md and relevant compatibility evidence before editing. Inspect the current branch, open PRs and CI; do not assume a historical SHA is current.
2. This is an existing project. Preserve history, unrelated changes and public visibility. Prefer scoped PRs; never force-push main. Do not deploy websites or use the owner's Mac/phone without explicit authorization.
3. Targets: Galaxy S25 / Android 16 (no-root baseline) and iPhone 16 / iOS 18.4.1 (desktop-assisted first). Do not infer region, firmware build, GMS, WeChat build or availability of bootloader unlock.
4. Keep backend submission, independent OS observation, target-app evidence and restoration evidence separate. Never promote dry runs, unit tests, emulators, upstream claims or CI builds into hardware passes.
5. No simulated success paths: unsupported operations return explicit errors. No automatic restart of injection. Cleanup acknowledgement does not prove real location. On lost transport report unknown.
6. Keep native backends separate from deterministic Rust logic. Do not invoke one new CLI process per coordinate update. Do not hide mock-source markers, patch WeChat, or make Root a prerequisite for the S25 baseline.
7. Pairing data, private keys, signing profiles, UDIDs, precise personal routes and chat data do not belong in Git. Use public/synthetic test points and redacted evidence IDs.
8. Pin external code and tools before adopting them; retain license notices. Do not rename upstream code as original work. No dependency imports are implied by docs/UPSTREAMS.md.
9. Run cargo test --workspace --all-targets --locked, cargo clippy --workspace --all-targets --locked -- -D warnings, and python -m unittest discover -s tests -v. Record commands actually run and their result. Preserve failing tests and fix implementation, not expectations, to meet a claim.
10. A handoff must state the actual commit, changed modules, tests, remaining device blockers and next executable task. Do not promise unattended/background work unless a real supported task has been created.
