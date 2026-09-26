#include "w4a8_tile.hpp"

#include <cmath>
#include <cstdlib>
#include <cstdint>
#include <fstream>
#include <iostream>
#include <limits>
#include <stdexcept>
#include <string>
#include <vector>

namespace {
std::uint32_t fbits(float value) {
    union { float f; std::uint32_t u; } bits;
    bits.f = value;
    return bits.u;
}

float from_bits(std::uint32_t bits) {
    union { float f; std::uint32_t u; } value;
    value.u = bits;
    return value.f;
}

float half_to_float(std::uint16_t half) {
    const std::uint32_t sign = static_cast<std::uint32_t>(half & 0x8000u) << 16;
    const std::uint32_t exponent = (half >> 10) & 0x1fu;
    std::uint32_t mantissa = half & 0x03ffu;
    if (exponent == 0) {
        if (mantissa == 0)
            return from_bits(sign);
        int unbiased = -14;
        while ((mantissa & 0x0400u) == 0) {
            mantissa <<= 1;
            --unbiased;
        }
        mantissa &= 0x03ffu;
        return from_bits(sign | (static_cast<std::uint32_t>(unbiased + 127) << 23) |
                         (mantissa << 13));
    }
    if (exponent == 0x1fu)
        return from_bits(sign | 0x7f800000u | (mantissa << 13));
    return from_bits(sign | ((exponent + 112u) << 23) | (mantissa << 13));
}

std::uint32_t read_u32_le(std::ifstream &file) {
    unsigned char bytes[4] = {0, 0, 0, 0};
    file.read(reinterpret_cast<char *>(bytes), sizeof(bytes));
    if (!file)
        throw std::runtime_error("short real fixture header");
    return static_cast<std::uint32_t>(bytes[0]) |
           (static_cast<std::uint32_t>(bytes[1]) << 8) |
           (static_cast<std::uint32_t>(bytes[2]) << 16) |
           (static_cast<std::uint32_t>(bytes[3]) << 24);
}

float read_x(const std::vector<ap_uint<256> > &x, int n, int k) {
    return from_bits(x[n * RM13_K_WORDS_F32 + k / 8]
                         .range((k % 8) * 32 + 31, (k % 8) * 32).to_uint());
}

void put_x(std::vector<ap_uint<256> > &x, int n, int k, float value) {
    x[n * RM13_K_WORDS_F32 + k / 8]
        .range((k % 8) * 32 + 31, (k % 8) * 32) = fbits(value);
}

int decode_w4(const std::vector<ap_uint<128> > &w, int m, int g, int kk) {
    const int words_per_m = RM13_GROUPS * RM13_WEIGHT_WORDS_PER_GROUP;
    const ap_uint<128> word = w[m * words_per_m + g * RM13_WEIGHT_WORDS_PER_GROUP + kk / 32];
    ap_int<4> code = word.range((kk % 32) * 4 + 3, (kk % 32) * 4);
    return code.to_int();
}

void put_w4(std::vector<ap_uint<128> > &w, int m, int g, int kk, int code) {
    const int words_per_m = RM13_GROUPS * RM13_WEIGHT_WORDS_PER_GROUP;
    ap_uint<128> &word = w[m * words_per_m + g * RM13_WEIGHT_WORDS_PER_GROUP + kk / 32];
    const unsigned nibble = static_cast<unsigned>(code) & 0xfu;
    word.range((kk % 32) * 4 + 3, (kk % 32) * 4) = nibble;
}

bool packed_weights_well_formed(const std::vector<ap_uint<128> > &w,
                                int active_m) {
    // This is a host/offline artifact check. The PL kernel trusts packed W4
    // produced by the validated packer and does not put a serial nibble scan
    // on the compute path.
    for (int m = 0; m < active_m; ++m) {
        for (int g = 0; g < RM13_GROUPS; ++g) {
            const int kbase = g * RM13_GROUP_SIZE;
            const int valid_k = (RM13_K - kbase < RM13_GROUP_SIZE)
                                    ? RM13_K - kbase : RM13_GROUP_SIZE;
            for (int kk = 0; kk < valid_k; ++kk) {
                if (decode_w4(w, m, g, kk) == -8)
                    return false;
            }
        }
    }
    return true;
}

int round_even(float value) {
    const bool neg = value < 0.0f;
    const float mag = neg ? -value : value;
    int base = static_cast<int>(mag);
    const float frac = mag - static_cast<float>(base);
    if (frac > 0.5f || (frac == 0.5f && (base & 1)))
        ++base;
    return neg ? -base : base;
}

bool almost_equal(float actual, float expected) {
    const float tolerance = 2.0e-5f * ((std::fabs(expected) > 1.0f)
                                           ? std::fabs(expected) : 1.0f);
    return std::fabs(actual - expected) <= tolerance;
}

struct Gold {
    std::vector<std::int32_t> partials;
    std::vector<float> x_scales;
    std::vector<float> output;
};

Gold make_gold(const std::vector<ap_uint<128> > &w,
               const std::vector<float> &ws,
               const std::vector<ap_uint<256> > &x,
               int active_m,
               int active_n) {
    Gold gold;
    gold.partials.resize(active_n * active_m * RM13_GROUPS);
    gold.x_scales.resize(active_n * RM13_GROUPS);
    gold.output.resize(active_n * active_m);
    std::vector<std::int8_t> qx(active_n * RM13_K);

    for (int n = 0; n < active_n; ++n) {
        for (int g = 0; g < RM13_GROUPS; ++g) {
            const int kbase = g * RM13_GROUP_SIZE;
            const int valid_k = (RM13_K - kbase < RM13_GROUP_SIZE)
                                    ? RM13_K - kbase : RM13_GROUP_SIZE;
            float max_abs = 0.0f;
            for (int kk = 0; kk < valid_k; ++kk) {
                const float value = read_x(x, n, kbase + kk);
                const std::uint32_t bits = fbits(value);
                if ((bits & 0x7f800000u) == 0x7f800000u)
                    throw std::runtime_error("nonfinite test input passed to golden quantizer");
                const float magnitude = from_bits(bits & 0x7fffffffu);
                if (magnitude > max_abs)
                    max_abs = magnitude;
            }
            const float scale = (max_abs == 0.0f) ? 1.0f : max_abs / 127.0f;
            gold.x_scales[n * RM13_GROUPS + g] = scale;
            for (int kk = 0; kk < valid_k; ++kk) {
                const int k = kbase + kk;
                int q = round_even(read_x(x, n, k) / scale);
                if (q < -127) q = -127;
                if (q > 127) q = 127;
                qx[n * RM13_K + k] = static_cast<std::int8_t>(q);
            }
        }
    }

    for (int n = 0; n < active_n; ++n) {
        for (int m = 0; m < active_m; ++m) {
            float output = 0.0f;
            for (int g = 0; g < RM13_GROUPS; ++g) {
                const int kbase = g * RM13_GROUP_SIZE;
                const int valid_k = (RM13_K - kbase < RM13_GROUP_SIZE)
                                        ? RM13_K - kbase : RM13_GROUP_SIZE;
                std::int32_t partial = 0;
                for (int kk = 0; kk < valid_k; ++kk)
                    partial += decode_w4(w, m, g, kk) *
                               static_cast<int>(qx[n * RM13_K + kbase + kk]);
                gold.partials[(n * active_m + m) * RM13_GROUPS + g] = partial;
                float term = static_cast<float>(partial);
                term = term * ws[m * RM13_GROUPS + g];
                term = term * gold.x_scales[n * RM13_GROUPS + g];
                output = output + term;
            }
            gold.output[n * active_m + m] = output;
        }
    }
    return gold;
}

void fill_inputs(std::vector<ap_uint<128> > &w,
                 std::vector<float> &ws,
                 std::vector<ap_uint<256> > &x,
                 int active_m,
                 int active_n) {
    const int words_per_m = RM13_GROUPS * RM13_WEIGHT_WORDS_PER_GROUP;
    w.assign(RM13_M_TILE * words_per_m, 0);
    ws.resize(RM13_M_TILE * RM13_GROUPS);
    x.assign(RM13_N_TILE * RM13_K_WORDS_F32, 0);

    for (int m = 0; m < RM13_M_TILE; ++m) {
        for (int g = 0; g < RM13_GROUPS; ++g) {
            ws[m * RM13_GROUPS + g] = 0.03125f *
                                         static_cast<float>(1 + ((m * 7 + g * 3) % 19));
            const int kbase = g * RM13_GROUP_SIZE;
            const int valid_k = (RM13_K - kbase < RM13_GROUP_SIZE)
                                    ? RM13_K - kbase : RM13_GROUP_SIZE;
            for (int kk = 0; kk < valid_k; ++kk) {
                // Deterministic coverage of all signed codes, including -7, 0, +7.
                const int code = ((m * 29 + g * 17 + kk * 11) % 15) - 7;
                put_w4(w, m, g, kk, code);
            }
            // Test-only poison proves a short last group never consumes padding.
            for (int kk = valid_k; kk < RM13_GROUP_SIZE; ++kk)
                put_w4(w, m, g, kk, 7);
        }
    }

    for (int n = 0; n < active_n; ++n) {
        for (int g = 0; g < RM13_GROUPS; ++g) {
            const int kbase = g * RM13_GROUP_SIZE;
            const int valid_k = (RM13_K - kbase < RM13_GROUP_SIZE)
                                    ? RM13_K - kbase : RM13_GROUP_SIZE;
            for (int kk = 0; kk < valid_k; ++kk) {
                float value = static_cast<float>(((n * 7 + g * 3 + kk * 13) % 61) - 30) * 0.125f;
                if (kk == 0)
                    value = 11.0f + static_cast<float>((n + g) % 13);
                if (kk == 1)
                    value = -(11.0f + static_cast<float>((n + g) % 13));
                if (n == 0 && g == 0) {
                    if (kk == 0) value = 127.0f;
                    if (kk == 1) value = 0.5f;
                    if (kk == 2) value = 1.5f;
                    if (kk == 3) value = 2.5f;
                    if (kk == 4) value = -0.5f;
                    if (kk == 5) value = -1.5f;
                    if (kk == 6) value = -2.5f;
                }
                if ((n == 1) && (g == 1))
                    value = 0.0f; // zero-only group requires scale=1 and zero codes
                put_x(x, n, kbase + kk, value);
            }
        }
    }
}

bool run_case(int active_m, int active_n) {
    std::vector<ap_uint<128> > w;
    std::vector<float> ws;
    std::vector<ap_uint<256> > x;
    fill_inputs(w, ws, x, active_m, active_n);
    const Gold gold = make_gold(w, ws, x, active_m, active_n);
    // HLS C/RTL cosim allocates each m_axi pointer to its declared static
    // depth, even though the logical active tile may be smaller.
    std::vector<float> y(RM13_M_TILE * RM13_N_TILE, -999.0f);
    std::vector<std::int32_t> partials(RM13_M_TILE * RM13_N_TILE * RM13_GROUPS,
                                       0x55555555);
    std::vector<float> xs(RM13_N_TILE * RM13_GROUPS, -999.0f);
    if (!packed_weights_well_formed(w, active_m)) {
        std::cerr << "offline W4 artifact check rejected generated fixture\n";
        return false;
    }
    const int stage_status = rm13_w4a8_tile(w.data(), ws.data(), x.data(), y.data(),
                                            partials.data(), xs.data(),
                                            RM13_STAGE_ACTIVATION, active_m, active_n);
    if (stage_status != 0) {
        std::cerr << "activation stage status " << stage_status << "\n";
        return false;
    }
    const int status = rm13_w4a8_tile(w.data(), ws.data(), x.data(), y.data(),
                                      partials.data(), xs.data(),
                                      RM13_COMPUTE_WEIGHT_TILE, active_m, active_n);
    if (status != 0) {
        std::cerr << "tile status " << status << " for active M/N="
                  << active_m << "/" << active_n << "\n";
        return false;
    }

    for (std::size_t i = 0; i < gold.partials.size(); ++i) {
        if (partials[i] != gold.partials[i]) {
            std::cerr << "integer partial mismatch index=" << i << " actual="
                      << partials[i] << " expected=" << gold.partials[i] << "\n";
            return false;
        }
    }
    for (std::size_t i = 0; i < gold.x_scales.size(); ++i) {
        if (fbits(xs[i]) != fbits(gold.x_scales[i])) {
            std::cerr << "activation scale mismatch index=" << i << " actual="
                      << xs[i] << " expected=" << gold.x_scales[i] << "\n";
            return false;
        }
    }
    int bitwise_outputs = 0;
    for (std::size_t i = 0; i < gold.output.size(); ++i) {
        if (!almost_equal(y[i], gold.output[i])) {
            std::cerr << "output mismatch index=" << i << " actual=" << y[i]
                      << " expected=" << gold.output[i] << "\n";
            return false;
        }
        if (fbits(y[i]) == fbits(gold.output[i]))
            ++bitwise_outputs;
    }
    std::cout << "case M=" << active_m << " N=" << active_n
              << ": exact int32 partials=" << gold.partials.size()
              << ", exact activation scales=" << gold.x_scales.size()
              << ", F32 outputs within 2e-5 relative/absolute floor; bitwise="
              << bitwise_outputs << "/" << gold.output.size() << "\n";
    return true;
}

bool run_real_up_fixture(const char *path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) {
        std::cerr << "cannot open RM13_REAL_FIXTURE: " << path << "\n";
        return false;
    }
    char magic[8];
    file.read(magic, sizeof(magic));
    const std::uint32_t fixture_k = read_u32_le(file);
    const std::uint32_t active_m = read_u32_le(file);
    const std::uint32_t active_n = read_u32_le(file);
    if (!file || std::string(magic, sizeof(magic)) != "R13W4T01" ||
        fixture_k != RM13_K || active_m < 1 || active_m > RM13_M_TILE ||
        active_n < 1 || active_n > RM13_N_TILE) {
        std::cerr << "invalid real-up fixture header\n";
        return false;
    }

