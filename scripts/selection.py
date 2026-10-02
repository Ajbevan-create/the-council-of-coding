"""Explicit OS and assistant choices; no installation side effects."""
import platform
import sys
from pathlib import Path

ASSISTANTS = ["codex", "claude-code", "opencode", "gemini", "perplexity", "generic", "custom", "all"]

def host_os():
    try:
        return {"Linux": "linux", "Darwin": "macos", "Windows": "windows"}[platform.system()]
    except KeyError:
        raise ValueError("Supported systems are Linux, macOS, and native Windows.")

def choose(title, choices):
    if not sys.stdin.isatty():
        raise ValueError("Explicit choices required: pass --os and --assistant in noninteractive use.")
    print(title)
    for index, key in enumerate(choices, 1):
        print(f"  {index}. {key}")
    while True:
        try:
            answer = input("Choose a number or name (no default): ").strip().lower()
        except EOFError:
            raise ValueError("Explicit choices required: no input supplied. Pass --os and --assistant explicitly.")
        if answer in choices:
            return answer
        if answer.isdigit() and 1 <= int(answer) <= len(choices):
            return choices[int(answer) - 1]
        print("Please choose one of the listed options.")

def select_os(value=None):
    selected = value or choose("Select your operating system", ["linux", "macos", "windows"])
    if selected not in ("linux", "macos", "windows"):
        raise ValueError("Choose linux, macos, or windows.")
    actual = host_os()
    if selected != actual:
        raise ValueError(f"Selected {selected}; this installer is running on {actual}. Choose the current host OS.")
    return selected

def select_assistants(value=None):
    selected = choose("Select your assistant (Gemini means Gemini CLI)", ASSISTANTS) if value is None else value
    parts = [item.strip().lower() for item in selected.split(",")]
    if not parts or any(item not in ASSISTANTS for item in parts):
        raise ValueError("Select a listed assistant; comma-separated names are supported.")
    if "all" in parts:
        parts = ASSISTANTS[:6] + [item for item in parts if item == "custom"]
    return list(dict.fromkeys(parts))

def target_paths(assistant, user_home, environment, custom=None):
    if assistant == "perplexity":
        return []
    if assistant == "codex":
        root = Path(environment["CODEX_HOME"]) / "skills" if environment.get("CODEX_HOME") else user_home / ".agents/skills"
    elif assistant == "claude-code":
        root = user_home / ".claude/skills"
    elif assistant == "opencode":
        root = Path(environment.get("XDG_CONFIG_HOME") or str(user_home / ".config")) / "opencode/skills"
    elif assistant == "gemini":
        root = user_home / ".gemini/skills"
    elif assistant == "generic":
        root = user_home / ".agents/skills"
    elif assistant == "custom" and custom is not None:
        root = Path(custom)
    else:
        raise ValueError("Custom requires --skills-dir with an absolute directory.")
    if not root.is_absolute():
        raise ValueError("Skill roots, CODEX_HOME, and XDG_CONFIG_HOME must be absolute.")
    return [root / "astra-local-orchestrator"]
