#include "matrix.h"

void matmul_sequential(const Matrix& A, const Matrix& B, Matrix& C) {
    int n = A.n;
    zero_matrix(C);

    for (int i = 0; i < n; i++) {
        for (int k = 0; k < n; k++) {
            double aik = A(i, k);

            for (int j = 0; j < n; j++) {
                C(i, j) += aik * B(k, j);
            }
        }
    }
}