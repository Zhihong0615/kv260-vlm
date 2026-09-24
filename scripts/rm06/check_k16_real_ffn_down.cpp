#include <algorithm>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <string>
#include <vector>

static bool read_exact(const std::string & path, void * dst, size_t bytes) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return false;
    in.read(static_cast<char *>(dst), static_cast<std::streamsize>(bytes));
    return static_cast<size_t>(in.gcount()) == bytes;
}

static float half_to_float(uint16_t h) {
    const uint32_t sign = (static_cast<uint32_t>(h & 0x8000u)) << 16;
    const uint32_t exp = (h >> 10) & 0x1fu;
    const uint32_t frac = h & 0x03ffu;
    uint32_t bits;
    if (exp == 0) {
        if (frac == 0) {
            bits = sign;
        } else {
            uint32_t normalized = frac;
            int shift = 0;
            for (int step = 0; step < 10; ++step) {
                if ((normalized & 0x0400u) == 0) {
                    normalized <<= 1;
                    ++shift;
                }
            }
            normalized &= 0x03ffu;
            bits = sign | (static_cast<uint32_t>(113 - shift) << 23) |
                   (normalized << 13);
        }
    } else if (exp == 0x1fu) {
        bits = sign | 0x7f800000u | (frac << 13);
    } else {
        bits = sign | ((exp + 112u) << 23) | (frac << 13);
    }
    float value;
    std::memcpy(&value, &bits, sizeof(value));
    return value;
}

int main(int argc, char ** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: check_k16_real_ffn_down TENSOR_DIR\n");
        return 2;
    }
    const std::string dir(argv[1]);
    const int K = 4304, M = 1152;
    const char * layers[] = {"ffn_down-0", "ffn_down-13", "ffn_down-26"};
    for (const char * layer : layers) {
        const int N = std::string(layer) == "ffn_down-0" ? 1120 : 280;
        const std::string prefix = dir + "/" + layer;
        std::vector<uint16_t> w(static_cast<size_t>(M) * K);
        std::vector<float> x(static_cast<size_t>(N) * K);
        std::vector<float> ref(static_cast<size_t>(N) * M);
        if (!read_exact(prefix + ".weight.f16", w.data(), w.size() * sizeof(w[0])) ||
            !read_exact(prefix + ".activation.f32", x.data(), x.size() * sizeof(x[0])) ||
            !read_exact(prefix + ".output.f32", ref.data(), ref.size() * sizeof(ref[0]))) {
            std::fprintf(stderr, "%s: missing or truncated W/X/Y payload\n", layer);
            return 3;
        }

        const int token_bases[] = {0, N == 1120 ? 544 : 128, N == 1120 ? 1088 : 224};
        const int output_bases[] = {0, 560, 1136};
        double max_abs = 0.0, sum_sq = 0.0, dot = 0.0, norm_got = 0.0, norm_ref = 0.0;
        size_t count = 0;
        for (int nb : token_bases) {
            for (int mb : output_bases) {
                for (int j = 0; j < 32; ++j) {
                    const int n = nb + j;
                    for (int i = 0; i < 16; ++i) {
                        const int m = mb + i;
                        float accum[16] = {};
                        for (int kbase = 0; kbase < K; kbase += 16) {
                            for (int p = 0; p < 16; ++p) {
                                const int k = kbase + p;
                                const float product = half_to_float(w[static_cast<size_t>(m) * K + k]) *
                                                      x[static_cast<size_t>(n) * K + k];
                                accum[p] = accum[p] + product;
                            }
                        }
                        float got = 0.0f;
                        for (int p = 0; p < 16; ++p) got = got + accum[p];
                        const float expected = ref[static_cast<size_t>(n) * M + m];
                        const double err = static_cast<double>(got) - expected;
                        max_abs = std::max(max_abs, std::fabs(err));
                        sum_sq += err * err;
                        dot += static_cast<double>(got) * expected;
                        norm_got += static_cast<double>(got) * got;
                        norm_ref += static_cast<double>(expected) * expected;
                        ++count;
                    }
                }
            }
        }
        const double rmse = std::sqrt(sum_sq / static_cast<double>(count));
        const double cosine = dot / std::sqrt(norm_got * norm_ref);
        std::printf("K16_REAL_FFN_DOWN layer=%s shape_K_M_N=%d_%d_%d tiles=9 tile_M_N=16_32 "
                    "outputs=%zu max_abs=%.17g rmse=%.17g cosine=%.17g\n",
                    layer, K, M, N, count, max_abs, rmse, cosine);
    }
    return 0;
}
