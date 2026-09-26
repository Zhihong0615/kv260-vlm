#pragma once

#include "ap_int.h"

#include <cstdint>

static constexpr int MAX_ACTIVE_K = 4304;
static constexpr int MAX_ACTIVE_M = 4304;
static constexpr int MAX_ACTIVE_N = 1120;
static constexpr int TILE_M = 16;
static constexpr int TILE_N = 32;
static constexpr int WEIGHT_PACK = 8;
static constexpr int ACTIVATION_PACK = 8;
static constexpr int OUTPUT_PACK = 8;
static constexpr int K_WORDS = MAX_ACTIVE_K / WEIGHT_PACK;
static constexpr int M_TILES_PER_BATCH = 8;
static constexpr int M_BATCH = TILE_M * M_TILES_PER_BATCH;
static constexpr int MAX_M_BATCHES = (MAX_ACTIVE_M + M_BATCH - 1) / M_BATCH;
static constexpr int WEIGHT_TILE_WORDS = TILE_M * K_WORDS;
static constexpr int WEIGHT_BATCH_WORDS = M_TILES_PER_BATCH * WEIGHT_TILE_WORDS;
static constexpr int ACTIVATION_TILE_WORDS = TILE_N * K_WORDS;
static constexpr int OUTPUT_TILE_WORDS = TILE_N * TILE_M / OUTPUT_PACK;
static constexpr int OUTPUT_BATCH_WORDS = M_TILES_PER_BATCH * OUTPUT_TILE_WORDS;

enum FfnTileTask : int {
    FFN_STAGE_ACTIVATION = 0,
    FFN_COMPUTE_WEIGHT_BATCH = 1,
};

// One X activation tile is cached on chip and reused for all nine output
// channel batches. Host pointers address bounded contiguous staging buffers,
// not full model tensors.
extern "C" int vision_ffn_unified_tile(
    const ap_uint<128> *weight_batch_f16,
    const ap_uint<256> *activation_tile_f32,
    ap_uint<256> *output_batch_f32,
    int task,
    int active_N,
    int active_K,
    int active_M,
    int n_base,
    int m_base,
    int tile_rows);
