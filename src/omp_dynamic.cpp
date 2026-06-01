#include "matrix.h"
#include "timer.h"
#include "dynamic_tuner.h"

#include <algorithm>
#include <functional>
#include <vector>

static double timed_sample_run(const Matrix& A, const Matrix& B, Matrix& C, int threads) {
    double start_time = get_time_sec();
    matmul_static(A, B, C, threads);
    return get_time_sec() - start_time;
}

static int effective_max_threads(int n, const DynamicTuningConfig& config) {
    int max_threads = config.max_threads > 0 ? config.max_threads : n;
    if (max_threads <= 0) {
        max_threads = 1;
    }
    return std::max(1, std::min(max_threads, n));
}

int tune_dynamic_thread_count(const Matrix& A, const Matrix& B, const DynamicTuningConfig& config) {
    (void)B;

    int n = A.n;
    int sample_n = std::max(1, std::min(config.sample_size, n));
    int max_threads = effective_max_threads(n, config);

    Matrix sample_a = create_matrix(sample_n);
    Matrix sample_b = create_matrix(sample_n);
    Matrix sample_c = create_matrix(sample_n);

    fill_matrix(sample_a);
    fill_matrix(sample_b);

    auto workload = [&](int threads) {
        return timed_sample_run(sample_a, sample_b, sample_c, threads);
    };

    return tune_dynamic_thread_count(max_threads, config, workload);
}

void matmul_dynamic(const Matrix& A, const Matrix& B, Matrix& C, int& selected_threads, const DynamicTuningConfig& config) {
    selected_threads = tune_dynamic_thread_count(A, B, config);
    matmul_static(A, B, C, selected_threads);
}
