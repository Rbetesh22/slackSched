#!/usr/bin/env bash
# Run every experiment grid, then rebuild the tables and plots.
# Each run takes ~5-15 s; the full set (~900 runs) takes a few hours with 2 workers.
# Grids skip runs already in their results file, so you can stop and resume.
set -euo pipefail
cd "$(dirname "$0")"
WORKERS="${WORKERS:-2}"

for g in main sigma stress long extra inflate slo kv2k sarathi; do
  python3 sweep.py "$g" "results/$g.jsonl" "$WORKERS"
done

python3 analyze.py
python3 extra_analysis.py
