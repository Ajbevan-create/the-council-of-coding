# Runtime

The portable Rust runner supports Linux, macOS, and native Windows. It connects only to `http://127.0.0.1:11434`, disables HTTP proxies and redirects, and does not start a service, download models, or execute proposed actions. Launch Ollama or run `ollama serve` before using it.

| Role | Exact alias | Pinned weights |
|---|---|---|
| Proposer | `qwen3.8-distill:9b-q4` | Empero Qwen3.8-9B Distill Q4_K_M, 5.78 GB |
| Reviewer / alternate proposer | `qwen3.5:4b` | Ollama Qwen3.5 4B Q4_K_M, 3.39 GB |
| Safety critic | `granite4:1b-q4-local` | IBM Granite 4.0 1B Q4_K_M, 1.02 GB |

The proposer is a community distillation built on Qwen3.5-9B, not an official small Qwen3.8 release. Quality and quantization equivalence have not been established by this package. `models/sources.json` records source URLs, pinned revisions or immutable weight digests, sizes, and SHA-256 values. The installer verifies downloads before import and reuses matching weight blobs. `--skip-models` explicitly skips pinned-weight verification. No weights are bundled.

Requirements: Python 3.10+, Rust/Cargo 1.88+ to build the source, and Ollama 0.34.2+ with these model architectures. Windows builds need Visual Studio C++ Build Tools and a Windows SDK; macOS needs Xcode Command Line Tools; Linux needs a C compiler/linker. Python scripts use only the standard library.

Default storage: Linux/macOS `~/.local/share/astra-local-workers`; Windows `%LOCALAPPDATA%/astra-local-workers`. Absolute `ASTRA_LOCAL_DATA_DIR` or installer `--runtime-dir` can override this. Installed `runtime.json` records the real binary and data directory; `scripts/run.py` passes that directory to the runner. The native binary lives under `bin/`, reports under `team-runs/`, downloaded model cache under `model-downloads/`.

Allow at least 25 GB free disk because downloads and imported copies coexist. Allow 16 GB RAM at a minimum; 24–32 GB is more practical. CPU-only inference may be slow. Calls run sequentially, with 16,384 context tokens and up to 4,096 output tokens; thinking is disabled. Granite uses CPU, retaining the original setup's workaround.

Unix run directories and lock files use 0700 and 0600. Windows inherits ACLs from the selected runtime location; the default is under the recipient's LOCALAPPDATA. A nonblocking file lock rejects concurrent councils. Brief and feedback limits are 8,000 UTF-8 bytes each, assembled context 10,000 bytes, API system-plus-prompt 12,000 bytes. Narrow source excerpts when a review prompt becomes too large. Models cannot directly read the filesystem.

Every report says `execution: not_executed`. `ready_for_manager_review` means both critics accepted without unresolved issues; `needs_manager_resolution` means disagreement; `error` means validation or runtime failed. None means an action ran. Raw calls and risk snapshots remain as evidence. Resume requires the same canonical workspace and proposer, a prior report, and actual feedback. Approvals do not carry forward. Validated drafts are saved before reviews, so review failures retain a resumable proposal. Per-call usage includes Ollama nanosecond durations, total seconds, and generation tokens per second; missing or nonpositive durations leave derived metrics null.

`--doctor` checks local connectivity and aliases without inference or filesystem creation. It does not prove response quality or successful council generation. The MCP adapter provides diagnostics and proposal/resume tools over local stdio, exposes no action-execution tool, and opens no network listener.
