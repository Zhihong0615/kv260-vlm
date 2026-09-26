#include "w4a8_tile.hpp"

#include <cstdint>

namespace {
static constexpr int W4_WORDS_PER_M = RM13_GROUPS * RM13_WEIGHT_WORDS_PER_GROUP;

std::uint32_t float_bits(float value) {
#pragma HLS INLINE
    union {
        float f;
        std::uint32_t u;
    } bits;
    bits.f = value;
    return bits.u;
}

float bits_float(std::uint32_t bits) {
#pragma HLS INLINE
    union {
        float f;
        std::uint32_t u;
    } value;
    value.u = bits;
    return value.f;
}

bool is_finite_bits(float value) {
#pragma HLS INLINE
    return (float_bits(value) & 0x7f800000u) != 0x7f800000u;
}

int round_ties_to_even(float value) {
#pragma HLS INLINE
    const bool negative = value < 0.0f;
    const float magnitude = negative ? -value : value;
    int base = static_cast<int>(magnitude);
    const float fraction = magnitude - static_cast<float>(base);
    if (fraction > 0.5f || (fraction == 0.5f && (base & 1)))
        ++base;
    return negative ? -base : base;
}

int decode_w4(ap_uint<128> word, int local_k) {
#pragma HLS INLINE
    ap_int<4> signed_code = word.range((local_k & 31) * 4 + 3, (local_k & 31) * 4);
    return signed_code.to_int();
}
} // namespace

