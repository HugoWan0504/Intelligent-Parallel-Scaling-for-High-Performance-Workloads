#!/bin/bash

make

mkdir -p results

OUTPUT="results/results.csv"

echo "mode,N,threads,time_sec,correct" > "$OUTPUT"

SIZES=(256 512 1024)
THREADS=(1 2 4 8)

for N in "${SIZES[@]}"; do
    echo "Running sequential N=$N"
    ./matmul sequential "$N" 1 --csv >> "$OUTPUT"

    for T in "${THREADS[@]}"; do
        echo "Running static N=$N threads=$T"
        ./matmul static "$N" "$T" --csv >> "$OUTPUT"
    done

    echo "Running dynamic N=$N"
    ./matmul dynamic "$N" 0 --csv >> "$OUTPUT"

    for T in "${THREADS[@]}"; do
        echo "Running optimized N=$N threads=$T"
        ./matmul optimized "$N" "$T" --csv >> "$OUTPUT"
    done
done

echo "Done. Results saved to $OUTPUT"