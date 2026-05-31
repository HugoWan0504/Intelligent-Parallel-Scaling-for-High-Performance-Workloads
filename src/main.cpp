#include "matrix.h"
#include "timer.h"

#include <algorithm>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>

static void print_usage() {
    std::cout << "Usage:\n";
    std::cout << "  ./matmul <mode> <matrix_size> <thread_count> [--csv] [options]\n\n";
    std::cout << "Modes:\n";
    std::cout << "  sequential\n";
    std::cout << "  static      OpenMP with a fixed thread count\n";
    std::cout << "  dynamic     OpenMP with sample-based thread tuning\n";
    std::cout << "  optimized   OpenMP with a fixed thread count and cache blocking\n\n";
    std::cout << "Options:\n";
    std::cout << "  --csv\n";
    std::cout << "  --block-size B\n";
    std::cout << "  --tune-goal performance|efficiency\n";
    std::cout << "  --tune-sample-size N\n";
    std::cout << "  --tune-trials N\n";
    std::cout << "  --max-threads N\n";
    std::cout << "  --efficiency-tolerance F\n\n";
    std::cout << "Examples:\n";
    std::cout << "  ./matmul sequential 512 1\n";
    std::cout << "  ./matmul static 1024 4 --csv\n";
    std::cout << "  ./matmul dynamic 1024 0 --csv --tune-goal efficiency\n";
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

static bool parse_nonnegative_double(const char* text, double& value) {
    char* end = nullptr;
    double parsed = std::strtod(text, &end);

    if (end == text || *end != '\0' || parsed < 0.0) {
        return false;
    }

    value = parsed;
    return true;
}

static void print_table_output(const std::string& mode,
                               int n,
                               int threads,
                               double runtime,
                               const std::string& correct) {
    std::cout << "mode=" << mode
              << " N=" << n
              << " threads=" << threads
              << " time=" << std::fixed << std::setprecision(3) << runtime << " sec"
              << " correct=" << correct << "\n";
}

static void print_csv_output(const std::string& mode,
                             int n,
                             int threads,
                             double runtime,
                             const std::string& correct) {
    std::cout << mode << ","
              << n << ","
              << threads << ","
              << std::fixed << std::setprecision(6) << runtime << ","
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
    DynamicTuningConfig tuning_config;

    for (int i = 4; i < argc; i++) {
        std::string option = argv[i];

        if (option == "--csv") {
            csv_mode = true;
        } else if (option == "--block-size") {
            if (i + 1 >= argc || !parse_positive_int(argv[i + 1], block_size)) {
                std::cerr << "Error: --block-size requires a positive integer.\n";
                return 1;
            }

            i++;
        } else if (option == "--tune-goal") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --tune-goal requires performance or efficiency.\n";
                return 1;
            }

            std::string goal = argv[i + 1];
            if (goal == "performance") {
                tuning_config.goal = TuningGoal::Performance;
            } else if (goal == "efficiency") {
                tuning_config.goal = TuningGoal::Efficiency;
            } else {
                std::cerr << "Error: --tune-goal must be performance or efficiency.\n";
                return 1;
            }

            i++;
        } else if (option == "--tune-sample-size") {
            if (i + 1 >= argc || !parse_positive_int(argv[i + 1], tuning_config.sample_size)) {
                std::cerr << "Error: --tune-sample-size requires a positive integer.\n";
                return 1;
            }

            i++;
        } else if (option == "--tune-trials") {
            if (i + 1 >= argc || !parse_positive_int(argv[i + 1], tuning_config.trials)) {
                std::cerr << "Error: --tune-trials requires a positive integer.\n";
                return 1;
            }

            i++;
        } else if (option == "--max-threads") {
            if (i + 1 >= argc || !parse_positive_int(argv[i + 1], tuning_config.max_threads)) {
                std::cerr << "Error: --max-threads requires a positive integer.\n";
                return 1;
            }

            i++;
        } else if (option == "--efficiency-tolerance") {
            if (i + 1 >= argc || !parse_nonnegative_double(argv[i + 1], tuning_config.efficiency_tolerance)) {
                std::cerr << "Error: --efficiency-tolerance requires a non-negative number.\n";
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

    if (mode == "dynamic" && thread_count > 0 && tuning_config.max_threads == 0) {
        tuning_config.max_threads = thread_count;
    }

    tuning_config.block_size = block_size;

    Matrix A = create_matrix(n);
    Matrix B = create_matrix(n);
    Matrix C = create_matrix(n);

    fill_matrix(A);
    fill_matrix(B);

    int actual_threads = thread_count;
    double start_time = 0.0;
    double end_time = 0.0;

    if (mode == "sequential") {
        actual_threads = 1;
        start_time = get_time_sec();
        matmul_sequential(A, B, C);
        end_time = get_time_sec();
    } else if (mode == "static") {
        actual_threads = std::max(1, std::min(thread_count, n));
        start_time = get_time_sec();
        matmul_static(A, B, C, actual_threads);
        end_time = get_time_sec();
    } else if (mode == "dynamic") {
        actual_threads = tune_dynamic_thread_count(A, B, tuning_config);
        start_time = get_time_sec();
        matmul_optimized(A, B, C, actual_threads, block_size);
        end_time = get_time_sec();
    } else if (mode == "optimized") {
        actual_threads = std::max(1, std::min(thread_count, n));
        start_time = get_time_sec();
        matmul_optimized(A, B, C, actual_threads, block_size);
        end_time = get_time_sec();
    } else {
        std::cerr << "Error: unknown mode: " << mode << "\n";
        print_usage();
        return 1;
    }

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
