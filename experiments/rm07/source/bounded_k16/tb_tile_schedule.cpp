#include "vision_ffn_down.hpp"

#include <cstdio>
#include <vector>

int main() {
    std::vector<ap_uint<128>> w(WEIGHT_BATCH_WORDS, 0);
    std::vector<ap_uint<256>> x(ACTIVATION_TILE_WORDS, 0);
    std::vector<ap_uint<256>> y(OUTPUT_BATCH_WORDS, 0);
    const int cases[][3] = {{1120, 0, 32}, {280, 256, 24}};
    for (const auto & c : cases) {
        const int active_N = c[0];
        const int n_base = c[1];
        const int tile_rows = c[2];
        int status = vision_ffn_down_tile(w.data(), x.data(), y.data(),
            FFN_STAGE_ACTIVATION, active_N, n_base, 0, tile_rows);
        if (status != 0) return 1;
        status = vision_ffn_down_tile(w.data(), x.data(), y.data(),
            FFN_COMPUTE_WEIGHT_BATCH, active_N, n_base, 0, tile_rows);
        if (status != 0) return 2;
        for (const auto & value : y)
            if (value != 0) return 3;
        std::printf("SCHEDULE_CSIM_PASS active_N=%d n_base=%d tile_rows=%d\n",
                    active_N, n_base, tile_rows);
    }
    return 0;
}
