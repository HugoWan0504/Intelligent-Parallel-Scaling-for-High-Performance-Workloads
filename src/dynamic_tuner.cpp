#include "dynamic_tuner.h"

#include <algorithm>
#include <limits>
#include <thread>
#include <vector>

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

    double average_time = 0.0;
    if (static_cast<int>(times.size()) <= 2) {
        for (double t : times) {
            average_time += t;
        }
        average_time /= static_cast<double>(times.size());
    } else {
        for (size_t i = 1; i + 1 < times.size(); ++i) {
            average_time += times[i];
        }
        average_time /= static_cast<double>(times.size() - 2);
    }

    double speedup = serial_time / average_time;
    double efficiency = speedup / static_cast<double>(threads);

    return CandidateResult{threads, average_time, speedup, efficiency};
}

} // namespace

int tune_dynamic_thread_count(int max_threads_hint,
                              const DynamicTuningConfig& config,
                              const WorkloadFunction& workload) {
    int max_threads = effective_max_threads(max_threads_hint, config);
    int trials = std::max(1, config.trials);

    double serial_time = benchmark_candidate(workload, 1, trials, 1.0).best_time;

    std::vector<int> thread_counts = candidate_thread_counts(max_threads);
    std::vector<CandidateResult> candidates;
    candidates.reserve(thread_counts.size());

    const CandidateResult* best_runtime = nullptr;
    double best_time_so_far = std::numeric_limits<double>::infinity();
    int worsening_count = 0;
    const int worsening_limit = 2;
    const double worsening_tol = 0.005;

    for (int threads : thread_counts) {
        CandidateResult res = benchmark_candidate(workload, threads, trials, serial_time);
        candidates.push_back(res);

        if (res.best_time + 1e-12 < best_time_so_far) {
            best_time_so_far = res.best_time;
            best_runtime = &candidates.back();
            worsening_count = 0;
        } else {
            if (res.best_time > best_time_so_far * (1.0 + worsening_tol)) {
                ++worsening_count;
            } else {
                worsening_count = 0;
            }
        }

        if (worsening_count >= worsening_limit) {
            break;
        }
    }

    if (best_runtime == nullptr && !candidates.empty()) {
        best_runtime = &candidates.front();
    }

    if (best_runtime != nullptr) {
        int best_threads = best_runtime->threads;
        std::vector<int> refine;
        if (best_threads > 1) {
            refine.push_back(best_threads - 1);
        }
        if (best_threads + 1 <= max_threads) {
            refine.push_back(best_threads + 1);
        }

        for (int t : refine) {
            bool already = false;
            for (const CandidateResult& c : candidates) {
                if (c.threads == t) {
                    already = true;
                    break;
                }
            }
            if (already) {
                continue;
            }
            candidates.push_back(benchmark_candidate(workload, t, trials, serial_time));
        }

        for (const CandidateResult& candidate : candidates) {
            if (candidate.best_time < best_runtime->best_time) {
                best_runtime = &candidate;
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
            candidate.best_time < selected->best_time ||
            (candidate.best_time == selected->best_time && candidate.threads < selected->threads)) {
            selected = &candidate;
        }
    }

    return selected != nullptr ? selected->threads : best_runtime->threads;
}
