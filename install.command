#!/bin/sh
set -eu
package_root=$(CDPATH= cd -P "$(dirname "$0")" && pwd)
exec sh "$package_root/install.sh" "$@"
