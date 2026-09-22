#include <cstddef>

constexpr int N = 64;

void vector_add(const int a[N], const int b[N], int c[N]) {
#pragma HLS INTERFACE m_axi port=a offset=slave bundle=gmem0 depth=N
#pragma HLS INTERFACE m_axi port=b offset=slave bundle=gmem1 depth=N
#pragma HLS INTERFACE m_axi port=c offset=slave bundle=gmem2 depth=N
#pragma HLS INTERFACE s_axilite port=a bundle=control
#pragma HLS INTERFACE s_axilite port=b bundle=control
#pragma HLS INTERFACE s_axilite port=c bundle=control
#pragma HLS INTERFACE s_axilite port=return bundle=control
  for (std::size_t i = 0; i < N; ++i) {
#pragma HLS PIPELINE II=1
    c[i] = a[i] + b[i];
  }
}
