import csv
from collections import defaultdict

from plot_config import SUMMARY_FILE, BEST_COMPARISON_FILE


def read_results(filename):
    rows = []

    with open(filename, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            correct_value = row["correct"].strip().lower()

            # Keep "true" and "skipped".
            # Only skip rows that actually failed correctness.
            if correct_value == "false":
                print(f"Warning: skipping incorrect row: {row}")
                continue

            rows.append({
                "mode": row["mode"],
                "N": int(row["N"]),
                "threads": int(row["threads"]),
                "trial": int(row["trial"]),
                "time_sec": float(row["time_sec"]),
                "correct": row["correct"]
            })

    return rows


def compute_summary(rows):
    grouped = defaultdict(list)

    for row in rows:
        key = (row["mode"], row["N"], row["threads"])
        grouped[key].append(row["time_sec"])

    summary = []

    for (mode, n, threads), times in grouped.items():
        avg_time = sum(times) / len(times)
        best_time = min(times)

        summary.append({
            "mode": mode,
            "N": n,
            "threads": threads,
            "avg_time_sec": avg_time,
            "best_time_sec": best_time,
            "num_trials": len(times)
        })

    summary.sort(key=lambda x: (x["N"], x["mode"], x["threads"]))
    return summary


def get_sequential_avg_times(summary):
    seq_times = {}

    for row in summary:
        if row["mode"] == "sequential":
            seq_times[row["N"]] = row["avg_time_sec"]

    return seq_times


def add_speedup_and_efficiency(summary):
    seq_times = get_sequential_avg_times(summary)

    for row in summary:
        n = row["N"]

        if n in seq_times:
            row["speedup_from_avg"] = seq_times[n] / row["avg_time_sec"]
            row["efficiency_from_avg"] = row["speedup_from_avg"] / row["threads"]
        else:
            row["speedup_from_avg"] = 0.0
            row["efficiency_from_avg"] = 0.0


def write_summary(summary):
    with open(SUMMARY_FILE, "w", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "mode",
                "N",
                "threads",
                "avg_time_sec",
                "best_time_sec",
                "speedup_from_avg",
                "efficiency_from_avg",
                "num_trials"
            ]
        )

        writer.writeheader()

        for row in summary:
            writer.writerow({
                "mode": row["mode"],
                "N": row["N"],
                "threads": row["threads"],
                "avg_time_sec": f"{row['avg_time_sec']:.3f}",
                "best_time_sec": f"{row['best_time_sec']:.3f}",
                "speedup_from_avg": f"{row['speedup_from_avg']:.3f}",
                "efficiency_from_avg": f"{row['efficiency_from_avg']:.3f}",
                "num_trials": row["num_trials"]
            })


def get_best_static_by_size(summary):
    best_static = {}

    for row in summary:
        if row["mode"] != "static":
            continue

        n = row["N"]

        if n not in best_static or row["avg_time_sec"] < best_static[n]["avg_time_sec"]:
            best_static[n] = row

    return best_static


def get_best_optimized_by_size(summary):
    best_optimized = {}

    for row in summary:
        if row["mode"] != "optimized":
            continue

        n = row["N"]

        if n not in best_optimized or row["avg_time_sec"] < best_optimized[n]["avg_time_sec"]:
            best_optimized[n] = row

    return best_optimized


def get_dynamic_by_size(summary):
    dynamic = {}

    for row in summary:
        if row["mode"] == "dynamic":
            dynamic[row["N"]] = row

    return dynamic


def get_sequential_by_size(summary):
    sequential = {}

    for row in summary:
        if row["mode"] == "sequential":
            sequential[row["N"]] = row

    return sequential


def write_best_comparison_table(summary):
    best_static = get_best_static_by_size(summary)
    dynamic = get_dynamic_by_size(summary)
    best_optimized = get_best_optimized_by_size(summary)

    sizes = sorted(set(row["N"] for row in summary))

    with open(BEST_COMPARISON_FILE, "w", newline="") as f:
        writer = csv.writer(f)

        writer.writerow([
            "N",
            "dynamic_threads",
            "dynamic_avg_time",
            "best_static_threads",
            "best_static_avg_time",
            "best_optimized_threads",
            "best_optimized_avg_time"
        ])

        for n in sizes:
            if n not in dynamic or n not in best_static or n not in best_optimized:
                continue

            writer.writerow([
                n,
                dynamic[n]["threads"],
                f"{dynamic[n]['avg_time_sec']:.3f}",
                best_static[n]["threads"],
                f"{best_static[n]['avg_time_sec']:.3f}",
                best_optimized[n]["threads"],
                f"{best_optimized[n]['avg_time_sec']:.3f}"
            ])

    print(f"Generated: {BEST_COMPARISON_FILE}")