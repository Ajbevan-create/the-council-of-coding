#!/usr/bin/env python3
"""User-level source installer. Python 3.10+, Rust 1.88+, Ollama 0.34.2+."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
import zipfile

from selection import select_os, select_assistants, target_paths

PACKAGE = Path(__file__).resolve().parent.parent
API = "http://127.0.0.1:11434"
VERSION = "0.3.0"

def digest(path):
    result = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            result.update(block)
    return result.hexdigest()

def verify_package(root=PACKAGE):
    manifest = root / "SHA256SUMS"
    if not manifest.is_file():
        raise ValueError("Package checksum manifest is missing; extract the full release ZIP.")
    for line in manifest.read_text(encoding="utf-8").splitlines():
        expected, name = line.split("  ", 1)
        path = (root / name).resolve()
        if not path.is_relative_to(root.resolve()) or not re.fullmatch(r"[a-f0-9]{64}", expected):
            raise ValueError("Invalid package checksum entry.")
        if not path.is_file() or digest(path) != expected:
            raise ValueError(f"Package checksum mismatch: {name}")

def api(path, payload=None):
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(API + path, data=body, headers={"Content-Type": "application/json"})
    try:
        with opener.open(request, timeout=15) as response:
            return json.load(response)
    except Exception as error:
        raise ValueError(f"Local Ollama check failed: {error}. Launch Ollama or run ollama serve.") from error

def runtime_dir(selected_os, environment, user_home):
    if environment.get("ASTRA_LOCAL_DATA_DIR"):
        root = Path(environment["ASTRA_LOCAL_DATA_DIR"])
    elif selected_os == "windows":
        if not environment.get("LOCALAPPDATA"):
            raise ValueError("LOCALAPPDATA is missing.")
        root = Path(environment["LOCALAPPDATA"]) / "astra-local-workers"
    else:
        root = user_home / ".local/share/astra-local-workers"
    if not root.is_absolute():
        raise ValueError("Runtime directory must be absolute.")
    return root

def command(argv, environment=None):
    subprocess.run([str(item) for item in argv], env=environment, check=True)

def build_native(cargo, rustc, root, selected_os, environment):
    output = subprocess.check_output([rustc, "-vV"], text=True, encoding="utf-8", env=environment)
    hosts = [line.removeprefix("host: ") for line in output.splitlines() if line.startswith("host: ")]
    if len(hosts) != 1 or not re.fullmatch(r"[A-Za-z0-9_]+(?:-[A-Za-z0-9_]+){2,}", hosts[0]):
        raise ValueError("Expected exactly one valid native host triple from rustc -vV.")
    host = hosts[0]
    build_environment = dict(environment, RUSTC=str(rustc))
    command([cargo, "build", "--release", "--locked", "--target", host,
             "--manifest-path", PACKAGE / "rust/Cargo.toml"], build_environment)
    executable = "astra-local-team.exe" if selected_os == "windows" else "astra-local-team"
    return root / "build" / host / "release" / executable

def download(model, cache):
    destination = cache / model["filename"]
    if destination.is_file() and digest(destination) == model["sha256"]:
        return destination
    part = destination.with_suffix(".gguf.part")
    print(f"Downloading {model['role']}: {model['bytes'] / 1e9:.2f} GB", flush=True)
    request = urllib.request.Request(model["url"], headers={"User-Agent": "astra-local-orchestrator/0.3.0"})
    received = 0
    result = hashlib.sha256()
    with urllib.request.urlopen(request, timeout=120) as response, part.open("wb") as stream:
        for block in iter(lambda: response.read(1024 * 1024), b""):
            received += len(block)
            if received > model["bytes"]:
                raise ValueError("Download exceeded its pinned size.")
            stream.write(block)
            result.update(block)
    if received != model["bytes"] or result.hexdigest() != model["sha256"]:
        raise ValueError(f"Model checksum mismatch: {model['alias']}. Nothing was imported.")
    os.replace(part, destination)
    return destination

def modelfile(model, weights):
    filename = weights.as_posix()
    if any(character in filename for character in '\n\r"'):
        raise ValueError("Model path contains an unsupported quote or newline.")
    text = f'FROM "{filename}"\n'
    if model.get("template"):
        text += 'TEMPLATE """' + (PACKAGE / model["template"]).read_text(encoding="utf-8") + '"""\n'
    for key, value in model["parameters"].items():
        text += f"PARAMETER {key} {value}\n"
    return text

def install_models(models, root, ollama, environment, replace=False):
    present = {item["name"] for item in api("/api/tags").get("models", [])}
    cache = root / "model-downloads"
    cache.mkdir(parents=True, exist_ok=True, mode=0o700)
    receipts = []
    for model in models:
        alias = model["alias"]
        if alias in present and not replace:
            info = api("/api/show", {"model": alias})
            if "sha256-" + model["sha256"] not in info.get("modelfile", ""):
                raise ValueError(f"Existing {alias} differs from the pinned weights. Use --replace-models explicitly to replace its alias.")
            receipts.append({"alias": alias, "sha256": model["sha256"], "action": "reused"})
            continue
        if shutil.disk_usage(root).free < model["bytes"] * 2 + 1024**3:
            raise ValueError("Insufficient free disk space for download and import; allow at least 25 GB for the initial setup.")
        weights = download(model, cache)
        with tempfile.TemporaryDirectory(prefix="import-", dir=root) as temporary:
            config = Path(temporary) / "Modelfile"
            config.write_text(modelfile(model, weights), encoding="utf-8")
            command([ollama, "create", alias, "-f", config], environment)
        receipts.append({"alias": alias, "sha256": model["sha256"], "action": "imported"})
    return receipts

def copy_skill(destination, root, binary, upgrade=False):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        if not upgrade:
            raise ValueError(f"Skill already exists: {destination}; use --upgrade to preserve a backup and replace it.")
    # Finish the new copy before moving the existing installation out of the way.
    with tempfile.TemporaryDirectory(prefix=".astra-install-", dir=destination.parent) as temporary:
        staged = Path(temporary) / destination.name
        shutil.copytree(PACKAGE, staged, ignore=shutil.ignore_patterns("target", "__pycache__", "*.pyc", ".git", ".github", "SHA256SUMS"))
        (staged / "runtime.json").write_text(json.dumps({"version": VERSION, "binary": str(binary), "data_dir": str(root)}, indent=2), encoding="utf-8")
        backup = None
        if destination.exists():
            # Keep old SKILL.md files outside assistant discovery directories.
            backups = root / "skill-backups"
            backups.mkdir(parents=True, exist_ok=True, mode=0o700)
            identity = hashlib.sha256(str(destination).encode("utf-8")).hexdigest()[:12]
            backup = backups / f"{destination.name}-{identity}-{time.time_ns()}"
            shutil.move(str(destination), str(backup))
            print(f"Previous skill preserved: {backup}")
        try:
            staged.rename(destination)
        except OSError:
            if backup is not None:
                shutil.move(str(backup), str(destination))
            raise

def install_runtime(build_binary, root, environment):
    """Prepare and diagnose everything before activation; restore on activation error."""
    binary = root / "bin" / build_binary.name
    adapter = root / "adapter"
    with tempfile.TemporaryDirectory(prefix=".runtime-install-", dir=root) as temporary:
        staged = Path(temporary)
        staged_binary = staged / build_binary.name
        shutil.copy2(build_binary, staged_binary)
        staged_adapter = staged / "adapter"
        shutil.copytree(PACKAGE / "scripts", staged_adapter, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        command([staged_binary, "--doctor"], environment)
        config = {"version": VERSION, "binary": str(binary), "data_dir": str(root)}
        (staged / "runtime.json").write_text(json.dumps(config, indent=2), encoding="utf-8")
        mcp_config = {"mcpServers": {"astra-local-council": {"command": sys.executable, "args": [str(adapter / "mcp_bridge.py")]}}}
        (staged / "mcp-config.json").write_text(json.dumps(mcp_config, indent=2), encoding="utf-8")
        replacements = [(staged_binary, binary), (staged_adapter, adapter),
                        (staged / "runtime.json", root / "runtime.json"),
                        (staged / "mcp-config.json", root / "mcp-config.json")]
        backup = root / "runtime-backups" / str(time.time_ns())
        old_paths = []
        activated = []
        binary.parent.mkdir(exist_ok=True, mode=0o700)
        try:
            for source, target in replacements:
                if target.exists() or target.is_symlink():
                    backup.mkdir(parents=True, exist_ok=True, mode=0o700)
                    prior = backup / target.name
                    shutil.move(str(target), str(prior))
                    old_paths.append((prior, target))
                os.replace(source, target)
                activated.append(target)
        except OSError:
            for target in reversed(activated):
                if target.is_dir() and not target.is_symlink():
                    shutil.rmtree(target)
                else:
                    target.unlink()
            for prior, target in reversed(old_paths):
                shutil.move(str(prior), str(target))
            raise
        if old_paths:
            print(f"Previous runtime preserved: {backup}")
    return binary

def main(argv=None):
    if sys.version_info < (3, 10):
        raise ValueError("Python 3.10 or newer is required.")
    parser = argparse.ArgumentParser(description="Choose both an OS and an assistant, then install the local council.")
    parser.add_argument("--os", choices=["linux", "macos", "windows"])
    parser.add_argument("--assistant", help="codex, claude-code, opencode, gemini, perplexity, generic, custom, all; comma-separated")
    parser.add_argument("--skills-dir", type=Path)
    parser.add_argument("--runtime-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Show the selected installation without writing, building, downloading, or contacting Ollama.")
    parser.add_argument("--skip-models", action="store_true", help="Use preinstalled aliases; skip pinned model verification and downloads.")
    parser.add_argument("--replace-models", action="store_true")
    parser.add_argument("--upgrade", action="store_true", help="Back up existing skill folders before replacing them.")
    options = parser.parse_args(argv)
    selected_os = select_os(options.os)
    assistants = select_assistants(options.assistant)
    user_home = Path.home()
    root = options.runtime_dir or runtime_dir(selected_os, os.environ, user_home)
    if not root.is_absolute():
        raise ValueError("--runtime-dir must be absolute.")
    root = root.resolve()
    package = PACKAGE.resolve()
    destinations = list(dict.fromkeys(path for assistant in assistants for path in target_paths(assistant, user_home, os.environ, options.skills_dir)))
    if root.is_relative_to(package) or package.is_relative_to(root):
        raise ValueError("Runtime directory must be separate from the unpacked package.")
    for destination in destinations:
        if destination.is_symlink():
            raise ValueError(f"Skill destination is a symlink: {destination}. Choose its actual directory explicitly.")
        if destination.exists() and not options.upgrade:
            raise ValueError(f"Skill already exists: {destination}. Use --upgrade for a preserved backup.")
        resolved = destination.resolve()
        if resolved.is_relative_to(package) or package.is_relative_to(resolved):
            raise ValueError("Install destination must be separate from the unpacked package.")
        if resolved.is_relative_to(root) or root.is_relative_to(resolved):
            raise ValueError("Runtime and skill directories must be separate from each other.")
    print(json.dumps({"os": selected_os, "assistants": assistants, "runtime": str(root), "skill_folders": [str(path) for path in destinations], "models": "preinstalled aliases" if options.skip_models else "10.2 GB pinned downloads; allow 25 GB free disk"}, indent=2))
    if options.dry_run:
        return 0
    verify_package()
    cargo, rustc, ollama = (shutil.which(name) for name in ["cargo", "rustc", "ollama"])
    if not all([cargo, rustc, ollama]):
        raise ValueError("Install Python 3.10+, Rust 1.88+ from rustup.rs, and Ollama 0.34.2+ from ollama.com/download; ensure cargo, rustc and ollama are on PATH. Windows also needs Visual Studio C++ Build Tools.")
    version = subprocess.check_output([rustc, "--version"], text=True).split()[1]
    if tuple(map(int, version.split(".")[:2])) < (1, 88):
        raise ValueError("Rust 1.88+ is required by the locked dependencies.")
    ollama_version = api("/api/version").get("version", "")
    match = re.match(r"(\d+)\.(\d+)\.(\d+)", ollama_version)
    if not match or tuple(map(int, match.groups())) < (0, 34, 2):
        raise ValueError("Ollama 0.34.2+ is required for these model architectures.")
    root.mkdir(parents=True, exist_ok=True, mode=0o700)
    environment = dict(os.environ, OLLAMA_HOST=API, OLLAMA_NO_CLOUD="1", ASTRA_LOCAL_DATA_DIR=str(root), CARGO_TARGET_DIR=str(root / "build"))
    models = json.loads((PACKAGE / "models/sources.json").read_text(encoding="utf-8"))["models"]
    receipts = [] if options.skip_models else install_models(models, root, ollama, environment, options.replace_models)
    build_binary = build_native(cargo, rustc, root, selected_os, environment)
    binary = install_runtime(build_binary, root, environment)
    for destination in destinations:
        copy_skill(destination, root, binary, options.upgrade)
    if "perplexity" in assistants:
        archive = root / "perplexity-skill.zip"
        with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
            for path in [PACKAGE / name for name in ["SKILL.md", "references/runtime.md", "references/compatibility.md", "LICENSE", "THIRD_PARTY_NOTICES.md"]]:
                bundle.write(path, path.relative_to(PACKAGE).as_posix())
        print(f"Perplexity: upload {archive} on Computer > Skills > Create skill > Upload a skill. Local execution also needs a working local connector; see references/compatibility.md.")
    (root / "install-receipt.json").write_text(json.dumps({"version": VERSION, "os": selected_os, "assistants": assistants, "model_imports": receipts, "model_checks_skipped": options.skip_models, "skill_folders": [str(path) for path in destinations]}, indent=2), encoding="utf-8")
    print(f"Installed. Local MCP connection template: {root / 'mcp-config.json'}")
    return 0

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError, subprocess.CalledProcessError) as error:
        print(f"Installation stopped: {error}", file=sys.stderr)
        raise SystemExit(1)
