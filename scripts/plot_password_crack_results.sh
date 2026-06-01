#!/usr/bin/env bash
set -euo pipefail

python3 scripts/plot_password_crack_results.py \
    --input "${IN:-results/password_crack.csv}" \
    --summary "${SUMMARY:-results/password_crack_summary.csv}" \
    --out-dir "${OUT_DIR:-plots/password_crack}" \
    --format "${FORMAT:-png}"
