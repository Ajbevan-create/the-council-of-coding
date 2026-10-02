#!/usr/bin/env python3
"""Invoke the installed native runner using the recipient's runtime configuration."""
import json
import os
from pathlib import Path
import subprocess
import sys

def runtime_config():
    directory = Path(__file__).resolve().parent
    for path in [directory.parent / "runtime.json", directory.parent.parent / "runtime.json"]:
        if path.is_file():
            try:
                value = json.loads(path.read_text(encoding="utf-8"))
                binary = Path(value["binary"])
                data_dir = Path(value["data_dir"])
            except (ValueError, KeyError, TypeError) as error:
                raise ValueError(f"Invalid runtime configuration: {path}") from error
            if binary.is_absolute() and binary.is_file() and data_dir.is_absolute():
                return binary, data_dir
    raise ValueError("Installed runtime configuration is missing. Run the package installer first.")

def main():
    binary, data_dir = runtime_config()
    environment = dict(os.environ, ASTRA_LOCAL_DATA_DIR=str(data_dir))
    return subprocess.run([str(binary), *sys.argv[1:]], env=environment).returncode

if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, OSError) as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1)
