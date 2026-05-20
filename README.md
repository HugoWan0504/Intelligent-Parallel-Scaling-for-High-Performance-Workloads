# Intelligent Parallel Scaling for High-Performance Workloads

## Reproducing Build, Experiment, Plot, and Adaptive Policy Results

This CS213 final project studies how thread count affects the performance of a shared-memory parallel workload. The current workload is dense matrix multiplication implemented in C++ with Pthreads.

The original project goal is to compare fixed thread allocation with dynamic thread scaling and optimized parallel execution. The project evaluates how runtime, speedup, and efficiency change across different matrix sizes and thread counts.

The current project includes four main execution modes:

1. Sequential baseline
2. Static Pthread execution
3. Dynamic Pthread execution
4. Optimized Pthread execution with cache blocking

In addition, the project now includes an adaptive policy analysis step. This extra analysis uses measured performance results to choose a near-best configuration with fewer threads, helping detect the point before diminishing returns.

---

## 1. Build the Project

Compile the project from the repository root directory:

```bash
make clean
make
```

This creates the executable:

```bash
matmul.exe
```

Run the executable with:

```bash
./matmul
```

---

## 2. Run Individual Tests

The program format is:

```bash
./matmul <mode> <matrix_size> <thread_count>
```

Available modes:

```bash
sequential
static
dynamic
optimized
```

Example commands:

```bash
./matmul sequential 256 1
./matmul static 256 4
./matmul dynamic 256 0
./matmul optimized 256 4
```

The dynamic version uses 0 as the thread-count argument because the program chooses the thread count automatically.

The program output shows:

```bash
Mode
Matrix size
Thread count
Runtime
Correctness
```

For larger matrix sizes, correctness may be reported as skipped to avoid adding an expensive sequential verification run to every timing experiment.

---

## 3. Run Small Experiments

For quick testing, run only matrix sizes up to 1024:

```bash
bash scripts/run_tests_small.sh
```

This creates:

```bash
results/results_small.csv
```

The small experiment script also copies the result to:

```bash
results/results.csv
```

so that the plotting scripts can use it directly.

---

## 4. Run Large Experiments

For larger matrix sizes such as 1536 and 2048, run:

```bash
bash scripts/run_tests_large.sh
```

This creates:

```bash
results/results_large.csv
```

Large experiments take longer because matrix multiplication scales approximately with O(N^3) work.

---

## 5. Combine Small and Large Results

After running both small and large experiments, combine them with:

```bash
bash scripts/combine_results.sh
```

This creates the combined result file:

```bash
results/results.csv
```

The CSV columns are:

```bash
mode,N,threads,trial,time_sec,correct
```

Each configuration is run multiple times, so the trial column records which repeated run produced the timing result.

---

## 6. Generate Summary Files and Plots

After generating results/results.csv, run:

```bash
python3 scripts/plot_results.py
```

This creates summary CSV files:

```bash
results/summary_results.csv
results/dynamic_vs_best_static.csv
results/adaptive_policy.csv
```

It also creates plot folders:

```bash
plots/average_runtime/
plots/best_runtime/
plots/speedup_from_avg/
plots/efficiency_from_avg/
plots/overall_average/
```

The four main metric folders contain plots for:

```bash
average runtime
best runtime
speedup from average runtime
parallel efficiency from average runtime
```

The overall_average folder contains high-level comparison plots, including the adaptive policy results.

---

## 7. Adaptive Policy Analysis

The adaptive policy analysis is an additional feature beyond the original proposal.

The original dynamic version chooses thread count using a simple rule based on matrix size. The adaptive policy is different: it uses measured experiment results to choose a configuration based on observed performance.

For each matrix size, the adaptive policy:

1. Finds the fastest measured static or optimized configuration.
2. Finds all configurations within 10% of that fastest runtime.
3. Selects the lowest-thread configuration among those near-best candidates.

This helps identify the point before diminishing returns. Instead of always choosing the fastest configuration, the adaptive policy may choose a slightly slower configuration if it uses fewer threads and remains close to the best runtime.

To run adaptive policy analysis directly:

```bash
python3 scripts/analyze_policy.py
```

The normal plotting command also runs adaptive policy analysis automatically:

```bash
python3 scripts/plot_results.py
```

Adaptive policy outputs:

