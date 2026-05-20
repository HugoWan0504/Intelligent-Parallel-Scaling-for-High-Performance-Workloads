import csv
import os

import matplotlib.pyplot as plt

from plot_config import (
    SUMMARY_FILE,
    ADAPTIVE_POLICY_FILE,
    PLOTS_DIR,
    NEAR_BEST_TOLERANCE
)


def read_summary(filename):
    rows = []

    with open(filename, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append({
                "mode": row["mode"],
                "N": int(row["N"]),
                "threads": int(row["threads"]),
                "avg_time_sec": float(row["avg_time_sec"]),
                "best_time_sec": float(row["best_time_sec"]),
                "speedup_from_avg": float(row["speedup_from_avg"]),
                "efficiency_from_avg": float(row["efficiency_from_avg"]),
                "num_trials": int(row["num_trials"])
            })

    return rows


def get_dynamic_by_size(rows):
    dynamic = {}

    for row in rows:
        if row["mode"] == "dynamic":
            dynamic[row["N"]] = row

    return dynamic


def get_candidates_by_size(rows):
    """
    Candidate configurations for the adaptive policy.

    I exclude:
      - sequential: baseline, not a parallel policy candidate
      - dynamic: existing heuristic policy, used for comparison

    I include:
      - static
      - optimized
    """

    candidates = {}

    for row in rows:
        if row["mode"] not in ["static", "optimized"]:
            continue

        n = row["N"]

        if n not in candidates:
            candidates[n] = []

        candidates[n].append(row)

    return candidates


def choose_adaptive_policy(rows):
    """
    For each matrix size N:
      1. Find the fastest measured static/optimized configuration.
      2. Find all configurations within NEAR_BEST_TOLERANCE of the best runtime.
      3. Choose the lowest-thread near-best configuration.
      4. If there is a tie in thread count, choose the faster one.

    This detects the point before diminishing returns.
    """

    candidates_by_size = get_candidates_by_size(rows)
    dynamic_by_size = get_dynamic_by_size(rows)

    policy_rows = []

    for n in sorted(candidates_by_size.keys()):
        candidates = candidates_by_size[n]

        if not candidates:
            continue

        best = min(candidates, key=lambda row: row["avg_time_sec"])
        best_time = best["avg_time_sec"]

        threshold_time = best_time * (1.0 + NEAR_BEST_TOLERANCE)

        near_best = [
            row for row in candidates
            if row["avg_time_sec"] <= threshold_time
        ]

        selected = min(
            near_best,
            key=lambda row: (row["threads"], row["avg_time_sec"])
        )

        slowdown_percent = (
            (selected["avg_time_sec"] - best_time) / best_time
        ) * 100.0

        thread_savings = best["threads"] - selected["threads"]

        dynamic = dynamic_by_size.get(n, None)

        if dynamic is not None:
            dynamic_slowdown_percent = (
                (dynamic["avg_time_sec"] - best_time) / best_time
            ) * 100.0
        else:
            dynamic_slowdown_percent = 0.0

        policy_rows.append({
            "N": n,

            "best_mode": best["mode"],
            "best_threads": best["threads"],
            "best_avg_time": best["avg_time_sec"],

            "selected_mode": selected["mode"],
            "selected_threads": selected["threads"],
            "selected_avg_time": selected["avg_time_sec"],
            "selected_slowdown_percent": slowdown_percent,
            "thread_savings_vs_best": thread_savings,

            "dynamic_threads": dynamic["threads"] if dynamic else "",
            "dynamic_avg_time": dynamic["avg_time_sec"] if dynamic else "",
            "dynamic_slowdown_percent": dynamic_slowdown_percent if dynamic else "",

            "tolerance_percent": NEAR_BEST_TOLERANCE * 100.0,
            "reason": "lowest-thread configuration within near-best runtime threshold"
        })

    return policy_rows


def write_adaptive_policy(policy_rows):
    with open(ADAPTIVE_POLICY_FILE, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "N",

                "best_mode",
                "best_threads",
                "best_avg_time",

                "selected_mode",
                "selected_threads",
                "selected_avg_time",
                "selected_slowdown_percent",
                "thread_savings_vs_best",

                "dynamic_threads",
                "dynamic_avg_time",
                "dynamic_slowdown_percent",

                "tolerance_percent",
                "reason"
            ]
        )

        writer.writeheader()

        for row in policy_rows:
            writer.writerow({
                "N": row["N"],

                "best_mode": row["best_mode"],
                "best_threads": row["best_threads"],
                "best_avg_time": f"{row['best_avg_time']:.3f}",

                "selected_mode": row["selected_mode"],
                "selected_threads": row["selected_threads"],
                "selected_avg_time": f"{row['selected_avg_time']:.3f}",
                "selected_slowdown_percent": f"{row['selected_slowdown_percent']:.3f}",
                "thread_savings_vs_best": row["thread_savings_vs_best"],

                "dynamic_threads": row["dynamic_threads"],
                "dynamic_avg_time": (
                    f"{row['dynamic_avg_time']:.3f}"
                    if row["dynamic_avg_time"] != ""
                    else ""
                ),
                "dynamic_slowdown_percent": (
                    f"{row['dynamic_slowdown_percent']:.3f}"
                    if row["dynamic_slowdown_percent"] != ""
                    else ""
                ),

                "tolerance_percent": f"{row['tolerance_percent']:.1f}",
                "reason": row["reason"]
            })

    print(f"Generated: {ADAPTIVE_POLICY_FILE}")


