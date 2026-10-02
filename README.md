# The Council of Coding

Download the source installer and separate Perplexity upload ZIP from [the 0.3.1 release](https://github.com/Ajbevan-create/the-council-of-coding/releases/tag/v0.3.1).

An open-source local AI council for coding, testing, and drafting. Your current assistant supervises a Qwen proposer, a Qwen reviewer, and a Granite safety critic. The workers return exact command/code proposals; the supervisor reviews them, performs authorized work, verifies the results, and sends actual feedback back to the council.

**The runner never executes model-proposed commands.** Agreement between models does not authorize an action or establish that the code is correct. Real review and tests remain necessary. Local inference uses your hardware; supervising work can still consume your assistant's account usage.

Native source installers are provided for Linux, macOS, and Windows, with mandatory OS and assistant selection. Supported profiles are Codex, Claude Code, OpenCode, Gemini CLI, Perplexity, generic Agent Skills, custom, and all standard targets. The skill's existing name, `astra-local-orchestrator`, and the binary name, `astra-local-team`, remain for compatibility.

## How the council works

```mermaid
flowchart LR
    S[Your supervising assistant] --> B[Bounded brief and source]
    B --> P[Local Qwen proposer]
    P --> R[Local Qwen reviewer]
    R --> G[Local Granite safety critic]
    G --> J[JSON report and risk history]
    J --> S
    S --> V[Authorized execution and verification]
    V --> F[Actual feedback for resume]
    F --> B
```

Calls run sequentially. Workers cannot inspect your project by themselves: the supervisor supplies relevant source, or reviews and executes a proposed inspection and returns its results. The local council is a drafting and review tool, not an autonomous shell executor.

| Role | Local alias | Quantized weight size |
|---|---|---|
| Default proposer | `qwen3.8-distill:9b-q4` | 5.78 GB |
| Reviewer / alternate proposer | `qwen3.5:4b` | 3.39 GB |
| Safety critic, forced to CPU | `granite4:1b-q4-local` | 1.02 GB |

The default proposer is a **community Qwen3.8 Distill built on Qwen3.5-9B**, not an official small Qwen3.8 release. Sources, pinned revisions/digests, sizes, and SHA-256 hashes are in [models/sources.json](models/sources.json). The installer verifies weights before import. Models and toolchains are downloaded separately and are not bundled.

## Minimum system specifications and recommendations

These are practical planning guidelines for the default models and 16K context, not a certification of every machine. The measured host had 16 GB system RAM plus an 8 GB GPU. RAM, VRAM, context, background applications, and Ollama's model loading behavior affect whether a workload fits.

| Component | Minimum starting point | Recommended |
|---|---|---|
| CPU / architecture | Modern 64-bit multicore CPU supported by Ollama and Rust | 6 or more modern physical cores; recent Intel/AMD or Apple Silicon |
| RAM with a supported discrete GPU | 16 GB, as tested with 8 GB VRAM | 32 GB or more |
| CPU-only / shared-memory setup | Plan for at least 24 GB; this mode was not benchmarked here | 32 GB or more; use the 4B proposer for lighter tasks |
| GPU | Optional; 8 GB VRAM is the tested accelerated starting point | Supported GPU with 12 GB or more VRAM, or Apple Silicon with adequate unified memory |
| Storage | 25 GB free for roughly 10.2 GB downloads, imported models, and build files | SSD with 35 GB or more free; allow space for retained reports and backups |
| Software | Python 3.10+, Rust/Cargo 1.88+, Ollama 0.34.2+ | Current compatible stable releases and working platform build tools |
| Connectivity | Internet for initial model/dependency downloads | After setup, inference uses the local loopback Ollama endpoint |

GPU support depends on the OS, device, and driver; consult [Ollama's hardware support](https://docs.ollama.com/gpu). A dedicated GPU is optional, but CPU-only inference can be much slower. More RAM is useful for source context and background tools; quantization does not establish equivalent model quality.

## Installation

1. Extract the release source ZIP or clone this repository into a user-writable directory.
2. Install [Python](https://www.python.org/downloads/), [Rust/Cargo](https://rustup.rs/), and [Ollama](https://ollama.com/download). Reopen the terminal so the tools are on `PATH`.
3. Install native build tools: a C compiler/linker on Linux; Xcode Command Line Tools on macOS (`xcode-select --install`); Visual Studio Build Tools with **Desktop development with C++** and a Windows SDK on Windows. WSL is not required.
4. Launch Ollama or run `ollama serve` in another terminal on the same machine, using local port 11434.
5. Run the installer from this directory:

   | OS | Command |
   |---|---|
   | Linux / macOS | `sh install.sh` |
   | Windows Command Prompt | `install.cmd` |
   | Windows PowerShell | `py -3 scripts/install.py` |

6. Select your OS, then your assistant. Neither menu has a default; blank and invalid answers require another choice. OS selection must match the machine running the installer. Refresh/restart your assistant's skill list after installation.

Python uses only the standard library; no pip packages are needed. On NixOS, expose native Python, Cargo, Rust, the linker, and Ollama on `PATH` using your normal Nix setup; generic downloaded toolchain executables may need NixOS-specific integration.

Linux installation is distribution-neutral: no DEB/APT, systemd, or Bash requirement. Debian/Ubuntu, Fedora/RHEL, Arch, openSUSE, Alpine/musl, NixOS, and other distributions use the same source installer when compatible prerequisites are available. See [the Linux distribution guide](references/linux.md) for native toolchains, CA certificates, and Ollama/libc requirements. The installer builds for the actual Rust host target even when cross-compilation defaults are configured.

The installer downloads and verifies pinned weights, imports aliases, builds the runner for your OS, checks its local diagnostic, and installs the selected skill folders. It does not alter your assistant's authentication, selected model, global agent instructions, or existing MCP configuration.

Both choices are required for noninteractive use:

```text
python3 scripts/install.py --os linux --assistant codex,claude-code,opencode,gemini --dry-run
py -3 scripts/install.py --os windows --assistant codex,claude-code
python3 scripts/install.py --os macos --assistant perplexity
```

Use the OS of the current shell; WSL selects `linux`. `--dry-run` performs no writes, builds, downloads, or Ollama requests. `custom` needs an absolute `--skills-dir`; absolute `--runtime-dir` selects a separate runtime location. Existing skill folders require `--upgrade`, with preserved backups outside skill discovery. The runtime replacement is staged and diagnosed before activation; activation failures restore previous runtime files.

`--skip-models` uses the required existing aliases and skips pinned-weight verification. `--replace-models` explicitly permits replacing conflicting aliases. Matching weight blobs are reused; other existing aliases stop installation. Model caches and install receipts remain in the runtime directory.

## Assistant compatibility

| Choice | Integration |
|---|---|
| Codex | `$CODEX_HOME/skills` when configured; otherwise `~/.agents/skills` |
| Claude Code | `~/.claude/skills` |
| OpenCode | `$XDG_CONFIG_HOME/opencode/skills`, otherwise `~/.config/opencode/skills` |
| Gemini | **Gemini CLI**, using `~/.gemini/skills` |
| Perplexity | Skill-upload ZIP and a local MCP template; a supported connector is needed for automatic local calls |
| Generic / custom | Agent Skills discovery or your explicitly selected absolute directory |

For legacy Codex setups, `custom --skills-dir` can select the absolute `.codex/skills` directory. Browser chat apps do not gain local shell access just from a skill upload. See [compatibility and official references](references/compatibility.md).

The installer generates `mcp-config.json` with the actual Python executable and adapter location. Optionally add that entry using your client's documented MCP settings. The adapter exposes only `astra_local_doctor` and `astra_local_propose`; it never executes proposed actions and opens no network listener. It supports initialize-handshake MCP revisions through 2025-11-25; modern-only clients need legacy compatibility.

Perplexity Computer accepts the separate `the-council-of-coding-perplexity.zip` or installer-generated `perplexity-skill.zip`. Upload through Computer > Skills > Create skill > Upload a skill. Perplexity's documented local MCP setup uses its macOS app and helper; other clients may need a manual local-report handoff. Uploading the instructions does not connect a cloud sandbox to your PC.

## Usage and feedback

Invoke `$astra-local-orchestrator` in a skill-capable assistant. Start with a diagnostic:

```text
python3 <absolute-installed-skill-directory>/scripts/run.py --doctor
```

Replace the placeholder with the installed path; Windows uses `py -3`. For a bounded council task:

```text
python3 <absolute-installed-skill-directory>/scripts/run.py --workspace <absolute-project-directory> --brief <absolute-task-file> --rounds 1
```

The brief must include the exact task, source needed for that task, file scope, constraints, and acceptance checks. Inspect the whole JSON report and code before acting. After actual execution or review, resume with the same workspace and proposer using `--resume <absolute-prior-run-directory> --feedback <absolute-results-file>`. Use `--model qwen3.5:4b` to select the lighter proposer.

Reports always say `execution: not_executed`. `ready_for_manager_review` means both critics accepted without unresolved issues. `needs_manager_resolution` means disagreement remains; `error` records validation/runtime failure. None proves that a command ran. Valid drafts survive subsequent review failures so they can be resumed with real feedback. Risk evidence persists; approval does not carry forward.

Briefs and feedback are limited to 8,000 UTF-8 bytes, assembled context to 10,000, and API system-plus-prompt to 12,000. Each call uses up to 16,384 context tokens and 4,096 output tokens; thinking is disabled. Large code drafts can exceed review limits: narrow the task. A nonblocking lock prevents concurrent councils. [Runtime details](references/runtime.md) explain storage and artifacts.

## Author's system, work, and measured performance

The measured development host is an **MSI Katana 17 B13VGK** running **NixOS 26.11 (Zokor)**, kernel 7.2.6, with a **Core i9-13900H** (14 cores / 20 threads), **16 GB RAM class** (15.37 GiB reported by Linux), an **RTX 4070 Laptop GPU** (8,188 MiB VRAM, driver 595.99.02), and a **1,024 GB WD PC SN5000S NVMe SSD**. Hardware/model identifiers were read on the actual host; usernames, hostnames, serials, and private paths are omitted.

An earlier requested target was a **ThinkPad T14 Gen 2 Intel with 32 GB DDR4**. Its exact CPU/GPU and OS were not verified, and it was not benchmarked here. Its RAM is a useful CPU-only starting point; the measured GPU-host speed should not be treated as a ThinkPad result.

[PERFORMANCE.md](PERFORMANCE.md) contains measured run latency, per-model token throughput, methodology, and the actual local drafting outcomes. During development, workers proposed implementation/refinement drafts; the supervising assistant rejected malformed or incorrect commands/code and implemented direct corrections. A smoke-test answer also needed actual feedback before it matched the requested text. Model agreement alone missed that problem.

The resulting project provides the Rust council, explicit multi-OS/multi-assistant installer, verified model sources, a local MCP adapter, retained risk/feedback artifacts, upgrade recovery, release tooling, and regression tests. [VALIDATION.md](VALIDATION.md) distinguishes software checks, real local inference, platform checks, and model-quality limits. This is not a general coding benchmark or a claim of equivalent quality to a frontier model.

## Development and troubleshooting

```text
cargo test --locked --manifest-path rust/Cargo.toml
python3 -m unittest discover -s tests -v
cargo build --release --locked --manifest-path rust/Cargo.toml
python3 scripts/package_release.py --checksums-only
python3 scripts/package_release.py --output-dir <absolute-directory-outside-this-repository>
```

Windows uses `py -3`. The GitHub Actions matrix covers native Linux, macOS, and Windows, plus installer/MCP/POSIX-launcher contracts in Ubuntu, Fedora, Arch, openSUSE, and Alpine containers. `.gitattributes` preserves LF bytes so Windows clones can verify the source checksum manifest.

If prerequisites are missing, install them and reopen your terminal. If Ollama is unavailable, launch it on the same host. Checksum/alias conflicts stop imports; use explicit replacement or the documented skip option deliberately. If the lock is busy, wait for the current council. A diagnostic passes without inference and therefore does not establish model generation or quality. Close an active Windows executable before upgrading. Share release/source files rather than runtime reports, caches, account settings, or credentials.

See [CONTRIBUTING.md](CONTRIBUTING.md) for changes and [CHANGELOG.md](CHANGELOG.md) for releases.

## License

Copyright (C) 2026 Ajbevan-create and contributors. Project code and original documentation are licensed under the [GNU General Public License, version 3 only (GPL-3.0-only)](LICENSE). You may redistribute and modify them under GPL version 3. They are provided without any warranty; see LICENSE for the full terms. The bundled Granite chat-template configuration retains its upstream Apache-2.0 terms; see [third-party notices](THIRD_PARTY_NOTICES.md) and [Apache-2.0](licenses/Apache-2.0.txt). Downloaded model weights and installed dependencies retain their publishers' licenses. No model weights are committed to this repository.
