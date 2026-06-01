#ifndef TIMER_H
#define TIMER_H

#include <chrono>

inline double get_time_sec() {
    using namespace std::chrono;
    return duration<double>(high_resolution_clock::now().time_since_epoch()).count();
}

#endif