#pragma once

#include "ap_int.h"

#include <cstdint>

namespace rm12_arith {

inline ap_uint<32> half_to_f32_bits(ap_uint<16> h) {
#pragma HLS INLINE
    const ap_uint<1> sign = h[15];
    const ap_uint<5> exp = h.range(14, 10);
    const ap_uint<10> frac = h.range(9, 0);
    ap_uint<32> out = 0;
    out[31] = sign;
    if (exp == 0) {
        if (frac == 0) {
            return out;
        }
        ap_uint<11> norm = frac;
        int shift = 0;
        for (int i = 0; i < 10; ++i) {
#pragma HLS UNROLL
            if (norm[10] == 0) {
                norm <<= 1;
                ++shift;
            }
        }
        out.range(30, 23) = static_cast<unsigned>(113 - shift);
        out.range(22, 13) = norm.range(9, 0);
    } else if (exp == 0x1f) {
        out.range(30, 23) = 0xff;
        out.range(22, 13) = frac;
    } else {
        out.range(30, 23) = exp + 112;
        out.range(22, 13) = frac;
    }
    return out;
}

inline ap_uint<32> f16xf32_rne_product(ap_uint<16> h, ap_uint<32> x) {
#pragma HLS INLINE
    const ap_uint<1> sign = h[15] ^ x[31];
    const ap_uint<5> he = h.range(14, 10);
    const ap_uint<10> hf = h.range(9, 0);
    const ap_uint<8> xe = x.range(30, 23);
    const ap_uint<23> xf = x.range(22, 0);
    const bool h_nan = (he == 31) && (hf != 0);
    const bool x_nan = (xe == 255) && (xf != 0);
    const bool h_inf = (he == 31) && (hf == 0);
    const bool x_inf = (xe == 255) && (xf == 0);
    const bool h_zero = (he == 0) && (hf == 0);
    const bool x_zero = (xe == 0) && (xf == 0);

    if (h_nan || x_nan || ((h_inf || x_inf) && (h_zero || x_zero)))
        return 0x7fc00000u;
    if (h_inf || x_inf) {
        ap_uint<32> out = 0x7f800000u;
        out[31] = sign;
        return out;
    }
    if (h_zero || x_zero) {
        ap_uint<32> out = 0;
        out[31] = sign;
        return out;
    }

    ap_uint<11> hs = 0;
    int he2 = 0;
    if (he == 0) {
        hs = hf;
        he2 = -24; // F16 subnormals are exact; their F32 expansion is normal.
    } else {
        hs = (1u << 10) | hf;
        he2 = static_cast<int>(he) - 25;
    }

    ap_uint<24> xs = 0;
    int xe2 = 0;
    if (xe == 0) {
        xs = xf;
        xe2 = -149;
    } else {
        xs = (1u << 23) | xf;
        xe2 = static_cast<int>(xe) - 150;
    }

    const ap_uint<35> product = hs * xs;
    int msb = 0;
    bool found = false;
    for (int bit = 34; bit >= 0; --bit) {
#pragma HLS UNROLL
        if (!found && product[bit]) {
            msb = bit;
            found = true;
        }
    }
    int exponent = msb + he2 + xe2;
    const int scale_to_subnormal = he2 + xe2 + 149;
    ap_uint<25> rounded = 0;

    if (exponent >= -126) {
        if (msb > 23) {
            const int shift = msb - 23;
            rounded = product >> shift;
            const ap_uint<35> remainder_mask = (ap_uint<35>(1) << shift) - 1;
            const ap_uint<35> remainder = product & remainder_mask;
            const ap_uint<35> halfway = ap_uint<35>(1) << (shift - 1);
            if ((remainder > halfway) ||
                ((remainder == halfway) && rounded[0]))
                ++rounded;
        } else {
            rounded = product << (23 - msb);
        }
        if (rounded[24]) {
            rounded >>= 1;
            ++exponent;
        }
        if (exponent > 127) {
            ap_uint<32> out = 0x7f800000u;
            out[31] = sign;
            return out;
        }
        ap_uint<32> out = 0;
        out[31] = sign;
        out.range(30, 23) = exponent + 127;
        out.range(22, 0) = rounded.range(22, 0);
        return out;
    }

    if (scale_to_subnormal >= 0) {
        rounded = product << scale_to_subnormal;
    } else {
        const int shift = -scale_to_subnormal;
        rounded = product >> shift;
        const ap_uint<35> remainder_mask = (ap_uint<35>(1) << shift) - 1;
        const ap_uint<35> remainder = product & remainder_mask;
        const ap_uint<35> halfway = ap_uint<35>(1) << (shift - 1);
        if ((remainder > halfway) ||
            ((remainder == halfway) && rounded[0]))
            ++rounded;
    }
    ap_uint<32> out = 0;
    out[31] = sign;
    if (rounded >= (1u << 23)) {
        out.range(30, 23) = 1; // rounded up to the smallest normal F32
    } else {
        out.range(22, 0) = rounded.range(22, 0);
    }
    return out;
}

inline float f32_from_bits(ap_uint<32> bits) {
#pragma HLS INLINE
    union { uint32_t u; float f; } value;
    value.u = static_cast<uint32_t>(bits);
    return value.f;
}

inline ap_uint<32> f32_to_bits(float value) {
#pragma HLS INLINE
    union { uint32_t u; float f; } result;
    result.f = value;
    return result.u;
}

} // namespace rm12_arith
