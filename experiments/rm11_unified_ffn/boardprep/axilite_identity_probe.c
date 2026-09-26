#define _GNU_SOURCE
#include <fcntl.h>
#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>

#define HLS_BASE UINT64_C(0xa0010000)
#define APM_BASE UINT64_C(0xa0000000)
#define MAP_BYTES UINT64_C(0x10000)
#define AP_CTRL 0x00u
#define AP_RETURN 0x10u
#define TASK 0x3cu
#define ACTIVE_N 0x44u
#define ACTIVE_K 0x4cu
#define ACTIVE_M 0x54u
#define N_BASE 0x5cu
#define M_BASE 0x64u
#define TILE_ROWS 0x6cu

static int text(const char *path, char *dst, size_t cap) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    size_t n = fread(dst, 1, cap - 1, f);
    int bad = ferror(f);
    fclose(f);
    if (bad) return -1;
    while (n && (dst[n - 1] == '\n' || dst[n - 1] == '\0')) --n;
    dst[n] = '\0';
    for (size_t i = 0; i < n; ++i) if (!dst[i]) dst[i] = ',';
    return 0;
}

static int get_u64(const char *path, uint64_t *v) {
    char s[80];
    if (text(path, s, sizeof(s)) || !s[0]) return -1;
    char *end = NULL;
    unsigned long long x = strtoull(s, &end, 0);
    if (end == s || *end) return -1;
    *v = (uint64_t)x;
    return 0;
}

static int find_uio(const char *wanted, char *dev, size_t dev_cap,
                    char *compat, size_t compat_cap, uint64_t *addr, uint64_t *size) {
    for (int id = 0; id < 64; ++id) {
        char path[256], name[128];
        snprintf(path, sizeof(path), "/sys/class/uio/uio%d/name", id);
        if (text(path, name, sizeof(name)) || strcmp(name, wanted)) continue;
        snprintf(dev, dev_cap, "/dev/uio%d", id);
        snprintf(path, sizeof(path), "/sys/class/uio/uio%d/device/of_node/compatible", id);
        if (text(path, compat, compat_cap)) return -1;
        snprintf(path, sizeof(path), "/sys/class/uio/uio%d/maps/map0/addr", id);
        if (get_u64(path, addr)) return -1;
        snprintf(path, sizeof(path), "/sys/class/uio/uio%d/maps/map0/size", id);
        if (get_u64(path, size)) return -1;
        return 0;
    }
    return -1;
}

static volatile uint32_t *map_dev(const char *dev) {
    int fd = open(dev, O_RDWR | O_SYNC);
    if (fd < 0) return NULL;
    void *p = mmap(NULL, (size_t)MAP_BYTES, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    return p == MAP_FAILED ? NULL : (volatile uint32_t *)p;
}

int main(void) {
    char hdev[64] = {0}, hcompat[256] = {0}, adev[64] = {0}, acompat[256] = {0};
    uint64_t haddr = 0, hsize = 0, aaddr = 0, asize = 0;
    if (find_uio("vision_ffn_unified_tile_0", hdev, sizeof(hdev), hcompat,
                 sizeof(hcompat), &haddr, &hsize) ||
        strcmp(hcompat, "xlnx,vision-ffn-unified-tile-1.0,generic-uio") ||
        haddr != HLS_BASE || hsize != MAP_BYTES) {
        fprintf(stderr, "RM11 HLS identity FAIL dev=%s compatible=%s addr=0x%" PRIx64 " size=0x%" PRIx64 "\n",
                hdev, hcompat, haddr, hsize);
        return 2;
    }
    if (find_uio("axi_perf_mon_0", adev, sizeof(adev), acompat, sizeof(acompat),
                 &aaddr, &asize) || strcmp(acompat, "generic-uio") ||
        aaddr != APM_BASE || asize != MAP_BYTES) {
        fprintf(stderr, "RM11 APM identity FAIL dev=%s compatible=%s addr=0x%" PRIx64 " size=0x%" PRIx64 "\n",
                adev, acompat, aaddr, asize);
        return 3;
    }
    printf("RM11_HLS_IDENTITY dev=%s compatible=%s addr=0x%" PRIx64 " size=0x%" PRIx64 " PASS\n",
           hdev, hcompat, haddr, hsize);
    printf("RM11_APM_IDENTITY dev=%s compatible=%s addr=0x%" PRIx64 " size=0x%" PRIx64 " PASS\n",
           adev, acompat, aaddr, asize);

    volatile uint32_t *regs = map_dev(hdev);
    if (!regs) { perror("mmap RM11 HLS UIO"); return 4; }
    regs[TASK / 4] = 99;
    regs[ACTIVE_N / 4] = 1120;
    regs[ACTIVE_K / 4] = 1152;
    regs[ACTIVE_M / 4] = 4304;
    regs[N_BASE / 4] = 0;
    regs[M_BASE / 4] = 0;
    regs[TILE_ROWS / 4] = 32;
    __sync_synchronize();
    regs[AP_CTRL / 4] = 1;
    for (unsigned i = 0; i < 100000000u; ++i) {
        if (regs[AP_CTRL / 4] & 2u) {
            int32_t ret = (int32_t)regs[AP_RETURN / 4];
            printf("RM11_AXILITE_INVALID_TASK ret=%" PRId32 " expected=-4 dma_pointer_used=0 %s\n",
                   ret, ret == -4 ? "PASS" : "FAIL");
            munmap((void *)regs, (size_t)MAP_BYTES);
            return ret == -4 ? 0 : 5;
        }
    }
    fprintf(stderr, "RM11 AXI-Lite invalid-task probe timed out\n");
    munmap((void *)regs, (size_t)MAP_BYTES);
    return 6;
}
