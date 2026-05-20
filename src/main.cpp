#include "matrix.h"
#include "timer.h"

#include <iostream>
#include <string>
#include <cstdlib>
#include <iomanip>

static void print_usage() {
    std::cout << "Usage:\n";
    std::cout << "  ./matmul <mode> <matrix_size> <thread_count>\n\n";
    std::cout << "Modes:\n";
    std::cout << "  sequential\n";
    std::cout << "  static\n";
    std::cout << "  dynamic\n";
    std::cout << "  optimized\n\n";
    std::cout << "Examples:\n";
    std::cout << "  ./matmul sequential 512 1\n";
    std::cout << "  ./matmul static 1024 4\n";
    std::cout << "  ./matmul dynamic 1024 0\n";
    std::cout << "  ./matmul optimized 1024 8\n";
}

static void print_table_output(const std::string& mode,
                               int n,
                               int threads,
                               double runtime,
                               const std::string& correct) {
    std::cout << "\n";
    std::cout << "+------------+--------+---------+-------------+---------+\n";
    std::cout << "| Mode       | N      | Threads | Time (sec)  | Correct |\n";
    std::cout << "+------------+--------+---------+-------------+---------+\n";

    std::cout << "| "
              << std::left << std::setw(10) << mode << " | "
              << std::right << std::setw(6) << n << " | "
              << std::right << std::setw(7) << threads << " | "
              << std::right << std::setw(11) << std::fixed << std::setprecision(3) << runtime << " | "
              << std::left << std::setw(7) << correct << " |\n";

    std::cout << "+------------+--------+---------+-------------+---------+\n";
}

static void print_csv_output(const std::string& mode,
                             int n,
                             int threads,
                             double runtime,
                             const std::string& correct) {
    std::cout << mode << ","
              << n << ","
              << threads << ","
              << std::fixed << std::setprecision(3) << runtime << ","
              << correct << "\n";
}

int main(int argc, char* argv[]) {
    if (argc != 4 && argc != 5) {
        print_usage();
        return 1;
    }

    std::string mode = argv[1];
    int n = std::atoi(argv[2]);
    int thread_count = std::atoi(argv[3]);

    bool csv_mode = false;
    if (argc == 5) {
        std::string output_mode = argv[4];
        if (output_mode == "--csv") {
            csv_mode = true;
        } else {
            std::cerr << "Error: unknown option: " << output_mode << "\n";
            print_usage();
            return 1;
        }
    }

    if (n <= 0) {
        std::cerr << "Error: matrix_size must be positive.\n";
        return 1;
    }

    if (thread_count <= 0 && mode != "dynamic") {
        std::cerr << "Error: thread_count must be positive except for dynamic mode.\n";
        return 1;
    }

    Matrix A = create_matrix(n);
    Matrix B = create_matrix(n);
    Matrix C = create_matrix(n);

    fill_matrix(A);
    fill_matrix(B);

    int actual_threads = thread_count;

    double start_time = get_time_sec();

    if (mode == "sequential") {
        actual_threads = 1;
        matmul_sequential(A, B, C);
    } else if (mode == "static") {
        matmul_static(A, B, C, thread_count);
    } else if (mode == "dynamic") {
        matmul_dynamic(A, B, C, actual_threads);
    } else if (mode == "optimized") {
        matmul_optimized(A, B, C, thread_count);
    } else {
        std::cerr << "Error: unknown mode: " << mode << "\n";
        print_usage();
        return 1;
    }

    double end_time = get_time_sec();
    double runtime = end_time - start_time;

    std::string correct = "skipped";

    if (mode == "sequential") {
        correct = "true";
    } else if (n <= 1024) {
        Matrix reference = create_matrix(n);
        matmul_sequential(A, B, reference);
        correct = compare_matrices(C, reference) ? "true" : "false";
    }

    if (csv_mode) {
        print_csv_output(mode, n, actual_threads, runtime, correct);
    } else {
        print_table_output(mode, n, actual_threads, runtime, correct);
    }

    return 0;
}