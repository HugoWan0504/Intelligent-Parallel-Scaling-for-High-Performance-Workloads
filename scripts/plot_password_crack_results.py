#!/usr/bin/env python3
import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, stdev

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError as error:
    raise SystemExit(
        "Missing dependency: matplotlib is required to generate plots. "
        "Install it with `python3 -m pip install matplotlib` or `python3 -m pip install -r requirements.txt`."
    ) from error

LABEL_COLORS = {
    "sequential": "black",
    "static": "tab:blue",
    "optimized": "tab:orange",
    "dynamic": "tab:green",
}


def read_summary(input_path):
    grouped = defaultdict(lambda: {"times": [], "speedups": [], "efficiencies": []})
    baseline_times = defaultdict(list)

    with input_path.open(newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            label = row["mode"]
            length = int(row["length"])
            threads = int(row["threads"])
            time_sec = float(row["time_sec"])

            key = (label, length, threads)
            grouped[key]["times"].append(time_sec)

            if label == "sequential":
                baseline_times[length].append(time_sec)

    baseline_avg = {length: mean(times) for length, times in baseline_times.items()}
    summary = []

    for (label, length, threads), values in grouped.items():
        avg_time = mean(values["times"])
        std_time = stdev(values["times"]) if len(values["times"]) > 1 else 0.0
        baseline = baseline_avg.get(length, avg_time)

        speedup = baseline / avg_time if avg_time > 0 else 0.0
        efficiency = speedup / threads if threads > 0 else 0.0

        summary.append({
            "label": label,
            "length": length,
            "threads": threads,
            "avg_time_sec": avg_time,
            "std_time_sec": std_time,
            "avg_speedup": speedup,
            "std_speedup": 0.0,
            "avg_efficiency": efficiency,
            "std_efficiency": 0.0,
        })

    return sorted(summary, key=lambda item: (item["length"], item["label"], item["threads"]))


def write_summary(summary, output_path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "label",
        "length",
        "threads",
        "avg_time_sec",
        "std_time_sec",
        "avg_speedup",
        "std_speedup",
        "avg_efficiency",
        "std_efficiency",
    ]
    with output_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(summary)


def plot_metric(rows, length, metric, std_metric, title, ylabel, output_path):
    from collections import defaultdict

    by_label = defaultdict(list)
    for row in rows:
        by_label[row["label"]].append(row)

    fig, ax = plt.subplots(figsize=(10.5, 6.2), dpi=150)
    fixed_threads = sorted({row["threads"] for row in rows if row["label"] != "dynamic"})

    for label in sorted(by_label):
        label_rows = sorted(by_label[label], key=lambda item: item["threads"])
        # labels are like 'password_static' or 'password_dynamic' — map to base label for colors
        base = label.split("_", 1)[1] if "_" in label else label
        color = LABEL_COLORS.get(base, "tab:gray")

        x_values = [row["threads"] for row in label_rows]
        y_values = [row[metric] for row in label_rows]
        y_errors = [row[std_metric] for row in label_rows]

        if label == "dynamic":
            for row in label_rows:
                ax.errorbar(
                    row["threads"],
                    row[metric],
                    yerr=row[std_metric],
                    fmt="D",
                    markersize=6,
                    capsize=4,
                    color=color,
                    label=label if row == label_rows[0] else None,
                )
        else:
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
        ax.set_xticks(sorted(set(fixed_threads + [row["threads"] for row in rows])))
    ax.grid(True, alpha=0.25)
    ax.legend(loc="center left", bbox_to_anchor=(1.02, 0.5), frameon=False)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


def main():
    parser = argparse.ArgumentParser(description="Plot password-cracking benchmark results.")
    parser.add_argument("--input", default="results/password_crack.csv", help="Input benchmark CSV")
    parser.add_argument("--summary", default="results/password_crack_summary.csv", help="Summary CSV output")
    parser.add_argument("--out-dir", default="plots/password_crack", help="Directory for generated plots")
    parser.add_argument("--format", default="png", choices=["png", "svg", "pdf"], help="Plot file format")
    args = parser.parse_args()

    input_path = Path(args.input)
    summary_path = Path(args.summary)
    out_dir = Path(args.out_dir)

    if not input_path.exists():
        raise SystemExit(f"Missing {input_path}. Run the password benchmark script first.")

    out_dir.mkdir(parents=True, exist_ok=True)
    summary = read_summary(input_path)
    write_summary(summary, summary_path)

    plots = [
        ("avg_time_sec", "std_time_sec", "Average Runtime", "Seconds"),
        ("avg_speedup", "std_speedup", "Average Speedup", "T_sequential / T_parallel"),
        ("avg_efficiency", "std_efficiency", "Average Efficiency", "Speedup / threads"),
    ]

    lengths = sorted({row["length"] for row in summary})
    for length in lengths:
        rows_for_length = [row for row in summary if row["length"] == length]
        for metric, std_metric, title, ylabel in plots:
            prefix = metric.split("_")[1]
            output_path = out_dir / f"{prefix}_length{length}.{args.format}"
            plot_metric(rows_for_length, length, metric, std_metric, title, ylabel, output_path)
            print(f"Wrote {output_path}")

    print(f"Wrote {summary_path}")


if __name__ == "__main__":
    main()
