#!/usr/bin/env bash
set -e

if [ "$(uname -s)" != "Linux" ]; then
    echo "This is supposed to be run on Linux only! Bye!"
    exit 1
fi

echo "Checking dependencies ..."

MISSING_PKGS=()

command -v make                 &>/dev/null || MISSING_PKGS+=(make)
command -v gh                   &>/dev/null || MISSING_PKGS+=(gh)
python3 -c "import tkinter"     &>/dev/null || MISSING_PKGS+=(python3-tk)
python3 -c "import venv"        &>/dev/null || MISSING_PKGS+=(python3-venv)
python3 -c "import ensurepip"   &>/dev/null || MISSING_PKGS+=(python3-venv)

if [ ${#MISSING_PKGS[@]} -gt 0 ]; then
    apt-get install -y "${MISSING_PKGS[@]}"
fi

echo ""
echo "Done. Run 'make help' to see available targets."
make help