    std::vector<unsigned char> packed_codes(active_m * RM13_GROUPS * 64);
    std::vector<float> packed_scales(active_m * RM13_GROUPS);
    std::vector<float> raw_x(active_n * fixture_k);
    file.read(reinterpret_cast<char *>(packed_codes.data()),
              static_cast<std::streamsize>(packed_codes.size()));
    file.read(reinterpret_cast<char *>(packed_scales.data()),
              static_cast<std::streamsize>(packed_scales.size() * sizeof(packed_scales[0])));
    file.read(reinterpret_cast<char *>(raw_x.data()),
              static_cast<std::streamsize>(raw_x.size() * sizeof(raw_x[0])));
    if (!file || file.peek() != std::ifstream::traits_type::eof()) {
        std::cerr << "truncated or oversized real-up fixture\n";
        return false;
    }

    std::vector<ap_uint<128> > w;
    std::vector<float> ws;
    std::vector<ap_uint<256> > x;
    const int words_per_m = RM13_GROUPS * RM13_WEIGHT_WORDS_PER_GROUP;
    w.assign(RM13_M_TILE * words_per_m, 0);
    ws.assign(RM13_M_TILE * RM13_GROUPS, 1.0f);
    x.assign(RM13_N_TILE * RM13_K_WORDS_F32, 0);

