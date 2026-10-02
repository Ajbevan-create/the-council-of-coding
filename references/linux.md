# Linux distributions

The source installer is distribution-neutral. It uses Python and a native Cargo build, has no `.deb`/APT dependency, and does not require systemd or Bash. Run `sh install.sh` or `python3 scripts/install.py` on any Linux distribution that supplies the compatible prerequisites below. Choose **linux** in the mandatory OS menu, then select your assistant.

## Prerequisites

- Python 3.10 or newer with its standard-library HTTPS/SSL support and a trusted system CA certificate bundle. No pip dependencies are needed.
- Rust/Cargo 1.88 or newer for your actual host architecture/libc, plus a working native C linker.
- Ollama 0.34.2 or newer that actually runs on the same host, with enough RAM/storage and supported hardware drivers. Start it with `ollama serve`; use your distribution's service manager only if you want automatic startup.
- A writable user installation directory. The skill installer runs as your user and does not invoke `sudo`, install OS packages, or change system services.

Install these prerequisites through your distribution's supported tooling. Package names and available versions vary by release; check `python3 --version`, `rustc --version`, `cargo --version`, and `ollama --version` before proceeding.

| Distribution family | Prerequisite tooling / considerations |
|---|---|
| Debian, Ubuntu, Mint, Pop!_OS | APT; Python, C build tools, CA certificates, and a sufficiently recent native Rust toolchain |
| Fedora, RHEL-family, Rocky, AlmaLinux | DNF; older enterprise releases may need a newer Rust/Python toolchain |
| Arch, Manjaro, EndeavourOS | Pacman; Python, base development tools, native Rust, and CA certificates |
| openSUSE Leap/Tumbleweed, SUSE | Zypper; Python, native development tools, Rust, and CA certificates |
| Alpine and other musl systems | APK or distro tooling; use a native musl Rust/C toolchain and an Ollama package/build compatible with musl |
| NixOS / Nix | Nixpkgs-native Python, Cargo, Rust, compiler/linker, certificates, and Ollama; preserve runtime dependencies in your Nix setup |
| Void, Gentoo, Slackware and others | Their native package/build tools; the same version, libc, certificates, and local Ollama requirements apply |

For NixOS, a starting development shell is `nix-shell -p python3 rustc cargo gcc cacert`, with a compatible Ollama installation available separately. Confirm the provided versions meet the requirements. Binaries built outside the Nix store still depend on their Nix runtime paths; keep the relevant packages referenced or rebuild after garbage collection. See the [NixOS Rust guide](https://wiki.nixos.org/wiki/Rust) and [native build environments](https://wiki.nixos.org/wiki/FAQ/I_installed_a_library_but_my_compiler_is_not_finding_it._Why%3F).

Upstream precompiled Ollama archives are not a universal libc/CPU guarantee. On musl, NixOS, unusual architectures, and older distributions, use a working distro-native package or supported source build. Check [Ollama's Linux instructions](https://docs.ollama.com/linux) and [Rust platform support](https://doc.rust-lang.org/rustc/platform-support.html). Inference always expects `http://127.0.0.1:11434` on the runner's host; a remote endpoint is not configurable.

## Verify before installing

From the extracted repository:

```sh
python3 -c "import ssl, urllib.request; print(ssl.OPENSSL_VERSION)"
sh install.sh --os linux --assistant codex --dry-run
```

The preview performs no writes, builds, downloads, or Ollama requests. For installation, launch local Ollama and run `sh install.sh`, or pass both explicit selection flags. Using `--skip-models` requires the existing council aliases. On a minimal distribution you may need the distribution's Python SSL/certificate packages before HTTPS model downloads work.

The runtime builds from source for the actual Rust host target; a user-configured cross-compilation target must not redirect the native install. No precompiled runner is distributed across incompatible Linux libcs.

## Coverage

A full local install and inference were exercised on NixOS. Native OS CI checks Ubuntu, macOS, and Windows. Linux container CI exercises installer/MCP contracts, source checksums, and the POSIX launcher on Ubuntu, Fedora, Arch, openSUSE Tumbleweed, and Alpine. Containers do not test GPU drivers, real Ollama inference, every derivative distro, or every CPU architecture. Consult [VALIDATION.md](../VALIDATION.md) for the actual recorded results.
