#include "vision_ffn_down.hpp"

#include <cstdint>

namespace {
static constexpr int PE_M = 4;
static constexpr int PE_N = 4;
static constexpr int K_LANES = 16;

// Persistent on-chip X tile: loaded by one bounded AXI transaction and reused
// across all nine 128-output batches for the same token extent.
static ap_uint<256> activation_cache[TILE_N][K_WORDS];

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

void stage_activation(const ap_uint<256> *src, int tile_rows) {
#pragma HLS INLINE off
    for (int n = 0; n < tile_rows; ++n) {
        for (int kw = 0; kw < K_WORDS; ++kw) {
#pragma HLS PIPELINE II=1
            activation_cache[n][kw] = src[n * K_WORDS + kw];
        }
    }
}

void compute_weight_batch(const ap_uint<128> *weight_batch,
                          ap_uint<256> *output_batch,
                          int tile_rows) {
#pragma HLS INLINE off
    ap_uint<128> weight_cache[TILE_M][K_WORDS];
#pragma HLS ARRAY_PARTITION variable=weight_cache cyclic factor=PE_M dim=1
#pragma HLS BIND_STORAGE variable=weight_cache type=ram_2p impl=uram

    for (int batch_tile = 0; batch_tile < M_TILES_PER_BATCH; ++batch_tile) {
        for (int m = 0; m < TILE_M; ++m) {
            for (int kw = 0; kw < K_WORDS; ++kw) {
#pragma HLS PIPELINE II=1
                const int src = batch_tile * WEIGHT_TILE_WORDS + m * K_WORDS + kw;
                weight_cache[m][kw] = weight_batch[src];
            }
        }

        float result_tile[TILE_N][TILE_M];
#pragma HLS ARRAY_PARTITION variable=result_tile complete dim=2
#pragma HLS BIND_STORAGE variable=result_tile type=ram_2p impl=bram

        for (int n = 0; n < tile_rows; n += PE_N) {
            for (int m = 0; m < TILE_M; m += PE_M) {
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

#pragma HLS LOOP_FLATTEN off
                for (int kbase = 0; kbase < FFN_K; kbase += K_LANES) {
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
                                    weight_cache[m + i][word]
                                        .range(lane * 16 + 15, lane * 16).to_uint());
                                const float wvalue = half_to_float(wbits);
                                const std::uint32_t xbits = activation_cache[n + j][word]
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
                        result_tile[n + j][m + i] = sum;
                    }
                }
            }
        }

        for (int n = 0; n < tile_rows; ++n) {
            for (int mw = 0; mw < TILE_M / OUTPUT_PACK; ++mw) {
#pragma HLS PIPELINE II=1
                ap_uint<256> packed = 0;
                for (int lane = 0; lane < OUTPUT_PACK; ++lane) {
#pragma HLS UNROLL
                    union { float f; std::uint32_t u; } bits;
                    bits.f = result_tile[n][mw * OUTPUT_PACK + lane];
                    packed.range(lane * 32 + 31, lane * 32) = bits.u;
                }
                const int dst = batch_tile * OUTPUT_TILE_WORDS +
                                n * (TILE_M / OUTPUT_PACK) + mw;
                output_batch[dst] = packed;
            }
        }
    }
}
} // namespace

extern "C" int vision_ffn_down_tile(
    const ap_uint<128> *weight_batch_f16,
    const ap_uint<256> *activation_tile_f32,
    ap_uint<256> *output_batch_f32,
    int task,
    int active_N,
    int n_base,
    int m_base,
    int tile_rows) {
#pragma HLS INTERFACE m_axi port=weight_batch_f16 offset=slave bundle=gmem_w depth=WEIGHT_BATCH_WORDS max_read_burst_length=64 num_read_outstanding=8
#pragma HLS INTERFACE m_axi port=activation_tile_f32 offset=slave bundle=gmem_x depth=ACTIVATION_TILE_WORDS max_read_burst_length=64 num_read_outstanding=8
#pragma HLS INTERFACE m_axi port=output_batch_f32 offset=slave bundle=gmem_y depth=OUTPUT_BATCH_WORDS max_write_burst_length=64 num_write_outstanding=8
#pragma HLS INTERFACE s_axilite port=weight_batch_f16 bundle=control
#pragma HLS INTERFACE s_axilite port=activation_tile_f32 bundle=control
#pragma HLS INTERFACE s_axilite port=output_batch_f32 bundle=control
#pragma HLS INTERFACE s_axilite port=task bundle=control
#pragma HLS INTERFACE s_axilite port=active_N bundle=control
#pragma HLS INTERFACE s_axilite port=n_base bundle=control
#pragma HLS INTERFACE s_axilite port=m_base bundle=control
#pragma HLS INTERFACE s_axilite port=tile_rows bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
#pragma HLS ARRAY_PARTITION variable=activation_cache cyclic factor=PE_N dim=1
#pragma HLS BIND_STORAGE variable=activation_cache type=ram_2p impl=uram

    static int cached_active_N = 0;
    static int cached_n_base = -1;
    static int cached_tile_rows = 0;
    static bool cache_valid = false;

    if (active_N != 280 && active_N != 1120) return -1;
    if (n_base < 0 || n_base >= active_N || (n_base % TILE_N) != 0) return -2;
    const int remaining = active_N - n_base;
    const int expected_rows = remaining < TILE_N ? remaining : TILE_N;
    if (tile_rows != expected_rows || (tile_rows % PE_N) != 0) return -3;

    if (task == FFN_STAGE_ACTIVATION) {
        stage_activation(activation_tile_f32, tile_rows);
        cached_active_N = active_N;
        cached_n_base = n_base;
        cached_tile_rows = tile_rows;
        cache_valid = true;
        return 0;
    }

    if (task != FFN_COMPUTE_WEIGHT_BATCH) return -4;
    if (!cache_valid || cached_active_N != active_N || cached_n_base != n_base ||
        cached_tile_rows != tile_rows) return -5;
    if (m_base < 0 || (m_base % M_BATCH) != 0 || m_base + M_BATCH > FFN_M)
        return -6;

    compute_weight_batch(weight_batch_f16, output_batch_f32, tile_rows);
    return 0;
}
