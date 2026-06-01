# Intelligent Parallel Scaling for High-Performance Workloads

This project studies automatic thread-count selection for dense matrix multiplication. The kernels now use OpenMP so the fixed-thread and tuned-thread implementations are compared with the same parallel runtime.

## Layout

- `include/` — public header files for the generic tuner and matrix utility interfaces.
- `src/` — implementation files and the program entry point.
- `scripts/` — benchmark and plotting helpers.
- `results/` — benchmark CSV outputs.
- `plots/` — generated plot files.

## Build

```bash
make clean
make
```

This creates:

```bash
./autotuner
```

## Execution Modes

```bash
./autotuner <mode> <size> <thread_count> [--csv] [options]
```

Modes:

- `sequential`: serial baseline.
- `static`: OpenMP matrix multiplication with a fixed number of threads.
- `dynamic`: OpenMP multiplication that first benchmarks candidate thread counts on a sample matrix, then runs the full problem with the selected thread count.

The original pthread implementations are preserved in `src/pthread_legacy.cpp` for reference. They are not part of the default build because the main comparison now uses OpenMP throughout.

Useful options:

```bash
--tune-goal performance|efficiency
--tune-sample-size N
--tune-trials N
--max-threads N
--efficiency-tolerance F
```

Examples:

```bash
./autotuner static 512 4
./autotuner dynamic 512 0 --tune-goal performance
./autotuner dynamic 512 0 --tune-goal efficiency --efficiency-tolerance 0.25
./autotuner dynamic 5 0 --workload password --charset abcdef --password-target abcde
```

For `dynamic`, the positional thread count may be `0`. Use `--max-threads` to cap the tuner search space, or pass a positive positional thread count as the cap.

## Dynamic Tuning Policy

The dynamic mode runs a short tuning phase before the real multiplication:

1. Build a sample matrix with size `min(matrix_size, --tune-sample-size)`.
2. Time OpenMP multiplication for candidate thread counts from `1` to `--max-threads`.
3. Compute speedup and efficiency for each candidate:

```text
Speedup:    S = T_serial / T_parallel
Efficiency: E = S / P
```

4. Select a thread count:

- `performance`: choose the candidate with the lowest sample runtime.
- `efficiency`: find candidates within `--efficiency-tolerance` of the fastest sample runtime, then choose the one with the best efficiency. This avoids selecting one thread simply because it is usually the most efficient but too slow.

The reported runtime for dynamic mode measures the final multiplication after tuning. This keeps runtime, speedup, and efficiency comparable with the fixed static and optimized runs. The tuning phase is still used to select the thread count, but it is treated as setup cost rather than as part of the kernel runtime.

## Benchmarks and Plots

Run the default benchmark:

```bash
scripts/run_openmp_benchmarks.sh
```

Run the password search workload benchmark:

```bash
scripts/run_password_crack.sh
```

Plot the password cracking results:

```bash
scripts/plot_password_crack_results.sh
```

This writes:

```bash
results/openmp_scaling.csv
```

Install the plotting dependency if needed:

```bash
python3 -m pip install -r requirements.txt
```

Generate matplotlib plots:

```bash
scripts/plot_openmp_results.sh
```

Outputs:

```bash
results/openmp_scaling_summary.csv
plots/openmp_scaling/runtime_N128.png
plots/openmp_scaling/speedup_N128.png
plots/openmp_scaling/efficiency_N128.png
```

The shell wrapper calls `scripts/plot_openmp_results.py`. To choose another output format:

```bash
FORMAT=svg scripts/plot_openmp_results.sh
```

You can adjust the benchmark without editing the script:

```bash
SIZES="128 256 512 1024" THREADS="1 2 4 8 16" TRIALS=5 scripts/run_openmp_benchmarks.sh
```

The CSV columns are:

```text
mode,N,threads,trial,time_sec,correct,goal,speedup,efficiency
```

The summary CSV groups fixed modes by `label,N,threads` and dynamic modes by `label,N`. Each plot shows one matrix size with thread count on the x-axis. Static and optimized runs form curves across the tested thread counts. Tuned runs are labeled `dynamic_performance` and `dynamic_efficiency` and are drawn as horizontal reference bars across the chart, with the selected thread count shown in the legend.

Note that `dynamic_efficiency` optimizes the tuning sample, while the plotted dynamic runtime includes both tuning and the final multiplication. It may not always have the highest end-to-end efficiency if the sample is noisy, too small, or not representative of the full matrix size.
