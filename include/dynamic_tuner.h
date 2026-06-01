#ifndef DYNAMIC_TUNER_H
#define DYNAMIC_TUNER_H

#include <functional>
#include <vector>

enum class TuningGoal {
    Performance,
    Efficiency
};

struct DynamicTuningConfig {
    TuningGoal goal = TuningGoal::Performance;
    int max_threads = 0;
    int sample_size = 512;
    int trials = 3;
    double efficiency_tolerance = 0.25;
    int block_size = 32; // workload-specific payload, ignored by the generic tuner itself
};

struct CandidateResult {
    int threads;
    double best_time;
    double speedup;
    double efficiency;
};

using WorkloadFunction = std::function<double(int threads)>;

int tune_dynamic_thread_count(int max_threads_hint,
                              const DynamicTuningConfig& config,
                              const WorkloadFunction& workload);

#endif // DYNAMIC_TUNER_H
