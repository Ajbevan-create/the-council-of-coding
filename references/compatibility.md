# Assistant compatibility

The skill uses the Agent Skills `SKILL.md` format. Direct execution requires shell access to the machine running the installed native runner and Ollama. The installer requires explicit OS and assistant choices; comma-separated assistants and `all` are supported.

| Choice | Integration |
|---|---|
| `codex` | `$CODEX_HOME/skills` when configured; otherwise `~/.agents/skills` |
| `claude-code` | `~/.claude/skills` |
| `opencode` | `$XDG_CONFIG_HOME/opencode/skills`, otherwise `~/.config/opencode/skills` |
| `gemini` | Gemini CLI: `~/.gemini/skills` |
| `perplexity` | Upload ZIP plus local stdio MCP template |
| `generic` | `~/.agents/skills` for hosts supporting that location |
| `custom` | Absolute `--skills-dir`; installer adds the skill folder name |

Refresh or restart the assistant's skill list after installation. Hosts retain their own trust and tool permissions. Installation does not change the assistant model, authentication, global agent instructions, or existing MCP settings. Existing skill folders require `--upgrade`, which preserves a backup. For legacy Codex installs without `CODEX_HOME`, use `custom` with the absolute `.codex/skills` directory. Other hosts can use their documented skill directory or load the skill as task instructions; a directory alone does not add local tool capability.

## Perplexity Computer

Upload the separate `the-council-of-coding-perplexity.zip`, or installer-generated `perplexity-skill.zip`, through Computer > Skills > Create skill > Upload a skill. `SKILL.md` is at the ZIP root; the upload stays below Perplexity's documented 10 MB limit.

A skill upload does not connect cloud execution to local Ollama. For real local delegation, connect the included `scripts/mcp_bridge.py` through a supported local MCP host. After installation, the runtime's `mcp-config.json` provides the exact Python executable and adapter script. Tools: `astra_local_doctor` and `astra_local_propose`. They return proposals for supervisor review and never execute proposed actions.

Perplexity's published local MCP guide documents its macOS app and PerplexityXPC helper. Follow that client's connector setup; availability depends on client/account. Direct local connector support on Windows/Linux is not established by that guide. On an unsupported client, run the council locally and supply its JSON report as a manual handoff. The runner itself works natively on all three OSes; automatic Perplexity access needs a working connector. The package does not publish a server or create a tunnel.

## Other MCP hosts

Optionally merge the runtime's `mcp-config.json` entry into your client's documented MCP settings. The installer writes a template instead of modifying existing client configuration. Use local stdio on the Ollama host, request a doctor's report first, and inspect proposals, critiques, and risk history. The adapter supports the MCP initialize handshake revisions from 2024-11-05 through 2025-11-25. It counters an unknown initialize revision with 2025-11-25 instead of claiming support. Modern-only clients need legacy handshake compatibility.

## Official references

- [OpenAI Docs: skills](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code skills](https://code.claude.com/docs/en/skills)
- [OpenCode skills](https://opencode.ai/docs/skills)
- [Gemini CLI skills](https://geminicli.com/docs/cli/skills/)
- [Perplexity skill uploads](https://www.perplexity.ai/help-center/en/articles/13914413-how-to-use-computer-skills)
- [Perplexity local MCP setup](https://www.perplexity.ai/help-center/en/articles/11502712-local-and-remote-mcps-for-perplexity)
- [MCP stdio transport](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/main/docs/specification/2025-03-26/basic/transports.mdx)
