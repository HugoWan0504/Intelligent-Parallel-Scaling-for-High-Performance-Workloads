#!/usr/bin/env python3
import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def result_label(row):
    mode = row["mode"]

    if mode == "sequential":
        return "sequential"
    if mode == "static":
        return "static"
    if mode == "optimized":
        return "optimized"
    if mode == "dynamic":
        return f"dynamic_{row['goal']}"

    return mode


def read_summary(input_path):
    grouped = defaultdict(
        lambda: {
            "count": 0,
            "time": 0.0,
            "speedup": 0.0,
            "efficiency": 0.0,
            "selected_threads": Counter(),
        }
    )

    with input_path.open(newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            label = result_label(row)
            n = int(row["N"])
            threads = int(row["threads"])

            if row["mode"] == "dynamic":
                key = (label, n, 0)
            else:
                key = (label, n, threads)

            grouped[key]["count"] += 1
            grouped[key]["time"] += float(row["time_sec"])
            grouped[key]["speedup"] += float(row["speedup"])
            grouped[key]["efficiency"] += float(row["efficiency"])
            grouped[key]["selected_threads"][threads] += 1

    summary = []
    for (label, n, threads), values in grouped.items():
        count = values["count"]
        selected_threads = values["selected_threads"].most_common(1)[0][0]

        summary.append(
            {
                "label": label,
                "N": n,
                "threads": threads,
                "selected_threads": selected_threads,
                "is_dynamic": label.startswith("dynamic_"),
                "avg_time_sec": values["time"] / count,
                "avg_speedup": values["speedup"] / count,
                "avg_efficiency": values["efficiency"] / count,
            }
        )

    return sorted(summary, key=lambda item: (item["N"], item["label"], item["threads"]))


def write_summary(summary, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with output_path.open("w", newline="") as csv_file:
        fieldnames = [
            "label",
            "N",
            "threads",
            "selected_threads",
            "is_dynamic",
            "avg_time_sec",
            "avg_speedup",
            "avg_efficiency",
        ]
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary)


def plot_metric(rows, n, metric, title, ylabel, output_path):
    by_label = defaultdict(list)
    for row in rows:
        by_label[row["label"]].append(row)

    fig, ax = plt.subplots(figsize=(10.5, 6.2), dpi=150)
    fixed_threads = sorted({row["threads"] for row in rows if not row["is_dynamic"]})

    if fixed_threads:
        x_min = fixed_threads[0]
        x_max = fixed_threads[-1]
    else:
        selected = sorted({row["selected_threads"] for row in rows})
        x_min = selected[0]
        x_max = selected[-1]

    for label in sorted(by_label):
        label_rows = sorted(by_label[label], key=lambda item: item["threads"])
        if label_rows[0]["is_dynamic"]:
            row = label_rows[0]
            ax.hlines(
                row[metric],
                x_min,
                x_max,
                linewidth=2.4,
                linestyles="--",
                label=f"{label} (selected {row['selected_threads']}t)",
            )
        else:
            x_values = [row["threads"] for row in label_rows]
            y_values = [row[metric] for row in label_rows]
            ax.plot(x_values, y_values, marker="o", linewidth=2.0, markersize=4.5, label=label)

    ax.set_title(f"{title} for N={n}")
    ax.set_xlabel("Threads")
    ax.set_ylabel(ylabel)
    ax.set_xticks(fixed_threads)
    ax.grid(True, alpha=0.25)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Plot OpenMP scaling benchmark results with matplotlib.")
    parser.add_argument("--input", default="results/openmp_scaling.csv", help="Benchmark CSV produced by run_openmp_benchmarks.sh")
    parser.add_argument("--summary", default="results/openmp_scaling_summary.csv", help="Aggregated summary CSV")
    parser.add_argument("--out-dir", default="plots/openmp_scaling", help="Directory for generated plots")
    parser.add_argument("--format", default="png", choices=["png", "svg", "pdf"], help="Plot file format")
    args = parser.parse_args()

    input_path = Path(args.input)
    summary_path = Path(args.summary)
    out_dir = Path(args.out_dir)

    if not input_path.exists():
        raise SystemExit(f"Missing {input_path}. Run scripts/run_openmp_benchmarks.sh first.")

    out_dir.mkdir(parents=True, exist_ok=True)
    summary = read_summary(input_path)
    write_summary(summary, summary_path)

    plots = [
        ("avg_time_sec", "Average Runtime", "Seconds", "runtime"),
        ("avg_speedup", "Average Speedup", "T_serial / T_parallel", "speedup"),
        ("avg_efficiency", "Average Efficiency", "Speedup / threads", "efficiency"),
    ]

    sizes = sorted({row["N"] for row in summary})
    for n in sizes:
        rows = [row for row in summary if row["N"] == n]
        for metric, title, ylabel, prefix in plots:
            output_path = out_dir / f"{prefix}_N{n}.{args.format}"
            plot_metric(rows, n, metric, title, ylabel, output_path)
            print(f"Wrote {output_path}")

    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
