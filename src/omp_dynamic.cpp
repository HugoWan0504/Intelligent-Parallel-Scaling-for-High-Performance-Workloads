#include "matrix.h"
#include "timer.h"

#include <algorithm>
#include <limits>
#include <omp.h>
#include <vector>

struct CandidateResult {
    int threads;
    double best_time;
    double speedup;
    double efficiency;
};

static int effective_max_threads(int n, const DynamicTuningConfig& config) {
    int max_threads = config.max_threads > 0 ? config.max_threads : omp_get_max_threads();

    if (max_threads <= 0) {
        max_threads = 1;
    }

    return std::max(1, std::min(max_threads, n));
}

static std::vector<int> candidate_thread_counts(int max_threads) {
    std::vector<int> candidates;

    int t = 1;
    while (t <= max_threads) {
        candidates.push_back(t);
        if (t > max_threads / 2) break; // avoid overflow
        t *= 2;
    }

    if (candidates.empty() || candidates.back() != max_threads) {
        candidates.push_back(max_threads);
    }

    return candidates;
}

static double timed_sample_run(const Matrix& A, const Matrix& B, Matrix& C, int threads, int block_size) {
    double start_time = get_time_sec();
    matmul_optimized(A, B, C, threads, block_size);
    return get_time_sec() - start_time;
}

static CandidateResult benchmark_candidate(const Matrix& A,
                                           const Matrix& B,
                                           Matrix& C,
                                           int threads,
                                           int block_size,
                                           int trials,
                                           double serial_time) {
    std::vector<double> times;
    times.reserve(trials);

    for (int trial = 0; trial < trials; trial++) {
        times.push_back(timed_sample_run(A, B, C, threads, block_size));
    }

    std::sort(times.begin(), times.end());

    double average_time = 0.0;
    if (static_cast<int>(times.size()) <= 2) {
        for (double t : times) average_time += t;
        average_time /= static_cast<double>(times.size());
    } else {
        // discard best and worst to reduce outlier effects
        for (size_t i = 1; i + 1 < times.size(); ++i) average_time += times[i];
        average_time /= static_cast<double>(times.size() - 2);
    }

    double speedup = serial_time / average_time;
    double efficiency = speedup / static_cast<double>(threads);

    return CandidateResult{threads, average_time, speedup, efficiency};
}

int tune_dynamic_thread_count(const Matrix& A, const Matrix& B, const DynamicTuningConfig& config) {
    (void)B;

    int n = A.n;
    int sample_n = std::max(1, std::min(config.sample_size, n));
    int max_threads = effective_max_threads(n, config);
    int trials = std::max(1, config.trials);
    int block_size = std::max(1, config.block_size);

    Matrix sample_a = create_matrix(sample_n);
    Matrix sample_b = create_matrix(sample_n);
    Matrix sample_c = create_matrix(sample_n);

    fill_matrix(sample_a);
    fill_matrix(sample_b);

    double serial_time = benchmark_candidate(sample_a, sample_b, sample_c, 1, block_size, trials, 1.0).best_time;

    std::vector<int> thread_counts = candidate_thread_counts(max_threads);
    std::vector<CandidateResult> candidates;
    candidates.reserve(thread_counts.size());

    const CandidateResult* best_runtime = nullptr;
    double best_time_so_far = std::numeric_limits<double>::infinity();
    int worsening_count = 0;
    const int worsening_limit = 2; // stop after 2 worsening candidates
    const double worsening_tol = 0.005; // 0.5% allowed noise

    for (int threads : thread_counts) {
        CandidateResult res = benchmark_candidate(sample_a, sample_b, sample_c, threads, block_size, trials, serial_time);
        candidates.push_back(res);

        if (res.best_time + 1e-12 < best_time_so_far) {
            best_time_so_far = res.best_time;
            best_runtime = &candidates.back();
            worsening_count = 0;
        } else {
            if (res.best_time > best_time_so_far * (1.0 + worsening_tol)) {
                ++worsening_count;
            } else {
                // within noise, reset
                worsening_count = 0;
            }
        }

        if (worsening_count >= worsening_limit) {
            break; // early stop: further exponential increases are worsening
        }
    }

    if (best_runtime == nullptr && !candidates.empty()) {
        best_runtime = &candidates.front();
    }

    // local refinement: try neighbors around best (best-1, best+1)
    if (best_runtime != nullptr) {
        int best_threads = best_runtime->threads;
        std::vector<int> refine;
        if (best_threads > 1) refine.push_back(best_threads - 1);
        if (best_threads + 1 <= max_threads) refine.push_back(best_threads + 1);

        for (int t : refine) {
            bool already = false;
            for (const CandidateResult& c : candidates) if (c.threads == t) { already = true; break; }
            if (already) continue;
            candidates.push_back(benchmark_candidate(sample_a, sample_b, sample_c, t, block_size, trials, serial_time));
        }

        // recompute best_runtime
        for (const CandidateResult& candidate : candidates) {
            if (candidate.best_time < best_runtime->best_time) {
                best_runtime = &candidate;
            }
        }
    }

    if (config.goal == TuningGoal::Performance) {
        return best_runtime->threads;
    }

    // Select by efficiency: require at least 80% of the best observed efficiency
    double max_efficiency = 0.0;
    for (const CandidateResult& c : candidates) {
        if (c.efficiency > max_efficiency) max_efficiency = c.efficiency;
    }

    double min_efficiency = 0.8 * max_efficiency;
    const CandidateResult* selected = nullptr;

    for (const CandidateResult& candidate : candidates) {
        if (candidate.efficiency + 1e-12 < min_efficiency) {
            continue;
        }

        if (selected == nullptr ||
            candidate.efficiency > selected->efficiency ||
            (candidate.efficiency == selected->efficiency && candidate.threads < selected->threads)) {
            selected = &candidate;
        }
    }

    return selected != nullptr ? selected->threads : best_runtime->threads;
}

void matmul_dynamic(const Matrix& A, const Matrix& B, Matrix& C, int& selected_threads, const DynamicTuningConfig& config) {
    selected_threads = tune_dynamic_thread_count(A, B, config);
    matmul_optimized(A, B, C, selected_threads, config.block_size);
}
