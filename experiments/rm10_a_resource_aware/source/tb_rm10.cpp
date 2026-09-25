#include "vision_ffn_down.hpp"

#include <cstdint>
#include <iostream>
#include <vector>

namespace {
std::uint32_t float_bits(float value) {
    union { float f; std::uint32_t u; } bits;
    bits.f = value;
    return bits.u;
}
}

int main() {
    std::vector<ap_uint<128>> weights(WEIGHT_BATCH_WORDS);
    std::vector<ap_uint<256>> activations(ACTIVATION_TILE_WORDS);
    std::vector<ap_uint<256>> outputs(OUTPUT_BATCH_WORDS);

    for (int i = 0; i < WEIGHT_BATCH_WORDS; ++i) {
        ap_uint<128> packed = 0;
        for (int lane = 0; lane < WEIGHT_PACK; ++lane)
            packed.range(lane * 16 + 15, lane * 16) = 0x3c00; // F16 +1
        weights[i] = packed;
    }
    for (int i = 0; i < ACTIVATION_TILE_WORDS; ++i) {
        ap_uint<256> packed = 0;
        for (int lane = 0; lane < ACTIVATION_PACK; ++lane)
            packed.range(lane * 32 + 31, lane * 32) = float_bits(1.0f);
        activations[i] = packed;
    }

    if (vision_ffn_down_tile(weights.data(), activations.data(), outputs.data(),
                             FFN_STAGE_ACTIVATION, 4, 0, 0, 4) != 0) {
        std::cerr << "activation staging failed\n";
        return 1;
    }
    if (vision_ffn_down_tile(weights.data(), activations.data(), outputs.data(),
                             FFN_COMPUTE_WEIGHT_BATCH, 4, 0, 0, 4) != 0) {
        std::cerr << "compute task failed\n";
        return 1;
    }

    int compared = 0;
    for (int batch_tile = 0; batch_tile < M_TILES_PER_BATCH; ++batch_tile) {
      for (int n = 0; n < 4; ++n) {
       for (int mw = 0; mw < TILE_M / OUTPUT_PACK; ++mw) {
        const int word = batch_tile * OUTPUT_TILE_WORDS +
                         n * (TILE_M / OUTPUT_PACK) + mw;
        for (int lane = 0; lane < OUTPUT_PACK; ++lane) {
            union { std::uint32_t u; float f; } value;
            value.u = outputs[word].range(lane * 32 + 31, lane * 32).to_uint();
            if (value.f != static_cast<float>(FFN_K)) {
                std::cerr << "mismatch output word=" << word << " lane=" << lane
                          << " actual=" << value.f << " expected=" << FFN_K << "\n";
                return 1;
            }
            ++compared;
        }
       }
      }
    }
    std::cout << "RM10 C-sim PASS: all " << compared * OUTPUT_PACK
              << " outputs are " << FFN_K << "\n";
    return 0;
}
