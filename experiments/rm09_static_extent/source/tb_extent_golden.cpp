#include "vision_ffn_down.hpp"

#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <vector>

namespace {
static constexpr int K_LANES = 16;

std::uint16_t weight_half(int m, int k) {
    int q = (m * 17 + k * 13 + (m * k) % 23) % 31 - 15;
    if (q == 0) q = 1;
    const std::uint16_t sign = q < 0 ? 0x8000u : 0u;
    const int magnitude = q < 0 ? -q : q;
    // IEEE-754 binary16 subnormal: magnitude * 2^-24.
    return static_cast<std::uint16_t>(sign | magnitude);
}

float activation_value(int n, int k) {
    const int q = (n * 7 + k * 11 + (n * k) % 19) % 23 - 11;
    return static_cast<float>(q) * (1.0f / 16.0f);
}

std::uint32_t float_bits(float value) {
    std::uint32_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

float reference_weight(std::uint16_t bits) {
    const float magnitude = static_cast<float>(bits & 0x7fffu) * (1.0f / 16777216.0f);
    return (bits & 0x8000u) ? -magnitude : magnitude;
}

float reference_dot(int m, int n, int n_base) {
    float partial[K_LANES];
    for (int p = 0; p < K_LANES; ++p) partial[p] = 0.0f;
    for (int kbase = 0; kbase < FFN_K; kbase += K_LANES) {
        for (int p = 0; p < K_LANES; ++p) {
            const int k = kbase + p;
            const float w = reference_weight(weight_half(m, k));
            const float x = activation_value(n_base + n, k);
            partial[p] += w * x;
        }
    }
    float sum = 0.0f;
    for (int p = 0; p < K_LANES; ++p) sum += partial[p];
    return sum;
}

bool run_case(int active_n) {
    const int n_base = ((active_n - 1) / TILE_N) * TILE_N;
    const int tile_rows = std::min(TILE_N, active_n - n_base);
    const int m_base = 512;
    std::vector<ap_uint<128>> w(WEIGHT_BATCH_WORDS, 0);
    std::vector<ap_uint<256>> x(ACTIVATION_TILE_WORDS, 0);
    std::vector<ap_uint<256>> y(OUTPUT_BATCH_WORDS, 0);

    for (int mt = 0; mt < M_BATCH; ++mt) {
        for (int kw = 0; kw < K_WORDS; ++kw) {
            ap_uint<128> packed = 0;
            for (int lane = 0; lane < WEIGHT_PACK; ++lane) {
                packed.range(lane * 16 + 15, lane * 16) =
                    weight_half(m_base + mt, kw * WEIGHT_PACK + lane);
            }
            w[mt * K_WORDS + kw] = packed;
        }
    }

    // Fill all 32 rows so a bad tail access is observable in the output check.
    for (int n = 0; n < TILE_N; ++n) {
        for (int kw = 0; kw < K_WORDS; ++kw) {
            ap_uint<256> packed = 0;
            for (int lane = 0; lane < ACTIVATION_PACK; ++lane) {
                const int k = kw * ACTIVATION_PACK + lane;
                packed.range(lane * 32 + 31, lane * 32) =
                    float_bits(activation_value(n_base + n, k));
            }
            x[n * K_WORDS + kw] = packed;
        }
    }

    const float sentinel = 12345.25f;
    ap_uint<256> untouched = 0;
    for (int lane = 0; lane < OUTPUT_PACK; ++lane) {
        untouched.range(lane * 32 + 31, lane * 32) = float_bits(sentinel);
    }
    std::fill(y.begin(), y.end(), untouched);

    int status = vision_ffn_down_tile(w.data(), x.data(), y.data(),
        FFN_STAGE_ACTIVATION, active_n, n_base, 0, tile_rows);
    if (status != 0) {
        std::printf("RM09_STATIC_EXTENT_CSIM_FAIL N=%d task=stage status=%d\n", active_n, status);
        return false;
    }
    status = vision_ffn_down_tile(w.data(), x.data(), y.data(),
        FFN_COMPUTE_WEIGHT_BATCH, active_n, n_base, m_base, tile_rows);
    if (status != 0) {
        std::printf("RM09_STATIC_EXTENT_CSIM_FAIL N=%d task=compute status=%d\n", active_n, status);
        return false;
    }

    std::size_t compared = 0;
    double max_abs = 0.0;
    for (int n = 0; n < TILE_N; ++n) {
        for (int mt = 0; mt < M_BATCH; ++mt) {
            const int batch_tile = mt / TILE_M;
            const int m = mt % TILE_M;
            const int mw = m / OUTPUT_PACK;
            const int lane = m % OUTPUT_PACK;
            const int out_word = batch_tile * OUTPUT_TILE_WORDS +
                                 n * (TILE_M / OUTPUT_PACK) + mw;
            const std::uint32_t got_bits = y[out_word]
                .range(lane * 32 + 31, lane * 32).to_uint();
            if (n >= tile_rows) {
                if (got_bits != float_bits(sentinel)) {
                    std::printf("RM09_STATIC_EXTENT_CSIM_FAIL N=%d padded_row=%d m=%d\n",
                                active_n, n, mt);
                    return false;
                }
                continue;
            }
            const float got = [] (std::uint32_t bits) {
                float value;
                std::memcpy(&value, &bits, sizeof(value));
                return value;
            }(got_bits);
            const float expected = reference_dot(m_base + mt, n, n_base);
            const double error = got > expected ? got - expected : expected - got;
            if (error > max_abs) max_abs = error;
            if (got_bits != float_bits(expected)) {
                std::printf("RM09_STATIC_EXTENT_CSIM_FAIL N=%d n=%d m=%d got=%.9g expected=%.9g\n",
                            active_n, n_base + n, m_base + mt, got, expected);
                return false;
            }
            ++compared;
        }
    }
    std::printf("RM09_STATIC_EXTENT_CSIM_PASS K=%d M=%d N=%d n_base=%d tile_rows=%d "
                "m_base=%d compared=%zu max_abs=%.9g\n",
                FFN_K, FFN_M, active_n, n_base, tile_rows, m_base, compared, max_abs);
    return true;
}

} // namespace

int main() {
    const int shapes[] = {1008, 252, 1056, 264};
    bool ok = true;
    for (int active_n : shapes) ok = run_case(active_n) && ok;

    std::vector<ap_uint<128>> w(WEIGHT_BATCH_WORDS, 0);
    std::vector<ap_uint<256>> x(ACTIVATION_TILE_WORDS, 0);
    std::vector<ap_uint<256>> y(OUTPUT_BATCH_WORDS, 0);
    const int bad_status = vision_ffn_down_tile(w.data(), x.data(), y.data(),
        FFN_STAGE_ACTIVATION, 1006, 992, 0, 14);
    if (bad_status != -1) {
        std::printf("RM09_STATIC_EXTENT_CSIM_FAIL invalid_N=1006 status=%d\n", bad_status);
        ok = false;
    } else {
        std::printf("RM09_STATIC_EXTENT_CSIM_PASS invalid_N=1006 status=-1\n");
    }
    return ok ? 0 : 1;
}
