#include "matrix.h"

#include <algorithm>
#include <omp.h>

void matmul_optimized(const Matrix& A, const Matrix& B, Matrix& C, int thread_count, int block_size) {
    int n = A.n;
    zero_matrix(C);

    thread_count = std::max(1, std::min(thread_count, n));
    block_size = std::max(1, std::min(block_size, n));
    omp_set_dynamic(0);

    #pragma omp parallel for num_threads(thread_count) schedule(static)
    for (int ii = 0; ii < n; ii += block_size) {
        int i_end = std::min(ii + block_size, n);

        for (int kk = 0; kk < n; kk += block_size) {
            int k_end = std::min(kk + block_size, n);

            for (int jj = 0; jj < n; jj += block_size) {
                int j_end = std::min(jj + block_size, n);

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
}
