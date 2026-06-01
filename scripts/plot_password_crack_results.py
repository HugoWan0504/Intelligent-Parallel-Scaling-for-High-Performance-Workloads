#!/usr/bin/env python3
import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, stdev

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# Match matmul colors exactly
LABEL_COLORS = {
    "static": "tab:blue",
    "dynamic_performance": "tab:green",
    "dynamic_efficiency": "tab:red",
}

def result_label(row):
    if row["mode"] == "dynamic":
        return f"dynamic_{row['goal']}"
    return row["mode"]

def read_summary(input_path):
    grouped = defaultdict(
        lambda: {
            "times": [],
            "threads": [],
            "selected_threads": Counter(),
        }
    )
    baseline_times = defaultdict(list)

    with input_path.open(newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            label = result_label(row)
            length = int(row["length"])
            threads = int(row["threads"])
            time_sec = float(row["time_sec"])

            key = (label, length, 0) if label.startswith("dynamic_") else (label, length, threads)

            grouped[key]["times"].append(time_sec)
            grouped[key]["threads"].append(threads)
            grouped[key]["selected_threads"][threads] += 1

            if threads == 1 and label in {"static", "sequential"}:
                baseline_times[length].append(time_sec)

    baseline_avg = {
        length: mean(times)
        for length, times in baseline_times.items()
        if times
    }

    summary = []
    for (label, length, threads), values in grouped.items():
        selected_threads = values["selected_threads"].most_common(1)[0][0]
        times = values["times"]
        threads_list = values["threads"]

        baseline = baseline_avg.get(length, mean(times))
        speedups = [baseline / t if t > 0 else 0.0 for t in times]
        efficiencies = [s / th if th > 0 else 0.0 for s, th in zip(speedups, threads_list)]

        summary.append({
            "label": label,
            "length": length,
            "threads": threads,
            "selected_threads": selected_threads,
            "is_dynamic": label.startswith("dynamic_"),

            "avg_time_sec": mean(times),
            "std_time_sec": stdev(times) if len(times) > 1 else 0.0,

            "avg_speedup": mean(speedups),
            "std_speedup": stdev(speedups) if len(speedups) > 1 else 0.0,

            "avg_efficiency": mean(efficiencies),
            "std_efficiency": stdev(efficiencies) if len(efficiencies) > 1 else 0.0,
        })

    return sorted(summary, key=lambda item: (item["length"], item["label"], item["threads"]))


def write_summary(summary, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as csv_file:
        fieldnames = [
            "label",
            "length",
            "threads",
            "selected_threads",
            "is_dynamic",
            "avg_time_sec",
            "std_time_sec",
            "avg_speedup",
            "std_speedup",
            "avg_efficiency",
            "std_efficiency",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary)


def plot_metric(rows, length, metric, std_metric, title, ylabel, output_path):
    from collections import defaultdict

    by_label = defaultdict(list)
    for row in rows:
        by_label[row["label"]].append(row)

    fig, ax = plt.subplots(figsize=(10.5, 6.2), dpi=150)

    fixed_threads = sorted({row["threads"] for row in rows if not row["is_dynamic"]})

    x_min, x_max = (fixed_threads[0], fixed_threads[-1]) if fixed_threads else (
        min(row["selected_threads"] for row in rows),
        max(row["selected_threads"] for row in rows),
    )

    for label in sorted(by_label):
        label_rows = sorted(by_label[label], key=lambda item: item["threads"])
        color = LABEL_COLORS.get(label, "tab:gray")

        if label_rows[0]["is_dynamic"]:
            # Plot dynamic as points
            for row in label_rows:
                ax.errorbar(
                    row["selected_threads"],
                    row[metric],
                    yerr=row[std_metric],
                    fmt="D",
                    markersize=6,
                    capsize=4,
                    color=color,
                    label=f"{label} ({row['selected_threads']}t)" if row == label_rows[0] else None,
                )
        else:
            x_values = [row["threads"] for row in label_rows]
            y_values = [row[metric] for row in label_rows]
            y_errors = [row[std_metric] for row in label_rows]

            ax.errorbar(
                x_values,
                y_values,
                yerr=y_errors,
                marker="o",
                linewidth=2.0,
                markersize=5,
                capsize=4,
                color=color,
                label=label,
            )

    ax.set_title(f"{title} for length={length}")
    ax.set_xlabel("Threads")
    ax.set_ylabel(ylabel)

    if fixed_threads:
        ax.set_xticks(fixed_threads)

    ax.grid(True, alpha=0.25)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)

    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Plot password-cracking benchmark results.")
    parser.add_argument("--input", default="results/password_crack.csv", help="Benchmark CSV")
    parser.add_argument("--summary", default="results/password_crack_summary.csv", help="Summary CSV")
    parser.add_argument("--out-dir", default="plots/password_crack", help="Output directory")
    parser.add_argument("--format", default="png", choices=["png", "svg", "pdf"], help="Plot format")
    args = parser.parse_args()

    input_path = Path(args.input)
    summary_path = Path(args.summary)
    out_dir = Path(args.out_dir)

    if not input_path.exists():
        raise SystemExit(f"Missing {input_path}. Run benchmark script first.")

    out_dir.mkdir(parents=True, exist_ok=True)

    summary = read_summary(input_path)
    write_summary(summary, summary_path)

    plots = [
        ("avg_time_sec", "std_time_sec", "Average Runtime", "Seconds"),
        ("avg_speedup", "std_speedup", "Average Speedup", "T_serial / T_parallel"),
        ("avg_efficiency", "std_efficiency", "Average Efficiency", "Speedup / threads"),
    ]

    lengths = sorted({row["length"] for row in summary})

    for length in lengths:
        rows_l = [row for row in summary if row["length"] == length]

        for metric, std_metric, title, ylabel in plots:
            prefix = metric.split("_")[1]
            output_path = out_dir / f"{prefix}_length{length}.{args.format}"

            plot_metric(rows_l, length, metric, std_metric, title, ylabel, output_path)
            print(f"Wrote {output_path}")

    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()