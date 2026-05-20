import csv
import os
from collections import defaultdict

import matplotlib.pyplot as plt


RESULTS_FILE = "results/results.csv"
PLOTS_DIR = "plots"
SUMMARY_FILE = "results/summary_results.csv"


def read_results(filename):
    rows = []

    with open(filename, "r") as f:
        reader = csv.DictReader(f)

        for row in reader:
            correct_value = row["correct"].strip().lower()

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


def make_dir(path):
    os.makedirs(path, exist_ok=True)


def plot_metric_by_threads_for_each_size(summary, metric, ylabel, title_prefix, output_dir):
    """
    For each N:
        x-axis: thread count
        lines: static / optimized
        dynamic appears as one point because it chooses one thread count automatically.
    """

    make_dir(output_dir)

    sizes = sorted(set(row["N"] for row in summary))

    for n in sizes:
        plt.figure(figsize=(8, 5))

        for mode in ["static", "optimized", "dynamic"]:
            values = [
                row for row in summary
                if row["N"] == n and row["mode"] == mode
            ]

            if not values:
                continue

            values.sort(key=lambda x: x["threads"])

            threads = [row["threads"] for row in values]
            y_values = [row[metric] for row in values]

            plt.plot(threads, y_values, marker="o", label=mode)

        plt.xlabel("Thread Count")
        plt.ylabel(ylabel)
        plt.title(f"{title_prefix} by Thread Count, N={n}")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        output_file = os.path.join(output_dir, f"{metric}_by_threads_N{n}.png")
        plt.savefig(output_file)
        plt.close()


def plot_metric_by_size_for_each_mode(summary, metric, ylabel, title_prefix, output_dir):
    """
    For each mode:
        x-axis: matrix size
        lines: different thread counts.
    """

    make_dir(output_dir)

    modes = ["static", "optimized", "dynamic"]

    for mode in modes:
        plt.figure(figsize=(8, 5))

        values_for_mode = [
            row for row in summary
            if row["mode"] == mode
        ]

        if not values_for_mode:
            continue

        thread_counts = sorted(set(row["threads"] for row in values_for_mode))

        for threads in thread_counts:
            values = [
                row for row in values_for_mode
                if row["threads"] == threads
            ]

            values.sort(key=lambda x: x["N"])

            sizes = [row["N"] for row in values]
            y_values = [row[metric] for row in values]

            plt.plot(sizes, y_values, marker="o", label=f"{threads} thread(s)")

        plt.xlabel("Matrix Size N")
        plt.ylabel(ylabel)
        plt.title(f"{title_prefix} by Matrix Size, {mode}")
        plt.legend()
        plt.grid(True)
        plt.tight_layout()

        output_file = os.path.join(output_dir, f"{metric}_by_size_{mode}.png")
        plt.savefig(output_file)
        plt.close()


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


def plot_best_approach_comparison(summary, metric, ylabel, title, output_file):
    """
    Compare:
        sequential
        best static
        dynamic
        best optimized

    x-axis:
        matrix size
    """

    sizes = sorted(set(row["N"] for row in summary))

    comparison_groups = [
        ("sequential", get_sequential_by_size(summary)),
        ("best static", get_best_static_by_size(summary)),
        ("dynamic", get_dynamic_by_size(summary)),
        ("best optimized", get_best_optimized_by_size(summary))
    ]

    plt.figure(figsize=(8, 5))

    for label, group in comparison_groups:
        x_values = []
        y_values = []

        for n in sizes:
            if n in group:
                x_values.append(n)
                y_values.append(group[n][metric])

        if x_values:
            plt.plot(x_values, y_values, marker="o", label=label)

    plt.xlabel("Matrix Size N")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    plt.savefig(output_file)
    plt.close()


