#!/usr/bin/env python3
"""Local stdio MCP adapter. Exposes diagnostics and proposals, never action execution."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
from run import runtime_config

MODELS = ["qwen3.8-distill:9b-q4", "qwen3.5:4b"]
PROTOCOL_VERSIONS = ["2024-11-05", "2025-03-26", "2025-06-18", "2025-11-25"]
TOOLS = [
    {"name": "astra_local_doctor", "description": "Check the installed local council and model aliases; no inference or proposed action execution.",
     "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
     "annotations": {"readOnlyHint": True, "destructiveHint": False, "openWorldHint": False}},
    {"name": "astra_local_propose", "description": "Ask local Qwen and Granite models for a reviewed JSON action proposal. Writes local council artifacts. Never executes proposed commands.",
     "inputSchema": {"type": "object", "properties": {
         "workspace": {"type": "string", "description": "Absolute existing path on the machine running this MCP server."},
         "brief": {"type": "string", "description": "Bounded task and relevant source; at most 8000 UTF-8 bytes."},
         "model": {"type": "string", "enum": MODELS},
         "rounds": {"type": "integer", "minimum": 1, "maximum": 3},
         "resume_dir": {"type": "string"}, "feedback": {"type": "string"}},
         "required": ["workspace", "brief"], "additionalProperties": False},
     "annotations": {"readOnlyHint": False, "destructiveHint": False, "openWorldHint": False}}
]

def bounded_text(value, name):
    if not isinstance(value, str) or len(value.encode("utf-8")) > 8000:
        raise ValueError(f"{name} must be a string of at most 8000 UTF-8 bytes.")
    return value

def tool_call(name, arguments):
    if not isinstance(arguments, dict):
        raise ValueError("Tool arguments must be an object.")
    binary, root = runtime_config()
    environment = dict(os.environ, ASTRA_LOCAL_DATA_DIR=str(root))
    if name == "astra_local_doctor":
        if arguments:
            raise ValueError("Doctor takes no arguments.")
        argv = [str(binary), "--doctor"]
    elif name == "astra_local_propose":
        if set(arguments) - {"workspace", "brief", "model", "rounds", "resume_dir", "feedback"}:
            raise ValueError("Unknown tool argument.")
        workspace = Path(arguments.get("workspace", ""))
        if not workspace.is_absolute() or not workspace.is_dir():
            raise ValueError("workspace must be an absolute existing directory on this machine.")
        brief = bounded_text(arguments.get("brief"), "brief")
        model = arguments.get("model", MODELS[0])
        rounds = arguments.get("rounds", 2)
        if model not in MODELS or type(rounds) is not int or not 1 <= rounds <= 3:
            raise ValueError("Invalid model or round count.")
        if ("resume_dir" in arguments) != ("feedback" in arguments):
            raise ValueError("resume_dir and actual feedback must be supplied together.")
        resume = None
        feedback = None
        if "resume_dir" in arguments:
            resume = Path(arguments["resume_dir"])
            if not resume.is_absolute() or not resume.is_dir():
                raise ValueError("resume_dir must be an absolute existing council run directory.")
            feedback = bounded_text(arguments["feedback"], "feedback")
        inputs = root / "bridge-inputs"
        inputs.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Keep inputs as evidence alongside the runner's retained report artifacts.
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md", dir=inputs, delete=False) as stream:
            stream.write(brief)
            task_path = stream.name
        argv = [str(binary), "--workspace", str(workspace), "--brief", task_path, "--model", model, "--rounds", str(rounds)]
        if resume is not None:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".md", dir=inputs, delete=False) as stream:
                stream.write(feedback)
                feedback_path = stream.name
            argv += ["--resume", str(resume), "--feedback", feedback_path]
    else:
        raise ValueError("Unknown tool.")
    result = subprocess.run(argv, capture_output=True, text=True, encoding="utf-8", env=environment, timeout=1800)
    text = result.stdout.strip()
    if not text or len(text.encode("utf-8")) > 512000:
        raise ValueError("Runner returned an empty or oversized report; inspect local artifacts.")
    json.loads(text)
    return {"content": [{"type": "text", "text": text}], "isError": result.returncode != 0}

def response(request):
    identifier = request.get("id")
    method = request.get("method")
    params = request.get("params", {})
    if not isinstance(params, dict):
        raise ValueError("params must be an object.")
    if method == "initialize":
        requested = params.get("protocolVersion")
        result = {"protocolVersion": requested if requested in PROTOCOL_VERSIONS else PROTOCOL_VERSIONS[-1],
                  "capabilities": {"tools": {}}, "serverInfo": {"name": "astra-local-council", "version": "0.2.0"}}
    elif method == "ping":
        result = {}
    elif method == "tools/list":
        result = {"tools": TOOLS}
    elif method == "tools/call":
        try:
            result = tool_call(params.get("name"), params.get("arguments", {}))
        except (ValueError, OSError, TypeError, subprocess.TimeoutExpired) as error:
            result = {"content": [{"type": "text", "text": str(error)}], "isError": True}
    else:
        return {"jsonrpc": "2.0", "id": identifier, "error": {"code": -32601, "message": "Method not found"}}
    return {"jsonrpc": "2.0", "id": identifier, "result": result}

def main():
    # Native Windows otherwise uses the console code page for redirected stdio.
    sys.stdin.reconfigure(encoding="utf-8")
    sys.stdout.reconfigure(encoding="utf-8")
    for line in sys.stdin:
        try:
            if len(line.encode("utf-8")) > 65536:
                raise ValueError("Request exceeds 64 KB.")
            request = json.loads(line)
            if not isinstance(request, dict) or request.get("jsonrpc") != "2.0":
                raise ValueError("Invalid JSON-RPC request.")
            if "id" not in request:
                continue
            answer = response(request)
        except (ValueError, TypeError) as error:
            answer = {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": str(error)}}
        print(json.dumps(answer), flush=True)

if __name__ == "__main__":
    main()
