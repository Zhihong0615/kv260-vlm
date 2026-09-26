#include "vision_ffn_unified.hpp"

#include <cstdint>
#include <iostream>
#include <vector>

namespace {
std::uint32_t float_bits(float value) {
    union { float f; std::uint32_t u; } bits;
    bits.f = value;
    return bits.u;
}

float output_at(const std::vector<ap_uint<256>> &outputs, int n, int m) {
    const int batch_tile = m / TILE_M;
    const int within_tile = m % TILE_M;
    const int word = batch_tile * OUTPUT_TILE_WORDS + n * (TILE_M / OUTPUT_PACK) +
                     within_tile / OUTPUT_PACK;
    const int lane = within_tile % OUTPUT_PACK;
    union { std::uint32_t u; float f; } value;
    value.u = outputs[word].range(lane * 32 + 31, lane * 32).to_uint();
    return value.f;
}

bool run_case(int active_K, int active_M, int m_base, int valid_rows) {
    const int k_words = active_K / WEIGHT_PACK;
    const int tile_rows = 4;
    std::vector<ap_uint<128>> weights(M_BATCH * k_words);
    std::vector<ap_uint<256>> activations(tile_rows * k_words);
    std::vector<ap_uint<256>> outputs(OUTPUT_BATCH_WORDS);

    for (int m = 0; m < M_BATCH; ++m) {
        for (int kw = 0; kw < k_words; ++kw) {
            ap_uint<128> packed = 0;
            const std::uint16_t h = m < valid_rows ? 0x3c00 : 0;
            for (int lane = 0; lane < WEIGHT_PACK; ++lane)
                packed.range(lane * 16 + 15, lane * 16) = h;
            weights[m * k_words + kw] = packed;
        }
    }
    for (int n = 0; n < tile_rows; ++n) {
        for (int kw = 0; kw < k_words; ++kw) {
            ap_uint<256> packed = 0;
            for (int lane = 0; lane < ACTIVATION_PACK; ++lane)
                packed.range(lane * 32 + 31, lane * 32) = float_bits(1.0f);
            activations[n * k_words + kw] = packed;
        }
    }

    if (vision_ffn_unified_tile(weights.data(), activations.data(), outputs.data(),
                                FFN_STAGE_ACTIVATION, tile_rows, active_K,
                                active_M, 0, m_base, tile_rows) != 0) {
        std::cerr << "activation staging failed active_K=" << active_K << "\n";
        return false;
    }
    if (vision_ffn_unified_tile(weights.data(), activations.data(), outputs.data(),
                                FFN_COMPUTE_WEIGHT_BATCH, tile_rows, active_K,
                                active_M, 0, m_base, tile_rows) != 0) {
        std::cerr << "compute failed active_K=" << active_K << " m_base=" << m_base << "\n";
        return false;
    }

    for (int n = 0; n < tile_rows; ++n) {
        for (int m = 0; m < M_BATCH; ++m) {
            const float expected = m < valid_rows ? static_cast<float>(active_K) : 0.0f;
            const float actual = output_at(outputs, n, m);
            if (actual != expected) {
                std::cerr << "mismatch K=" << active_K << " M=" << active_M
                          << " m_base=" << m_base << " row=" << m
                          << " actual=" << actual << " expected=" << expected << "\n";
                return false;
            }
        }
    }
    std::cout << "case PASS active_K=" << active_K << " active_M=" << active_M
              << " m_base=" << m_base << " valid_rows=" << valid_rows << "\n";
    return true;
}
}

int main() {
    // Exercise both real orientations and the padded up-family final batch.
    if (!run_case(4304, 1152, 1024, 128)) return 1;
    if (!run_case(1152, 4304, 4224, 80)) return 1;
    std::cout << "RM11 unified HLS C-sim PASS\n";
    return 0;
}
