#include "matrix.h"

#include <pthread.h>
#include <vector>
#include <algorithm>

struct StaticTask {
    const Matrix* A;
    const Matrix* B;
    Matrix* C;
    int row_start;
    int row_end;
};

static void* static_worker(void* arg) {
    StaticTask* task = static_cast<StaticTask*>(arg);

    const Matrix& A = *(task->A);
    const Matrix& B = *(task->B);
    Matrix& C = *(task->C);

    int n = A.n;

    for (int i = task->row_start; i < task->row_end; i++) {
        for (int k = 0; k < n; k++) {
            double aik = A(i, k);

            for (int j = 0; j < n; j++) {
                C(i, j) += aik * B(k, j);
            }
        }
    }

    return nullptr;
}

void matmul_static(const Matrix& A, const Matrix& B, Matrix& C, int thread_count) {
    int n = A.n;
    zero_matrix(C);

    thread_count = std::max(1, std::min(thread_count, n));

    std::vector<pthread_t> threads(thread_count);
    std::vector<StaticTask> tasks(thread_count);

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

        current_row += rows;

        pthread_create(&threads[t], nullptr, static_worker, &tasks[t]);
    }

    for (int t = 0; t < thread_count; t++) {
        pthread_join(threads[t], nullptr);
    }
}