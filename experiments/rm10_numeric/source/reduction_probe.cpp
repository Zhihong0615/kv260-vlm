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
constexpr int K = 4304;
constexpr int M = 1152;
constexpr std::array<int, 4> BOUNDS = {0, 1088, 2176, 3264};
constexpr std::array<double, 9> ABS_EDGES = {
    0.0, 1.0e-8, 1.0e-7, 1.0e-6, 1.0e-5,
    1.0e-4, 1.0e-3, 1.0e-2, INFINITY};
constexpr std::array<const char *, 8> ABS_LABELS = {
    "0_to_1e-8", "1e-8_to_1e-7", "1e-7_to_1e-6", "1e-6_to_1e-5",
    "1e-5_to_1e-4", "1e-4_to_1e-3", "1e-3_to_1e-2", "1e-2_to_inf"};
constexpr std::array<const char *, 3> CANDIDATES = {"A_interleave_R5", "B_split4_aligned", "C_hybrid_R5_tree"};

bool read_exact(const std::string &path, void *dst, size_t bytes) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return false;
    in.read(static_cast<char *>(dst), static_cast<std::streamsize>(bytes));
    return static_cast<size_t>(in.gcount()) == bytes;
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
            bits = sign | (static_cast<uint32_t>(113 - shift) << 23) | (normalized << 13);
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

// Build with -fno-fast-math -ffp-contract=off. These helpers make each HLS
// FP32 multiply/add a separately rounded operation and forbid multiply-add fusion.
inline float f32_mul(float a, float b) { return a * b; }
inline float f32_add(float a, float b) { return a + b; }

struct Metrics {
    double max_abs = 0.0;
    double sum_sq = 0.0;
    double dot = 0.0;
    double norm_got = 0.0;
    double norm_ref = 0.0;
    uint64_t count = 0;
    std::array<uint64_t, 8> abs_hist{};

    void add(float got, float ref) {
        const double err = static_cast<double>(got) - static_cast<double>(ref);
        const double abs_err = std::fabs(err);
        max_abs = std::max(max_abs, abs_err);
        sum_sq += err * err;
        dot += static_cast<double>(got) * ref;
        norm_got += static_cast<double>(got) * got;
        norm_ref += static_cast<double>(ref) * ref;
        ++count;
        const auto it = std::upper_bound(ABS_EDGES.begin(), ABS_EDGES.end(), abs_err);
        const size_t bin = it == ABS_EDGES.begin() ? 0 : std::min<size_t>(7, static_cast<size_t>(it - ABS_EDGES.begin() - 1));
        ++abs_hist[bin];
    }

    double rmse() const { return std::sqrt(sum_sq / static_cast<double>(count)); }
    double cosine() const { return dot / std::sqrt(norm_got * norm_ref); }
    bool passes() const { return max_abs <= 1.0e-3 && rmse() <= 1.0e-4 && cosine() >= 0.999; }
};

float candidate_a(const float (&acc)[16][5]) {
    float lanes[16] = {};
    for (int p = 0; p < 16; ++p) {
        float lane = 0.0f;
        for (int b = 0; b < 5; ++b) lane = f32_add(lane, acc[p][b]);
        lanes[p] = lane;
    }
    float total = 0.0f;
    for (int p = 0; p < 16; ++p) total = f32_add(total, lanes[p]);
    return total;
}

float candidate_c(const float (&acc)[16][5]) {
    float lanes[16] = {};
    for (int p = 0; p < 16; ++p) {
        const float t0 = f32_add(acc[p][0], acc[p][1]);
        const float t1 = f32_add(acc[p][2], acc[p][3]);
        const float t2 = f32_add(t0, t1);
        lanes[p] = f32_add(t2, acc[p][4]);
    }
    float total = 0.0f;
    for (int p = 0; p < 16; ++p) total = f32_add(total, lanes[p]);
    return total;
}

float candidate_b(const float (&acc)[4][16]) {
    float seg[4] = {};
    for (int s = 0; s < 4; ++s) {
        for (int p = 0; p < 16; ++p) seg[s] = f32_add(seg[s], acc[s][p]);
    }
    const float t0 = f32_add(seg[0], seg[1]);
    const float t1 = f32_add(seg[2], seg[3]);
    return f32_add(t0, t1);
}

