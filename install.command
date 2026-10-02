#!/usr/bin/env bash
set -euo pipefail
package_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
bash "$package_root/install.sh" "$@"
