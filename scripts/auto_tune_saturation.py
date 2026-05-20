#!/usr/bin/env python3
"""
Search-based auto-tuning and runtime saturation analysis.

This script extends the original project from manual benchmarking into an
experimental auto-tuning workflow. It supports:
  1. linear sweep over thread counts,
  2. binary-style saturation search over thread counts,
  3. hill-climbing search over optimized-mode block sizes.

Outputs:
  results/saturation_results.csv
  results/saturation_summary.csv
  plots/saturation/*.png
"""

import argparse
import csv
import os
import subprocess
from dataclasses import dataclass
from statistics import mean
from typing import Dict, List, Optional, Sequence, Tuple

import matplotlib.pyplot as plt


RESULTS_DIR = "results"
PLOTS_DIR = os.path.join("plots", "saturation")
RAW_FILE = os.path.join(RESULTS_DIR, "saturation_results.csv")
SUMMARY_FILE = os.path.join(RESULTS_DIR, "saturation_summary.csv")


@dataclass
class Measurement:
    mode: str
    search: str
    n: int
    threads: int
    block_size: int
    trial: int
    time_sec: float
    correct: str


@dataclass
class SummaryRow:
    mode: str
    search: str
    n: int
    threads: int
    block_size: int
    avg_time_sec: float
    best_time_sec: float
    num_trials: int


def parse_int_list(text: str) -> List[int]:
    values = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        value = int(item)
        if value <= 0:
            raise ValueError("all values must be positive")
        values.append(value)
    if not values:
        raise ValueError("list cannot be empty")
    return values


def run_command(command: Sequence[str]) -> Tuple[str, str]:
    completed = subprocess.run(
        command,
        text=True,
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "Command failed:\n"
            + " ".join(command)
            + "\nSTDOUT:\n"
            + completed.stdout
            + "\nSTDERR:\n"
            + completed.stderr
        )

    return completed.stdout.strip(), completed.stderr.strip()


def run_matmul(mode: str, n: int, threads: int, block_size: int, trial: int, search: str) -> Measurement:
    command = ["./matmul", mode, str(n), str(threads)]

    if mode == "optimized":
        command += ["--block-size", str(block_size)]

    command.append("--csv")

    stdout, _ = run_command(command)
    fields = stdout.split(",")

    if len(fields) != 5:
        raise RuntimeError(f"Unexpected matmul CSV output: {stdout}")

    out_mode, out_n, out_threads, out_time, correct = fields

    return Measurement(
        mode=out_mode,
        search=search,
        n=int(out_n),
        threads=int(out_threads),
        block_size=block_size if out_mode == "optimized" else 0,
        trial=trial,
        time_sec=float(out_time),
        correct=correct,
    )


def measure_config(mode: str, n: int, threads: int, block_size: int, trials: int, search: str) -> List[Measurement]:
    rows = []
    for trial in range(1, trials + 1):
        print(
            f"Running mode={mode} search={search} N={n} "
            f"threads={threads} block={block_size} trial={trial}"
        )
        rows.append(run_matmul(mode, n, threads, block_size, trial, search))
    return rows


def average_time(rows: Sequence[Measurement]) -> float:
    return mean(row.time_sec for row in rows)


def improvement(previous_time: float, current_time: float) -> float:
    if previous_time <= 0:
        return 0.0
    return (previous_time - current_time) / previous_time


def linear_thread_sweep(
    mode: str,
    n: int,
    threads: Sequence[int],
    trials: int,
    saturation_threshold: float,
) -> List[Measurement]:
    """
    Reliable baseline: test every thread count.
    The summary step later marks the saturation point from these data.
    """
    rows = []
    for t in threads:
        rows.extend(measure_config(mode, n, t, 32, trials, "linear_threads"))
    return rows


def binary_saturation_search(
    mode: str,
    n: int,
    threads: Sequence[int],
    trials: int,
    saturation_threshold: float,
) -> List[Measurement]:
    """
    Practical binary-style heuristic for thread saturation.

    It does not assume perfect monotonicity. It tests the midpoint, checks its
    neighbors, moves toward the better side, and keeps a small verification set.
    The goal is near-best saturation detection, not a mathematical proof of the
    global optimum.
    """
    candidates = sorted(set(threads))
    tested: Dict[int, List[Measurement]] = {}

    def test(index: int) -> float:
        index = max(0, min(index, len(candidates) - 1))
        t = candidates[index]
        if t not in tested:
            tested[t] = measure_config(mode, n, t, 32, trials, "binary_threads")
        return average_time(tested[t])

    lo = 0
    hi = len(candidates) - 1

    while lo <= hi:
        mid = (lo + hi) // 2
        mid_time = test(mid)
        left_time = test(mid - 1) if mid > 0 else None
        right_time = test(mid + 1) if mid < len(candidates) - 1 else None

        if right_time is not None:
            gain_right = improvement(mid_time, right_time)
            if gain_right < saturation_threshold:
                break

        if left_time is not None and left_time <= mid_time:
            hi = mid - 1
        elif right_time is not None and right_time < mid_time:
            lo = mid + 1
        else:
            break

    rows: List[Measurement] = []
    for t in sorted(tested.keys()):
        rows.extend(tested[t])
    return rows