    for (int m = 0; m < static_cast<int>(active_m); ++m) {
        for (int g = 0; g < RM13_GROUPS; ++g) {
            const int scale_index = m * RM13_GROUPS + g;
            const float scale = packed_scales[scale_index];
            if (!std::isfinite(scale) || scale <= 0.0f) {
                std::cerr << "invalid F32 weight scale in real fixture\n";
                return false;
            }
            ws[scale_index] = scale;
            const int source_group_offset = (m * RM13_GROUPS + g) * 64;
            for (int kk = 0; kk < RM13_GROUP_SIZE; ++kk) {
                const unsigned byte = packed_codes[source_group_offset + kk / 2];
                const unsigned nibble = (kk & 1) ? (byte >> 4) : (byte & 0xfu);
                int code = static_cast<int>(nibble);
                if (code & 8)
                    code -= 16;
                put_w4(w, m, g, kk, code);
            }
        }
    }
    for (int n = 0; n < static_cast<int>(active_n); ++n) {
        for (int k = 0; k < RM13_K; ++k)
            put_x(x, n, k, raw_x[n * fixture_k + k]);
    }
    if (!packed_weights_well_formed(w, active_m)) {
        std::cerr << "offline W4 validation failed on real fixture\n";
        return false;
    }

    const Gold gold = make_gold(w, ws, x, active_m, active_n);
    std::vector<float> y(RM13_M_TILE * RM13_N_TILE, -999.0f);
    std::vector<std::int32_t> partials(RM13_M_TILE * RM13_N_TILE * RM13_GROUPS,
                                       0x55555555);
    std::vector<float> xs(RM13_N_TILE * RM13_GROUPS, -999.0f);
    const int stage_status = rm13_w4a8_tile(w.data(), ws.data(), x.data(), y.data(),
                                            partials.data(), xs.data(),
                                            RM13_STAGE_ACTIVATION, active_m, active_n);
    const int compute_status = stage_status == 0
        ? rm13_w4a8_tile(w.data(), ws.data(), x.data(), y.data(), partials.data(),
                         xs.data(), RM13_COMPUTE_WEIGHT_TILE, active_m, active_n)
        : stage_status;
    if (compute_status != 0) {
        std::cerr << "real fixture hardware function returned " << compute_status << "\n";
        return false;
    }
    for (std::size_t i = 0; i < gold.partials.size(); ++i) {
        if (partials[i] != gold.partials[i]) {
            std::cerr << "real fixture int32 partial mismatch at " << i << "\n";
            return false;
        }
    }
    for (std::size_t i = 0; i < gold.x_scales.size(); ++i) {
        if (fbits(xs[i]) != fbits(gold.x_scales[i])) {
            std::cerr << "real fixture activation scale mismatch at " << i << "\n";
            return false;
        }
    }
    int bitwise_outputs = 0;
    for (std::size_t i = 0; i < gold.output.size(); ++i) {
        if (!almost_equal(y[i], gold.output[i])) {
            std::cerr << "real fixture output mismatch at " << i << "\n";
            return false;
        }
        if (fbits(y[i]) == fbits(gold.output[i]))
            ++bitwise_outputs;
    }
    std::cout << "real FFN-up packed-cache fixture K=" << RM13_K << " M=" << active_m
              << " N=" << active_n << ": exact int32 partials=" << gold.partials.size()
              << ", exact activation scales=" << gold.x_scales.size()
              << ", F32 outputs within 2e-5 relative/absolute floor; bitwise="
              << bitwise_outputs << "/" << gold.output.size() << "\n";
    return true;
}

