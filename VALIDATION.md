# Validation for release 0.3.1

The 0.3.1 update changes project licensing to GPL-3.0-only and aligns version metadata. The functional portability and performance evidence below was obtained for 0.3.0; historical measurements retain their original version labels. For 0.3.1, all 29 Python tests and 13 Rust tests passed again locally. Both release ZIPs were checked for the full GPLv3 text and GPL-3.0-only skill metadata; all source archive hashes matched the regenerated manifest.

Checked on a native Linux host on 2026-10-02:

- All 13 Rust tests passed: proposal/review schemas, argument validation, consensus, risk retention, isolated storage, locking, resume checks, failed-review draft recovery, and raw duration/throughput metrics.
- All 29 Python tests passed: forced selections, OS mismatch, invalid/empty/EOF input, target paths, zero-side-effect preview, canonical path overlap, native host builds despite inherited cross targets, malformed host rejection, checksums, alias conflicts/reuse, staged skill/runtime upgrade, backup/rollback behavior, and MCP contracts.
- Native release build and a real user-level install passed in an isolated directory whose path contained spaces. This used `custom`, an explicit runtime directory, and `--skip-models` with existing local aliases; it did not change the creator's installed skill or model aliases.
- Installed helper `--doctor` passed against local Ollama. The generated MCP template completed an initialize handshake and returned a successful real diagnostic report over stdio.
- A real 0.3.0 runtime/skill upgrade passed in an isolated Linux directory, preserving prior runtime and skill backups. Regression tests also injected diagnostic, adapter-copy, and activation failures to verify recovery.
- One council inference and one resume with actual correction feedback completed with all three local models. Both retained `execution: not_executed` and empty actions. The first answer appended unrequested text despite both reviewers accepting; the supervisor caught this and the resumed answer matched the requested text. This validates the wiring and feedback flow, not general coding quality.
- Three final release diagnostic councils completed with a median wall time of 22.400 seconds. Two returned the exact requested answer; one added text that both critics accepted. See [PERFORMANCE.md](PERFORMANCE.md) for counters, methodology, and actual local drafting failures/corrections.
- All three pinned weight URLs responded with the expected content lengths. Real multi-gigabyte downloads were not repeated. Downloader checksum/cache behavior was tested with small controlled fixtures; model replacement and fresh Ollama imports were not performed on this host.
- Skill frontmatter passed the skill-creator validator. Python files compiled; Bash launchers passed syntax checking. Release archive contents and checksum manifest were verified after extraction.
- A fresh Git checkout configured with `core.autocrlf=true` retained the expected source checksums because `.gitattributes` enforces LF. This is a local checkout check, not a native Windows execution claim.

All eight jobs in [GitHub Actions run 36980476755](https://github.com/Ajbevan-create/the-council-of-coding/actions/runs/36980476755) passed for code commit `47fc4048d4369bc4e1d5faeb5bfd0e84cfe1d23d`:

| Environment | Verified |
|---|---|
| Ubuntu native | 13 Rust tests, 29 Python tests, source checksums, POSIX launcher preview, native release build |
| macOS native (ARM64 runner) | 13 Rust tests, 29 Python tests, source checksums, POSIX launcher preview, native release build |
| Windows native (x64 runner) | 13 Rust tests, 29 Python tests, source checksums, CMD and PowerShell launcher previews, native release build |
| Ubuntu, Fedora, Arch, openSUSE Tumbleweed, Alpine containers | 29 Python installer/MCP tests, source checksums, POSIX launcher syntax and preview on each distribution |

An initial public source transfer was truncated; cloning it back and checking the manifest caught that error, and the complete source was restored. Subsequent native CI exposed package-path alias and terminal EOF cases, which were corrected and given regression coverage before the successful run above. The installer-generated Perplexity ZIP was subsequently corrected to include the project license/notices and verified through a real isolated Linux install. No precompiled native binaries are bundled. Real assistant discovery/upload and full macOS/Windows Ollama inference remain untested.

The Linux source installer has no DEB/APT or systemd dependency. POSIX launchers remove a Bash prerequisite. A real NixOS native install/upgrade passed even with `CARGO_BUILD_TARGET=wasm32-unknown-unknown` inherited; the helper explicitly selected the actual native Rust host and diagnosed the resulting binary successfully. The distribution guide documents Python SSL/CA certificates, native GNU/musl toolchains, NixOS runtime paths, and compatible local Ollama requirements. The container checks are not a guarantee of every derivative distro, architecture, GPU, or upstream Ollama binary; musl Rust release builds and container inference were not performed by those contract jobs.

The MCP adapter supports initialize-handshake revisions through 2025-11-25. A client requiring only the newer stateless MCP revision needs legacy compatibility. Perplexity upload instructions and local MCP availability depend on its client/account; see `references/compatibility.md`.

Implementation drafts were delegated to local Qwen workers. A resumed metrics helper was accepted by both critics but failed an actual regression test; the supervisor corrected its raw duration fields and verified the fix. The supervisor directly implemented recovery, installer staging, release tooling, and tests after other local drafts fell short. Model agreement did not authorize actions or substitute for verification.
