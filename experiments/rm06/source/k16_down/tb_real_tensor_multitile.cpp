#include "vision_gemm.hpp"

#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <random>
#include <set>
#include <string>
#include <vector>

static bool read_exact(const char *path, void *data, std::size_t bytes) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return false;
    in.read(static_cast<char *>(data), static_cast<std::streamsize>(bytes));
    return static_cast<std::size_t>(in.gcount()) == bytes;
}

int main(int argc, char **argv) {
    if (argc != 5) {
        std::fprintf(stderr, "usage: tb_real_tensor WEIGHT_F16 ACTIVATION_F32 CPU_OUTPUT_F32 LAYER\n");
        return 2;
    }
    std::vector<std::uint16_t> raw_w(static_cast<std::size_t>(VLM_OUT) * VLM_K);
    std::vector<float> raw_x(static_cast<std::size_t>(VLM_N) * VLM_K);
    std::vector<float> raw_y(static_cast<std::size_t>(VLM_N) * VLM_OUT);
    if (!read_exact(argv[1], raw_w.data(), raw_w.size() * sizeof(raw_w[0])) ||
        !read_exact(argv[2], raw_x.data(), raw_x.size() * sizeof(raw_x[0])) ||
        !read_exact(argv[3], raw_y.data(), raw_y.size() * sizeof(raw_y[0]))) {
        std::fprintf(stderr, "failed to read exact real-tensor payloads\n");
        return 3;
    }

    std::vector<ap_uint<128>> w(W_WORDS, 0);
    std::vector<ap_uint<256>> x(X_WORDS, 0);
    std::vector<ap_uint<256>> y(Y_WORDS, 0);
    for (std::size_t i = 0; i < raw_w.size(); ++i)
        w[i / PACK].range((i % PACK) * 16 + 15, (i % PACK) * 16) = raw_w[i];
    for (std::size_t i = 0; i < raw_x.size(); ++i) {
        std::uint32_t bits;
        std::memcpy(&bits, &raw_x[i], sizeof(bits));
        x[i / PACK].range((i % PACK) * 32 + 31, (i % PACK) * 32) = bits;
    }

    const int token_bases[] = {0, VLM_N == 1120 ? 544 : 128, VLM_N == 1120 ? 1088 : 224};
    const int output_bases[] = {0, 560, 1136};
    std::set<std::pair<int, int>> tiles;
    for (int nb : token_bases)
        for (int mb : output_bases)
            tiles.emplace(nb, mb);
    std::mt19937 rng(static_cast<std::uint32_t>(42 + VLM_N));
    while (tiles.size() < 12) {
        const int nb = static_cast<int>(rng() % (VLM_N / MACRO_N)) * MACRO_N;
        const int mb = static_cast<int>(rng() % (VLM_OUT / MACRO_M)) * MACRO_M;
        tiles.emplace(nb, mb);
    }
    for (const auto & tile : tiles)
        vision_macro_tile(w.data(), x.data(), y.data(), tile.second, tile.first);

    double max_abs = 0.0, sum_sq = 0.0, dot = 0.0, norm_a = 0.0, norm_b = 0.0;
    std::uint64_t bitwise_equal = 0;
    std::size_t count = 0;
    for (const auto & tile : tiles) {
        const int nb = tile.first;
        const int mb = tile.second;
        for (int n = 0; n < MACRO_N; ++n) {
            for (int m = 0; m < MACRO_M; ++m) {
                const std::size_t out_idx = static_cast<std::size_t>(nb + n) * VLM_OUT + mb + m;
                const std::uint32_t got_bits = y[out_idx / PACK]
                    .range((out_idx % PACK) * 32 + 31, (out_idx % PACK) * 32).to_uint();
                float got;
                std::memcpy(&got, &got_bits, sizeof(got));
                const float ref = raw_y[out_idx];
                const double err = static_cast<double>(got) - ref;
                const double abs_err = std::fabs(err);
                if (abs_err > max_abs) max_abs = abs_err;
                sum_sq += err * err;
                dot += static_cast<double>(got) * ref;
                norm_a += static_cast<double>(got) * got;
                norm_b += static_cast<double>(ref) * ref;
                std::uint32_t ref_bits;
                std::memcpy(&ref_bits, &ref, sizeof(ref_bits));
                if (got_bits == ref_bits) ++bitwise_equal;
                ++count;
            }
        }
    }
    const double rmse = std::sqrt(sum_sq / static_cast<double>(count));
    const double cosine = dot / std::sqrt(norm_a * norm_b);
    std::printf("REAL_TENSOR_K16 layer=%s shape_K_M_N=%d_%d_%d tiles=%zu (9-grid+3-seeded-random) tile_M_N=%d_%d "
                "elements=%zu max_abs=%.17g rmse=%.17g cosine=%.17g bitwise_equal=%llu\n",
                argv[4], VLM_K, VLM_OUT, VLM_N, tiles.size(), MACRO_M, MACRO_N, count,
                max_abs, rmse, cosine, static_cast<unsigned long long>(bitwise_equal));
    return 0;
}
