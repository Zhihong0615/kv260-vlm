#include "microkernel.hpp"

ap_uint<32> fp16x32_mul_b(ap_uint<16> weight_bits, ap_uint<32> activation_bits) {
#pragma HLS INTERFACE ap_ctrl_hs port=return
    return rm12_arith::f16xf32_rne_product(weight_bits, activation_bits);
}
