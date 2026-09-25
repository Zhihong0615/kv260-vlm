#include "vision_ffn_down.hpp"

#include <cstdint>

namespace {
static constexpr int PE_M = 4;
static constexpr int PE_N = 4;
static constexpr int K_LANES = 16;
#ifndef RM10_ARCH
#define RM10_ARCH 0
#endif
static constexpr int RM10_INTERLEAVE_BANKS = 5;
static constexpr int RM10_A_ISSUE = 4;
static constexpr int RM10_A_GROUPS = FFN_K / RM10_A_ISSUE;

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
#if RM10_ARCH == 0
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
#elif RM10_ARCH == 4
                // Resource-aware A revision: each cycle issues four K products
                // for each of the sixteen outputs in this 4x4 output group.
                // The four products are reduced as a balanced pairwise tree,
                // then accumulated into one of five temporal FP32 banks.
                // Since bank = group % 5, each bank is revisited exactly five
                // loop iterations later. The fadd recurrence latency is five
                // cycles in this tool flow, so the truthful dependence distance
                // is 5 and an II=1 schedule is legal.
                float accum[PE_M][PE_N][RM10_INTERLEAVE_BANKS];
#pragma HLS ARRAY_PARTITION variable=accum complete dim=0
                for (int i = 0; i < PE_M; ++i) {
#pragma HLS UNROLL
                    for (int j = 0; j < PE_N; ++j) {
#pragma HLS UNROLL
                        for (int b = 0; b < RM10_INTERLEAVE_BANKS; ++b) {
#pragma HLS UNROLL
                            accum[i][j][b] = 0.0f;
                        }
                    }
                }

#pragma HLS LOOP_FLATTEN off
                for (int group = 0; group < RM10_A_GROUPS; ++group) {
#pragma HLS PIPELINE II=1
#pragma HLS DEPENDENCE variable=accum inter distance=5
                    const int kbase = group * RM10_A_ISSUE;
                    const int bank = group % RM10_INTERLEAVE_BANKS;
                    for (int i = 0; i < PE_M; ++i) {
#pragma HLS UNROLL
                        for (int j = 0; j < PE_N; ++j) {
#pragma HLS UNROLL
                            float product[RM10_A_ISSUE];
#pragma HLS ARRAY_PARTITION variable=product complete dim=1
                            for (int q = 0; q < RM10_A_ISSUE; ++q) {
#pragma HLS UNROLL
                                const int k = kbase + q;
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
                                product[q] = wvalue * xvalue.f;
                            }
                            const float left = product[0] + product[1];
                            const float right = product[2] + product[3];
                            const float chunk = left + right;
                            accum[i][j][bank] += chunk;
                        }
                    }
                }

                for (int i = 0; i < PE_M; ++i) {
#pragma HLS UNROLL
                    for (int j = 0; j < PE_N; ++j) {
#pragma HLS UNROLL
                        const float t0 = accum[i][j][0] + accum[i][j][1];
                        const float t1 = accum[i][j][2] + accum[i][j][3];
                        result_tile[n + j][m + i] = (t0 + t1) + accum[i][j][4];
                    }
                }
#elif RM10_ARCH == 1 || RM10_ARCH == 3
                // A/C: split each of the original 16 residue streams into five
                // temporal banks. Group g updates bank g mod 5, so a given bank
                // is revisited only after five K-group iterations.
                float accum[PE_M][PE_N][K_LANES][RM10_INTERLEAVE_BANKS];
#pragma HLS ARRAY_PARTITION variable=accum complete dim=0
                for (int i = 0; i < PE_M; ++i) {
#pragma HLS UNROLL
                    for (int j = 0; j < PE_N; ++j) {
#pragma HLS UNROLL
                        for (int p = 0; p < K_LANES; ++p) {
#pragma HLS UNROLL
                            for (int b = 0; b < RM10_INTERLEAVE_BANKS; ++b) {
#pragma HLS UNROLL
                                accum[i][j][p][b] = 0.0f;
                            }
                        }
                    }
                }

#pragma HLS LOOP_FLATTEN off
                for (int group = 0; group < FFN_K / K_LANES; ++group) {
#pragma HLS PIPELINE II=1
                    const int kbase = group * K_LANES;
                    const int bank = group % RM10_INTERLEAVE_BANKS;
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
                                accum[i][j][p][bank] += wvalue * xvalue.f;
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
                            float lane_sum = 0.0f;
#if RM10_ARCH == 1
                            lane_sum += accum[i][j][p][0];
                            lane_sum += accum[i][j][p][1];
                            lane_sum += accum[i][j][p][2];
                            lane_sum += accum[i][j][p][3];
                            lane_sum += accum[i][j][p][4];
#else
                            lane_sum = (accum[i][j][p][0] + accum[i][j][p][1]) +
                                       (accum[i][j][p][2] + accum[i][j][p][3]);
                            lane_sum += accum[i][j][p][4];
#endif
                            sum += lane_sum;
                        }
                        result_tile[n + j][m + i] = sum;
                    }
                }
#elif RM10_ARCH == 2
                // B: four independent contiguous K segments, each retaining the
                // baseline 16-residue FP32 chains. Segment boundaries align to
                // K_LANES groups: 68/68/68/65 groups (1088/1088/1088/1040 K).
                float accum[PE_M][PE_N][4][K_LANES];
#pragma HLS ARRAY_PARTITION variable=accum complete dim=0
                for (int i = 0; i < PE_M; ++i) {
#pragma HLS UNROLL
                    for (int j = 0; j < PE_N; ++j) {
#pragma HLS UNROLL
                        for (int s = 0; s < 4; ++s) {
#pragma HLS UNROLL
                            for (int p = 0; p < K_LANES; ++p) {
#pragma HLS UNROLL
                                accum[i][j][s][p] = 0.0f;
                            }
                        }
                    }
                }

#pragma HLS LOOP_FLATTEN off
                for (int local_group = 0; local_group < 68; ++local_group) {
#pragma HLS PIPELINE II=1
                    for (int s = 0; s < 4; ++s) {
#pragma HLS UNROLL
                        const int first_group = (s < 3) ? s * 68 : 204;
                        const int group_count = (s < 3) ? 68 : 65;
                        if (local_group < group_count) {
                            const int kbase = (first_group + local_group) * K_LANES;
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
                                        accum[i][j][s][p] += wvalue * xvalue.f;
                                    }
                                }
                            }
                        }
                    }
                }

                for (int i = 0; i < PE_M; ++i) {
#pragma HLS UNROLL
                    for (int j = 0; j < PE_N; ++j) {
#pragma HLS UNROLL
                        float segment_sum[4];
#pragma HLS ARRAY_PARTITION variable=segment_sum complete dim=1
                        for (int s = 0; s < 4; ++s) {
#pragma HLS UNROLL
                            float part = 0.0f;
                            for (int p = 0; p < K_LANES; ++p) {
#pragma HLS UNROLL
                                part += accum[i][j][s][p];
                            }
                            segment_sum[s] = part;
                        }
                        result_tile[n + j][m + i] =
                            (segment_sum[0] + segment_sum[1]) +
                            (segment_sum[2] + segment_sum[3]);
                    }
                }
#else
#error "RM10_ARCH must be 0, 1 (A), 2 (B), 3 (C), or 4 (A resource-aware revision)"
#endif
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

    if (active_N < PE_N || active_N > MAX_ACTIVE_N || (active_N % PE_N) != 0)
        return -1;
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