def plot_adaptive_runtime(policy_rows):
    output_dir = os.path.join(PLOTS_DIR, "overall_average")
    os.makedirs(output_dir, exist_ok=True)

    sizes = [row["N"] for row in policy_rows]
    best_times = [row["best_avg_time"] for row in policy_rows]
    selected_times = [row["selected_avg_time"] for row in policy_rows]

    dynamic_times = []
    for row in policy_rows:
        if row["dynamic_avg_time"] == "":
            dynamic_times.append(None)
        else:
            dynamic_times.append(row["dynamic_avg_time"])

    plt.figure(figsize=(8, 5))

    plt.plot(sizes, best_times, marker="o", label="best measured")
    plt.plot(sizes, selected_times, marker="o", label="adaptive selected")

    if any(value is not None for value in dynamic_times):
        valid_sizes = []
        valid_dynamic_times = []

        for n, value in zip(sizes, dynamic_times):
            if value is not None:
                valid_sizes.append(n)
                valid_dynamic_times.append(value)

        plt.plot(valid_sizes, valid_dynamic_times, marker="o", label="current dynamic")

    plt.xlabel("Matrix Size N")
    plt.ylabel("Average Runtime (seconds)")
    plt.title("Adaptive Policy Runtime Comparison")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    output_file = os.path.join(output_dir, "adaptive_policy_runtime.png")
    plt.savefig(output_file)
    plt.close()

    print(f"Generated: {output_file}")


def plot_adaptive_threads(policy_rows):
    output_dir = os.path.join(PLOTS_DIR, "overall_average")
    os.makedirs(output_dir, exist_ok=True)

    sizes = [row["N"] for row in policy_rows]
    best_threads = [row["best_threads"] for row in policy_rows]
    selected_threads = [row["selected_threads"] for row in policy_rows]

    dynamic_threads = []
    for row in policy_rows:
        if row["dynamic_threads"] == "":
            dynamic_threads.append(None)
        else:
            dynamic_threads.append(row["dynamic_threads"])

    plt.figure(figsize=(8, 5))

    plt.plot(sizes, best_threads, marker="o", label="best measured threads")
    plt.plot(sizes, selected_threads, marker="o", label="adaptive selected threads")

    if any(value is not None for value in dynamic_threads):
        valid_sizes = []
        valid_dynamic_threads = []

        for n, value in zip(sizes, dynamic_threads):
            if value is not None:
                valid_sizes.append(n)
                valid_dynamic_threads.append(value)

        plt.plot(valid_sizes, valid_dynamic_threads, marker="o", label="current dynamic threads")

    plt.xlabel("Matrix Size N")
    plt.ylabel("Thread Count")
    plt.title("Adaptive Policy Thread Selection")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    output_file = os.path.join(output_dir, "adaptive_policy_threads.png")
    plt.savefig(output_file)
    plt.close()

    print(f"Generated: {output_file}")


def run_adaptive_policy_analysis():
    rows = read_summary(SUMMARY_FILE)
    policy_rows = choose_adaptive_policy(rows)

    write_adaptive_policy(policy_rows)
    plot_adaptive_runtime(policy_rows)
    plot_adaptive_threads(policy_rows)


def main():
    run_adaptive_policy_analysis()


if __name__ == "__main__":
    main()