#include <inttypes.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <xrt.h>

static long read_cma_free_kb(void) {
    FILE *fp = fopen("/proc/meminfo", "r");
    if (!fp) return -1;
    char line[256];
    long value = -1;
    while (fgets(line, sizeof(line), fp)) {
        if (sscanf(line, "CmaFree: %ld kB", &value) == 1) break;
    }
    fclose(fp);
    return value;
}

static long read_cma_success_pages(void) {
    FILE *fp = fopen("/sys/kernel/mm/cma/reserved/alloc_pages_success", "r");
    if (!fp) return -1;
    long value = -1;
    if (fscanf(fp, "%ld", &value) != 1) value = -1;
    fclose(fp);
    return value;
}

int main(int argc, char **argv) {
    const size_t bytes = argc > 1 ? (size_t)strtoull(argv[1], NULL, 0) : 4096;
    if (bytes < 4096 || (bytes & 4095) != 0) {
        fprintf(stderr, "size must be a page-rounded value >= 4096\n");
        return 1;
    }
    printf("requested_bytes=%zu CmaFree_before_kB=%ld CMA_success_pages_before=%ld\n",
           bytes, read_cma_free_kb(), read_cma_success_pages());
    unsigned int count = xclProbe();
    printf("xclProbe=%u\n", count);
    if (count == 0) return 2;

    xclDeviceHandle dev = xclOpen(0, NULL, XCL_INFO);
    if (!dev) {
        fprintf(stderr, "xclOpen(0) failed\n");
        return 3;
    }

    xclBufferHandle bo = xclAllocBO(dev, bytes, 0, 0);
    if (bo == 0) {
        fprintf(stderr, "xclAllocBO failed\n");
        xclClose(dev);
        return 4;
    }

    struct xclBOProperties props;
    memset(&props, 0, sizeof(props));
    if (xclGetBOProperties(dev, bo, &props) != 0) {
        fprintf(stderr, "xclGetBOProperties failed\n");
        xclFreeBO(dev, bo);
        xclClose(dev);
        return 5;
    }
    printf("allocated_bytes=%" PRIu64 " CmaFree_allocated_kB=%ld CMA_success_pages_allocated=%ld\n",
           props.size, read_cma_free_kb(), read_cma_success_pages());

    volatile uint32_t *p = (volatile uint32_t *)xclMapBO(dev, bo, true);
    if (!p) {
        fprintf(stderr, "xclMapBO failed\n");
        xclFreeBO(dev, bo);
        xclClose(dev);
        return 6;
    }

    p[0] = UINT32_C(0x524d3038);
    p[1] = UINT32_C(0xa55a1234);
    if (xclSyncBO(dev, bo, XCL_BO_SYNC_BO_TO_DEVICE, bytes, 0) != 0 ||
        xclSyncBO(dev, bo, XCL_BO_SYNC_BO_FROM_DEVICE, bytes, 0) != 0 ||
        p[0] != UINT32_C(0x524d3038) || p[1] != UINT32_C(0xa55a1234)) {
        fprintf(stderr, "BO sync/round-trip failed\n");
        xclUnmapBO(dev, bo, (void *)p);
        xclFreeBO(dev, bo);
        xclClose(dev);
        return 7;
    }

    printf("bo_handle=%u size=%" PRIu64 " paddr=0x%" PRIx64
           " map=%p round_trip=PASS CmaFree_before_release_kB=%ld CMA_success_pages_before_release=%ld\n",
           props.handle, props.size, props.paddr, (void *)p,
           read_cma_free_kb(), read_cma_success_pages());
    xclUnmapBO(dev, bo, (void *)p);
    xclFreeBO(dev, bo);
    xclClose(dev);
    printf("CmaFree_after_release_kB=%ld CMA_success_pages_after_release=%ld\n",
           read_cma_free_kb(), read_cma_success_pages());
    return 0;
}
