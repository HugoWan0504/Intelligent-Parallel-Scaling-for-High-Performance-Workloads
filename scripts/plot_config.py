RESULTS_FILE = "results/results.csv"
SUMMARY_FILE = "results/summary_results.csv"
BEST_COMPARISON_FILE = "results/dynamic_vs_best_static.csv"
ADAPTIVE_POLICY_FILE = "results/adaptive_policy.csv"

PLOTS_DIR = "plots"

# Near-best threshold for adaptive policy.
# 0.10 means a configuration is considered near-best if it is within 10%
# of the fastest measured runtime.
NEAR_BEST_TOLERANCE = 0.10


METRIC_CONFIGS = [
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