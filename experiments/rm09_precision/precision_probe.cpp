#include <algorithm>
#include <array>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

#if defined(_OPENMP)
#include <omp.h>
#endif

namespace {
constexpr int K = 4304;
constexpr int M = 1152;
constexpr int LANES = 16;
constexpr float REL_DENOM_MIN = 1.0e-4f;

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
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

uint16_t float_to_half(float f) {
    uint32_t bits;
    std::memcpy(&bits, &f, sizeof(bits));
    const uint32_t sign = (bits >> 16) & 0x8000u;
    const uint32_t exp = (bits >> 23) & 0xffu;
    const uint32_t frac = bits & 0x7fffffu;
    if (exp == 0xffu) {
        return static_cast<uint16_t>(sign | 0x7c00u | (frac ? 0x0200u : 0u));
    }
    int32_t half_exp = static_cast<int32_t>(exp) - 127 + 15;
    if (half_exp >= 31) return static_cast<uint16_t>(sign | 0x7c00u);
    if (half_exp <= 0) {
        if (half_exp < -10) return static_cast<uint16_t>(sign);
        uint32_t mant = frac | 0x800000u;
        const int shift = 14 - half_exp;
        uint32_t out = mant >> shift;
        const uint32_t rem = mant & ((1u << shift) - 1u);
        const uint32_t halfway = 1u << (shift - 1);
        if (rem > halfway || (rem == halfway && (out & 1u))) ++out;
        return static_cast<uint16_t>(sign | out);
    }
    uint32_t out = (static_cast<uint32_t>(half_exp) << 10) | (frac >> 13);
    const uint32_t rem = frac & 0x1fffu;
    if (rem > 0x1000u || (rem == 0x1000u && (out & 1u))) ++out;
    return static_cast<uint16_t>(sign | out);
}

uint16_t float_to_bfloat16(float f) {
    uint32_t bits;
    std::memcpy(&bits, &f, sizeof(bits));
    // Round to nearest, ties to even using the discarded low 16 bits.
    bits += 0x7fffu + ((bits >> 16) & 1u);
    return static_cast<uint16_t>(bits >> 16);
}

float bfloat16_to_float(uint16_t b) {
    const uint32_t bits = static_cast<uint32_t>(b) << 16;
    float value;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

double sorted_quantile(const std::vector<double> &values, double q) {
    if (values.empty()) return 0.0;
    const size_t idx = static_cast<size_t>(std::floor(q * (values.size() - 1)));
    return values[idx];
}

struct Metrics {
    double max_abs = 0.0;
    double sum_sq = 0.0;
    double dot = 0.0;
    double norm_got = 0.0;
    double norm_ref = 0.0;
    double near_zero_sum_sq = 0.0;
    double near_zero_max_abs = 0.0;
    double delta_p0_sum_sq = 0.0;
    double delta_p0_max_abs = 0.0;
    size_t count = 0;
    size_t near_zero_count = 0;
    std::vector<double> relative;
    std::vector<double> abs_reference;

    void add(float got, float ref, float p0_got) {
        const double err = static_cast<double>(got) - static_cast<double>(ref);
        const double abs_err = std::fabs(err);
        const double delta_p0 = static_cast<double>(got) - p0_got;
        max_abs = std::max(max_abs, abs_err);
        sum_sq += err * err;
        delta_p0_max_abs = std::max(delta_p0_max_abs, std::fabs(delta_p0));
        delta_p0_sum_sq += delta_p0 * delta_p0;
        dot += static_cast<double>(got) * ref;
        norm_got += static_cast<double>(got) * got;
        norm_ref += static_cast<double>(ref) * ref;
        ++count;
        abs_reference.push_back(std::fabs(static_cast<double>(ref)));
        if (std::fabs(ref) < REL_DENOM_MIN) {
            ++near_zero_count;
            near_zero_sum_sq += err * err;
            near_zero_max_abs = std::max(near_zero_max_abs, abs_err);
        } else {
            relative.push_back(abs_err / std::fabs(static_cast<double>(ref)));
        }
    }

    double quantile(double q) {
        if (relative.empty()) return NAN;
        const size_t idx = static_cast<size_t>(std::floor(q * (relative.size() - 1)));
        return relative[idx];
    }

    void print(const char *candidate, const char *layer, int n) {
        std::sort(relative.begin(), relative.end());
        std::sort(abs_reference.begin(), abs_reference.end());
        const double rmse = std::sqrt(sum_sq / static_cast<double>(count));
        const double delta_p0_rmse = std::sqrt(delta_p0_sum_sq / static_cast<double>(count));
        const double cosine = dot / std::sqrt(norm_got * norm_ref);
        const double near_rmse = near_zero_count
            ? std::sqrt(near_zero_sum_sq / static_cast<double>(near_zero_count)) : 0.0;
        std::printf("%s,%s,%d,%d,%d,%zu,%.9g,%.9g,%.15g,%.9g,%.9g,%zu,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g\n",
                    candidate, layer, K, M, n, count, max_abs, rmse, cosine,
                    delta_p0_max_abs, delta_p0_rmse,
                    near_zero_count, near_rmse, near_zero_max_abs,
                    quantile(0.50), quantile(0.90), quantile(0.99),
                    relative.empty() ? NAN : relative.back(),
                    abs_reference[abs_reference.size() / 2],
                    abs_reference[static_cast<size_t>(0.90 * (abs_reference.size() - 1))],
                    abs_reference[static_cast<size_t>(0.99 * (abs_reference.size() - 1))]);
    }
};

enum class Mode { P0_F16_F32, P1_F16_F16, P2_BF16_BF16, P3_F16_PRODUCT_F16_ACC };

const char *mode_name(Mode mode) {
    switch (mode) {
        case Mode::P0_F16_F32: return "P0_F16W_F32X_F32ACC_K16";
        case Mode::P1_F16_F16: return "P1_F16W_F16X_F32ACC_K16";
        case Mode::P2_BF16_BF16: return "P2_BF16W_BF16X_F32ACC_K16";
        case Mode::P3_F16_PRODUCT_F16_ACC: return "P3_F16_PRODUCT_F16ACC16_INTERLEAVED";
    }
    return "unknown";
}

std::vector<float> run_candidate(Mode mode, const std::vector<uint16_t> &w16,
                   const std::vector<float> &x32, const std::vector<float> &ref,
                   const char *layer, int n, const std::vector<float> *p0_got = nullptr) {
    const size_t out_count = static_cast<size_t>(n) * M;
    Metrics metrics;
    metrics.relative.reserve(out_count);
    auto start = std::chrono::steady_clock::now();

    // Quantize outside the dot-product loop. The P0 schedule mirrors RM07's
    // 16 interleaved FP32 accumulators and ordered FP32 final reduction.
    std::vector<float> wf(static_cast<size_t>(M) * K);
    std::vector<float> xf(static_cast<size_t>(n) * K);
    std::vector<uint16_t> wh(static_cast<size_t>(M) * K);
    std::vector<uint16_t> xh(static_cast<size_t>(n) * K);
    std::vector<uint16_t> wb(static_cast<size_t>(M) * K);
    std::vector<uint16_t> xb(static_cast<size_t>(n) * K);

    for (size_t i = 0; i < wf.size(); ++i) {
        if (mode == Mode::P2_BF16_BF16) {
            wb[i] = float_to_bfloat16(half_to_float(w16[i]));
            wf[i] = bfloat16_to_float(wb[i]);
        } else {
            wf[i] = half_to_float(w16[i]);
            if (mode == Mode::P3_F16_PRODUCT_F16_ACC) wh[i] = w16[i];
        }
    }
    for (size_t i = 0; i < xf.size(); ++i) {
        if (mode == Mode::P1_F16_F16 || mode == Mode::P3_F16_PRODUCT_F16_ACC) {
            xh[i] = float_to_half(x32[i]);
            xf[i] = half_to_float(xh[i]);
        } else if (mode == Mode::P2_BF16_BF16) {
            xb[i] = float_to_bfloat16(x32[i]);
            xf[i] = bfloat16_to_float(xb[i]);
        } else {
            xf[i] = x32[i];
        }
    }

    std::vector<float> got(out_count);
    const int total = n * M;
#if defined(_OPENMP)
#pragma omp parallel for schedule(static)
#endif
    for (int oi = 0; oi < total; ++oi) {
        const int row = oi / M;
        const int col = oi % M;
        if (mode == Mode::P3_F16_PRODUCT_F16_ACC) {
            std::array<uint16_t, LANES> acc{};
            for (int kbase = 0; kbase < K; kbase += LANES) {
                for (int lane = 0; lane < LANES; ++lane) {
                    const int k = kbase + lane;
                    const float w = half_to_float(wh[static_cast<size_t>(col) * K + k]);
                    const float x = half_to_float(xh[static_cast<size_t>(row) * K + k]);
                    const uint16_t product = float_to_half(w * x);
                    const float updated = half_to_float(acc[lane]) + half_to_float(product);
                    acc[lane] = float_to_half(updated);
                }
            }
            float sum = 0.0f;
            for (int lane = 0; lane < LANES; ++lane) sum += half_to_float(acc[lane]);
            got[static_cast<size_t>(oi)] = sum;
        } else {
            std::array<float, LANES> acc{};
            const size_t woff = static_cast<size_t>(col) * K;
            const size_t xoff = static_cast<size_t>(row) * K;
            for (int kbase = 0; kbase < K; kbase += LANES) {
                for (int lane = 0; lane < LANES; ++lane) {
                    const int k = kbase + lane;
                    acc[lane] += wf[woff + k] * xf[xoff + k];
                }
            }
            float sum = 0.0f;
            for (int lane = 0; lane < LANES; ++lane) sum += acc[lane];
            got[static_cast<size_t>(oi)] = sum;
        }
    }

    for (size_t i = 0; i < out_count; ++i) {
        metrics.add(got[i], ref[i], p0_got ? (*p0_got)[i] : got[i]);
    }
    const auto elapsed = std::chrono::duration<double>(std::chrono::steady_clock::now() - start).count();
    metrics.print(mode_name(mode), layer, n);
    std::fprintf(stderr, "candidate_done=%s layer=%s seconds=%.3f\n", mode_name(mode), layer, elapsed);
    return got;
}
} // namespace

int main(int argc, char **argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: precision_probe TENSOR_DIR\n");
        return 2;
    }
    const std::string dir = argv[1];
    std::puts("candidate,layer,K,M,N,count,max_abs,rmse,cosine,delta_vs_p0_max_abs,delta_vs_p0_rmse,small_ref_lt_1e-4_count,small_ref_rmse,small_ref_max_abs,rel_abs_q50_ref_ge_1e-4,rel_abs_q90_ref_ge_1e-4,rel_abs_q99_ref_ge_1e-4,rel_abs_max_ref_ge_1e-4,ref_abs_q50,ref_abs_q90,ref_abs_q99");
    for (const char *layer : {"ffn_down-0", "ffn_down-13", "ffn_down-26"}) {
        const int n = std::string(layer) == "ffn_down-0" ? 1120 : 280;
        const std::string prefix = dir + "/" + layer;
        std::vector<uint16_t> w(static_cast<size_t>(M) * K);
        std::vector<float> x(static_cast<size_t>(n) * K);
        std::vector<float> ref(static_cast<size_t>(n) * M);
        if (!read_exact(prefix + ".weight.f16", w.data(), w.size() * sizeof(w[0])) ||
            !read_exact(prefix + ".activation.f32", x.data(), x.size() * sizeof(x[0])) ||
            !read_exact(prefix + ".output.f32", ref.data(), ref.size() * sizeof(ref[0]))) {
            std::fprintf(stderr, "%s: missing or truncated W/X/Y payload\n", layer);
            return 3;
        }

        double x_f16_sq = 0.0, x_bf16_sq = 0.0, w_bf16_sq = 0.0;
        double x_f16_max = 0.0, x_bf16_max = 0.0, w_bf16_max = 0.0;
        size_t x_f16_changed = 0, x_bf16_changed = 0, w_bf16_changed = 0;
        float x_min = INFINITY, x_max = -INFINITY;
        std::vector<double> x_abs;
        std::vector<double> x_f16_nonzero_errors;
        std::vector<double> x_bf16_nonzero_errors;
        x_abs.reserve(x.size());
        x_f16_nonzero_errors.reserve(100000);
        x_bf16_nonzero_errors.reserve(x.size());
        for (float value : x) {
            const double e16 = static_cast<double>(half_to_float(float_to_half(value))) - value;
            const double ebf = static_cast<double>(bfloat16_to_float(float_to_bfloat16(value))) - value;
            x_min = std::min(x_min, value);
            x_max = std::max(x_max, value);
            x_abs.push_back(std::fabs(static_cast<double>(value)));
            x_f16_sq += e16 * e16;
            x_bf16_sq += ebf * ebf;
            x_f16_max = std::max(x_f16_max, std::fabs(e16));
            x_bf16_max = std::max(x_bf16_max, std::fabs(ebf));
            x_f16_changed += e16 != 0.0;
            x_bf16_changed += ebf != 0.0;
            if (e16 != 0.0) x_f16_nonzero_errors.push_back(std::fabs(e16));
            if (ebf != 0.0) x_bf16_nonzero_errors.push_back(std::fabs(ebf));
        }
        std::sort(x_abs.begin(), x_abs.end());
        std::sort(x_f16_nonzero_errors.begin(), x_f16_nonzero_errors.end());
        std::sort(x_bf16_nonzero_errors.begin(), x_bf16_nonzero_errors.end());
        for (uint16_t value : w) {
            const float f = half_to_float(value);
            const double ebf = static_cast<double>(bfloat16_to_float(float_to_bfloat16(f))) - f;
            w_bf16_sq += ebf * ebf;
            w_bf16_max = std::max(w_bf16_max, std::fabs(ebf));
            w_bf16_changed += ebf != 0.0;
        }
        std::fprintf(stderr,
                     "input_quant,layer=%s,x_count=%zu,x_min=%.9g,x_max=%.9g,x_abs_q50=%.9g,x_abs_q90=%.9g,x_abs_q99=%.9g,x_abs_max=%.9g,x_f16_changed=%zu,x_f16_changed_pct=%.9g,x_f16_rmse=%.9g,x_f16_max_abs=%.9g,x_f16_err_changed_q50=%.9g,x_f16_err_changed_q90=%.9g,x_f16_err_changed_q99=%.9g,x_bf16_changed=%zu,x_bf16_changed_pct=%.9g,x_bf16_rmse=%.9g,x_bf16_max_abs=%.9g,x_bf16_err_changed_q99=%.9g,w_count=%zu,w_bf16_changed=%zu,w_bf16_max_abs=%.9g,w_bf16_rmse=%.9g\n",
                     layer, x.size(), x_min, x_max,
                     sorted_quantile(x_abs, 0.50), sorted_quantile(x_abs, 0.90),
                     sorted_quantile(x_abs, 0.99), x_abs.back(),
                     x_f16_changed, 100.0 * x_f16_changed / x.size(),
                     std::sqrt(x_f16_sq / x.size()), x_f16_max,
                     sorted_quantile(x_f16_nonzero_errors, 0.50),
                     sorted_quantile(x_f16_nonzero_errors, 0.90),
                     sorted_quantile(x_f16_nonzero_errors, 0.99),
                     x_bf16_changed, 100.0 * x_bf16_changed / x.size(),
                     std::sqrt(x_bf16_sq / x.size()), x_bf16_max,
                     sorted_quantile(x_bf16_nonzero_errors, 0.99),
                     w.size(), w_bf16_changed,
                     w_bf16_max, std::sqrt(w_bf16_sq / w.size()));

        const std::vector<float> p0_got = run_candidate(Mode::P0_F16_F32, w, x, ref, layer, n);
        run_candidate(Mode::P1_F16_F16, w, x, ref, layer, n, &p0_got);
        run_candidate(Mode::P2_BF16_BF16, w, x, ref, layer, n, &p0_got);
        run_candidate(Mode::P3_F16_PRODUCT_F16_ACC, w, x, ref, layer, n, &p0_got);
    }
    return 0;
}
