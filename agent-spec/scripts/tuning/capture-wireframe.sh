#!/usr/bin/env bash
# capture-wireframe.sh — Screenshot a URL to a PNG file.
#
# Usage: scripts/tuning/capture-wireframe.sh <url> <output_path> [width] [height]
#
# Requires: npx playwright (installed on first run)
set -euo pipefail

URL="${1:?Usage: capture-wireframe.sh <url> <output_path> [width] [height]}"
OUTPUT="${2:?Usage: capture-wireframe.sh <url> <output_path> [width] [height]}"
WIDTH="${3:-1280}"
HEIGHT="${4:-800}"

mkdir -p "$(dirname "$OUTPUT")"

node -e "
const { chromium } = require('playwright');
(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: ${WIDTH}, height: ${HEIGHT} } });
  await page.goto('${URL}', { waitUntil: 'networkidle', timeout: 30000 });
  await page.screenshot({ path: '${OUTPUT}', fullPage: false });
  await browser.close();
  console.log('Saved: ${OUTPUT}');
})();
" 2>/dev/null || {
  # Fallback: try npx playwright screenshot CLI
  npx playwright screenshot --viewport-size="${WIDTH},${HEIGHT}" "$URL" "$OUTPUT" 2>/dev/null && echo "Saved: $OUTPUT" || {
    echo "ERROR: Could not capture screenshot. Install playwright: npm i -g playwright" >&2
    exit 1
  }
}
