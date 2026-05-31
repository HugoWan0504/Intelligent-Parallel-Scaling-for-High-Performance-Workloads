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

    for (int threads = 1; threads <= max_threads; threads *= 2) {
        candidates.push_back(threads);
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
    double total_time = 0.0;

    for (int trial = 0; trial < trials; trial++) {
        total_time += timed_sample_run(A, B, C, threads, block_size);
    }

    double average_time = total_time / static_cast<double>(trials);
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

    for (int threads : thread_counts) {
        candidates.push_back(benchmark_candidate(sample_a, sample_b, sample_c, threads, block_size, trials, serial_time));
    }

    const CandidateResult* best_runtime = &candidates.front();
    for (const CandidateResult& candidate : candidates) {
        if (candidate.best_time < best_runtime->best_time) {
            best_runtime = &candidate;
        }
    }

    if (config.goal == TuningGoal::Performance) {
        return best_runtime->threads;
    }

    double allowed_time = best_runtime->best_time * (1.0 + std::max(0.0, config.efficiency_tolerance));
    const CandidateResult* selected = nullptr;

    for (const CandidateResult& candidate : candidates) {
        if (candidate.best_time > allowed_time) {
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
