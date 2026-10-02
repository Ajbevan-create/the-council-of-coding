#!/usr/bin/env bash
set -euo pipefail
package_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Install Python 3.10+ from https://www.python.org/downloads/, then rerun this installer.' >&2
  exit 1
fi
exec python3 "$package_root/scripts/install.py" "$@"
