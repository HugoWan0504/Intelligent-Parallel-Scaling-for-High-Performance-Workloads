#ifndef PASSWORD_SEARCH_WORKLOAD_H
#define PASSWORD_SEARCH_WORKLOAD_H

#include <string>

struct PasswordSearchConfig {
    std::string charset = "abcdefghijklmnopqrstuvwxyz";
    int length = 4;
    std::string target;
};

class PasswordSearchWorkload {
public:
    explicit PasswordSearchWorkload(const PasswordSearchConfig& config);

    double operator()(int threads);
    bool found() const;
    const std::string& target() const;
    int length() const;

private:
    std::string charset_;
    int length_;
    std::string target_;
    bool found_ = false;
};

#endif // PASSWORD_SEARCH_WORKLOAD_H