void write_metrics(const std::string &dir, const std::vector<std::string> &layers,
                   const std::vector<int> &ns, const std::vector<std::array<Metrics, 3>> &all) {
    std::ofstream summary(dir + "/summary.csv");
    summary << std::scientific << std::setprecision(17);
    summary << "layer,K,M,N,count,candidate,max_abs,rmse,cosine,gate\n";
    std::ofstream hist(dir + "/absolute_error_histogram.csv");
    hist << "layer,candidate,abs_error_bin,count\n";
    for (size_t li = 0; li < layers.size(); ++li) {
        for (size_t c = 0; c < CANDIDATES.size(); ++c) {
            const Metrics &m = all[li][c];
            summary << layers[li] << ',' << K << ',' << M << ',' << ns[li] << ',' << m.count << ','
                    << CANDIDATES[c] << ',' << m.max_abs << ',' << m.rmse() << ',' << m.cosine() << ','
                    << (m.passes() ? "PASS" : "FAIL") << '\n';
            for (size_t b = 0; b < m.abs_hist.size(); ++b) {
                hist << layers[li] << ',' << CANDIDATES[c] << ',' << ABS_LABELS[b] << ',' << m.abs_hist[b] << '\n';
            }
        }
    }
}
} // namespace

int main(int argc, char **argv) {
    if (argc != 3) {
        std::fprintf(stderr, "usage: reduction_probe TENSOR_DIR OUTPUT_DIR\n");
        return 2;
    }
    const std::string tensor_dir = argv[1];
    const std::string output_dir = argv[2];
    const std::array<std::string, 3> layers = {"ffn_down-0", "ffn_down-13", "ffn_down-26"};
    const std::array<int, 3> ns = {1120, 280, 280};
    std::vector<std::array<Metrics, 3>> all(layers.size());

    for (size_t li = 0; li < layers.size(); ++li) {
        const std::string prefix = tensor_dir + "/" + layers[li];
        const int n = ns[li];
        std::vector<uint16_t> weights(static_cast<size_t>(M) * K);
        std::vector<float> activations(static_cast<size_t>(n) * K);
        std::vector<float> reference(static_cast<size_t>(n) * M);
        if (!read_exact(prefix + ".weight.f16", weights.data(), weights.size() * sizeof(weights[0])) ||
            !read_exact(prefix + ".activation.f32", activations.data(), activations.size() * sizeof(activations[0])) ||
            !read_exact(prefix + ".output.f32", reference.data(), reference.size() * sizeof(reference[0]))) {
            std::fprintf(stderr, "%s: missing or truncated W/X/Y payload\n", layers[li].c_str());
            return 3;
        }
        std::array<std::vector<float>, 3> output = {
            std::vector<float>(reference.size()), std::vector<float>(reference.size()),
            std::vector<float>(reference.size())};
        const int total = n * M;
#if defined(_OPENMP)
#pragma omp parallel for schedule(static)
#endif
        for (int oi = 0; oi < total; ++oi) {
            const int row = oi / M;
            const int col = oi % M;
            const size_t woff = static_cast<size_t>(col) * K;
            const size_t xoff = static_cast<size_t>(row) * K;
            float a[16][5] = {};
            float b[4][16] = {};
            for (int k = 0; k < K; ++k) {
                const float w = half_to_float(weights[woff + k]);
                const float x = activations[xoff + k];
                const float product = f32_mul(w, x);
                const int p = k & 15;
                const int group = k >> 4;
                a[p][group % 5] = f32_add(a[p][group % 5], product);
                const int segment = k < BOUNDS[1] ? 0 : k < BOUNDS[2] ? 1 : k < BOUNDS[3] ? 2 : 3;
                b[segment][p] = f32_add(b[segment][p], product);
            }
            output[0][oi] = candidate_a(a);
            output[1][oi] = candidate_b(b);
            output[2][oi] = candidate_c(a);
        }
        for (size_t c = 0; c < CANDIDATES.size(); ++c) {
            for (size_t oi = 0; oi < reference.size(); ++oi) all[li][c].add(output[c][oi], reference[oi]);
        }
        std::fprintf(stderr, "completed layer=%s N=%d outputs=%zu\n", layers[li].c_str(), n, reference.size());
    }
    write_metrics(output_dir, std::vector<std::string>(layers.begin(), layers.end()),
                  std::vector<int>(ns.begin(), ns.end()), all);
    return 0;
}
