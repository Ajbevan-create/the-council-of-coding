# Contributing

Use a focused issue or pull request with the problem, proposed behavior, and evidence from your host. Include OS, Rust/Python/Ollama versions, hardware, and reproducible steps when relevant. Omit credentials, personal runtime reports, machine usernames, and private source.

Run `cargo test --locked --manifest-path rust/Cargo.toml` and `python3 -m unittest discover -s tests -v`; Windows uses `py -3`. Build with `cargo build --release --locked --manifest-path rust/Cargo.toml`. Keep native Windows and macOS support intact. The CI workflow checks all three OSes.

The runner must never execute model-proposed commands. Preserve review disagreement, exact risk evidence, and actual feedback. Do not silently truncate proposed code to fit a review. Performance claims need measured duration/token data and the exact test conditions.

After changing package files, regenerate `SHA256SUMS` with `python3 scripts/package_release.py --checksums-only`. Release archives are generated outside the source tree; never commit model weights, runtime configuration, or reports.

Project code and original documentation are licensed under GPL-3.0-only. Contributions to them are accepted under the same license; see LICENSE. Keep third-party model and template notices intact.
