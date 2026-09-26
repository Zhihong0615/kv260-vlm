#include <algorithm>
#include <array>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <fstream>
#include <iomanip>
#include <string>
#include <vector>

#if defined(_OPENMP)
#include <omp.h>
#endif

namespace {
constexpr int K = 1152;
constexpr int M = 4304;
constexpr std::array<const char *, 3> LAYERS = {
    "ffn_up-0", "ffn_up-13", "ffn_up-26"};
constexpr std::array<int, 3> NS = {1120, 280, 280};

bool read_exact(const std::string &path, void *dst, size_t bytes) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return false;
    in.read(static_cast<char *>(dst), static_cast<std::streamsize>(bytes));
    return static_cast<size_t>(in.gcount()) == bytes && in.peek() == std::ifstream::traits_type::eof();
}

float half_to_float(uint16_t h) {
    const uint32_t sign = static_cast<uint32_t>(h & 0x8000u) << 16;
    const uint32_t exp = (h >> 10) & 0x1fu;
    const uint32_t frac = h & 0x03ffu;
    uint32_t bits;
    if (exp == 0) {
        if (frac == 0) {
            bits = sign;
        } else {
            uint32_t normalized = frac;
            int shift = 0;
            while ((normalized & 0x0400u) == 0) {
                normalized <<= 1;
                ++shift;
            }
            normalized &= 0x03ffu;
            bits = sign | (static_cast<uint32_t>(113 - shift) << 23) |
                   (normalized << 13);
        }
    } else if (exp == 0x1fu) {
        bits = sign | 0x7f800000u | (frac << 13);
    } else {
        bits = sign | ((exp + 112u) << 23) | (frac << 13);
    }
    float value;
    static_assert(sizeof(value) == sizeof(bits));
    __builtin_memcpy(&value, &bits, sizeof(value));
    return value;
}

inline float f32_mul(float a, float b) { return a * b; }
inline float f32_add(float a, float b) { return a + b; }

struct Metrics {
    double max_abs = 0.0;
    double sum_sq = 0.0;
    double dot = 0.0;
    double norm_got = 0.0;
    double norm_ref = 0.0;
    uint64_t count = 0;

    void add(float got, float ref) {
        const double err = static_cast<double>(got) - static_cast<double>(ref);
        max_abs = std::max(max_abs, std::fabs(err));
        sum_sq += err * err;
        dot += static_cast<double>(got) * ref;
        norm_got += static_cast<double>(got) * got;
        norm_ref += static_cast<double>(ref) * ref;
        ++count;
    }

    double rmse() const { return std::sqrt(sum_sq / static_cast<double>(count)); }
    double cosine() const { return dot / std::sqrt(norm_got * norm_ref); }
    bool passes() const {
        return std::isfinite(max_abs) && std::isfinite(rmse()) && std::isfinite(cosine()) &&
               max_abs <= 1.0e-3 && rmse() <= 1.0e-4 && cosine() >= 0.999;
    }
};

float rm10_issue4_interleave10_tree(const float (&acc)[10]) {
    const float t0 = f32_add(acc[0], acc[1]);
    const float t1 = f32_add(acc[2], acc[3]);
    const float t2 = f32_add(acc[4], acc[5]);
    const float t3 = f32_add(acc[6], acc[7]);
    const float t4 = f32_add(acc[8], acc[9]);
    return f32_add(f32_add(f32_add(t0, t1), f32_add(t2, t3)), t4);
}
} // namespace

int main(int argc, char **argv) {
    if (argc != 3) {
        std::fprintf(stderr, "usage: up_numeric_probe TENSOR_DIR OUTPUT_DIR\n");
        return 2;
    }
    const std::string tensor_dir = argv[1];
    const std::string output_dir = argv[2];
    std::ofstream summary(output_dir + "/summary.csv");
    summary << "layer,K,M,N,count,max_abs,rmse,cosine,gate\n"
            << std::scientific << std::setprecision(17);
    bool all_pass = true;

    for (size_t li = 0; li < LAYERS.size(); ++li) {
        const std::string layer = LAYERS[li];
        const std::string prefix = tensor_dir + "/" + layer;
        const int n = NS[li];
        std::vector<uint16_t> weights(static_cast<size_t>(M) * K);
        std::vector<float> activations(static_cast<size_t>(n) * K);
        std::vector<float> reference(static_cast<size_t>(n) * M);
        if (!read_exact(prefix + ".weight.f16", weights.data(), weights.size() * sizeof(weights[0])) ||
            !read_exact(prefix + ".activation.f32", activations.data(), activations.size() * sizeof(activations[0])) ||
            !read_exact(prefix + ".output.f32", reference.data(), reference.size() * sizeof(reference[0]))) {
            std::fprintf(stderr, "%s: missing, truncated, or oversized W/X/Y payload\n", layer.c_str());
            return 3;
        }

        std::vector<float> output(reference.size());
        const int total = n * M;
#if defined(_OPENMP)
#pragma omp parallel for schedule(static)
#endif
        for (int oi = 0; oi < total; ++oi) {
            const int row = oi / M;
            const int col = oi % M;
            const size_t woff = static_cast<size_t>(col) * K;
            const size_t xoff = static_cast<size_t>(row) * K;
            float accum[10] = {};
            for (int group = 0; group < K / 4; ++group) {
                float product[4];
                for (int q = 0; q < 4; ++q) {
                    const int k = group * 4 + q;
                    product[q] = f32_mul(half_to_float(weights[woff + k]), activations[xoff + k]);
                }
                const float pair0 = f32_add(product[0], product[1]);
                const float pair1 = f32_add(product[2], product[3]);
                const float chunk = f32_add(pair0, pair1);
                const int bank = group % 10;
                accum[bank] = f32_add(accum[bank], chunk);
            }
            output[oi] = rm10_issue4_interleave10_tree(accum);
        }

        Metrics m;
        for (size_t oi = 0; oi < reference.size(); ++oi) m.add(output[oi], reference[oi]);
        const char * gate = m.passes() ? "PASS" : "FAIL";
        summary << layer << ',' << K << ',' << M << ',' << n << ',' << m.count << ','
                << m.max_abs << ',' << m.rmse() << ',' << m.cosine() << ',' << gate << '\n';
        std::fprintf(stderr, "numeric layer=%s K=%d M=%d N=%d count=%llu max_abs=%.9g RMSE=%.9g cosine=%.15f gate=%s\n",
                     layer.c_str(), K, M, n, static_cast<unsigned long long>(m.count),
                     m.max_abs, m.rmse(), m.cosine(), gate);
        all_pass = all_pass && m.passes();
    }
    return all_pass ? 0 : 1;
}
