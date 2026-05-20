#ifndef MATRIX_H
#define MATRIX_H

#include <vector>
#include <string>

struct Matrix {
    int n;
    std::vector<double> data;

    Matrix();
    Matrix(int size);

    double& operator()(int row, int col);
    const double& operator()(int row, int col) const;
};

Matrix create_matrix(int n);
void fill_matrix(Matrix& mat);
void zero_matrix(Matrix& mat);
bool compare_matrices(const Matrix& a, const Matrix& b, double eps = 1e-6);

void matmul_sequential(const Matrix& A, const Matrix& B, Matrix& C);
void matmul_static(const Matrix& A, const Matrix& B, Matrix& C, int thread_count);
void matmul_dynamic(const Matrix& A, const Matrix& B, Matrix& C, int& selected_threads);
void matmul_optimized(const Matrix& A, const Matrix& B, Matrix& C, int thread_count);

#endif