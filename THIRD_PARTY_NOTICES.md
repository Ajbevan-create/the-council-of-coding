# Third-party sources

No model weights, Ollama executable, Rust toolchain, or third-party crate sources are bundled. The installer downloads the pinned model sources in `models/sources.json`; Cargo uses `rust/Cargo.lock`.

- [Empero Qwen3.8-9B Distill](https://huggingface.co/empero-ai/Qwen3.8-9B-Distill): community distillation of Qwen3.5-9B, publisher license Apache-2.0.
- [Ollama Qwen3.5 4B](https://ollama.com/library/qwen3.5:4b): publisher license Apache-2.0; immutable Ollama weight blob is pinned.
- [IBM Granite 4.0 1B GGUF](https://huggingface.co/ibm-granite/granite-4.0-1b-GGUF): publisher license Apache-2.0; bundled chat-template configuration comes from the original local model setup.

Consult publisher repositories and installed dependency licenses for terms and notices. Copyright (C) 2026 Ajbevan-create and contributors. Project code and original documentation are licensed under GNU GPL version 3 only (GPL-3.0-only); see LICENSE. No MIT licensing option is offered for this release. `models/granite-template.txt` retains upstream Apache-2.0 terms; the license text is included in `licenses/Apache-2.0.txt` in the full source package. The separate Perplexity ZIP contains instructions and project notices only; it does not bundle the Granite template or model weights. Downloaded model weights and dependencies retain their upstream terms.
