#include "dynamic_tuner.h"

#include <algorithm>
#include <limits>
#include <thread>
#include <vector>
#include <iostream>

namespace {

static int effective_max_threads(int max_threads_hint, const DynamicTuningConfig& config) {
    int max_threads = config.max_threads > 0 ? config.max_threads : static_cast<int>(std::thread::hardware_concurrency());
    if (max_threads <= 0) {
        max_threads = 1;
    }

    if (max_threads_hint > 0) {
        return std::max(1, std::min(max_threads, max_threads_hint));
    }

    return max_threads;
}

static std::vector<int> candidate_thread_counts(int max_threads) {
    std::vector<int> candidates;

    int threads = 1;
    while (threads <= max_threads) {
        candidates.push_back(threads);
        if (threads > max_threads / 2) break;
        threads *= 2;
    }

    if (candidates.empty() || candidates.back() != max_threads) {
        candidates.push_back(max_threads);
    }

    return candidates;
}

static CandidateResult benchmark_candidate(const WorkloadFunction& workload,
                                           int threads,
                                           int trials,
                                           double serial_time) {
    std::vector<double> times;
    times.reserve(trials);

    for (int trial = 0; trial < trials; ++trial) {
        times.push_back(workload(threads));
    }

    std::sort(times.begin(), times.end());

    double median_time = 0.0;
    if (!times.empty()) {
        size_t mid = times.size() / 2;
        if (times.size() % 2 == 1) {
            median_time = times[mid];
        } else {
            median_time = (times[mid - 1] + times[mid]) * 0.5;
        }
    }

    double speedup = serial_time / median_time;
    double efficiency = speedup / static_cast<double>(threads);

    return CandidateResult{threads, median_time, speedup, efficiency};
}

} // namespace

int tune_dynamic_thread_count(int max_threads_hint,
                              const DynamicTuningConfig& config,
                              const WorkloadFunction& workload) {
    int max_threads = effective_max_threads(max_threads_hint, config);
    int trials = std::max(1, config.trials);

    double serial_time = benchmark_candidate(workload, 1, trials, 1.0).median_time;

    std::vector<int> thread_counts = candidate_thread_counts(max_threads);
    std::vector<CandidateResult> candidates;
    candidates.reserve(thread_counts.size());

    const CandidateResult* best_runtime = nullptr;
    double best_time_so_far = std::numeric_limits<double>::infinity();

    for (int threads : thread_counts) {
        CandidateResult res = benchmark_candidate(workload, threads, trials, serial_time);
        candidates.push_back(res);

        std::cerr << res.median_time << " " << best_time_so_far << " " << res.threads << "\n";

        if (res.median_time + 1e-12 < best_time_so_far) {
            best_time_so_far = res.median_time;
            best_runtime = &candidates.back();
        } else {
            break;
        }
    }

    if (best_runtime == nullptr && !candidates.empty()) {
        best_runtime = &candidates.front();
    }

    if (config.goal == TuningGoal::Performance) {
        return best_runtime != nullptr ? best_runtime->threads : 1;
    }

    // Goal: Efficiency
    const CandidateResult* selected = nullptr;
    for (const auto& candidate : candidates) {
        if (candidate.median_time > best_runtime->median_time * (1.0 + config.efficiency_tolerance)) {
            continue;
        }

        if (selected == nullptr ||
            candidate.median_time < selected->median_time ||
            (candidate.median_time == selected->median_time && candidate.threads < selected->threads)) {
            selected = &candidate;
        }
    }

    return selected != nullptr ? selected->threads : (best_runtime != nullptr ? best_runtime->threads : 1);
}