bool run_accumulator_bound_case(int weight_sign) {
    const int active_m = 1;
    const int active_n = 1;
    std::vector<ap_uint<128> > w;
    std::vector<float> ws;
    std::vector<ap_uint<256> > x;
    fill_inputs(w, ws, x, active_m, active_n);
    for (int g = 0; g < RM13_GROUPS; ++g) {
        ws[g] = 1.0f;
        const int kbase = g * RM13_GROUP_SIZE;
        const int valid_k = (RM13_K - kbase < RM13_GROUP_SIZE)
                                ? RM13_K - kbase : RM13_GROUP_SIZE;
        for (int kk = 0; kk < valid_k; ++kk) {
            put_w4(w, 0, g, kk, weight_sign * 7);
            put_x(x, 0, kbase + kk, 127.0f);
        }
    }
    if (!packed_weights_well_formed(w, active_m)) {
        std::cerr << "offline W4 artifact validator rejected legal boundary codes\n";
        return false;
    }
    const Gold gold = make_gold(w, ws, x, active_m, active_n);
    std::vector<float> y(RM13_M_TILE * RM13_N_TILE, -999.0f);
    std::vector<std::int32_t> partials(RM13_M_TILE * RM13_N_TILE * RM13_GROUPS,
                                       0x55555555);
    std::vector<float> xs(RM13_N_TILE * RM13_GROUPS, -999.0f);
    const int stage_status = rm13_w4a8_tile(w.data(), ws.data(), x.data(), y.data(),
                                            partials.data(), xs.data(),
                                            RM13_STAGE_ACTIVATION, active_m, active_n);
    const int compute_status = stage_status == 0
        ? rm13_w4a8_tile(w.data(), ws.data(), x.data(), y.data(), partials.data(),
                         xs.data(), RM13_COMPUTE_WEIGHT_TILE, active_m, active_n)
        : stage_status;
    if (compute_status != 0) {
        std::cerr << "boundary-code kernel call failed: " << compute_status << "\n";
        return false;
    }
    for (int g = 0; g < RM13_GROUPS; ++g) {
        const int valid_k = (RM13_K - g * RM13_GROUP_SIZE < RM13_GROUP_SIZE)
                                ? RM13_K - g * RM13_GROUP_SIZE : RM13_GROUP_SIZE;
        const std::int64_t expected64 = static_cast<std::int64_t>(weight_sign) *
                                        valid_k * 7 * 127;
        if (expected64 < std::numeric_limits<std::int32_t>::min() ||
            expected64 > std::numeric_limits<std::int32_t>::max() ||
            partials[g] != expected64 || partials[g] != gold.partials[g]) {
            std::cerr << "int32 accumulator boundary mismatch group=" << g
                      << " actual=" << partials[g] << " expected=" << expected64 << "\n";
            return false;
        }
    }
    if (!almost_equal(y[0], gold.output[0])) {
        std::cerr << "boundary-code output differs from independent scale merge\n";
        return false;
    }
    std::cout << "int32 accumulator boundary sign=" << weight_sign
              << ": group0=" << partials[0] << ", last="
              << partials[RM13_GROUPS - 1] << ", within int32\n";
    return true;
}
} // namespace