def write_best_comparison_table(summary):
    output_file = "results/dynamic_vs_best_static.csv"

    best_static = get_best_static_by_size(summary)
    dynamic = get_dynamic_by_size(summary)
    best_optimized = get_best_optimized_by_size(summary)

    sizes = sorted(set(row["N"] for row in summary))

    with open(output_file, "w", newline="") as f:
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

    print(f"Generated: {output_file}")


def plot_overall_average_comparison(summary, metric, ylabel, title, output_file):
    """
    Creates one extra plot comparing average metric value across approaches.

    For static and optimized:
        use the best configuration per matrix size first,
        then average across all matrix sizes.

    For dynamic:
        use the dynamic-selected configuration per matrix size,
        then average across all matrix sizes.
    """

    groups = {
        "sequential": get_sequential_by_size(summary),
        "best static": get_best_static_by_size(summary),
        "dynamic": get_dynamic_by_size(summary),
        "best optimized": get_best_optimized_by_size(summary)
    }

    labels = []
    averages = []

    for label, group in groups.items():
        values = [row[metric] for row in group.values()]

        if not values:
            continue

        labels.append(label)
        averages.append(sum(values) / len(values))

    plt.figure(figsize=(8, 5))
    plt.bar(labels, averages)

    plt.xlabel("Approach")
    plt.ylabel(ylabel)
    plt.title(title)
    plt.grid(True, axis="y")
    plt.tight_layout()

    plt.savefig(output_file)
    plt.close()


def main():
    make_dir(PLOTS_DIR)

    rows = read_results(RESULTS_FILE)
    summary = compute_summary(rows)
    add_speedup_and_efficiency(summary)
    write_summary(summary)

    print(f"Generated: {SUMMARY_FILE}")

    metric_configs = [
        {
            "metric": "avg_time_sec",
            "ylabel": "Average Runtime (seconds)",
            "title": "Average Runtime",
            "folder": "average_runtime"
        },
        {
            "metric": "best_time_sec",
            "ylabel": "Best Runtime (seconds)",
            "title": "Best Runtime",
            "folder": "best_runtime"
        },
        {
            "metric": "speedup_from_avg",
            "ylabel": "Speedup from Average Runtime",
            "title": "Speedup from Average Runtime",
            "folder": "speedup_from_avg"
        },
        {
            "metric": "efficiency_from_avg",
            "ylabel": "Parallel Efficiency from Average Runtime",
            "title": "Parallel Efficiency from Average Runtime",
            "folder": "efficiency_from_avg"
        }
    ]

    for config in metric_configs:
        metric = config["metric"]
        ylabel = config["ylabel"]
        title = config["title"]
        folder = config["folder"]

        by_threads_dir = os.path.join(PLOTS_DIR, folder, "by_threads")
        by_size_dir = os.path.join(PLOTS_DIR, folder, "by_size")
        comparison_dir = os.path.join(PLOTS_DIR, folder, "best_comparison")
        overall_dir = os.path.join(PLOTS_DIR, folder, "overall_average")

        make_dir(comparison_dir)
        make_dir(overall_dir)

        plot_metric_by_threads_for_each_size(
            summary,
            metric,
            ylabel,
            title,
            by_threads_dir
        )

        plot_metric_by_size_for_each_mode(
            summary,
            metric,
            ylabel,
            title,
            by_size_dir
        )

        plot_best_approach_comparison(
            summary,
            metric,
            ylabel,
            f"{title}: Sequential vs Best Static vs Dynamic vs Best Optimized",
            os.path.join(comparison_dir, f"{metric}_best_comparison.png")
        )

        plot_overall_average_comparison(
            summary,
            metric,
            ylabel,
            f"Overall Average {title}",
            os.path.join(overall_dir, f"{metric}_overall_average.png")
        )

    write_best_comparison_table(summary)

    print("All plots generated.")
    print("Main output folders:")
    print("  plots/average_runtime/")
    print("  plots/best_runtime/")
    print("  plots/speedup_from_avg/")
    print("  plots/efficiency_from_avg/")


if __name__ == "__main__":
    main()