extern "C" int rm13_w4a8_tile(
    const ap_uint<128> *packed_w4,
    const float *weight_scales,
    const ap_uint<256> *packed_x_f32,
    float *output_f32,
#if RM13_DEBUG_OUTPUTS
    std::int32_t *group_partials_debug,
    float *activation_scales_debug,
#endif
    int task,
    int active_m,
    int active_n) {
#pragma HLS INTERFACE m_axi port=packed_w4 offset=slave bundle=gmem_w depth=RM13_M_TILE*RM13_GROUPS*RM13_WEIGHT_WORDS_PER_GROUP max_read_burst_length=64 num_read_outstanding=8
#pragma HLS INTERFACE m_axi port=weight_scales offset=slave bundle=gmem_ws depth=RM13_M_TILE*RM13_GROUPS max_read_burst_length=64 num_read_outstanding=8
#pragma HLS INTERFACE m_axi port=packed_x_f32 offset=slave bundle=gmem_x depth=RM13_N_TILE*RM13_K_WORDS_F32 max_read_burst_length=64 num_read_outstanding=8
#pragma HLS INTERFACE m_axi port=output_f32 offset=slave bundle=gmem_y depth=RM13_M_TILE*RM13_N_TILE max_write_burst_length=64 num_write_outstanding=8
#if RM13_DEBUG_OUTPUTS
#pragma HLS INTERFACE m_axi port=group_partials_debug offset=slave bundle=gmem_p depth=RM13_N_TILE*RM13_M_TILE*RM13_GROUPS max_write_burst_length=64 num_write_outstanding=8
#pragma HLS INTERFACE m_axi port=activation_scales_debug offset=slave bundle=gmem_xs depth=RM13_N_TILE*RM13_GROUPS max_write_burst_length=64 num_write_outstanding=8
#endif
#pragma HLS INTERFACE s_axilite port=active_m bundle=control
#pragma HLS INTERFACE s_axilite port=active_n bundle=control
#pragma HLS INTERFACE s_axilite port=task bundle=control
#pragma HLS INTERFACE s_axilite port=packed_w4 bundle=control
#pragma HLS INTERFACE s_axilite port=weight_scales bundle=control
#pragma HLS INTERFACE s_axilite port=packed_x_f32 bundle=control
#pragma HLS INTERFACE s_axilite port=output_f32 bundle=control
#if RM13_DEBUG_OUTPUTS
#pragma HLS INTERFACE s_axilite port=group_partials_debug bundle=control
#pragma HLS INTERFACE s_axilite port=activation_scales_debug bundle=control
#endif
#pragma HLS INTERFACE s_axilite port=return bundle=control

    if (task != RM13_STAGE_ACTIVATION && task != RM13_COMPUTE_WEIGHT_TILE)
        return -1;
    if (active_m < 1 || active_m > RM13_M_TILE ||
        active_n < 1 || active_n > RM13_N_TILE)
        return -1;

    ap_uint<128> w_cache[RM13_M_TILE][RM13_GROUPS][RM13_WEIGHT_WORDS_PER_GROUP];
    float ws_cache[RM13_M_TILE][RM13_GROUPS];
    static ap_int<8> x_cache[RM13_N_TILE][RM13_K];
    static float xs_cache[RM13_N_TILE][RM13_GROUPS];
    static int activation_ready = 0;
    static int cached_active_n = 0;
#pragma HLS ARRAY_PARTITION variable=w_cache cyclic factor=RM13_PE_M dim=1
#pragma HLS ARRAY_PARTITION variable=ws_cache cyclic factor=RM13_PE_M dim=1
#pragma HLS ARRAY_PARTITION variable=x_cache cyclic factor=RM13_PE_N dim=1
#pragma HLS ARRAY_PARTITION variable=xs_cache cyclic factor=RM13_PE_N dim=1
#pragma HLS BIND_STORAGE variable=w_cache type=ram_2p impl=uram
#pragma HLS BIND_STORAGE variable=x_cache type=ram_2p impl=uram
#pragma HLS BIND_STORAGE variable=ws_cache type=ram_2p impl=bram
#pragma HLS BIND_STORAGE variable=xs_cache type=ram_2p impl=bram

    if (task == RM13_STAGE_ACTIVATION)
        activation_ready = 0;

    // Pull only one bounded M tile of already quantized W4 codes and scales.
    if (task == RM13_COMPUTE_WEIGHT_TILE) {
    for (int m = 0; m < active_m; ++m) {
        for (int g = 0; g < RM13_GROUPS; ++g) {
            const float scale = weight_scales[m * RM13_GROUPS + g];
            if (!is_finite_bits(scale) || scale <= 0.0f)
                return -4;
            ws_cache[m][g] = scale;
            for (int word = 0; word < RM13_WEIGHT_WORDS_PER_GROUP; ++word) {
#pragma HLS PIPELINE II=1
                w_cache[m][g][word] = packed_w4[m * W4_WORDS_PER_M +
                                                g * RM13_WEIGHT_WORDS_PER_GROUP + word];
            }
        }
    }

    }

    // Cache one packed X tile in bounded on-chip storage. The packed word is
    // loaded once from DDR, then shared by the maxabs and quantization passes.
    if (task == RM13_STAGE_ACTIVATION) {
      // One 128-element source group is the only F32 input retained locally.
      // This keeps the staging cache bounded as N_TILE grows.
      ap_uint<256> group_words[RM13_GROUP_SIZE / 8];
#pragma HLS ARRAY_PARTITION variable=group_words complete dim=1
      for (int n = 0; n < active_n; ++n) {
        for (int g = 0; g < RM13_GROUPS; ++g) {
            const int kbase = g * RM13_GROUP_SIZE;
            const int valid_k = (RM13_K - kbase < RM13_GROUP_SIZE)
                                    ? RM13_K - kbase : RM13_GROUP_SIZE;
            for (int word = 0; word < RM13_GROUP_SIZE / 8; ++word) {
#pragma HLS PIPELINE II=1
                if (word < valid_k / 8)
                    group_words[word] = packed_x_f32[n * RM13_K_WORDS_F32 +
                                                     kbase / 8 + word];
            }
            float max_abs = 0.0f;
            int nonfinite_seen = 0;
            for (int word_in_group = 0; word_in_group < RM13_GROUP_SIZE / 8; ++word_in_group) {
#pragma HLS PIPELINE II=1
                if (word_in_group < valid_k / 8) {
                    const ap_uint<256> packed = group_words[word_in_group];
                    float magnitude[8];
#pragma HLS ARRAY_PARTITION variable=magnitude complete dim=1
                    for (int lane = 0; lane < 8; ++lane) {
#pragma HLS UNROLL
                        const std::uint32_t bits = packed.range(lane * 32 + 31, lane * 32).to_uint();
                        const float value = bits_float(bits);
                        if (!is_finite_bits(value))
                            nonfinite_seen = 1;
                        magnitude[lane] = bits_float(bits & 0x7fffffffu);
                    }
                    const float max01 = magnitude[0] > magnitude[1] ? magnitude[0] : magnitude[1];
                    const float max23 = magnitude[2] > magnitude[3] ? magnitude[2] : magnitude[3];
                    const float max45 = magnitude[4] > magnitude[5] ? magnitude[4] : magnitude[5];
                    const float max67 = magnitude[6] > magnitude[7] ? magnitude[6] : magnitude[7];
                    const float max0123 = max01 > max23 ? max01 : max23;
                    const float max4567 = max45 > max67 ? max45 : max67;
                    const float word_max = max0123 > max4567 ? max0123 : max4567;
                    if (word_max > max_abs)
                        max_abs = word_max;
                }
            }
            if (nonfinite_seen)
                return -2;
            const float scale = (max_abs == 0.0f) ? 1.0f : max_abs / 127.0f;
            xs_cache[n][g] = scale;
#if RM13_DEBUG_OUTPUTS
            activation_scales_debug[n * RM13_GROUPS + g] = scale;
#endif

            for (int kk = 0; kk < RM13_GROUP_SIZE; ++kk) {
#pragma HLS PIPELINE II=1
                if (kk < valid_k) {
                    const ap_uint<256> packed = group_words[kk >> 3];
                    const std::uint32_t bits = packed.range(((kbase + kk) & 7) * 32 + 31,
                                                            ((kbase + kk) & 7) * 32).to_uint();
                    const float value = bits_float(bits);
                    const float ratio = value / scale;
                    int q = round_ties_to_even(ratio);
                    if (q < -127) q = -127;
                    if (q > 127) q = 127;
                    x_cache[n][kbase + kk] = static_cast<ap_int<8>>(q);
          }
        }
      }
    }
    cached_active_n = active_n;
    activation_ready = 1;
    return 0;
    }

    if (!activation_ready || cached_active_n != active_n)
        return -5;

    // Each output is merged group-by-group in increasing K order. The int32
    // partial is reset at each scale group and never mixed with another group.
    for (int nbase = 0; nbase < active_n; nbase += RM13_PE_N) {
        for (int mbase = 0; mbase < active_m; mbase += RM13_PE_M) {
            float result[RM13_PE_N][RM13_PE_M];
#pragma HLS ARRAY_PARTITION variable=result complete dim=0
            for (int j = 0; j < RM13_PE_N; ++j) {
#pragma HLS UNROLL
                for (int i = 0; i < RM13_PE_M; ++i) {
#pragma HLS UNROLL
                    result[j][i] = 0.0f;
                }
            }
            for (int g = 0; g < RM13_GROUPS; ++g) {
                const int kbase = g * RM13_GROUP_SIZE;
                const int valid_k = (RM13_K - kbase < RM13_GROUP_SIZE)
                                        ? RM13_K - kbase : RM13_GROUP_SIZE;
                std::int32_t partial[RM13_PE_N][RM13_PE_M];
#pragma HLS ARRAY_PARTITION variable=partial complete dim=0
                for (int j = 0; j < RM13_PE_N; ++j) {
#pragma HLS UNROLL
                    for (int i = 0; i < RM13_PE_M; ++i) {
#pragma HLS UNROLL
                        partial[j][i] = 0;
                    }
                }
                for (int kk = 0; kk < RM13_GROUP_SIZE; ++kk) {
#pragma HLS PIPELINE II=1
                    if (kk < valid_k) {
                      for (int j = 0; j < RM13_PE_N; ++j) {
#pragma HLS UNROLL
                          for (int i = 0; i < RM13_PE_M; ++i) {
#pragma HLS UNROLL
                            const int m = mbase + i;
                            const int n = nbase + j;
                            int w_code = 0;
                            if (m < active_m) {
                                const ap_uint<128> packed = w_cache[m][g][kk >> 5];
                                w_code = decode_w4(packed, kk);
                            }
                            const int x_code = (n < active_n)
                                                   ? x_cache[n][kbase + kk].to_int() : 0;
                            partial[j][i] += w_code * x_code;
                          }
                        }
                    }
                }
                for (int output_index = 0;
                     output_index < RM13_PE_N * RM13_PE_M; ++output_index) {
#pragma HLS PIPELINE II=1
                        const int j = output_index / RM13_PE_M;
                        const int i = output_index % RM13_PE_M;
                        const int m = mbase + i;
                        const int n = nbase + j;
                        if (m < active_m && n < active_n) {
#if RM13_DEBUG_OUTPUTS
                            const int debug_index = (n * active_m + m) * RM13_GROUPS + g;
                            group_partials_debug[debug_index] = partial[j][i];
#endif
                            float term = static_cast<float>(partial[j][i]);
                            term = term * ws_cache[m][g];
                            term = term * xs_cache[n][g];
                            result[j][i] = result[j][i] + term;
                        }
                }
            }
            for (int j = 0; j < RM13_PE_N; ++j) {
#pragma HLS UNROLL
                for (int i = 0; i < RM13_PE_M; ++i) {
#pragma HLS UNROLL
                    const int m = mbase + i;
                    const int n = nbase + j;
                    if (m < active_m && n < active_n)
                        output_f32[n * active_m + m] = result[j][i];
                }
            }
        }
    }
    return 0;
}
