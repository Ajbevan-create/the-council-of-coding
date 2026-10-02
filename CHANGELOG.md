# Changelog

Linux refinement: POSIX launchers, distribution-neutral prerequisites, explicit native Rust target despite cross-compilation defaults, and distro container CI. Canonical path/terminal EOF regressions found by native platform CI are covered.

## 0.3.0 — 2026-10-02

- Publish The Council of Coding as an MIT-licensed project with upstream model/template notices.
- Preserve a valid proposal and risk evidence before reviews, so a failed reviewer can be corrected through resume.
- Clarify worker output modes and avoid substituting setup/test commands for requested code.
- Add measured Ollama duration fields and generation throughput, retaining unknown values as null.
- Stage the runtime binary and adapter, run diagnostics before activation, and restore earlier files on activation failure.
- Enforce LF checkout bytes for portable checksum verification and provide a reproducible release packager.
- Document requirements, measured author hardware, actual local drafting outcomes, performance methodology, and assistant/platform limits.
- Add regression tests for review failure recovery, metrics, failed diagnostics, adapter copying, and runtime activation rollback.

## 0.2.0 — 2026-10-02

- Add Linux, macOS, and native Windows source installers with explicit OS and assistant selection.
- Add pinned model sources, portable storage, installed runtime helpers, a local stdio MCP adapter, and separate Perplexity skill upload.
- Remove the creator-specific service dependency from the shareable runner.
