---
name: astra-local-orchestrator
license: MIT
description: Delegate bounded implementation, testing, or drafting to local Qwen workers with Qwen and Granite review, then inspect and execute authorized proposals using the current supervising assistant. Requires an installed local Ollama council. Skip trivial tasks, explicit single-agent work, and local implementation workers.
---

# Local Council Orchestrator

Keep the current assistant and selected model as supervisor. Local workers propose complete commands or code; the supervisor reviews them, executes routine authorized actions with host tools, verifies results, and supplies actual feedback. The runner and MCP adapter never execute model-proposed actions. Model agreement is advice, not permission.

## Establish the execution environment

Read [runtime details](references/runtime.md) for models, limits, and report meanings, and [compatibility](references/compatibility.md) for the current host.

- When `ASTRA_LOCAL_WORKER=1`, or when assigned a local implementation-worker brief, perform the assigned work directly. Do not recursively invoke this skill.
- Prefer an available `astra_local_doctor` MCP tool; otherwise run the installed skill's `scripts/run.py --doctor` with Python 3. The installer creates recipient-specific `runtime.json` beside this skill.
- Verify that the runtime, real project paths, and Ollama are on the same host. A cloud sandbox's loopback address refers to that sandbox, not the user's computer. Uploading a skill does not connect the two.
- If the runtime or connector is unavailable, report its actual diagnostic and point to the package installer. Do not claim local work occurred or silently substitute cloud workers. Continue useful independent planning.

## Draft, review, and execute

1. Write a bounded brief with exact file scope, relevant source snippets, constraints, and meaningful acceptance checks. Supply source explicitly: workers cannot inspect files unless the supervisor executes a proposed inspection and returns its result.
2. Call `astra_local_propose` with an absolute existing workspace, brief, and one to three rounds. Alternatively run:

   ```text
   python3 <absolute-skill-directory>/scripts/run.py --workspace <absolute-project-directory> --brief <absolute-brief-file> --rounds 2 --model qwen3.8-distill:9b-q4
   ```

   On Windows use `py -3`. Resolve placeholders to real host paths before executing.
3. Inspect the complete proposal, critiques, raw output when needed, and risk history. Confirm paths, argument quoting, source facts, and effects even when both critics accept. Neither `ready_for_manager_review` nor a model approval flag authorizes execution.
4. Execute routine actions within the user's authorization and verify actual results. Ask the current user about dangerous or materially uncertain actions lacking existing specific authorization, after preparing a reviewable result. Prior authorization counts. Respect the user's approval rules and preferences.
5. Return actual outputs and focused corrections through a resume call using the same workspace and proposer, plus `--resume <absolute-run-directory> --feedback <absolute-results-file>`; or the MCP tool's `resume_dir` and `feedback`. Resume retains risk evidence but does not carry approvals forward. Narrow failed tasks and disclose direct supervisor corrections. Do not force consensus or invent successful tests.

Default proposer: community Qwen3.8 Distill 9B at Q4_K_M. Alternate proposer and reviewer: `qwen3.5:4b`. Safety critic: `granite4:1b-q4-local`, on CPU. Keep supervising model and account settings unchanged. Local inference runs on the recipient's machine; supervising work can still consume their assistant's account usage. Do not promise equivalent quality, a quota reduction, or unlimited usage.
