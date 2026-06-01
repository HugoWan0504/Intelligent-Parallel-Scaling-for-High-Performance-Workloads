#include "matrix.h"

#include <algorithm>
#include <omp.h>

void matmul_static(const Matrix& A, const Matrix& B, Matrix& C, int thread_count) {
    int n = A.n;
    zero_matrix(C);

    thread_count = std::max(1, std::min(thread_count, n));
    omp_set_dynamic(0);

    #pragma omp parallel for num_threads(thread_count) schedule(static) collapse(2)
    for (int i = 0; i < n; i++) {
        for (int k = 0; k < n; k++) {
            double aik = A(i, k);

            for (int j = 0; j < n; j++) {
                C(i, j) += aik * B(k, j);
            }
        }
    }
}
