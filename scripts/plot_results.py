import os

from plot_config import RESULTS_FILE, PLOTS_DIR, METRIC_CONFIGS
from plot_data import (
    read_results,
    compute_summary,
    add_speedup_and_efficiency,
    write_summary,
    write_best_comparison_table
)
from plot_make import (
    make_dir,
    clean_plot_folders,
    plot_metric_by_threads_for_each_size,
    plot_metric_by_size_for_each_mode,
    plot_best_approach_comparison,
    plot_overall_average_comparison
)


def main():
    make_dir(PLOTS_DIR)

    rows = read_results(RESULTS_FILE)
    summary = compute_summary(rows)
    add_speedup_and_efficiency(summary)

    write_summary(summary)
    write_best_comparison_table(summary)

    clean_plot_folders(METRIC_CONFIGS)

    for config in METRIC_CONFIGS:
        metric = config["metric"]
        ylabel = config["ylabel"]
        title = config["title"]
        folder = config["folder"]

        metric_dir = os.path.join(PLOTS_DIR, folder)
        overall_dir = os.path.join(PLOTS_DIR, "overall_average")

        plot_metric_by_threads_for_each_size(
            summary,
            metric,
            ylabel,
            title,
            metric_dir
        )

        plot_metric_by_size_for_each_mode(
            summary,
            metric,
            ylabel,
            title,
            metric_dir
        )

        plot_best_approach_comparison(
            summary,
            metric,
            ylabel,
            f"{title}: Sequential vs Best Static vs Dynamic vs Best Optimized",
            os.path.join(metric_dir, f"{metric}_best_comparison.png")
        )

        plot_overall_average_comparison(
            summary,
            metric,
            ylabel,
            f"Overall Average {title}",
            os.path.join(overall_dir, f"{metric}_overall_average.png")
        )

    print("All plots generated.")
    print("Plot folders:")
    print("  plots/average_runtime/")
    print("  plots/best_runtime/")
    print("  plots/speedup_from_avg/")
    print("  plots/efficiency_from_avg/")
    print("  plots/overall_average/")


if __name__ == "__main__":
    main()