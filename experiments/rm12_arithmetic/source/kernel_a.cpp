#include "microkernel.hpp"

ap_uint<32> fp16x32_mul_a(ap_uint<16> weight_bits, ap_uint<32> activation_bits) {
#pragma HLS INTERFACE ap_ctrl_hs port=return
    const ap_uint<32> weight_f32_bits = rm12_arith::half_to_f32_bits(weight_bits);
    const float weight = rm12_arith::f32_from_bits(weight_f32_bits);
    const float activation = rm12_arith::f32_from_bits(activation_bits);
    const float product = weight * activation;
    return rm12_arith::f32_to_bits(product);
}
