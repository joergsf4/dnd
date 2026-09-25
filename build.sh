#!/bin/bash
# Builds the SGDK project inside the doragasu/docker-sgdk container.
# Usage: ./build.sh          -> build the ROM
#        ./build.sh clean    -> clean build artifacts
set -euo pipefail
cd "$(dirname "$0")"
docker run --rm -v "$PWD":/m68k -t registry.gitlab.com/doragasu/docker-sgdk:v2.11 "$@"

# Requirement: keep the ROM within the biggest commercial Mega Drive cartridge size
# (40 Mbit = 5 MB, Super Street Fighter II). Only checked after a normal build.
if [ "${1:-}" != "clean" ] && [ -f out/rom.bin ]; then
    LIMIT=5242880
    SIZE=$(wc -c < out/rom.bin | tr -d ' ')
    echo "ROM size: $SIZE bytes ($((SIZE * 100 / LIMIT)) % of the $LIMIT byte limit)"
    if [ "$SIZE" -gt "$LIMIT" ]; then
        echo "ERROR: the ROM is bigger than the biggest commercial Mega Drive game (Super Street Fighter II, 5 MB)" >&2
        exit 1
    fi
fi
