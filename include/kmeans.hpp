#pragma once
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <limits>
#include <stdexcept>
#include <vector>

namespace km {
using Clock = std::chrono::steady_clock;
inline double elapsed(Clock::time_point a) {
    return std::chrono::duration<double>(Clock::now()-a).count();
}
inline uint64_t mix(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}
inline double uniform(uint64_t x) { return (mix(x) >> 11) * 0x1.0p-53; }
// Ten latent groups, independent of requested K. Uniform bounded noise.
inline double sample(uint64_t row, uint64_t col, uint64_t seed) {
    uint64_t group = mix(row ^ mix(seed)) % 10;
    double center = 12.0 * uniform(group * 0x100000001b3ULL ^ mix(col) ^ mix(seed+1));
    double noise = uniform(mix(row) ^ mix(col+100) ^ mix(seed+2)) - 0.5;
    return center + noise;
}
inline std::vector<uint64_t> initial_indices(uint64_t n, int k, uint64_t seed) {
    std::vector<uint64_t> ids;
    uint64_t state = seed;
    for (int c=0;c<k;++c) {
        state = mix(state);
        uint64_t id = state % n;
        while (std::find(ids.begin(),ids.end(),id)!=ids.end()) id=(id+1)%n;
        ids.push_back(id);
    }
    return ids;
}
inline int nearest(const double* x, const std::vector<double>& centers, int k, int d, double& best) {
    int label=0; best=std::numeric_limits<double>::infinity();
    for(int c=0;c<k;++c) {
        double s=0;
        for(int j=0;j<d;++j) { double v=x[j]-centers[size_t(c)*d+j]; s+=v*v; }
        if(s<best) {best=s;label=c;}
    }
    return label;
}
}
