#include "vision_gemm.hpp"

#include <cstdint>

namespace {
float half_to_float(std::uint16_t h) {
#pragma HLS INLINE
    const std::uint32_t sign = (static_cast<std::uint32_t>(h & 0x8000u)) << 16;
    const std::uint32_t exp = (h >> 10) & 0x1fu;
    const std::uint32_t frac = h & 0x03ffu;
    std::uint32_t bits;
    if (exp == 0) {
        if (frac == 0) {
            bits = sign;
        } else {
            std::uint32_t normalized = frac;
            int shift = 0;
            for (int step = 0; step < 10; ++step) {
#pragma HLS UNROLL
                if ((normalized & 0x0400u) == 0) {
                    normalized <<= 1;
                    ++shift;
                }
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
} // namespace

void vision_macro_tile(const ap_uint<128> *weights_f16_packed,
                       const ap_uint<256> *activations_f32_packed,
                       ap_uint<256> *output_f32_packed,
                       int output_row_base,
                       int token_base) {
#pragma HLS INLINE
    // Full-K macro-tile buffers are distributed as four banks along the PE
    // dimensions. Both candidate and baseline hold the same number of FP32
    // values locally (206,592 = 826,368 bytes).
    ap_uint<128> weight_tile[PE_M][MACRO_M / PE_M][K_WORDS];
    ap_uint<256> activation_tile[PE_N][MACRO_N / PE_N][K_WORDS];
    float result_tile[MACRO_N][MACRO_M];
#pragma HLS ARRAY_PARTITION variable=weight_tile complete dim=1
#pragma HLS ARRAY_PARTITION variable=activation_tile complete dim=1
#pragma HLS BIND_STORAGE variable=weight_tile type=ram_2p impl=uram
#pragma HLS BIND_STORAGE variable=activation_tile type=ram_2p impl=uram
#pragma HLS BIND_STORAGE variable=result_tile type=ram_2p impl=bram

    // Read contiguous source rows. Binary16 weights are expanded exactly to
    // binary32 when consumed; activations and partial sums remain binary32.
    for (int m = 0; m < MACRO_M; ++m) {
        for (int kw = 0; kw < K_WORDS; ++kw) {
#pragma HLS PIPELINE II=1
            const int src = (output_row_base + m) * K_WORDS + kw;
            weight_tile[m % PE_M][m / PE_M][kw] = weights_f16_packed[src];
        }
    }
    for (int n = 0; n < MACRO_N; ++n) {
        for (int kw = 0; kw < K_WORDS; ++kw) {
#pragma HLS PIPELINE II=1
            const int src = (token_base + n) * K_WORDS + kw;
            activation_tile[n % PE_N][n / PE_N][kw] = activations_f32_packed[src];
        }
    }

    // Fixed PE group. K is traversed in compile-time lane groups so each
    // accumulator bank is addressed by a constant unrolled lane index.
    for (int mb = 0; mb < MACRO_M; mb += PE_M) {
        for (int nb = 0; nb < MACRO_N; nb += PE_N) {
#ifdef HLS_DYNAMIC_PARTIAL
            float accum[PE_M][PE_N][8];
#pragma HLS ARRAY_PARTITION variable=accum complete dim=0
            for (int i = 0; i < PE_M; ++i) {
#pragma HLS UNROLL
                for (int j = 0; j < PE_N; ++j) {
#pragma HLS UNROLL
                    for (int p = 0; p < 8; ++p) {
#pragma HLS UNROLL
                        accum[i][j][p] = 0.0f;
                    }
                }
            }
#ifdef HLS_NO_FLATTEN
#pragma HLS LOOP_FLATTEN off
#endif
            for (int k = 0; k < VLM_K; ++k) {
#pragma HLS PIPELINE II=1
                const int partial = k & 7;
                const int word = k >> 3;
                const int lane = k & 7;
                for (int i = 0; i < PE_M; ++i) {
#pragma HLS UNROLL
                    const std::uint16_t wbits = static_cast<std::uint16_t>(
                        weight_tile[i][mb / PE_M][word]
                            .range(lane * 16 + 15, lane * 16).to_uint());
                    const float wvalue = half_to_float(wbits);
                    for (int j = 0; j < PE_N; ++j) {
#pragma HLS UNROLL
                        const std::uint32_t xbits = activation_tile[j][nb / PE_N][word]
                            .range(lane * 32 + 31, lane * 32).to_uint();
                        union { std::uint32_t u; float f; } xvalue;
                        xvalue.u = xbits;
                        accum[i][j][partial] += wvalue * xvalue.f;
                    }
                }
            }
            for (int i = 0; i < PE_M; ++i) {
#pragma HLS UNROLL
                for (int j = 0; j < PE_N; ++j) {
#pragma HLS UNROLL
                    float sum = 0.0f;
                    for (int p = 0; p < 8; ++p) {
#pragma HLS UNROLL
                        sum += accum[i][j][p];
                    }
                    result_tile[nb + j][mb + i] = sum;
                }
            }
#else
            float accum[PE_M][PE_N][K_LANES];
#pragma HLS ARRAY_PARTITION variable=accum complete dim=0
            for (int i = 0; i < PE_M; ++i) {
#pragma HLS UNROLL
                for (int j = 0; j < PE_N; ++j) {
#pragma HLS UNROLL
                    for (int p = 0; p < K_LANES; ++p) {
#pragma HLS UNROLL
                        accum[i][j][p] = 0.0f;
                    }
                }
            }
#ifdef HLS_NO_FLATTEN
#pragma HLS LOOP_FLATTEN off
#endif
            for (int kbase = 0; kbase < VLM_K; kbase += K_LANES) {
#pragma HLS PIPELINE II=1
                for (int i = 0; i < PE_M; ++i) {
#pragma HLS UNROLL
                    for (int j = 0; j < PE_N; ++j) {
#pragma HLS UNROLL
                        for (int p = 0; p < K_LANES; ++p) {
#pragma HLS UNROLL
                            const int k = kbase + p;
                            const int word = k >> 3;
                            const int lane = k & 7;
                            const std::uint16_t wbits = static_cast<std::uint16_t>(
                                weight_tile[i][mb / PE_M][word]
                                    .range(lane * 16 + 15, lane * 16).to_uint());
                            const float wvalue = half_to_float(wbits);
                            const std::uint32_t xbits = activation_tile[j][nb / PE_N][word]
                                .range(lane * 32 + 31, lane * 32).to_uint();
                            union { std::uint32_t u; float f; } xvalue;
                            xvalue.u = xbits;
                            accum[i][j][p] += wvalue * xvalue.f;
                        }
                    }
                }
            }
            for (int i = 0; i < PE_M; ++i) {
#pragma HLS UNROLL
                for (int j = 0; j < PE_N; ++j) {
#pragma HLS UNROLL
                    float sum = 0.0f;
                    for (int p = 0; p < K_LANES; ++p) {
#pragma HLS UNROLL
                        sum += accum[i][j][p];
                    }
                    result_tile[nb + j][mb + i] = sum;
                }
            }
#endif
        }
    }

    // Pack-friendly contiguous output rows, enabling burst inference and
    // widening on the m_axi output port.
    for (int n = 0; n < MACRO_N; ++n) {
        for (int m = 0; m < MACRO_M; m += PACK) {
#pragma HLS PIPELINE II=1
            ap_uint<256> packed = 0;
            for (int lane = 0; lane < PACK; ++lane) {
#pragma HLS UNROLL
                union { float f; std::uint32_t u; } bits;
                bits.f = result_tile[n][m + lane];
                packed.range(lane * 32 + 31, lane * 32) = bits.u;
            }
            const int dst = ((token_base + n) * VLM_OUT + output_row_base + m) / PACK;
            output_f32_packed[dst] = packed;
        }
    }
}

extern "C" void vision_gemm(const ap_uint<128> *weights_f16_packed,
                            const ap_uint<256> *activations_f32_packed,
                            ap_uint<256> *output_f32_packed) {
#pragma HLS INTERFACE m_axi port=weights_f16_packed offset=slave bundle=gmem_w depth=W_WORDS max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=activations_f32_packed offset=slave bundle=gmem_x depth=X_WORDS max_read_burst_length=64 num_read_outstanding=16
#pragma HLS INTERFACE m_axi port=output_f32_packed offset=slave bundle=gmem_y depth=Y_WORDS max_write_burst_length=64 num_write_outstanding=16
#pragma HLS INTERFACE s_axilite port=weights_f16_packed bundle=control
#pragma HLS INTERFACE s_axilite port=activations_f32_packed bundle=control
#pragma HLS INTERFACE s_axilite port=output_f32_packed bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control

    for (int m0 = 0; m0 < VLM_OUT; m0 += MACRO_M) {
        for (int n0 = 0; n0 < VLM_N; n0 += MACRO_N) {
            vision_macro_tile(weights_f16_packed, activations_f32_packed,
                              output_f32_packed, m0, n0);
        }
    }
}
