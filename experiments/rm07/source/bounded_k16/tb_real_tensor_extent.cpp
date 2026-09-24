#include "vision_ffn_down.hpp"

#include <cmath>
#include <algorithm>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

static bool read_exact(const char *path, void *data, std::size_t bytes) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return false;
    in.read(static_cast<char *>(data), static_cast<std::streamsize>(bytes));
    return static_cast<std::size_t>(in.gcount()) == bytes;
}

static std::uint32_t float_bits(float value) {
    std::uint32_t bits;
    std::memcpy(&bits, &value, sizeof(bits));
    return bits;
}

int main(int argc, char **argv) {
    if (argc != 6) {
        std::fprintf(stderr,
            "usage: tb_real_tensor_extent WEIGHT_F16 ACTIVATION_F32 CPU_OUTPUT_F32 LAYER ACTIVE_N\n");
        return 2;
    }
    const int active_N = std::stoi(argv[5]);
    if (active_N != 280 && active_N != 1120) return 2;

    std::vector<std::uint16_t> raw_w(static_cast<std::size_t>(FFN_M) * FFN_K);
    std::vector<float> raw_x(static_cast<std::size_t>(active_N) * FFN_K);
    std::vector<float> raw_y(static_cast<std::size_t>(active_N) * FFN_M);
    if (!read_exact(argv[1], raw_w.data(), raw_w.size() * sizeof(raw_w[0])) ||
        !read_exact(argv[2], raw_x.data(), raw_x.size() * sizeof(raw_x[0])) ||
        !read_exact(argv[3], raw_y.data(), raw_y.size() * sizeof(raw_y[0]))) {
        std::fprintf(stderr, "failed to read exact real-tensor payloads\n");
        return 3;
    }

    std::vector<ap_uint<256>> x(TILE_N * K_WORDS, 0);
    std::vector<ap_uint<128>> w(M_BATCH * K_WORDS, 0);
    std::vector<ap_uint<256>> y(OUTPUT_BATCH_WORDS, 0);

    const int n_bases[] = {0, active_N == 1120 ? 544 : 128,
                           active_N == 1120 ? 1088 : 256};
    const int m_bases[] = {0, 512, 1024};
    double max_abs = 0.0, sum_sq = 0.0, dot = 0.0, norm_got = 0.0, norm_ref = 0.0;
    std::size_t count = 0;
    int commands = 0;

    for (int n_base : n_bases) {
        const int tile_rows = (active_N - n_base < TILE_N) ? active_N - n_base : TILE_N;
        std::fill(x.begin(), x.end(), ap_uint<256>(0));
        for (int n = 0; n < tile_rows; ++n) {
            for (int kw = 0; kw < K_WORDS; ++kw) {
                ap_uint<256> packed = 0;
                for (int lane = 0; lane < ACTIVATION_PACK; ++lane) {
                    const std::size_t src = static_cast<std::size_t>(n_base + n) * FFN_K + kw * ACTIVATION_PACK + lane;
                    packed.range(lane * 32 + 31, lane * 32) = float_bits(raw_x[src]);
                }
                x[n * K_WORDS + kw] = packed;
            }
        }
        const int stage_status = vision_ffn_down_tile(
            w.data(), x.data(), y.data(), FFN_STAGE_ACTIVATION,
            active_N, n_base, 0, tile_rows);
        if (stage_status != 0) {
            std::fprintf(stderr, "activation stage failed: status=%d N=%d n_base=%d\n",
                         stage_status, active_N, n_base);
            return 4;
        }

        for (int m_base : m_bases) {
            std::fill(w.begin(), w.end(), ap_uint<128>(0));
            for (int mt = 0; mt < M_BATCH; ++mt) {
                for (int kw = 0; kw < K_WORDS; ++kw) {
                    ap_uint<128> packed = 0;
                    for (int lane = 0; lane < WEIGHT_PACK; ++lane) {
                        const std::size_t src = static_cast<std::size_t>(m_base + mt) * FFN_K +
                                                kw * WEIGHT_PACK + lane;
                        packed.range(lane * 16 + 15, lane * 16) = raw_w[src];
                    }
                    w[mt * K_WORDS + kw] = packed;
                }
            }
            std::fill(y.begin(), y.end(), ap_uint<256>(0));
            const int status = vision_ffn_down_tile(
                w.data(), x.data(), y.data(), FFN_COMPUTE_WEIGHT_BATCH,
                active_N, n_base, m_base, tile_rows);
            if (status != 0) {
                std::fprintf(stderr, "compute failed: status=%d N=%d n_base=%d m_base=%d\n",
                             status, active_N, n_base, m_base);
                return 5;
            }
            ++commands;

            for (int mt = 0; mt < M_BATCH; ++mt) {
                const int batch_tile = mt / TILE_M;
                const int m = mt % TILE_M;
                const int mw = m / OUTPUT_PACK;
                const int lane = m % OUTPUT_PACK;
                for (int n = 0; n < tile_rows; ++n) {
                    const int out_word = batch_tile * OUTPUT_TILE_WORDS +
                                         n * (TILE_M / OUTPUT_PACK) + mw;
                    const std::uint32_t got_bits = y[out_word]
                        .range(lane * 32 + 31, lane * 32).to_uint();
                    float got;
                    std::memcpy(&got, &got_bits, sizeof(got));
                    const float ref = raw_y[static_cast<std::size_t>(n_base + n) * FFN_M + m_base + mt];
                    const double err = static_cast<double>(got) - ref;
                    const double abs_err = std::fabs(err);
                    if (abs_err > max_abs) max_abs = abs_err;
                    sum_sq += err * err;
                    dot += static_cast<double>(got) * ref;
                    norm_got += static_cast<double>(got) * got;
                    norm_ref += static_cast<double>(ref) * ref;
                    ++count;
                }
            }
        }
    }

    const double rmse = std::sqrt(sum_sq / static_cast<double>(count));
    const double cosine = dot / std::sqrt(norm_got * norm_ref);
    std::printf("RM07_REAL_TENSOR layer=%s shape_K_M_N=%d_%d_%d sampled_n_bases=%d,%d,%d "
                "m_bases=0,512,1024 compute_commands=%d output_elements=%zu "
                "max_abs=%.17g rmse=%.17g cosine=%.17g\n",
                argv[4], FFN_K, FFN_M, active_N, n_bases[0], n_bases[1], n_bases[2],
                commands, count, max_abs, rmse, cosine);
    return 0;
}
