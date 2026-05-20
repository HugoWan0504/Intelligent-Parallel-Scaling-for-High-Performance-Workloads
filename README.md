# Intelligent Parallel Scaling for High-Performance Workloads

## Reproducing Build, Experiment, and Plot Results

This CS213 final project studies how thread count affects the performance of a shared-memory parallel workload. The main workload used in this project is dense matrix multiplication implemented in C++ with Pthreads.

The project compares several execution strategies:

1. Sequential baseline
2. Static Pthread execution
3. Dynamic thread scaling
4. Optimized Pthread execution with cache blocking

The goal is to evaluate whether dynamically adjusting the number of threads can improve performance compared to using a fixed thread count. The project measures runtime, correctness, speedup, and parallel efficiency.

---

## 1. Build the Project

First, compile the project from the repository root directory.

```bash
make clean
make
```

This creates the executable:

```bash
matmul.exe
```

On Linux or MSYS2-style terminals, the executable can be run as:

```bash
./matmul
```

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

The dynamic version uses 0 as the thread-count argument because the program chooses the thread count automatically based on the matrix size.

The program prints a table showing:

- execution mode
- matrix size
- number of threads used
- runtime in seconds
- correctness result

## 3. Run All Experiments

To run the full experiment script:

```bash
bash scripts/run_tests.sh
```

This script runs the sequential, static, dynamic, and optimized versions across multiple matrix sizes and thread counts.

The result file is generated at:

```bash
results/results.csv
```

The CSV file uses the following columns:

```bash
mode,N,threads,time_sec,correct
```

This step produces the raw timing data used for later analysis.

## 4. Generate Plots

After generating `results/results.csv`, run:

```bash
python3 scripts/plot_results.py
```

This creates the following plots:

```bash
plots/runtime_vs_threads.png
plots/speedup_vs_threads.png
plots/efficiency_vs_threads.png
```

These plots are used to compare:

- runtime as thread count changes
- speedup compared to the sequential baseline
- parallel efficiency across different configurations

## Current Implementation

### Sequential Baseline

The sequential version performs standard dense matrix multiplication using one thread. This version is used as the correctness reference and speedup baseline.

### Static Pthread Version

The static version uses a fixed number of Pthreads. Matrix rows are divided among threads before execution. This version is used to study how performance changes with different fixed thread counts.

### Dynamic Pthread Version

The dynamic version selects the number of threads automatically based on matrix size. This follows the project idea of adapting thread count to workload conditions instead of using one fixed configuration for all inputs.

Current thread-selection rule:

```bash
N <= 256   -> 1 thread
N <= 512   -> 2 threads
N <= 1024  -> 4 threads
N > 1024   -> 8 threads
```

This version tests the project proposal idea that thread count should adapt to workload size instead of staying fixed for all inputs.

### Optimized Pthread Version

The optimized version uses Pthreads with cache blocking. The goal is to improve data locality and reduce memory-access overhead compared to the basic static version.

## Next Focus

The next focus is improving the quality of the experimental evaluation before writing the final report.

### 1. Run each test multiple times

The current experiment results are based on single runs. Runtime can fluctuate because of background programs, scheduling, and system load.

Next step:

```bash
Run each configuration 3 to 5 times.
Report the average runtime.
Optionally also keep the best runtime.
```

This will make the results more reliable and easier to defend in the report.

### 2. Add larger matrix sizes

The current tests mainly use smaller and medium matrix sizes, such as:

```bash
256
512
1024
```

The next useful size is:

```bash
2048
```

This matters because small inputs may not benefit much from parallelism. For small matrices, thread creation and scheduling overhead can dominate. Larger matrices should better show whether static, dynamic, and optimized execution actually scale.

### 3. Improve the dynamic policy

The current dynamic version uses a simple rule based only on matrix size.

Current idea:

```bash
small N  -> fewer threads
large N  -> more threads
```

Next, compare the dynamic choice against the best static result for each matrix size.

Important question:

```bash
Did the dynamic version choose a thread count close to the best fixed-thread configuration?
```

### 4. Analyze the optimized version carefully

The optimized version uses cache blocking, but it may not always be faster for small inputs.

Things to check:

```bash
Does optimized beat static for larger N?
Does blocking overhead hurt small N?
Does the optimized version scale better as thread count increases?
```

This analysis is important because optimization results are not always perfect. The report should explain both improvements and limitations.

### 5. Prepare report-ready results

Before starting the final report, regenerate clean results and plots after the experiment changes.

Recommended command sequence:

```bash
make clean
make
bash scripts/run_tests.sh
python3 scripts/plot_results.py
git status
```

After that, the report can use:

```bash
results/results.csv
plots/runtime_vs_threads.png
plots/speedup_vs_threads.png
plots/efficiency_vs_threads.png
```

## Notes

- This project was tested using MSYS2 UCRT64 on Windows.
- The project uses Pthreads for shared-memory parallel programming.
- Runtime results may fluctuate between runs.
- The final report should focus on explaining the trade-off between thread count, overhead, speedup, and efficiency.

