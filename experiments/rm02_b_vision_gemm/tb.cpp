#include "vision_gemm.hpp"

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <vector>

static float ref_half_to_float(std::uint16_t h) {
    const std::uint32_t sign = (static_cast<std::uint32_t>(h & 0x8000u)) << 16;
    const std::uint32_t exp = (h >> 10) & 0x1fu;
    const std::uint32_t frac = h & 0x03ffu;
    std::uint32_t bits;
    if (exp == 0) {
        if (frac == 0) {
            bits = sign;
        } else {
            unsigned normalized = frac;
            int shift = 0;
            while ((normalized & 0x0400u) == 0) {
                normalized <<= 1;
                ++shift;
            }
            normalized &= 0x03ffu;
            bits = sign | (static_cast<std::uint32_t>(113 - shift) << 23) |
                   (normalized << 13);
        }
    } else if (exp == 0x1fu) {
        bits = sign | 0x7f800000u | (frac << 13);
    } else {
        bits = sign | ((exp + 112u) << 23) | (frac << 13);
    }
    union {
        std::uint32_t u;
        float f;
    } value;
    value.u = bits;
    return value.f;
}

int main() {
    constexpr int m0 = 32;
    constexpr int n0 = 64;
    std::vector<ap_uint<128>> w(W_WORDS, 0);
    std::vector<ap_uint<256>> x(X_WORDS, 0);
    std::vector<ap_uint<256>> y(Y_WORDS, 0);

    const std::uint16_t half_values[] = {
        0xB400, 0xB000, 0xAC00, 0x0000, 0x2C00, 0x3000, 0x3400,
        0xA800, 0x2800, 0x3800, 0xBC00, 0x3C00, 0xC000};
    for (int m = 0; m < MACRO_M; ++m) {
        for (int k = 0; k < VLM_K; ++k) {
            const std::uint16_t value =
                half_values[(m * 7 + k * 3) % (sizeof(half_values) / sizeof(half_values[0]))];
            const std::size_t idx = static_cast<std::size_t>(m0 + m) * VLM_K + k;
            w[idx / PACK].range((idx % PACK) * 16 + 15, (idx % PACK) * 16) = value;
        }
    }
    for (int n = 0; n < MACRO_N; ++n) {
        for (int k = 0; k < VLM_K; ++k) {
            const int q = ((n * 11 + k * 5) % 65) - 32;
            const float value =
                static_cast<float>(q) * (1.0f / 128.0f);
            union { float f; std::uint32_t u; } bits;
            bits.f = value;
            const std::size_t idx = static_cast<std::size_t>(n0 + n) * VLM_K + k;
            x[idx / PACK].range((idx % PACK) * 32 + 31, (idx % PACK) * 32) = bits.u;
        }
    }

    vision_macro_tile(w.data(), x.data(), y.data(), m0, n0);

    double max_abs = 0.0;
    double max_rel = 0.0;
    int bad = 0;
    for (int n = 0; n < MACRO_N; ++n) {
        for (int m = 0; m < MACRO_M; ++m) {
            float golden = 0.0f;
            for (int k = 0; k < VLM_K; ++k) {
                const std::size_t wi = static_cast<std::size_t>(m0 + m) * VLM_K + k;
                const std::size_t xi = static_cast<std::size_t>(n0 + n) * VLM_K + k;
                const std::uint16_t wbits = static_cast<std::uint16_t>(
                    w[wi / PACK].range((wi % PACK) * 16 + 15, (wi % PACK) * 16).to_uint());
                const std::uint32_t xbits = x[xi / PACK]
                    .range((xi % PACK) * 32 + 31, (xi % PACK) * 32).to_uint();
                union { std::uint32_t u; float f; } xvalue;
                xvalue.u = xbits;
                const float product = ref_half_to_float(wbits) * xvalue.f;
                golden = golden + product;
            }
            const std::size_t yi = static_cast<std::size_t>(n0 + n) * VLM_OUT + m0 + m;
            const std::uint32_t ybits = y[yi / PACK]
                .range((yi % PACK) * 32 + 31, (yi % PACK) * 32).to_uint();
            union { std::uint32_t u; float f; } yvalue;
            yvalue.u = ybits;
            const float actual = yvalue.f;
            const double abs_error = std::fabs(static_cast<double>(actual) - golden);
            const double rel_error = abs_error / (std::fabs(static_cast<double>(golden)) + 1e-6);
            if (abs_error > max_abs) max_abs = abs_error;
            if (rel_error > max_rel) max_rel = rel_error;
            if (abs_error > 1e-3 + 5e-5 * std::fabs(static_cast<double>(golden))) {
                if (bad < 8) {
                    std::fprintf(stderr,
                                 "mismatch m=%d n=%d golden=%.9g actual=%.9g abs=%.4g\n",
                                 m0 + m, n0 + n, golden, actual, abs_error);
                }
                ++bad;
            }
        }
    }
    std::printf("C-SIM_TILE_PASS reduction=%d tokens=%d outputs=%d tile=%dx%d pe=%dx%d "
                "outputs=%d max_abs_error=%.9g max_rel_error=%.9g\n",
                VLM_K, VLM_N, VLM_OUT, MACRO_M, MACRO_N, PE_M, PE_N,
                MACRO_M * MACRO_N, max_abs, max_rel);
    if (bad != 0) {
        std::fprintf(stderr, "C-SIM_TILE_FAIL bad=%d\n", bad);
        return 1;
    }
    return 0;
}
