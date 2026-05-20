#include "matrix.h"

#include <pthread.h>
#include <vector>
#include <algorithm>

struct OptimizedTask {
    const Matrix* A;
    const Matrix* B;
    Matrix* C;
    int row_start;
    int row_end;
    int block_size;
};

static void* optimized_worker(void* arg) {
    OptimizedTask* task = static_cast<OptimizedTask*>(arg);

    const Matrix& A = *(task->A);
    const Matrix& B = *(task->B);
    Matrix& C = *(task->C);

    int n = A.n;
    int block = task->block_size;

    for (int ii = task->row_start; ii < task->row_end; ii += block) {
        int i_end = std::min(ii + block, task->row_end);

        for (int kk = 0; kk < n; kk += block) {
            int k_end = std::min(kk + block, n);

            for (int jj = 0; jj < n; jj += block) {
                int j_end = std::min(jj + block, n);

                for (int i = ii; i < i_end; i++) {
                    for (int k = kk; k < k_end; k++) {
                        double aik = A(i, k);

                        for (int j = jj; j < j_end; j++) {
                            C(i, j) += aik * B(k, j);
                        }
                    }
                }
            }
        }
    }

    return nullptr;
}

void matmul_optimized(const Matrix& A, const Matrix& B, Matrix& C, int thread_count) {
    int n = A.n;
    zero_matrix(C);

    thread_count = std::max(1, std::min(thread_count, n));

    const int block_size = 32;

    std::vector<pthread_t> threads(thread_count);
    std::vector<OptimizedTask> tasks(thread_count);

    int rows_per_thread = n / thread_count;
    int extra_rows = n % thread_count;

    int current_row = 0;

    for (int t = 0; t < thread_count; t++) {
        int rows = rows_per_thread + (t < extra_rows ? 1 : 0);

        tasks[t].A = &A;
        tasks[t].B = &B;
        tasks[t].C = &C;
        tasks[t].row_start = current_row;
        tasks[t].row_end = current_row + rows;
        tasks[t].block_size = block_size;

        current_row += rows;

        pthread_create(&threads[t], nullptr, optimized_worker, &tasks[t]);
    }

    for (int t = 0; t < thread_count; t++) {
        pthread_join(threads[t], nullptr);
    }
}