#!/bin/bash
set -e

# Default auto-tuning run. Adjust these lists if your machine has fewer/more cores.
python3 scripts/auto_tune_saturation.py \
    --sizes 256,512,1024 \
    --threads 1,2,4,8,16 \
    --blocks 8,16,32,64,128 \
    --trials 3 \
    --threshold 0.05