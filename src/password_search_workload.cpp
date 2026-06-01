#include "password_search_workload.h"
#include "timer.h"

#include <atomic>
#include <cstdint>
#include <omp.h>
#include <string>
#include <vector>

PasswordSearchWorkload::PasswordSearchWorkload(const PasswordSearchConfig& config)
    : charset_(config.charset),
      length_(std::max(1, config.length)),
      target_(config.target),
      found_(false) {
    if (charset_.empty()) {
        charset_ = "abcdefghijklmnopqrstuvwxyz";
    }

    if (target_.empty() || static_cast<int>(target_.size()) != length_) {
        target_.assign(length_, charset_.back());
    }
}

bool PasswordSearchWorkload::found() const {
    return found_;
}

const std::string& PasswordSearchWorkload::target() const {
    return target_;
}

int PasswordSearchWorkload::length() const {
    return length_;
}

static uint64_t power_u64(uint64_t base, int exp) {
    uint64_t result = 1;
    for (int i = 0; i < exp; ++i) {
        if (result > UINT64_MAX / base) {
            return UINT64_MAX;
        }
        result *= base;
    }
    return result;
}

double PasswordSearchWorkload::operator()(int threads) {
    const size_t charset_size = charset_.size();
    const uint64_t total_candidates = power_u64(static_cast<uint64_t>(charset_size), length_);
    const uint64_t search_space = total_candidates == UINT64_MAX ? 0 : total_candidates;

    if (search_space == 0) {
        // Fallback to a simpler synthetic search if the exact space is too large.
        const int iterations = 1000000;
        std::atomic<bool> found(false);
        omp_set_num_threads(std::max(1, threads));

        double start_time = get_time_sec();
#pragma omp parallel for schedule(dynamic, 1024)
        for (int i = 0; i < iterations; ++i) {
            if (found.load(std::memory_order_relaxed)) {
                continue;
            }
            std::string candidate(length_, ' ');
            uint64_t code = static_cast<uint64_t>(i);
            for (int d = length_ - 1; d >= 0; --d) {
                candidate[d] = charset_[code % charset_size];
                code /= charset_size;
            }
            if (candidate == target_) {
                found.store(true, std::memory_order_relaxed);
            }
        }
        double end_time = get_time_sec();
        found_ = found.load(std::memory_order_relaxed);
        return end_time - start_time;
    }

    omp_set_num_threads(std::max(1, threads));
    std::atomic<bool> found(false);

    double start_time = get_time_sec();
#pragma omp parallel
    {
        std::string candidate(length_, ' ');
#pragma omp for schedule(dynamic, 1024)
        for (uint64_t idx = 0; idx < search_space; ++idx) {
            if (found.load(std::memory_order_relaxed)) {
                continue;
            }

            uint64_t code = idx;
            for (int d = length_ - 1; d >= 0; --d) {
                candidate[d] = charset_[code % charset_size];
                code /= charset_size;
            }

            if (candidate == target_) {
                found.store(true, std::memory_order_relaxed);
            }
        }
    }
    double end_time = get_time_sec();

    found_ = found.load(std::memory_order_relaxed);
    return end_time - start_time;
}
