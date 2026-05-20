#include "matrix.h"
#include "timer.h"

#include <iostream>
#include <string>
#include <cstdlib>
#include <iomanip>

static void print_usage() {
    std::cout << "Usage:\n";
    std::cout << "  ./matmul <mode> <matrix_size> <thread_count> [--csv] [--block-size B]\n\n";
    std::cout << "Modes:\n";
    std::cout << "  sequential\n";
    std::cout << "  static\n";
    std::cout << "  dynamic\n";
    std::cout << "  optimized\n\n";
    std::cout << "Examples:\n";
    std::cout << "  ./matmul sequential 512 1\n";
    std::cout << "  ./matmul static 1024 4 --csv\n";
    std::cout << "  ./matmul dynamic 1024 0 --csv\n";
    std::cout << "  ./matmul optimized 1024 8 --block-size 64 --csv\n";
}

static bool parse_positive_int(const char* text, int& value) {
    char* end = nullptr;
    long parsed = std::strtol(text, &end, 10);

    if (end == text || *end != '\0' || parsed <= 0) {
        return false;
    }

    value = static_cast<int>(parsed);
    return true;
}

static void print_table_output(const std::string& mode,
                               int n,
                               int threads,
                               double runtime,
                               const std::string& correct) {
    (void)mode;
    (void)n;
    (void)threads;
    (void)correct;

    std::cout << std::fixed << std::setprecision(3)
              << runtime << " sec\n";
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
    if (argc < 4) {
        print_usage();
        return 1;
    }

    std::string mode = argv[1];
    int n = std::atoi(argv[2]);
    int thread_count = std::atoi(argv[3]);

    bool csv_mode = false;
    int block_size = 32;

    for (int i = 4; i < argc; i++) {
        std::string option = argv[i];

        if (option == "--csv") {
            csv_mode = true;
        } else if (option == "--block-size") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --block-size requires a positive integer.\n";
                return 1;
            }

            if (!parse_positive_int(argv[i + 1], block_size)) {
                std::cerr << "Error: block size must be a positive integer.\n";
                return 1;
            }

            i++;
        } else {
            std::cerr << "Error: unknown option: " << option << "\n";
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
        matmul_optimized(A, B, C, thread_count, block_size);
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