def hillclimb_block_search(
    n: int,
    threads: int,
    block_sizes: Sequence[int],
    trials: int,
) -> List[Measurement]:
    """
    Local search for optimized tile/block size.

    Block size is not guaranteed to be monotonic, so hill climbing is a better
    heuristic than binary search here.
    """
    candidates = sorted(set(block_sizes))
    if not candidates:
        return []

    current = len(candidates) // 2
    tested: Dict[int, List[Measurement]] = {}

    def test(index: int) -> float:
        index = max(0, min(index, len(candidates) - 1))
        block = candidates[index]
        if block not in tested:
            tested[block] = measure_config("optimized", n, threads, block, trials, "hillclimb_block")
        return average_time(tested[block])

    while True:
        current_time = test(current)
        left_time = test(current - 1) if current > 0 else None
        right_time = test(current + 1) if current < len(candidates) - 1 else None

        move_left = left_time is not None and left_time < current_time
        move_right = right_time is not None and right_time < current_time

        if move_left and (not move_right or left_time <= right_time):
            current -= 1
        elif move_right:
            current += 1
        else:
            break

    rows: List[Measurement] = []
    for block in sorted(tested.keys()):
        rows.extend(tested[block])
    return rows


def write_raw(rows: Sequence[Measurement], filename: str) -> None:
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "mode",
                "search",
                "N",
                "threads",
                "block_size",
                "trial",
                "time_sec",
                "correct",
            ],
        )
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "mode": row.mode,
                "search": row.search,
                "N": row.n,
                "threads": row.threads,
                "block_size": row.block_size,
                "trial": row.trial,
                "time_sec": f"{row.time_sec:.6f}",
                "correct": row.correct,
            })
    print(f"Generated: {filename}")


def summarize(rows: Sequence[Measurement]) -> List[SummaryRow]:
    groups: Dict[Tuple[str, str, int, int, int], List[Measurement]] = {}
    for row in rows:
        key = (row.mode, row.search, row.n, row.threads, row.block_size)
        groups.setdefault(key, []).append(row)

    summary = []
    for (mode, search, n, threads, block_size), group in sorted(groups.items()):
        times = [row.time_sec for row in group]
        summary.append(SummaryRow(
            mode=mode,
            search=search,
            n=n,
            threads=threads,
            block_size=block_size,
            avg_time_sec=mean(times),
            best_time_sec=min(times),
            num_trials=len(group),
        ))
    return summary


def write_summary(summary: Sequence[SummaryRow], filename: str) -> None:
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    with open(filename, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "mode",
                "search",
                "N",
                "threads",
                "block_size",
                "avg_time_sec",
                "best_time_sec",
                "num_trials",
            ],
        )
        writer.writeheader()
        for row in summary:
            writer.writerow({
                "mode": row.mode,
                "search": row.search,
                "N": row.n,
                "threads": row.threads,
                "block_size": row.block_size,
                "avg_time_sec": f"{row.avg_time_sec:.6f}",
                "best_time_sec": f"{row.best_time_sec:.6f}",
                "num_trials": row.num_trials,
            })
    print(f"Generated: {filename}")


def find_saturation_point(points: Sequence[SummaryRow], threshold: float) -> Optional[SummaryRow]:
    ordered = sorted(points, key=lambda row: row.threads)
    if len(ordered) < 2:
        return ordered[0] if ordered else None

    previous = ordered[0]
    for current in ordered[1:]:
        gain = improvement(previous.avg_time_sec, current.avg_time_sec)
        if gain < threshold:
            return previous
        previous = current
    return ordered[-1]


def plot_thread_saturation(summary: Sequence[SummaryRow], threshold: float) -> None:
    os.makedirs(PLOTS_DIR, exist_ok=True)

    ns = sorted({row.n for row in summary})
    modes = ["static", "optimized"]

    for n in ns:
        plt.figure(figsize=(8, 5))
        for mode in modes:
            points = [
                row for row in summary
                if row.n == n and row.mode == mode and row.search == "linear_threads"
            ]
            if not points:
                continue

            points = sorted(points, key=lambda row: row.threads)
            xs = [row.threads for row in points]
            ys = [row.avg_time_sec for row in points]
            plt.plot(xs, ys, marker="o", label=f"{mode} linear sweep")

            sat = find_saturation_point(points, threshold)
            if sat is not None:
                plt.scatter([sat.threads], [sat.avg_time_sec], marker="x", s=100,
                            label=f"{mode} saturation ≈ {sat.threads} threads")

        plt.xlabel("Thread Count")
        plt.ylabel("Average Runtime (seconds)")
        plt.title(f"Runtime Saturation by Thread Count, N={n}")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        output_file = os.path.join(PLOTS_DIR, f"thread_saturation_N{n}.png")
        plt.savefig(output_file)
        plt.close()
        print(f"Generated: {output_file}")