```bash
results/adaptive_policy.csv
plots/overall_average/adaptive_policy_runtime.png
plots/overall_average/adaptive_policy_threads.png
```

The adaptive policy CSV includes:

```bash
N
best_mode
best_threads
best_avg_time
selected_mode
selected_threads
selected_avg_time
selected_slowdown_percent
thread_savings_vs_best
dynamic_threads
dynamic_avg_time
dynamic_slowdown_percent
tolerance_percent
reason
```
---

## Current Implementation

### Sequential Baseline

The sequential version performs dense matrix multiplication using one thread. It is used as the correctness reference and speedup baseline.

### Static Pthread Version

The static version uses a fixed number of Pthreads. Matrix rows are divided across threads before execution. This version is used to measure how performance changes as thread count increases.

### Dynamic Pthread Version

The dynamic version automatically selects the number of threads based on matrix size. This represents the original proposal idea of adjusting thread count instead of using one fixed configuration for all workloads.

### Optimized Pthread Version

The optimized version uses Pthreads with cache blocking. The goal is to improve data locality and reduce memory-access overhead compared to the basic static implementation.

### Adaptive Policy Analysis

The adaptive policy analysis uses the measured static and optimized results to select a near-best configuration with fewer threads. This makes the project more useful because it studies both performance and resource usage.

---

## Workflow

For quick testing:

```bash
make clean
make
bash scripts/run_tests_small.sh
python3 scripts/plot_results.py
```

For full final results:

```bash
make clean
make
bash scripts/run_tests_small.sh
bash scripts/run_tests_large.sh
bash scripts/combine_results.sh
python3 scripts/plot_results.py
```

---

## Notes

- The project uses Pthreads for shared-memory parallel programming.
- Runtime results may fluctuate between runs due to scheduling, system load, and background processes.
- The experiment scripts run each configuration multiple times to support average and best runtime analysis.
- The final report should focus on thread scaling, runtime overhead, speedup, efficiency, and diminishing returns.

---

## Search-Based Auto-Tuning and Saturation Analysis

This extension adds a deeper tuning layer on top of the original static, dynamic, and optimized comparisons. Instead of only plotting manually selected thread counts, the new saturation workflow automatically tests candidate configurations and marks where runtime improvement begins to flatten.

The main script is:

```bash
python3 scripts/auto_tune_saturation.py
```

A simpler wrapper is also provided:

```bash
bash scripts/run_saturation.sh
```

The default wrapper tests:

```bash
sizes:       256, 512, 1024
threads:     1, 2, 4, 8, 16
block sizes: 8, 16, 32, 64, 128
trials:      3
threshold:   5% improvement
```

The saturation rule is based on the runtime improvement between two neighboring configurations:

```bash
improvement = (previous_time - current_time) / previous_time
```

If adding more threads improves runtime by less than the threshold, the curve is treated as saturated around the previous useful configuration. This lets the project report both the fastest configuration and the lower-cost configuration before diminishing returns.

---

## Supported Search Heuristics

| Heuristic                  | Purpose                                                                   |
| -------------------------- | ------------------------------------------------------------------------- |
| Linear thread sweep        | Tests all thread counts and acts as the reliable baseline.                |
| Binary saturation search   | Uses a binary-style heuristic to reduce the number of thread-count tests. |
| Hill-climbing block search | Tunes the optimized matrix multiplication block/tile size.                |
| -------------------------- | ------------------------------------------------------------------------- |

The generated outputs are:

```bash
results/saturation_results.csv
results/saturation_summary.csv
plots/saturation/thread_saturation_N*.png
plots/saturation/block_saturation_N*.png
plots/saturation/search_cost_comparison.png
```

Example custom run:

```bash
python3 scripts/auto_tune_saturation.py \
    --sizes 256,512,1024,2048 \
    --threads 1,2,4,8,16,32 \
    --blocks 8,16,32,64,128,256 \
    --trials 3 \
    --threshold 0.05
```

The optimized executable now also supports a configurable block size:

```bash
./matmul optimized 1024 8 --block-size 64 --csv
```

This makes the project less hardcoded and more like a practical auto-tuning benchmark. The final report can use this section to discuss runtime saturation, diminishing returns, search cost, and the trade-off between best runtime and resource-efficient thread selection.


After replacing/adding these files, run:

```bash
make clean
make
bash scripts/run_saturation.sh
```

The main new output folder should be:

```bash
plots/saturation/
```