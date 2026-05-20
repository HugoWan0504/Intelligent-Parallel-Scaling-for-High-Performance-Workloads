#include "matrix.h"

#include <algorithm>
#include <thread>

static int choose_thread_count(int n) {
    int hardware_threads = static_cast<int>(std::thread::hardware_concurrency());

    if (hardware_threads <= 0) {
        hardware_threads = 8;
    }

    int selected_threads;

    if (n <= 128) {
        selected_threads = 1;
    } else if (n <= 256) {
        selected_threads = 4;
    } else {
        selected_threads = 8;
    }

    selected_threads = std::min(selected_threads, hardware_threads);
    selected_threads = std::max(1, selected_threads);

    return selected_threads;
}

void matmul_dynamic(const Matrix& A, const Matrix& B, Matrix& C, int& selected_threads) {
    selected_threads = choose_thread_count(A.n);

    matmul_static(A, B, C, selected_threads);
}