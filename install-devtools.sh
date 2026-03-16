#!/usr/bin/env bash
if [ ! "$(uname -s)" = "Linux" ]; then
    echo "This is supposed to be run on Linux only! Bye!"
    exit 1
fi

echo "Checking dependencies ..."

if ! command -v "make" &>/dev/null; then
    echo "  Installing make ..."
    sudo apt install make
fi
echo "  ✔️ make"


MISSING_PY_PACKS=""
python3 -c "import tkinter" 2>/dev/null || MISSING_PY_PACKS="$MISSING_PY_PACKS python3-tk"
python3 -c "import venv" 2>/dev/null    || MISSING_PY_PACKS="$MISSING_PY_PACKS python3-venv"

if [ -n "$MISSING_PY_PACKS" ]; then
    echo "  Installing missing Python packages:$MISSING_PY_PACKS ..."
    sudo apt install -y $MISSING_PY_PACKS
fi
echo "  ✔️ python3"

echo "✔️ All done!"
echo ""
echo "Now use make to continue:"
make help