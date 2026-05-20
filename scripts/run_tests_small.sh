#!/bin/bash

make

mkdir -p results

OUTPUT="results/results_small.csv"

echo "mode,N,threads,trial,time_sec,correct" > "$OUTPUT"

SIZES=(256 512 1024)
THREADS=(1 2 4 8)
TRIALS=3

for N in "${SIZES[@]}"; do
    for TRIAL in $(seq 1 $TRIALS); do
        echo "Running sequential N=$N trial=$TRIAL"
        ./matmul sequential "$N" 1 --csv | awk -v trial="$TRIAL" -F',' '{print $1","$2","$3","trial","$4","$5}' >> "$OUTPUT"
    done

    for T in "${THREADS[@]}"; do
        for TRIAL in $(seq 1 $TRIALS); do
            echo "Running static N=$N threads=$T trial=$TRIAL"
            ./matmul static "$N" "$T" --csv | awk -v trial="$TRIAL" -F',' '{print $1","$2","$3","trial","$4","$5}' >> "$OUTPUT"
        done
    done

    for TRIAL in $(seq 1 $TRIALS); do
        echo "Running dynamic N=$N trial=$TRIAL"
        ./matmul dynamic "$N" 0 --csv | awk -v trial="$TRIAL" -F',' '{print $1","$2","$3","trial","$4","$5}' >> "$OUTPUT"
    done

    for T in "${THREADS[@]}"; do
        for TRIAL in $(seq 1 $TRIALS); do
            echo "Running optimized N=$N threads=$T trial=$TRIAL"
            ./matmul optimized "$N" "$T" --csv | awk -v trial="$TRIAL" -F',' '{print $1","$2","$3","trial","$4","$5}' >> "$OUTPUT"
        done
    done
done

cp "$OUTPUT" results/results.csv

echo "Done. Small results saved to $OUTPUT"
echo "Also copied to results/results.csv for plotting"