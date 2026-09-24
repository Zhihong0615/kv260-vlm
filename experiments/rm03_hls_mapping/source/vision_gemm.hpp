#pragma once

#include "ap_int.h"
#include <cstdint>

// Frozen MiniCPM-V vision-encoder ffn_up-0 operation, expressed in row-major
// GEMM convention: Y[N, OUT] = X[N, K] * W[OUT, K]^T.
static constexpr int VLM_K = 4304;   // reduction / input channels
static constexpr int VLM_N = 1120;   // image-token rows
static constexpr int VLM_OUT = 1152; // output channels
#ifndef HLS_PE_M
#define HLS_PE_M 4
#endif
#ifndef HLS_PE_N
#define HLS_PE_N 4
#endif
#ifndef HLS_K_LANES
#define HLS_K_LANES 8
#endif
static constexpr int PE_M = HLS_PE_M;
static constexpr int PE_N = HLS_PE_N;
static constexpr int K_LANES = HLS_K_LANES;
static constexpr int PACK = 8;
static constexpr int K_WORDS = VLM_K / PACK;
static constexpr int W_WORDS = VLM_OUT * K_WORDS;
static constexpr int X_WORDS = VLM_N * K_WORDS;
static constexpr int Y_WORDS = VLM_N * VLM_OUT / PACK;

#ifndef TILE_M
#define TILE_M 16
#endif
#ifndef TILE_N
#define TILE_N 32
#endif

static constexpr int MACRO_M = TILE_M;
static constexpr int MACRO_N = TILE_N;

static_assert(VLM_K % K_LANES == 0, "K_LANES must divide the frozen reduction dimension");
static_assert(MACRO_M % PE_M == 0, "PE_M must divide output tile");
static_assert(MACRO_N % PE_N == 0, "PE_N must divide token tile");

// Synthesis top: processes the entire frozen real workload.
extern "C" void vision_gemm(const ap_uint<128> *weights_f16_packed,
                            const ap_uint<256> *activations_f32_packed,
                            ap_uint<256> *output_f32_packed);

// C-simulation entry used to execute and check one macro-tile of the exact
// frozen workload without simulating all 5.56 billion MACs.
void vision_macro_tile(const ap_uint<128> *weights_f16_packed,
                       const ap_uint<256> *activations_f32_packed,
                       ap_uint<256> *output_f32_packed,
                       int output_row_base,
                       int token_base);
