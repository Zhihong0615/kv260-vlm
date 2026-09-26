#include "microkernel.hpp"

#include <cstdint>
#include <cstdio>

ap_uint<32> fp16x32_mul_a(ap_uint<16>, ap_uint<32>);
ap_uint<32> fp16x32_mul_b(ap_uint<16>, ap_uint<32>);

namespace {
uint32_t rng = 0x9e3779b9u;
uint32_t next_u32() {
    rng ^= rng << 13;
    rng ^= rng >> 17;
    rng ^= rng << 5;
    return rng;
}
bool nan32(uint32_t bits) {
    return ((bits >> 23) & 0xffu) == 0xffu && (bits & 0x7fffffu) != 0;
}
bool check(uint16_t h, uint32_t x, uint64_t &cases, uint64_t &mismatches) {
    const uint32_t a = static_cast<uint32_t>(fp16x32_mul_a(h, x));
    const uint32_t b = static_cast<uint32_t>(fp16x32_mul_b(h, x));
    ++cases;
    const bool ok = (nan32(a) && nan32(b)) || a == b;
    if (!ok && mismatches < 8)
        std::fprintf(stderr, "mismatch h=%04x x=%08x A=%08x B=%08x\n", h, x, a, b);
    if (!ok) ++mismatches;
    return ok;
}
}

int main() {
    const uint32_t edges[] = {
        0x00000000u, 0x80000000u, 0x00000001u, 0x00000002u,
        0x007fffffu, 0x00800000u, 0x00800001u, 0x3f000000u,
        0x3f800000u, 0xbf800000u, 0x40000000u, 0x7f7fffffu,
        0x7f800000u, 0xff800000u, 0x7fc00000u, 0x7f800001u,
        0xffc12345u, 0x33800000u, 0x33000000u, 0x4b000001u,
        0x4b000000u, 0x4b000002u, 0x00800010u, 0x80800001u,
    };
    uint64_t cases = 0, mismatches = 0;
    for (unsigned h = 0; h < 65536; ++h)
        for (uint32_t x : edges) check(static_cast<uint16_t>(h), x, cases, mismatches);
    for (unsigned i = 0; i < 1000000; ++i)
        check(static_cast<uint16_t>(next_u32()), next_u32(), cases, mismatches);
    std::printf("boundary_random_cases=%llu mismatches=%llu\n",
                static_cast<unsigned long long>(cases),
                static_cast<unsigned long long>(mismatches));
    return mismatches == 0 ? 0 : 1;
}
