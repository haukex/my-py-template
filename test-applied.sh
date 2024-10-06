#!/bin/bash
set -euo pipefail

# This script tests using apply.py on an empty directory to see if the created project works.
# This re-uses the venvs from this directory by default; use -v to create new venvs (takes a while!)

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

VENV_PATH="$SCRIPT_DIR"
usage() { echo "Usage: $0 [-v]" 1>&2; exit 1; }
while getopts "v" OPT; do
    case "${OPT}" in
        v)
            VENV_PATH=.
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

umask 022  # so simple-perms is happy

TEMPDIR="$( mktemp --directory )"
trap 'set +ex; popd; rm -rf "$TEMPDIR"' EXIT

set -x

"$SCRIPT_DIR/apply.py" "$TEMPDIR"

pushd "$TEMPDIR"

touch dummy.py

git init
git add .
git commit -m 'Initial commit (TESTS)'

# make  # dependencies may not be installed

dev/local-actions.sh -e "$VENV_PATH"

set +x
echo -e "\n=====> \e[1;32mALL GOOD\e[0m <====="
