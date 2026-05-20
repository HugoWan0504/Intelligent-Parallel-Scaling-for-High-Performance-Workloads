#!/bin/bash

SMALL="results/results_small.csv"
LARGE="results/results_large.csv"
OUTPUT="results/results.csv"

if [ ! -f "$SMALL" ]; then
    echo "Error: $SMALL does not exist."
    echo "Run: bash scripts/run_tests_small.sh"
    exit 1
fi

echo "mode,N,threads,trial,time_sec,correct" > "$OUTPUT"

tail -n +2 "$SMALL" >> "$OUTPUT"

if [ -f "$LARGE" ]; then
    tail -n +2 "$LARGE" >> "$OUTPUT"
else
    echo "Warning: $LARGE does not exist. Only small results were used."
fi

echo "Combined results saved to $OUTPUT"