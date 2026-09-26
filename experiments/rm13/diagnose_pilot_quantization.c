#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <inttypes.h>
#include <math.h>
#include <glob.h>

typedef struct {
    char magic[8];
    uint32_t version, bits, group_size, groups;
    int64_t k, m;
    uint64_t fingerprint;
} Header;

static uint64_t fnv64(const void *data, size_t size) {
    const unsigned char *bytes = (const unsigned char *) data;
    uint64_t hash = UINT64_C(14695981039346656037);
    for (size_t i = 0; i < size; ++i) {
        hash ^= bytes[i];
        hash *= UINT64_C(1099511628211);
    }
    return hash;
}

static int32_t round_ties_even(float value) {
    return (int32_t) nearbyintf(value);
}

static int read_bytes(const char *path, void *destination, size_t size) {
    FILE *file = fopen(path, "rb");
    if (file == NULL) return 0;
    const int ok = fread(destination, 1, size, file) == size;
    fclose(file);
    return ok;
}

static int read_cache(const char *path, Header *header, float **scales, uint8_t **codes) {
    FILE *file = fopen(path, "rb");
    if (file == NULL || fread(header, sizeof(*header), 1, file) != 1) {
        if (file != NULL) fclose(file);
        return 0;
    }
    if (memcmp(header->magic, "RM13WQ1", 7) != 0 || header->version != 1 ||
        header->bits != 4 || header->group_size != 128 ||
        header->groups != (uint32_t) ((header->k + 127) / 128)) {
        fclose(file);
        return 0;
    }
    const size_t scale_count = (size_t) header->m * header->groups;
    const size_t code_count = scale_count * 64;
    *scales = (float *) malloc(scale_count * sizeof(float));
    *codes = (uint8_t *) malloc(code_count);
    const int ok = *scales != NULL && *codes != NULL &&
        fread(*scales, sizeof(float), scale_count, file) == scale_count &&
        fread(*codes, 1, code_count, file) == code_count;
    fclose(file);
    if (!ok) {
        free(*scales); free(*codes); *scales = NULL; *codes = NULL;
    }
    return ok;
}

static void print_histogram_all(const char *cache_dir) {
    char pattern[1024];
    snprintf(pattern, sizeof(pattern), "%s/*_w4_g128.bin", cache_dir);
    glob_t files = {0};
    if (glob(pattern, 0, NULL, &files) != 0) {
        puts("HIST_FAIL glob");
        return;
    }
    uint64_t histogram[15] = {0};
    uint64_t total = 0;
    uint64_t valid_files = 0;
    for (size_t fi = 0; fi < files.gl_pathc; ++fi) {
        Header h;
        float *scales = NULL;
        uint8_t *codes = NULL;
        if (!read_cache(files.gl_pathv[fi], &h, &scales, &codes)) continue;
        ++valid_files;
        for (int64_t row = 0; row < h.m; ++row) {
            for (uint32_t group = 0; group < h.groups; ++group) {
                const int valid = (int) fmin(128.0, (double) h.k - (double) group * 128.0);
                const size_t offset = ((size_t) row * h.groups + group) * 64;
                for (int i = 0; i < valid; ++i) {
                    int q = (codes[offset + (size_t) i / 2] >> ((i & 1) * 4)) & 0x0f;
                    if (q & 0x08) q -= 16;
                    ++histogram[q + 7];
                    ++total;
                }
            }
        }
        free(scales); free(codes);
    }
    const uint64_t saturated = histogram[0] + histogram[14];
    printf("HIST files=%" PRIu64 " elements=%" PRIu64 " q-7..7=", valid_files, total);
    for (int i = 0; i < 15; ++i) printf("%s%" PRIu64, i ? "," : "", histogram[i]);
    printf(" saturated=%" PRIu64 " saturation_fraction=%.9g\n",
           saturated, (double) saturated / (double) total);
    globfree(&files);
}

