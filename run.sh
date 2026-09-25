#!/bin/bash
# Launches the built ROM in BlastEm.
set -euo pipefail
cd "$(dirname "$0")"
ROM="out/rom.bin"
if [ ! -f "$ROM" ]; then
    echo "ROM not found at $ROM — run ./build.sh first." >&2
    exit 1
fi
blastem "$ROM"