int main() {
    if (!run_case(7, 3))
        return 1;
    if (!run_accumulator_bound_case(1) || !run_accumulator_bound_case(-1))
        return 1;

    std::vector<ap_uint<128> > w;
    std::vector<float> ws;
    std::vector<ap_uint<256> > x;
    fill_inputs(w, ws, x, 7, 3);
    std::vector<float> y(RM13_M_TILE * RM13_N_TILE, -999.0f);
    std::vector<std::int32_t> partials(RM13_M_TILE * RM13_N_TILE * RM13_GROUPS);
    std::vector<float> xs(RM13_N_TILE * RM13_GROUPS);

    // The CPU/offline artifact check rejects reserved -8 before submission.
    put_w4(w, 0, 0, 0, -8);
    if (packed_weights_well_formed(w, 7)) {
        std::cerr << "offline W4 artifact check accepted reserved -8\n";
        return 1;
    }
    put_w4(w, 0, 0, 0, 0);

    // Nonfinite activation input must request CPU fallback before writing Y.
    put_x(x, 0, 1, from_bits(0x7fc00000u));
    for (std::size_t i = 0; i < RM13_M_TILE * RM13_N_TILE; ++i)
        y[i] = -999.0f;
    if (rm13_w4a8_tile(w.data(), ws.data(), x.data(), y.data(), partials.data(),
                       xs.data(), RM13_STAGE_ACTIVATION, 7, 3) != -2) {
        std::cerr << "nonfinite activation was not rejected\n";
        return 1;
    }
    for (std::size_t i = 0; i < RM13_M_TILE * RM13_N_TILE; ++i) {
        if (y[i] != -999.0f) {
            std::cerr << "nonfinite fallback wrote a partial output\n";
            return 1;
        }
    }
    std::cout << "edge checks: offline packed-W4 validator rejects -8; nonfinite X requests fallback before Y writes\n";
    const char *real_fixture = std::getenv("RM13_REAL_FIXTURE");
    if (real_fixture && *real_fixture && !run_real_up_fixture(real_fixture))
        return 1;
    return 0;
}
