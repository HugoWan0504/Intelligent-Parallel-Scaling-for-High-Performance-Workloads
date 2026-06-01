#include "dynamic_tuner.h"
#include "matrix.h"
#include "password_search_workload.h"
#include "timer.h"

#include <algorithm>
#include <cstdlib>
#include <iomanip>
#include <iostream>
#include <string>

static void print_usage() {
    std::cout << "Usage:\n";
    std::cout << "  ./autotuner <mode> <size> <thread_count> [--csv] [options]\n\n";
    std::cout << "Modes:\n";
    std::cout << "  static      OpenMP with a fixed thread count\n";
    std::cout << "  dynamic     OpenMP with sample-based thread tuning\n";
    std::cout << "Options:\n";
    std::cout << "  --csv\n";
    std::cout << "  --workload matrix|password\n";
    std::cout << "  --charset STRING\n";
    std::cout << "  --password-target STRING\n";
    std::cout << "  --tune-goal performance|efficiency\n";
    std::cout << "  --tune-sample-size N\n";
    std::cout << "  --tune-trials N\n";
    std::cout << "  --max-threads N\n";
    std::cout << "  --efficiency-tolerance F\n\n";
    std::cout << "Examples:\n";
    std::cout << "  ./autotuner static 1024 4 --csv\n";
    std::cout << "  ./autotuner dynamic 1024 0 --csv --tune-goal efficiency\n";
    std::cout << "  ./autotuner optimized 1024 8 --csv\n";
    std::cout << "  ./autotuner dynamic 5 0 --workload password --charset abcdef --password-target fffff\n";
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
    std::string workload_type = "matrix";
    std::string charset = "abcdefghijklmnopqrstuvwxyz";
    std::string password_target;
    DynamicTuningConfig tuning_config;

    for (int i = 4; i < argc; i++) {
        std::string option = argv[i];

        if (option == "--csv") {
            csv_mode = true;
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
        } else if (option == "--workload") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --workload requires matrix or password.\n";
                return 1;
            }
            workload_type = argv[i + 1];
            if (workload_type != "matrix" && workload_type != "password") {
                std::cerr << "Error: --workload must be matrix or password.\n";
                return 1;
            }
            i++;
        } else if (option == "--charset") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --charset requires a string.\n";
                return 1;
            }
            charset = argv[i + 1];
            i++;
        } else if (option == "--password-target") {
            if (i + 1 >= argc) {
                std::cerr << "Error: --password-target requires a string.\n";
                return 1;
            }
            password_target = argv[i + 1];
            i++;
        } else {
            std::cerr << "Error: unknown option: " << option << "\n";
            print_usage();
            return 1;
        }
    }

    if (n <= 0) {
        std::cerr << "Error: size must be positive.\n";
        return 1;
    }

    if (thread_count <= 0 && mode != "dynamic") {
        std::cerr << "Error: thread_count must be positive except for dynamic mode.\n";
        return 1;
    }

    if (mode == "dynamic" && thread_count > 0 && tuning_config.max_threads == 0) {
        tuning_config.max_threads = thread_count;
    }

    std::string output_mode = workload_type + "_" + mode;
    int actual_threads = thread_count;
    double start_time = 0.0;
    double end_time = 0.0;
    std::string correct = "skipped";

    if (workload_type == "matrix") {
        Matrix A = create_matrix(n);
        Matrix B = create_matrix(n);
        Matrix C = create_matrix(n);

        fill_matrix(A);
        fill_matrix(B);

       if (mode == "static") {
            actual_threads = std::max(1, std::min(thread_count, n));
            start_time = get_time_sec();
            matmul_static(A, B, C, actual_threads);
            end_time = get_time_sec();
        } else if (mode == "dynamic") {
            actual_threads = tune_dynamic_thread_count(n, tuning_config, [&](int threads) {
                Matrix sample_a = create_matrix(std::max(1, std::min(tuning_config.sample_size, n)));
                Matrix sample_b = create_matrix(std::max(1, std::min(tuning_config.sample_size, n)));
                Matrix sample_c = create_matrix(std::max(1, std::min(tuning_config.sample_size, n)));
                fill_matrix(sample_a);
                fill_matrix(sample_b);
                double start = get_time_sec();
                matmul_static(sample_a, sample_b, sample_c, threads);
                return get_time_sec() - start;
            });

            start_time = get_time_sec();
            matmul_static(A, B, C, actual_threads);
            end_time = get_time_sec();
        } else {
            std::cerr << "Error: unknown mode: " << mode << "\n";
            print_usage();
            return 1;
        }

        if (mode != "sequential" && n <= 1024) {
            Matrix reference = create_matrix(n);
            matmul_sequential(A, B, reference);
            correct = compare_matrices(C, reference) ? "true" : "false";
        }
    } else if (workload_type == "password") {
        PasswordSearchConfig password_config;
        password_config.charset = charset;
        password_config.length = n;
        password_config.target = password_target;
        PasswordSearchWorkload password_workload(password_config);

        if (mode == "static" || mode == "optimized") {
            actual_threads = std::max(1, thread_count);
            start_time = get_time_sec();
            password_workload(actual_threads);
            end_time = get_time_sec();
        } else if (mode == "dynamic") {
            actual_threads = tune_dynamic_thread_count(thread_count, tuning_config, password_workload);
            start_time = get_time_sec();
            password_workload(actual_threads);
            end_time = get_time_sec();
        } else {
            std::cerr << "Error: unknown mode: " << mode << "\n";
            print_usage();
            return 1;
        }

        correct = password_workload.found() ? "true" : "false";
    } else {
        std::cerr << "Error: unknown workload: " << workload_type << "\n";
        print_usage();
        return 1;
    }

    double runtime = end_time - start_time;

    if (csv_mode) {
        print_csv_output(output_mode, n, actual_threads, runtime, correct);
    } else {
        print_table_output(output_mode, n, actual_threads, runtime, correct);
    }

    return 0;
}
