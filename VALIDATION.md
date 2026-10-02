# Validation for release 0.3.0

Checked on a native Linux host on 2026-10-02:

- All 13 Rust tests passed: proposal/review schemas, argument validation, consensus, risk retention, isolated storage, locking, resume checks, failed-review draft recovery, and raw duration/throughput metrics.
- All 25 Python tests passed: forced selections, OS mismatch, invalid/empty input, target paths, zero-side-effect preview, path overlap, checksums, alias conflicts/reuse, staged skill/runtime upgrade, backup/rollback behavior, and MCP contracts.
- Native release build and a real user-level install passed in an isolated directory whose path contained spaces. This used `custom`, an explicit runtime directory, and `--skip-models` with existing local aliases; it did not change the creator's installed skill or model aliases.
- Installed helper `--doctor` passed against local Ollama. The generated MCP template completed an initialize handshake and returned a successful real diagnostic report over stdio.
- A real 0.3.0 runtime/skill upgrade passed in an isolated Linux directory, preserving prior runtime and skill backups. Regression tests also injected diagnostic, adapter-copy, and activation failures to verify recovery.
- One council inference and one resume with actual correction feedback completed with all three local models. Both retained `execution: not_executed` and empty actions. The first answer appended unrequested text despite both reviewers accepting; the supervisor caught this and the resumed answer matched the requested text. This validates the wiring and feedback flow, not general coding quality.
- Three final release diagnostic councils completed with a median wall time of 22.400 seconds. Two returned the exact requested answer; one added text that both critics accepted. See [PERFORMANCE.md](PERFORMANCE.md) for counters, methodology, and actual local drafting failures/corrections.
- All three pinned weight URLs responded with the expected content lengths. Real multi-gigabyte downloads were not repeated. Downloader checksum/cache behavior was tested with small controlled fixtures; model replacement and fresh Ollama imports were not performed on this host.
- Skill frontmatter passed the skill-creator validator. Python files compiled; Bash launchers passed syntax checking. Release archive contents and checksum manifest were verified after extraction.
- A fresh Git checkout configured with `core.autocrlf=true` retained the expected source checksums because `.gitattributes` enforces LF. This is a local checkout check, not a native Windows execution claim.

Native macOS and Windows builds, PowerShell/batch execution, and real assistant discovery/upload were **not run on this host**. Unix-specific Rust imports are conditional, native platform paths and launchers are included, and `.github/workflows/test.yml` supplies a Linux/macOS/Windows test and release-build matrix. Those CI jobs have not been executed by this packaging session. No precompiled native binaries are bundled.

The MCP adapter supports initialize-handshake revisions through 2025-11-25. A client requiring only the newer stateless MCP revision needs legacy compatibility. Perplexity upload instructions and local MCP availability depend on its client/account; see `references/compatibility.md`.

Implementation drafts were delegated to local Qwen workers. A resumed metrics helper was accepted by both critics but failed an actual regression test; the supervisor corrected its raw duration fields and verified the fix. The supervisor directly implemented recovery, installer staging, release tooling, and tests after other local drafts fell short. Model agreement did not authorize actions or substitute for verification.
