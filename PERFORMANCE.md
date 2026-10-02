# Measured performance and actual work

Measured on 2026-10-02, release 0.3.0, on the author's MSI Katana 17 B13VGK: Core i9-13900H (14 cores / 20 threads), 16 GB RAM class (15.37 GiB Linux MemTotal), RTX 4070 Laptop GPU with 8,188 MiB VRAM and NVIDIA driver 595.99.02, 1,024 GB WD PC SN5000S NVMe, NixOS 26.11, kernel 7.2.6. Ollama 0.34.2 and the pinned aliases were already installed.

## Three-run diagnostic measurement

Three sequential CLI runs each requested one proposal/review round, no actions, and the exact answer `COUNCIL_READY`. All three completed with `ready_for_manager_review`, an empty action list, and `execution: not_executed`. Two of the three returned the exact requested answer; run 3 added extra text despite both critics accepting it. The supervisor detected that mismatch; reviewer agreement did not establish task correctness. No proposed command was executed.

| Run | End-to-end wall time | Exact answer | Model calls |
|---|---|---|---|
| 1 | 22.400 s | Passed | 3 |
| 2 | 24.770 s | Passed | 3 |
| 3 | 22.051 s | Failed | 3 |

Median end-to-end time: **22.400 seconds**. This is latency for a very small three-model council, not the time to solve a programming task.

| Model | Total input tokens | Total output tokens | Generation tokens/s | Mean model-load time | Mean API-call total |
|---|---|---|---|---|---|
| `qwen3.8-distill:9b-q4` | 975 | 106 | 24.27 | 5.52 s | 7.47 s |
| `qwen3.5:4b` | 624 | 43 | 49.00 | 10.19 s | 10.75 s |
| `granite4:1b-q4-local` | 615 | 45 | 38.97 | 3.28 s | 4.84 s |

Throughput is total generated tokens divided by total generation duration across the three calls for that model. It excludes loading and prompt processing. End-to-end wall time includes CLI overhead and every sequential model call. Ollama reports durations in nanoseconds; see [the official chat API fields](https://docs.ollama.com/api/chat). The machine reloaded models during these runs: summed reported loading time accounts for about 80–85% of each council's wall time. This is an observation from the timing counters, not a measured claim about the cause of every reload.

These are short outputs (24–42 proposer tokens, 14–15 reviewer tokens, 15 safety tokens), so throughput is a small-sample measurement. Cache state, power profile, thermals, background load, and GPU allocation were not controlled. Qwen used Ollama's automatic placement; Granite was explicitly CPU-only. No peak RAM/VRAM profiling was performed. The ThinkPad T14 with 32 GB DDR4 was not tested, and these GPU-host figures should not be extrapolated to its CPU.

The sanitized counters are in [benchmarks/diagnostic-2026-10-02.json](benchmarks/diagnostic-2026-10-02.json). Private raw reports and actual host paths are excluded from the repository. To reproduce, build the runner, put this brief in a local file, invoke it with an absolute existing workspace and `--rounds 1`, and time the process three times:

```text
Diagnostic inference test. Return actions as an empty array and answer exactly COUNCIL_READY. Do not propose any command. The supervisor will check the JSON; do not claim files changed or tests ran.
```

Runtime options: 16,384 context tokens, 4,096 output-token cap, thinking disabled, temperature 0.6, top-p 0.95, top-k 20, and two-minute keep-alive. Granite overrides temperature to 0.3 and `num_gpu` to 0. Models run sequentially. Model agreement is not execution permission.

## What the local workers actually produced

The local council was used for original packaging drafts and release refinement. The supervising assistant inspected the complete proposals and supplied source and actual correction feedback. Before clarifying the worker prompt, there were four drafting calls:

| Task | Proposer | Actual outcome |
|---|---|---|
| Add duration/throughput metrics | Qwen3.8 Distill 9B | Proposed an inappropriate Cargo command and invalid Rust; reviewer rejected it; no action executed |
| Correct that draft using actual feedback | Qwen3.8 Distill 9B | Malformed Python action/invalid Rust remained; the subsequent review exceeded the input limit; no action executed |
| Preserve drafts after reviewer failure | Qwen3.8 Distill 9B | Described the intended fix but proposed only running tests; no implementation action executed |
| Narrow metrics helper only | Qwen3.5 4B | Proposed extra toolchain/scaffolding actions instead of the requested helper; reviewer rejected it; no action executed |

**None of those four patches was applied as written.** The supervisor clarified the prompt so a helper request produces code instead of setup commands. A fifth call produced a helper with incorrect input field names. Actual review feedback corrected those names in a sixth call; both critics accepted it, but a real regression test still failed because it changed integer nanosecond values into floats and discarded raw zero durations. The supervisor corrected the four raw duration output fields, removed unused bindings, integrated the locally drafted helper, and verified all tests passed. The supervisor directly implemented the partial-progress recovery, runtime upgrade staging/rollback, release tooling, and regression tests. An earlier answer-only smoke test also appended unrequested text despite both critics accepting; actual supervisor feedback corrected it on resume.

The final software passes its automated checks and real diagnostic/inference tests, but these results do not establish strong autonomous coding quality. The council's useful contribution was a reviewable drafting/review loop and visible failure evidence. It needs supervision, small tasks, exact source, and actual acceptance checks. No paid cloud implementation worker was used; supervising planning/review/corrections still used the selected root assistant.

For the Linux distribution refinement, two additional Qwen drafting calls proposed a native build-target helper and resumed it with actual review feedback. The first included unwanted scaffolding and incomplete target validation. Both critics accepted the resumed helper, but a real test showed its regex accepted a malformed target by matching only a prefix. The supervisor changed this to exactly-one, whole-string validation, removed redundant imports, used the existing command wrapper, and integrated the helper with passing regression tests. Direct supervisor corrections also handled canonical package paths, terminal EOF feedback, POSIX launchers, and distro documentation/CI. These calls are separate from the three-run diagnostic timing sample above.
