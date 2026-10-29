#!/usr/bin/env bash
# Clone Vidur at the commit these experiments used and install its Python deps.
set -euo pipefail
cd "$(dirname "$0")"

VIDUR_COMMIT=abae7f6
if [ ! -d vidur ]; then
  git clone https://github.com/microsoft/vidur.git vidur
fi
git -C vidur checkout -q "$VIDUR_COMMIT"

python3 -m pip install -r requirements.txt

echo
echo "Setup done. The first simulation trains Vidur's timing models (~20-25 min on 2 CPUs, once)."
echo "Warm it up with:  python3 slacksim.py '{\"strategy\": \"fcfs\", \"qps\": 2, \"n\": 50, \"seed\": 1}'"
