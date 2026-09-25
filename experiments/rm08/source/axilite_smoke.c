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

#define HLS_BASE 0xA0010000u
#define MAP_BYTES 0x10000u
#define AP_CTRL 0x00u
#define AP_RETURN 0x10u
#define TASK 0x3cu
#define ACTIVE_N 0x44u
#define N_BASE 0x4cu
#define TILE_ROWS 0x5cu

static int read_text(const char *path, char *dst, size_t cap) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    ssize_t n = read(fd, dst, cap - 1);
    close(fd);
    if (n < 0) return -1;
    while (n > 0 && (dst[n - 1] == '\n' || dst[n - 1] == '\0')) --n;
    dst[n] = '\0';
    for (ssize_t i = 0; i < n; ++i) if (dst[i] == '\0') dst[i] = ',';
    return 0;
}

static int find_uio(const char *wanted, char *dev, size_t dev_cap,
                    char *compatible, size_t compat_cap) {
    for (int i = 0; i < 64; ++i) {
        char path[256], name[128];
        snprintf(path, sizeof(path), "/sys/class/uio/uio%d/name", i);
        if (read_text(path, name, sizeof(name)) != 0) continue;
        if (strcmp(name, wanted) != 0) continue;
        snprintf(dev, dev_cap, "/dev/uio%d", i);
        snprintf(path, sizeof(path), "/sys/class/uio/uio%d/device/of_node/compatible", i);
        if (read_text(path, compatible, compat_cap) != 0) compatible[0] = '\0';
        return i;
    }
    return -1;
}

static volatile uint32_t *map_uio(const char *dev) {
    int fd = open(dev, O_RDWR | O_SYNC);
    if (fd < 0) return NULL;
    void *p = mmap(NULL, MAP_BYTES, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    if (p == MAP_FAILED) return NULL;
    return (volatile uint32_t *)p;
}

static int64_t elapsed_ns(struct timespec a, struct timespec b) {
    return (int64_t)(b.tv_sec - a.tv_sec) * INT64_C(1000000000) +
           (int64_t)(b.tv_nsec - a.tv_nsec);
}

int main(void) {
    char dev[64], compatible[256] = "";
    int id = find_uio("vision_ffn_down_tile_0", dev, sizeof(dev),
                      compatible, sizeof(compatible));
    if (id < 0) {
        fprintf(stderr, "vision_ffn_down_tile_0 UIO node missing\n");
        return 2;
    }
    char version_path[128], uio_version[64] = "UNKNOWN";
    snprintf(version_path, sizeof(version_path), "/sys/class/uio/uio%d/version", id);
    (void)read_text(version_path, uio_version, sizeof(uio_version));
    if (!strstr(compatible, "xlnx,vision-ffn-down-tile-1.0")) {
        fprintf(stderr, "unexpected HLS compatible/version: %s\n", compatible);
        return 3;
    }
    printf("HLS UIO=%s uio_version=%s compatible=%s expected_control_base=0x%08x\n",
           dev, uio_version, compatible, HLS_BASE);

    volatile uint32_t *regs = map_uio(dev);
    if (!regs) {
        perror("map HLS UIO");
        return 4;
    }
    const uint32_t before = regs[AP_CTRL / 4];
    printf("AP_CTRL_before=0x%08" PRIx32 " idle=%u\n", before, (before >> 2) & 1u);

    /* Invalid task returns -4 after scalar checks; no m_axi pointer is used. */
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
        fprintf(stderr, "safe AXI-Lite task probe timed out\n");
        munmap((void *)regs, MAP_BYTES);
        return 5;
    }
    const int32_t result = (int32_t)regs[AP_RETURN / 4];
    printf("AXI_LITE_ABI_PROBE=0x%08" PRIx32 " (%" PRId32 ") expected=-4 %s\n",
           (uint32_t)result, result, result == -4 ? "PASS" : "FAIL");
    regs[AP_CTRL / 4] = 0;
    munmap((void *)regs, MAP_BYTES);
    if (result != -4) return 6;

    char apm_dev[64], apm_compatible[256] = "";
    int apm_id = find_uio("axi_perf_mon_0", apm_dev, sizeof(apm_dev),
                          apm_compatible, sizeof(apm_compatible));
    if (apm_id < 0) {
        fprintf(stderr, "axi_perf_mon_0 UIO node missing\n");
        return 7;
    }
    volatile uint32_t *apm = map_uio(apm_dev);
    if (!apm) {
        perror("map APM UIO");
        return 8;
    }
    printf("APM UIO=%s compatible=%s GClockCounterMSB=0x%08" PRIx32
           " LSB=0x%08" PRIx32 "\n",
           apm_dev, apm_compatible, apm[0], apm[1]);
    munmap((void *)apm, MAP_BYTES);
    return 0;
}
