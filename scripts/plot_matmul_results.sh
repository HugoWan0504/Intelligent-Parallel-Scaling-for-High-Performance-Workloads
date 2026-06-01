#!/usr/bin/env bash
set -euo pipefail

python3 scripts/plot_matmul_results.py \
    --input "${IN:-results/openmp_scaling.csv}" \
    --summary "${SUMMARY:-results/openmp_scaling_summary.csv}" \
    --out-dir "${OUT_DIR:-plots/openmp_scaling}" \
    --format "${FORMAT:-png}"
