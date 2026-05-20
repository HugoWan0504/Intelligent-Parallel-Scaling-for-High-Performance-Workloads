import csv
import os
from collections import defaultdict

import matplotlib.pyplot as plt


RESULTS_FILE = "results/results.csv"
PLOTS_DIR = "plots"


def read_results(filename):
    rows = []

    with open(filename, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            rows.append({
                "mode": row["mode"],
                "N": int(row["N"]),
                "threads": int(row["threads"]),
                "time_sec": float(row["time_sec"]),
                "correct": row["correct"]
            })

    return rows


def get_sequential_times(rows):
    seq_times = {}

    for row in rows:
        if row["mode"] == "sequential":
            seq_times[row["N"]] = row["time_sec"]

    return seq_times


def plot_runtime_vs_threads(rows):
    grouped = defaultdict(list)

    for row in rows:
        if row["mode"] != "sequential":
            key = (row["mode"], row["N"])
            grouped[key].append(row)

    for (mode, n), values in grouped.items():
        values.sort(key=lambda x: x["threads"])

        threads = [row["threads"] for row in values]
        times = [row["time_sec"] for row in values]

        plt.plot(threads, times, marker="o", label=f"{mode}, N={n}")

    plt.xlabel("Thread Count")
    plt.ylabel("Runtime (seconds)")
    plt.title("Runtime vs Thread Count")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    output = os.path.join(PLOTS_DIR, "runtime_vs_threads.png")
    plt.savefig(output)
    plt.close()


def plot_speedup_vs_threads(rows):
    seq_times = get_sequential_times(rows)
    grouped = defaultdict(list)

    for row in rows:
        if row["mode"] != "sequential":
            key = (row["mode"], row["N"])
            grouped[key].append(row)

    for (mode, n), values in grouped.items():
        values.sort(key=lambda x: x["threads"])

        threads = []
        speedups = []

        for row in values:
            if n in seq_times:
                threads.append(row["threads"])
                speedups.append(seq_times[n] / row["time_sec"])

        plt.plot(threads, speedups, marker="o", label=f"{mode}, N={n}")

    plt.xlabel("Thread Count")
    plt.ylabel("Speedup")
    plt.title("Speedup vs Thread Count")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    output = os.path.join(PLOTS_DIR, "speedup_vs_threads.png")
    plt.savefig(output)
    plt.close()


def plot_efficiency_vs_threads(rows):
    seq_times = get_sequential_times(rows)
    grouped = defaultdict(list)

    for row in rows:
        if row["mode"] != "sequential":
            key = (row["mode"], row["N"])
            grouped[key].append(row)

    for (mode, n), values in grouped.items():
        values.sort(key=lambda x: x["threads"])

        threads = []
        efficiencies = []

        for row in values:
            if n in seq_times:
                speedup = seq_times[n] / row["time_sec"]
                efficiency = speedup / row["threads"]

                threads.append(row["threads"])
                efficiencies.append(efficiency)

        plt.plot(threads, efficiencies, marker="o", label=f"{mode}, N={n}")

    plt.xlabel("Thread Count")
    plt.ylabel("Parallel Efficiency")
    plt.title("Parallel Efficiency vs Thread Count")
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    output = os.path.join(PLOTS_DIR, "efficiency_vs_threads.png")
    plt.savefig(output)
    plt.close()


def main():
    os.makedirs(PLOTS_DIR, exist_ok=True)

    rows = read_results(RESULTS_FILE)

    plot_runtime_vs_threads(rows)
    plot_speedup_vs_threads(rows)
    plot_efficiency_vs_threads(rows)

    print("Plots generated:")
    print("  plots/runtime_vs_threads.png")
    print("  plots/speedup_vs_threads.png")
    print("  plots/efficiency_vs_threads.png")


if __name__ == "__main__":
    main()