def plot_block_saturation(summary: Sequence[SummaryRow]) -> None:
    os.makedirs(PLOTS_DIR, exist_ok=True)

    ns = sorted({row.n for row in summary})
    for n in ns:
        points = [
            row for row in summary
            if row.n == n and row.mode == "optimized" and row.search == "hillclimb_block"
        ]
        if not points:
            continue

        points = sorted(points, key=lambda row: row.block_size)
        xs = [row.block_size for row in points]
        ys = [row.avg_time_sec for row in points]

        best = min(points, key=lambda row: row.avg_time_sec)

        plt.figure(figsize=(8, 5))
        plt.plot(xs, ys, marker="o", label="optimized hill-climb samples")
        plt.scatter([best.block_size], [best.avg_time_sec], marker="x", s=100,
                    label=f"best sampled block = {best.block_size}")
        plt.xlabel("Block / Tile Size")
        plt.ylabel("Average Runtime (seconds)")
        plt.title(f"Optimized Runtime by Block Size, N={n}")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        output_file = os.path.join(PLOTS_DIR, f"block_saturation_N{n}.png")
        plt.savefig(output_file)
        plt.close()
        print(f"Generated: {output_file}")


def plot_search_cost(summary: Sequence[SummaryRow]) -> None:
    os.makedirs(PLOTS_DIR, exist_ok=True)

    groups: Dict[str, int] = {}
    for row in summary:
        groups[row.search] = groups.get(row.search, 0) + 1

    if not groups:
        return

    searches = sorted(groups.keys())
    counts = [groups[name] for name in searches]

    plt.figure(figsize=(8, 5))
    plt.bar(searches, counts)
    plt.xlabel("Search Heuristic")
    plt.ylabel("Unique Configurations Tested")
    plt.title("Search Cost Comparison")
    plt.xticks(rotation=20)
    plt.tight_layout()
    output_file = os.path.join(PLOTS_DIR, "search_cost_comparison.png")
    plt.savefig(output_file)
    plt.close()
    print(f"Generated: {output_file}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Auto-tune matmul and plot runtime saturation curves.")
    parser.add_argument("--sizes", default="256,512,1024", help="comma-separated matrix sizes")
    parser.add_argument("--threads", default="1,2,4,8,16", help="comma-separated thread counts")
    parser.add_argument("--blocks", default="8,16,32,64,128", help="comma-separated optimized block sizes")
    parser.add_argument("--trials", type=int, default=3, help="trials per configuration")
    parser.add_argument("--threshold", type=float, default=0.05, help="saturation threshold, e.g. 0.05 for 5%%")
    parser.add_argument("--skip-make", action="store_true", help="do not run make before benchmarking")
    args = parser.parse_args()

    sizes = parse_int_list(args.sizes)
    threads = parse_int_list(args.threads)
    blocks = parse_int_list(args.blocks)

    if args.trials <= 0:
        raise ValueError("trials must be positive")

    if not args.skip_make:
        run_command(["make"])

    all_rows: List[Measurement] = []

    for n in sizes:
        all_rows.extend(linear_thread_sweep("static", n, threads, args.trials, args.threshold))
        all_rows.extend(linear_thread_sweep("optimized", n, threads, args.trials, args.threshold))

        # Binary search is demonstrated on the static policy because thread scaling
        # is the cleanest place to detect diminishing returns.
        all_rows.extend(binary_saturation_search("static", n, threads, args.trials, args.threshold))

        # Use the current best linear optimized thread count as the hill-climb thread setting.
        optimized_rows = [
            row for row in all_rows
            if row.mode == "optimized" and row.search == "linear_threads" and row.n == n
        ]
        optimized_summary = summarize(optimized_rows)
        best_thread_row = min(optimized_summary, key=lambda row: row.avg_time_sec)
        all_rows.extend(hillclimb_block_search(n, best_thread_row.threads, blocks, args.trials))

    write_raw(all_rows, RAW_FILE)
    summary = summarize(all_rows)
    write_summary(summary, SUMMARY_FILE)

    plot_thread_saturation(summary, args.threshold)
    plot_block_saturation(summary)
    plot_search_cost(summary)

    print("Done. Saturation outputs:")
    print(f"  {RAW_FILE}")
    print(f"  {SUMMARY_FILE}")
    print(f"  {PLOTS_DIR}/")


if __name__ == "__main__":
    main()