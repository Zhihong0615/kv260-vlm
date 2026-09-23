#include <iostream>

constexpr int kVectorSize = 64;

void vector_add(const int a[kVectorSize], const int b[kVectorSize],
                int c[kVectorSize]);

int main() {
  int a[kVectorSize] = {};
  int b[kVectorSize] = {};
  int c[kVectorSize] = {};

  for (int i = 0; i < kVectorSize; ++i) {
    a[i] = i - 17;
    b[i] = (i * 3) + 5;
  }

  vector_add(a, b, c);

  for (int i = 0; i < kVectorSize; ++i) {
    const int expected = a[i] + b[i];
    if (c[i] != expected) {
      std::cerr << "Mismatch at index " << i << ": got " << c[i]
                << ", expected " << expected << '\n';
      return 1;
    }
  }

  std::cout << "vector_add C simulation: PASS\n";
  return 0;
}
