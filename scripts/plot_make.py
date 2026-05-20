import os

import matplotlib.pyplot as plt

from plot_config import PLOTS_DIR
from plot_data import (
    get_best_static_by_size,
    get_best_optimized_by_size,
    get_dynamic_by_size,
    get_sequential_by_size
)


def make_dir(path):
    os.makedirs(path, exist_ok=True)


def plot_metric_by_threads_for_each_size(summary, metric, ylabel, title_prefix, output_dir):
    """
    For each N:
      x-axis = thread count
      lines = static / optimized / dynamic
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

        output_file = os.path.join(output_dir, f"{metric}_threads_N{n}.png")
        plt.savefig(output_file)
        plt.close()


def plot_metric_by_size_for_each_mode(summary, metric, ylabel, title_prefix, output_dir):
    """
    For each mode:
      x-axis = matrix size
      lines = different thread counts
    """

    make_dir(output_dir)

    for mode in ["static", "optimized", "dynamic"]:
        values_for_mode = [
            row for row in summary
            if row["mode"] == mode
        ]

        if not values_for_mode:
            continue

        plt.figure(figsize=(8, 5))

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

        output_file = os.path.join(output_dir, f"{metric}_size_{mode}.png")
        plt.savefig(output_file)
        plt.close()


def plot_best_approach_comparison(summary, metric, ylabel, title, output_file):
    """
    Compare:
      sequential
      best static
      dynamic
      best optimized
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


def plot_overall_average_comparison(summary, metric, ylabel, title, output_file):
    """
    One bar plot per metric.
    Uses:
      sequential
      best static
      dynamic
      best optimized
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


def clean_plot_folders(metric_configs):
    """
    Optional cleanup:
    removes old PNG files from the new plot folders only.
    """

    make_dir(PLOTS_DIR)

    folders = [config["folder"] for config in metric_configs]
    folders.append("overall_average")

    for folder in folders:
        folder_path = os.path.join(PLOTS_DIR, folder)
        make_dir(folder_path)

        for filename in os.listdir(folder_path):
            if filename.endswith(".png"):
                os.remove(os.path.join(folder_path, filename))