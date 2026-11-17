#!/usr/bin/env bash
# Screenshot the Desktop pair pane (server/src/inbox.html) in each scenario of harness.html, with headless Chrome.
# Usage: server/tests/pane/shot.sh OUT_DIR [scenario ...]   (run from the repo root; needs Google Chrome)
set -euo pipefail
out=${1:?usage: shot.sh OUT_DIR [scenario ...]}
shift
scenarios=("${@:-idle update started request joining paired files}")
read -ra scenarios <<<"${scenarios[*]}"
chrome=${CHROME:-"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"}
mkdir -p "$out"
port=8765
python3 -m http.server -b 127.0.0.1 "$port" >/dev/null 2>&1 &
srv=$!
trap 'kill $srv' EXIT
sleep 1
for s in "${scenarios[@]}"; do
  # Headless Chrome lays out at least 500 px wide; the harness pins the pane to 400 px within that.
  "$chrome" --headless=new --disable-gpu --hide-scrollbars --force-dark-mode --window-size=500,760 \
    --virtual-time-budget=4000 --screenshot="$out/$s.png" \
    "http://127.0.0.1:$port/server/tests/pane/harness.html?s=$s" >/dev/null 2>&1
  echo "$out/$s.png"
done
