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

    // Optional refinement phase (kept as-is)
    if (best_runtime != nullptr) {
        auto is_power_of_two = [](int x) {
            return x > 0 && (x & (x - 1)) == 0;
        };

        auto prev_power_of_two = [](int x) {
            int p = 1;
            while (p * 2 <= x) {
                p *= 2;
            }
            return p;
        };

        auto already_tested = [&](int t) {
            for (const CandidateResult& c : candidates) {
                if (c.threads == t) {
                    return true;
                }
            }
            return false;
        };

        auto find_candidate = [&](int t) -> const CandidateResult* {
            for (const CandidateResult& c : candidates) {
                if (c.threads == t) {
                    return &c;
                }
            }
            return nullptr;
        };

        int best_threads = best_runtime->threads;
        int lower_bound = best_threads;
        int upper_bound = best_threads;

        if (is_power_of_two(best_threads)) {
            lower_bound = best_threads;
            upper_bound = std::min(max_threads, best_threads * 2);
        } else {
            lower_bound = prev_power_of_two(best_threads);
            upper_bound = best_threads;
        }

        while (lower_bound + 1 < upper_bound) {
            int mid = (lower_bound + upper_bound) / 2;
            if (mid == lower_bound || mid == upper_bound || already_tested(mid)) {
                break;
            }

            candidates.push_back(benchmark_candidate(workload, mid, trials, serial_time));
            const CandidateResult* mid_candidate = &candidates.back();
            if (mid_candidate->median_time < best_runtime->median_time) {
                best_runtime = mid_candidate;
            }

            const CandidateResult* low_candidate = find_candidate(lower_bound);
            const CandidateResult* high_candidate = find_candidate(upper_bound);
            if (!low_candidate || !high_candidate) {
                break;
            }

            if (mid_candidate->median_time < low_candidate->median_time &&
                mid_candidate->median_time < high_candidate->median_time) {
                if (mid - lower_bound > upper_bound - mid) {
                    lower_bound = mid;
                } else {
                    upper_bound = mid;
                }
            } else if (mid_candidate->median_time > low_candidate->median_time) {
                upper_bound = mid;
            } else {
                lower_bound = mid;
            }
        }
    }

    if (config.goal == TuningGoal::Performance) {
        return best_runtime->threads;
    }

    double max_efficiency = 0.0;
    for (const CandidateResult& c : candidates) {
        if (c.efficiency > max_efficiency) {
            max_efficiency = c.efficiency;
        }
    }

    double min_efficiency = 0.8 * max_efficiency;
    const CandidateResult* selected = nullptr;

    for (const CandidateResult& candidate : candidates) {
        if (candidate.efficiency + 1e-12 < min_efficiency) {
            continue;
        }

        if (selected == nullptr ||
            candidate.median_time < selected->median_time ||
            (candidate.median_time == selected->median_time && candidate.threads < selected->threads)) {
            selected = &candidate;
        }
    }

    return selected != nullptr ? selected->threads : best_runtime->threads;
}