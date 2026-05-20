#include "matrix.h"

#include <cmath>

Matrix::Matrix() : n(0) {}

Matrix::Matrix(int size) : n(size), data(size * size, 0.0) {}

double& Matrix::operator()(int row, int col) {
    return data[row * n + col];
}

const double& Matrix::operator()(int row, int col) const {
    return data[row * n + col];
}

Matrix create_matrix(int n) {
    return Matrix(n);
}

void fill_matrix(Matrix& mat) {
    for (int i = 0; i < mat.n; i++) {
        for (int j = 0; j < mat.n; j++) {
            mat(i, j) = static_cast<double>((i * 31 + j * 17 + 7) % 100) / 100.0;
        }
    }
}

void zero_matrix(Matrix& mat) {
    std::fill(mat.data.begin(), mat.data.end(), 0.0);
}

bool compare_matrices(const Matrix& a, const Matrix& b, double eps) {
    if (a.n != b.n) {
        return false;
    }

    for (int i = 0; i < a.n; i++) {
        for (int j = 0; j < a.n; j++) {
            if (std::fabs(a(i, j) - b(i, j)) > eps) {
                return false;
            }
        }
    }

    return true;
}