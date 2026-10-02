#!/bin/sh
set -eu
package_root=$(CDPATH= cd -P "$(dirname "$0")" && pwd)
if ! command -v python3 >/dev/null 2>&1; then
  echo 'Install Python 3.10+ from https://www.python.org/downloads/, then rerun this installer.' >&2
  exit 1
fi
exec python3 "$package_root/scripts/install.py" "$@"
