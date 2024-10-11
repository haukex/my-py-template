#!/bin/bash
set -euo pipefail

# This script tests using apply.py on an empty directory to see if the created project works.

script_dir="$( CDPATH='' cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" && pwd )"

usage() { echo "Usage: $0 VENV_PATH" 1>&2; exit 1; }
[[ $# -eq 1 ]] || usage
venv_path="$1"
test -d "$venv_path" || usage

umask 022  # so simple-perms is happy

temp_dir="$( mktemp --directory )"
trap 'set +ex; popd >/dev/null; rm -rf "$temp_dir"' EXIT
set -x

"$script_dir/apply.py" "$temp_dir"

pushd "$temp_dir"

touch dummy.py

git init
git add .
git commit -m 'Initial commit (TESTS)'

dev/local-actions.sh "$venv_path"
