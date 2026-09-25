#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>

#define HLS_BASE UINT64_C(0xa0010000)
#define APM_BASE UINT64_C(0xa0000000)
#define MAP_BYTES UINT64_C(0x10000)
#define AP_CTRL 0x00u
#define AP_RETURN 0x10u
#define TASK 0x3cu
#define ACTIVE_N 0x44u
#define N_BASE 0x4cu
#define TILE_ROWS 0x5cu

typedef struct {
    int id;
    char dev[64];
    char compatible[256];
    uint64_t addr;
    uint64_t size;
} uio_info;

static int read_text(const char *path, char *dst, size_t cap) {
    FILE *file = fopen(path, "rb");
    if (!file) return -1;
    size_t n = fread(dst, 1, cap - 1, file);
    int failed = ferror(file);
    fclose(file);
    if (failed) return -1;
    while (n > 0 && (dst[n - 1] == '\n' || dst[n - 1] == '\0')) --n;
    dst[n] = '\0';
    for (size_t i = 0; i < n; ++i) if (dst[i] == '\0') dst[i] = ',';
    return 0;
}

static int read_u64(const char *path, uint64_t *value) {
    char text[64];
    if (read_text(path, text, sizeof(text)) != 0 || text[0] == '\0') return -1;
    errno = 0;
    char *end = NULL;
    unsigned long long parsed = strtoull(text, &end, 0);
    if (errno || end == text || *end != '\0') return -1;
    *value = (uint64_t)parsed;
    return 0;
}

static int find_uio(const char *wanted, uio_info *info) {
    for (int id = 0; id < 64; ++id) {
        char path[256], name[128];
        snprintf(path, sizeof(path), "/sys/class/uio/uio%d/name", id);
        if (read_text(path, name, sizeof(name)) != 0 || strcmp(name, wanted) != 0) continue;
        info->id = id;
        snprintf(info->dev, sizeof(info->dev), "/dev/uio%d", id);
        snprintf(path, sizeof(path), "/sys/class/uio/uio%d/device/of_node/compatible", id);
        if (read_text(path, info->compatible, sizeof(info->compatible)) != 0) info->compatible[0] = '\0';
        snprintf(path, sizeof(path), "/sys/class/uio/uio%d/maps/map0/addr", id);
        if (read_u64(path, &info->addr) != 0) return -1;
        snprintf(path, sizeof(path), "/sys/class/uio/uio%d/maps/map0/size", id);
        if (read_u64(path, &info->size) != 0) return -1;
        return 0;
    }
    return -1;
}

static volatile uint32_t *map_uio(const uio_info *info) {
    int fd = open(info->dev, O_RDWR | O_SYNC);
    if (fd < 0) return NULL;
    void *mapped = mmap(NULL, (size_t)MAP_BYTES, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    if (mapped == MAP_FAILED) return NULL;
    return (volatile uint32_t *)mapped;
}

static int64_t elapsed_ns(struct timespec start, struct timespec now) {
    return (int64_t)(now.tv_sec - start.tv_sec) * INT64_C(1000000000) +
           (int64_t)(now.tv_nsec - start.tv_nsec);
}

int main(void) {
    uio_info hls = {0}, apm = {0};
    if (find_uio("vision_ffn_down_tile_0", &hls) != 0) {
        fprintf(stderr, "RM09 identity FAIL: HLS UIO missing or has no map metadata\n");
        return 2;
    }
    if (strcmp(hls.compatible, "xlnx,vision-ffn-down-tile-1.0,generic-uio") != 0 ||
        hls.addr != HLS_BASE || hls.size != MAP_BYTES) {
        fprintf(stderr, "RM09 HLS identity mismatch: compatible=%s addr=0x%" PRIx64 " size=0x%" PRIx64 "\n",
                hls.compatible, hls.addr, hls.size);
        return 3;
    }
    printf("RM09_HLS_IDENTITY uio=%s compatible=%s addr=0x%" PRIx64 " size=0x%" PRIx64 " PASS\n",
           hls.dev, hls.compatible, hls.addr, hls.size);

    if (find_uio("axi_perf_mon_0", &apm) != 0) {
        fprintf(stderr, "RM09 identity FAIL: APM UIO missing or has no map metadata\n");
        return 4;
    }
    if (strcmp(apm.compatible, "generic-uio") != 0 || apm.addr != APM_BASE || apm.size != MAP_BYTES) {
        fprintf(stderr, "RM09 APM identity mismatch: compatible=%s addr=0x%" PRIx64 " size=0x%" PRIx64 "\n",
                apm.compatible, apm.addr, apm.size);
        return 5;
    }
    printf("RM09_APM_IDENTITY uio=%s compatible=%s addr=0x%" PRIx64 " size=0x%" PRIx64 " PASS\n",
           apm.dev, apm.compatible, apm.addr, apm.size);

    volatile uint32_t *regs = map_uio(&hls);
    if (!regs) {
        perror("mmap RM09 HLS UIO");
        return 6;
    }
    printf("AP_CTRL_before=0x%08" PRIx32 "\n", regs[AP_CTRL / 4]);

    /* Invalid task exits through scalar validation before any DMA address is used. */
    regs[TASK / 4] = 99;
    regs[ACTIVE_N / 4] = 1120;
    regs[N_BASE / 4] = 0;
    regs[TILE_ROWS / 4] = 32;
    __sync_synchronize();
    struct timespec start, now;
    clock_gettime(CLOCK_MONOTONIC, &start);
    regs[AP_CTRL / 4] = 1;
    int done = 0;
    do {
        if (regs[AP_CTRL / 4] & 2u) {
            done = 1;
            break;
        }
        clock_gettime(CLOCK_MONOTONIC, &now);
    } while (elapsed_ns(start, now) < INT64_C(1000000000));
    if (!done) {
        fprintf(stderr, "RM09 invalid-task probe timed out\n");
        munmap((void *)regs, (size_t)MAP_BYTES);
        return 7;
    }
    const int32_t result = (int32_t)regs[AP_RETURN / 4];
    printf("AXI_LITE_ABI_PROBE=0x%08" PRIx32 " (%" PRId32 ") expected=-4 %s dma_pointer_used=0\n",
           (uint32_t)result, result, result == -4 ? "PASS" : "FAIL");
    regs[AP_CTRL / 4] = 0;
    munmap((void *)regs, (size_t)MAP_BYTES);
    return result == -4 ? 0 : 8;
}
