#include "microkernel.hpp"

#include <cstdint>
#include <cstdio>
#include <fstream>
#include <string>
#include <vector>

ap_uint<32> fp16x32_mul_a(ap_uint<16>, ap_uint<32>);
ap_uint<32> fp16x32_mul_b(ap_uint<16>, ap_uint<32>);

namespace {
bool read_exact(const std::string &path, void *dst, size_t bytes) {
    std::ifstream in(path, std::ios::binary);
    if (!in) return false;
    in.read(static_cast<char *>(dst), static_cast<std::streamsize>(bytes));
    return static_cast<size_t>(in.gcount()) == bytes;
}
uint32_t bits(float f) {
    union { uint32_t u; float f; } v;
    v.f = f;
    return v.u;
}
uint32_t reduce10(const std::vector<uint32_t> &products) {
    float acc[10] = {};
    for (size_t group = 0; group < products.size() / 4; ++group) {
        union { uint32_t u; float f; } p[4];
        for (int q = 0; q < 4; ++q) p[q].u = products[group * 4 + q];
        const float left = p[0].f + p[1].f;
        const float right = p[2].f + p[3].f;
        const float chunk = left + right;
        acc[group % 10] += chunk;
    }
    const float t0 = acc[0] + acc[1];
    const float t1 = acc[2] + acc[3];
    const float t2 = acc[4] + acc[5];
    const float t3 = acc[6] + acc[7];
    const float t4 = acc[8] + acc[9];
    return bits(((t0 + t1) + (t2 + t3)) + t4);
}
}

int main(int argc, char **argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: real_tensor_probe TENSOR_DIR\n");
        return 2;
    }
    const std::string dir = argv[1];
    const char *layers[] = {"ffn_up-0", "ffn_up-13", "ffn_up-26"};
    const int ns[] = {1120, 280, 280};
    constexpr int K = 1152;
    constexpr int M = 4304;
    uint64_t products = 0, mismatches = 0, reductions = 0;

    for (int li = 0; li < 3; ++li) {
        std::vector<uint16_t> weights(static_cast<size_t>(K) * M);
        std::vector<float> activations(static_cast<size_t>(K) * ns[li]);
        const std::string prefix = dir + "/" + layers[li];
        if (!read_exact(prefix + ".weight.f16", weights.data(), weights.size() * sizeof(uint16_t)) ||
            !read_exact(prefix + ".activation.f32", activations.data(), activations.size() * sizeof(float))) {
            std::fprintf(stderr, "missing or truncated inputs for %s\n", layers[li]);
            return 3;
        }

        // Each (k,m) weight is paired with a real activation for token m mod N.
        // This scans every captured weight and samples real activation values.
        for (int m = 0; m < M; ++m) {
            const int n = m % ns[li];
            std::vector<uint32_t> pa(K), pb(K);
            for (int k = 0; k < K; ++k) {
                const uint16_t w = weights[static_cast<size_t>(k) * M + m];
                const uint32_t x = bits(activations[static_cast<size_t>(k) * ns[li] + n]);
                pa[k] = static_cast<uint32_t>(fp16x32_mul_a(w, x));
                pb[k] = static_cast<uint32_t>(fp16x32_mul_b(w, x));
                ++products;
                if (pa[k] != pb[k]) ++mismatches;
            }
            ++reductions;
            if (reduce10(pa) != reduce10(pb)) ++mismatches;
        }
        std::printf("layer=%s weights=%zu activation_values=%zu sampled_output_channels=%d N=%d\n",
                    layers[li], weights.size(), activations.size(), M, ns[li]);
    }
    std::printf("real_product_pairs=%llu same_order_reductions=%llu mismatches=%llu\n",
                static_cast<unsigned long long>(products),
                static_cast<unsigned long long>(reductions),
                static_cast<unsigned long long>(mismatches));
    return mismatches == 0 ? 0 : 1;
}
