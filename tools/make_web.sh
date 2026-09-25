#!/bin/bash
# Assembles site/ for the browser version (GitHub Pages, or an HTML5 upload to itch.io): web/index.html,
# the current ROM (out/rom.bin) as nautiloid.bin, and the EmulatorJS player with the Genesis Plus GX
# core (downloaded once into site/data/), plus site/nautiloid-web.zip with index.html at the root.
# The same approach as the Wanderburg project's tools/make_itch.sh.
# Build the ROM first (./build.sh). Test locally: (cd site && python3 -m http.server 8000), then open
# http://localhost:8000/?autostart
set -euo pipefail
cd "$(dirname "$0")/.."

[ -f out/rom.bin ] || { echo "build first: ./build.sh" >&2; exit 1; }
mkdir -p site
cp web/index.html web/LICENSES.txt site/
cp out/rom.bin site/nautiloid.bin

BASE=https://cdn.emulatorjs.org/stable/data
FILES=(loader.js emulator.min.js emulator.min.css
       cores/genesis_plus_gx-wasm.data cores/genesis_plus_gx-legacy-wasm.data cores/reports/genesis_plus_gx.json
       compression/extract7z.js)
for f in "${FILES[@]}"; do
    if [ ! -s "site/data/$f" ]; then
        mkdir -p "site/data/$(dirname "$f")"
        curl -fsSL -o "site/data/$f" "$BASE/$f"
        echo "downloaded $f"
    fi
done

rm -f site/nautiloid-web.zip
(cd site && zip -qr -X nautiloid-web.zip index.html nautiloid.bin LICENSES.txt data)
ls -la site/nautiloid-web.zip
