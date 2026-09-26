#pragma once

#include "ap_int.h"

#include <cstdint>

#ifndef RM13_K
#define RM13_K 4304
#endif
#ifndef RM13_DEBUG_OUTPUTS
#define RM13_DEBUG_OUTPUTS 1
#endif

static constexpr int RM13_GROUP_SIZE = 128;
static constexpr int RM13_GROUPS = (RM13_K + RM13_GROUP_SIZE - 1) / RM13_GROUP_SIZE;
static constexpr int RM13_K_WORDS_F32 = RM13_K / 8;
static constexpr int RM13_WEIGHT_WORDS_PER_GROUP = 4; // 128 W4 codes / 32 per 128-bit word
#ifndef RM13_TILE_M
#define RM13_TILE_M 16
#endif
#ifndef RM13_TILE_N
#define RM13_TILE_N 4
#endif
#ifndef RM13_PROCESSING_M
#define RM13_PROCESSING_M 4
#endif
#ifndef RM13_PROCESSING_N
#define RM13_PROCESSING_N 4
#endif
static constexpr int RM13_M_TILE = RM13_TILE_M;
static constexpr int RM13_N_TILE = RM13_TILE_N;
static constexpr int RM13_PE_M = RM13_PROCESSING_M;
static constexpr int RM13_PE_N = RM13_PROCESSING_N;
enum Rm13Task : int {
    RM13_STAGE_ACTIVATION = 0,
    RM13_COMPUTE_WEIGHT_TILE = 1,
};

// Tile-local interface. Weight nibbles are m-major, group-major, then k-local;
// low nibble is the even local K code. X is token-major, K contiguous, with
// eight F32 values per 256-bit word. Output is token-major, M contiguous.
// Diagnostic outputs expose exact integer group partials and runtime X scales
// for bit-level contract auditing; production callers may discard them.
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
    int active_n);