static int diagnose_one(const char *cache_path, const char *tensor_dir, const char *op) {
    Header h;
    float *weight_scales = NULL;
    uint8_t *weight_codes = NULL;
    if (!read_cache(cache_path, &h, &weight_scales, &weight_codes)) {
        fprintf(stderr, "DIAG_FAIL cache=%s\n", cache_path);
        return 0;
    }

    char path[1024];
    const size_t weight_count = (size_t) h.k * (size_t) h.m;
    snprintf(path, sizeof(path), "%s/%s.weight.f16", tensor_dir, op);
    _Float16 *weight = (_Float16 *) malloc(weight_count * sizeof(_Float16));
    if (weight == NULL || !read_bytes(path, weight, weight_count * sizeof(_Float16)) ||
        fnv64(weight, weight_count * sizeof(_Float16)) != h.fingerprint) {
        fprintf(stderr, "DIAG_FAIL source weight or fingerprint op=%s\n", op);
        free(weight); free(weight_scales); free(weight_codes);
        return 0;
    }

    snprintf(path, sizeof(path), "%s/%s.activation.f32", tensor_dir, op);
    float *activation = (float *) malloc((size_t) h.k * sizeof(float));
    if (activation == NULL || !read_bytes(path, activation, (size_t) h.k * sizeof(float))) {
        fprintf(stderr, "DIAG_FAIL activation op=%s\n", op);
        free(weight); free(weight_scales); free(weight_codes); free(activation);
        return 0;
    }

    snprintf(path, sizeof(path), "%s/%s.output.f32", tensor_dir, op);
    float *reference = (float *) malloc((size_t) h.m * sizeof(float));
    if (reference == NULL || !read_bytes(path, reference, (size_t) h.m * sizeof(float))) {
        fprintf(stderr, "DIAG_FAIL original output op=%s\n", op);
        free(weight); free(weight_scales); free(weight_codes); free(activation); free(reference);
        return 0;
    }

    int8_t *activation_codes = (int8_t *) malloc((size_t) h.k);
    float *activation_scales = (float *) malloc((size_t) h.groups * sizeof(float));
    if (activation_codes == NULL || activation_scales == NULL) {
        fprintf(stderr, "DIAG_FAIL scratch op=%s\n", op);
        free(weight); free(weight_scales); free(weight_codes); free(activation); free(reference);
        free(activation_codes); free(activation_scales);
        return 0;
    }
    for (uint32_t group = 0; group < h.groups; ++group) {
        const int start = (int) group * 128;
        const int valid = (int) fmin(128.0, (double) h.k - start);
        float maximum = 0.0f;
        for (int i = 0; i < valid; ++i) maximum = fmaxf(maximum, fabsf(activation[start + i]));
        activation_scales[group] = maximum == 0.0f ? 1.0f : maximum / 127.0f;
        for (int i = 0; i < valid; ++i) {
            int q = round_ties_even(activation[start + i] / activation_scales[group]);
            if (q < -127) q = -127;
            if (q > 127) q = 127;
            activation_codes[start + i] = (int8_t) q;
        }
    }

    double squared_error = 0.0, squared_reference = 0.0, squared_output = 0.0;
    double dot = 0.0, max_abs = 0.0;
    uint64_t histogram[15] = {0}, saturated = 0;
    for (int64_t row = 0; row < h.m; ++row) {
        volatile float output = 0.0f;
        for (uint32_t group = 0; group < h.groups; ++group) {
            const int start = (int) group * 128;
            const int valid = (int) fmin(128.0, (double) h.k - start);
            const size_t offset = ((size_t) row * h.groups + group) * 64;
            int32_t partial = 0;
            for (int i = 0; i < valid; ++i) {
                int q = (weight_codes[offset + (size_t) i / 2] >> ((i & 1) * 4)) & 0x0f;
                if (q & 0x08) q -= 16;
                ++histogram[q + 7];
                if (q == -7 || q == 7) ++saturated;
                partial += q * (int32_t) activation_codes[start + i];
            }
            volatile float term = (float) partial;
            term = term * weight_scales[(size_t) row * h.groups + group];
            term = term * activation_scales[group];
            output = output + term;
        }
        const double actual = output;
        const double expected = reference[row];
        const double difference = actual - expected;
        max_abs = fmax(max_abs, fabs(difference));
        squared_error += difference * difference;
        squared_reference += expected * expected;
        squared_output += actual * actual;
        dot += actual * expected;
    }
    const double denominator = sqrt(squared_reference * squared_output);
    const double cosine = denominator == 0.0 ? 1.0 : dot / denominator;
    const char *suffix = strrchr(op, '-');
    const int layer = suffix == NULL ? -1 : atoi(suffix + 1);
    printf("DIAG qid=37804 op=%s layer=%d W4A8 K=%" PRId64 " M=%" PRId64
           " sampled_tokens=1 reference=RM11_original_capture source_fingerprint=match"
           " maxabs=%.9g rmse=%.9g cosine=%.15g\n",
           op, layer, h.k, h.m, max_abs, sqrt(squared_error / (double) h.m), cosine);
    printf("LAYER_HIST op=%s elements=%" PRIu64 " q-7..7=", op, weight_count);
    for (int i = 0; i < 15; ++i) printf("%s%" PRIu64, i ? "," : "", histogram[i]);
    printf(" saturated=%" PRIu64 " saturation_fraction=%.9g\n",
           saturated, (double) saturated / (double) weight_count);

    free(weight); free(weight_scales); free(weight_codes); free(activation); free(reference);
    free(activation_codes); free(activation_scales);
    return 1;
}

int main(int argc, char **argv) {
    if (argc < 4) {
        fprintf(stderr, "usage: %s W4_CACHE_DIR RM11_TENSOR_DIR TENSOR_NAME...\n", argv[0]);
        return 2;
    }
    print_histogram_all(argv[1]);
    for (int i = 3; i < argc; ++i) {
        char cache_path[1024];
        snprintf(cache_path, sizeof(cache_path), "%s/%s_w4_g128.bin", argv[1], argv[i]);
        if (!diagnose_one(cache_path, argv[2], argv[i])) return 1;
    }
    return 0;
}
