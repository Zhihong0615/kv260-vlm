#define _GNU_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <time.h>
#include <unistd.h>
#include <xrt.h>

#define K 4304u
#define M 1152u
#define TILE_N 32u
#define TILE_M 16u
#define M_BATCH 128u
#define K_WORDS (K / 8u)
#define WEIGHT_BATCH_BYTES ((size_t)M_BATCH * K * 2u)
#define X_TILE_BYTES ((size_t)TILE_N * K * 4u)
#define Y_BATCH_BYTES ((size_t)TILE_N * M_BATCH * 4u)
#define HLS_MAP_BYTES 0x10000u
#define APM_MAP_BYTES 0x10000u
#define HLS_BASE 0xA0010000u

#define REG_AP_CTRL 0x00u
#define REG_AP_RETURN 0x10u
#define REG_W_LO 0x18u
#define REG_W_HI 0x1cu
#define REG_X_LO 0x24u
#define REG_X_HI 0x28u
#define REG_Y_LO 0x30u
#define REG_Y_HI 0x34u
#define REG_TASK 0x3cu
#define REG_ACTIVE_N 0x44u
#define REG_N_BASE 0x4cu
#define REG_M_BASE 0x54u
#define REG_TILE_ROWS 0x5cu
#define APM_GCC_MSB 0x00u
#define APM_GCC_LSB 0x04u
#define APM_METRIC_SELECT0 0x44u
#define APM_METRIC_COUNTER0 0x100u
#define APM_METRIC_COUNTER1 0x110u
#define APM_METRIC_COUNTER2 0x120u
#define APM_CONTROL 0x300u

enum { TASK_STAGE_X = 0, TASK_COMPUTE_W = 1 };

typedef struct {
    uint64_t pack_ns;
    uint64_t sync_to_ns;
    uint64_t sync_from_ns;
    uint64_t unpack_ns;
    uint64_t hls_wait_ns;
    uint64_t hls_cycles;
    uint64_t stage_wait_ns;
    uint64_t compute_wait_ns;
    uint64_t stage_cycles;
    uint64_t compute_cycles;
    uint64_t control_submit_ns;
    uint64_t wall_ns;
    uint64_t input_bytes;
    uint64_t output_bytes;
    uint64_t apm_w_read_bytes;
    uint64_t apm_x_read_bytes;
    uint64_t apm_y_write_bytes;
    uint64_t stage_commands;
    uint64_t compute_commands;
} Stats;

static uint64_t now_ns(void) {
    struct timespec t;
    clock_gettime(CLOCK_MONOTONIC_RAW, &t);
    return (uint64_t)t.tv_sec * UINT64_C(1000000000) + (uint64_t)t.tv_nsec;
}

static size_t page_round(size_t n) {
    return (n + 4095u) & ~(size_t)4095u;
}

static int read_exact(const char *path, void *dst, size_t bytes) {
    FILE *f = fopen(path, "rb");
    if (!f) return -1;
    size_t got = fread(dst, 1, bytes, f);
    int extra = fgetc(f);
    int ok = got == bytes && extra == EOF && !ferror(f);
    fclose(f);
    return ok ? 0 : -1;
}

static long cma_free_kb(void) {
    FILE *f = fopen("/proc/meminfo", "r");
    char line[256];
    long value = -1;
    if (!f) return value;
    while (fgets(line, sizeof(line), f)) {
        if (sscanf(line, "CmaFree: %ld kB", &value) == 1) break;
    }
    fclose(f);
    return value;
}

static long cma_pages_success(void) {
    FILE *f = fopen("/sys/kernel/mm/cma/reserved/alloc_pages_success", "r");
    long v = -1;
    if (f) {
        if (fscanf(f, "%ld", &v) != 1) v = -1;
        fclose(f);
    }
    return v;
}

static int read_text(const char *path, char *dst, size_t cap) {
    int fd = open(path, O_RDONLY);
    if (fd < 0) return -1;
    ssize_t n = read(fd, dst, cap - 1);
    close(fd);
    if (n < 0) return -1;
    while (n > 0 && (dst[n - 1] == '\n' || dst[n - 1] == '\0')) --n;
    dst[n] = '\0';
    return 0;
}

static int find_uio(const char *wanted, char *dev, size_t dev_cap) {
    for (int i = 0; i < 64; ++i) {
        char path[256], name[128];
        snprintf(path, sizeof(path), "/sys/class/uio/uio%d/name", i);
        if (read_text(path, name, sizeof(name)) != 0) continue;
        if (strcmp(name, wanted) == 0) {
            snprintf(dev, dev_cap, "/dev/uio%d", i);
            return i;
        }
    }
    return -1;
}

static volatile uint32_t *map_uio(const char *dev, size_t bytes) {
    int fd = open(dev, O_RDWR | O_SYNC);
    if (fd < 0) return NULL;
    void *p = mmap(NULL, bytes, PROT_READ | PROT_WRITE, MAP_SHARED, fd, 0);
    close(fd);
    return p == MAP_FAILED ? NULL : (volatile uint32_t *)p;
}

static uint32_t apm_cycles32(volatile uint32_t *apm) {
    return apm[APM_GCC_LSB / 4u];
}

static void reg64(volatile uint32_t *regs, unsigned lo, uint64_t value) {
    regs[lo / 4u] = (uint32_t)value;
    regs[(lo + 4u) / 4u] = (uint32_t)(value >> 32);
}

static int run_task(volatile uint32_t *regs, volatile uint32_t *apm,
                    uint64_t waddr, uint64_t xaddr, uint64_t yaddr,
                    unsigned task, unsigned active_n, unsigned n_base,
                    unsigned m_base, unsigned tile_rows, Stats *s) {
    uint64_t t0 = now_ns();
    reg64(regs, REG_W_LO, waddr);
    reg64(regs, REG_X_LO, xaddr);
    reg64(regs, REG_Y_LO, yaddr);
    regs[REG_TASK / 4u] = task;
    regs[REG_ACTIVE_N / 4u] = active_n;
    regs[REG_N_BASE / 4u] = n_base;
    regs[REG_M_BASE / 4u] = m_base;
    regs[REG_TILE_ROWS / 4u] = tile_rows;
    __sync_synchronize();
    regs[REG_AP_CTRL / 4u] = 1u;
    __sync_synchronize();
    uint64_t t1 = now_ns();
    s->control_submit_ns += t1 - t0;
    uint32_t c0 = apm_cycles32(apm);
    uint64_t p0 = now_ns();
    uint64_t deadline = p0 + UINT64_C(30000000000);
    while ((regs[REG_AP_CTRL / 4u] & 2u) == 0u) {
        if (now_ns() > deadline) {
            fprintf(stderr, "HLS timeout task=%u N=%u n_base=%u m_base=%u ctrl=0x%08x\n",
                    task, active_n, n_base, m_base, regs[REG_AP_CTRL / 4u]);
            return -1;
        }
    }
    uint64_t p1 = now_ns();
    uint32_t c1 = apm_cycles32(apm);
    uint32_t dc = c1 - c0;
    s->hls_wait_ns += p1 - p0;
    s->hls_cycles += dc;
    if (task == TASK_STAGE_X) {
        s->stage_wait_ns += p1 - p0;
        s->stage_cycles += dc;
        ++s->stage_commands;
    } else {
        s->compute_wait_ns += p1 - p0;
        s->compute_cycles += dc;
        ++s->compute_commands;
    }
    int32_t status = (int32_t)regs[REG_AP_RETURN / 4u];
    if (status != 0) {
        fprintf(stderr, "HLS returned %" PRId32 " task=%u N=%u n_base=%u m_base=%u\n",
                status, task, active_n, n_base, m_base);
        return -1;
    }
    return 0;
}

static int alloc_bo(xclDeviceHandle dev, size_t bytes, xclBufferHandle *bo,
                    struct xclBOProperties *prop, void **mapping) {
    size_t rounded = page_round(bytes);
    *bo = xclAllocBO(dev, rounded, 0, 0);
    if (*bo == 0) return -1;
    memset(prop, 0, sizeof(*prop));
    if (xclGetBOProperties(dev, *bo, prop) != 0) return -1;
    *mapping = xclMapBO(dev, *bo, true);
    if (!*mapping) return -1;
    memset(*mapping, 0, rounded);
    return 0;
}

static int sync_bo(xclDeviceHandle dev, xclBufferHandle bo, int direction,
                   size_t bytes, uint64_t *time_ns) {
    uint64_t t0 = now_ns();
    int rc = xclSyncBO(dev, bo, direction, bytes, 0);
    *time_ns += now_ns() - t0;
    return rc;
}

int main(int argc, char **argv) {
    if (argc != 6 && argc != 7) {
        fprintf(stderr, "usage: %s WEIGHT_F16 ACTIVATION_F32 CPU_OUTPUT_F32 LAYER ACTIVE_N [CALLS]\n", argv[0]);
        return 2;
    }
    unsigned active_n = (unsigned)strtoul(argv[5], NULL, 10);
    unsigned calls = argc > 6 ? (unsigned)strtoul(argv[6], NULL, 10) : 1u;
    if ((active_n != 280u && active_n != 1120u) || calls == 0u) return 2;
    size_t w_bytes = (size_t)M * K * sizeof(uint16_t);
    size_t x_bytes = (size_t)active_n * K * sizeof(float);
    size_t y_bytes = (size_t)active_n * M * sizeof(float);
    uint16_t *raw_w = malloc(w_bytes);
    float *raw_x = malloc(x_bytes);
    float *raw_y = malloc(y_bytes);
    float *result = calloc((size_t)active_n * M, sizeof(float));
    if (!raw_w || !raw_x || !raw_y || !result) {
        fprintf(stderr, "host allocation failed\n");
        return 3;
    }
    if (read_exact(argv[1], raw_w, w_bytes) || read_exact(argv[2], raw_x, x_bytes) ||
        read_exact(argv[3], raw_y, y_bytes)) {
        fprintf(stderr, "input file size/read mismatch\n");
        return 4;
    }

    char hls_dev[64], apm_dev[64];
    if (find_uio("vision_ffn_down_tile_0", hls_dev, sizeof(hls_dev)) < 0 ||
        find_uio("axi_perf_mon_0", apm_dev, sizeof(apm_dev)) < 0) {
        fprintf(stderr, "required RM07 UIO device missing\n");
        return 5;
    }
    volatile uint32_t *regs = map_uio(hls_dev, HLS_MAP_BYTES);
    volatile uint32_t *apm = map_uio(apm_dev, APM_MAP_BYTES);
    if (!regs || !apm) {
        perror("mmap UIO");
        return 6;
    }

    long cma_before = cma_free_kb();
    long pages_before = cma_pages_success();
    if (xclProbe() == 0u) {
        fprintf(stderr, "XRT found no device\n");
        return 7;
    }
    xclDeviceHandle dev = xclOpen(0, NULL, XCL_INFO);
    if (!dev) {
        fprintf(stderr, "xclOpen failed\n");
        return 8;
    }
    xclBufferHandle wbo = 0, xbo = 0, ybo = 0;
    struct xclBOProperties wp, xp, yp;
    void *wm = NULL, *xm = NULL, *ym = NULL;
    if (alloc_bo(dev, WEIGHT_BATCH_BYTES, &wbo, &wp, &wm) ||
        alloc_bo(dev, X_TILE_BYTES, &xbo, &xp, &xm) ||
        alloc_bo(dev, Y_BATCH_BYTES, &ybo, &yp, &ym)) {
        fprintf(stderr, "bounded XRT BO allocation/map failed\n");
        return 9;
    }
    printf("RM08_RUN layer=%s K_M_N=%u_%u_%u calls=%u\n", argv[4], K, M, active_n, calls);
    printf("CMA before_kB=%ld allocated_kB=%ld pages_before=%ld pages_after=%ld BO_bytes=%" PRIu64 "+%" PRIu64 "+%" PRIu64 " rounded_total=%zu\n",
           cma_before, cma_free_kb(), pages_before, cma_pages_success(), wp.size, xp.size, yp.size,
           page_round(WEIGHT_BATCH_BYTES) + page_round(X_TILE_BYTES) + page_round(Y_BATCH_BYTES));
    long cma_min_kb = cma_free_kb();
    printf("BO paddr W=0x%" PRIx64 " X=0x%" PRIx64 " Y=0x%" PRIx64 " HLS=%s APM=%s APM_GCC_MSB=0x%08x LSB=0x%08x\n",
           wp.paddr, xp.paddr, yp.paddr, hls_dev, apm_dev,
           apm[APM_GCC_MSB / 4u], apm[APM_GCC_LSB / 4u]);

    /* APM 5.0 selectors: event 3=read bytes, event 2=write bytes;
       selector bits [7:5] choose W/X/Y monitor slots 0/1/2. */
    apm[APM_METRIC_SELECT0 / 4u] = 3u | (35u << 8) | (66u << 16);
    apm[APM_CONTROL / 4u] = (1u << 1) | (1u << 17); /* reset metrics and global clock */
    __sync_synchronize();
    usleep(1000);
    apm[APM_CONTROL / 4u] = 1u | (1u << 16); /* enable metrics and global clock */
    __sync_synchronize();
    usleep(1000);

    uint64_t cal0_ns = now_ns();
    uint32_t cal0_cycles = apm_cycles32(apm);
    struct timespec wait = {.tv_sec = 0, .tv_nsec = 200000000};
    nanosleep(&wait, NULL);
    uint64_t cal1_ns = now_ns();
    uint32_t cal1_cycles = apm_cycles32(apm);
    double pl_hz = (double)(uint32_t)(cal1_cycles - cal0_cycles) * 1.0e9 /
                   (double)(cal1_ns - cal0_ns);
    printf("APM_CLOCK_CAL cycles=%" PRIu32 " wall_ms=%.3f measured_MHz=%.3f\n",
           (uint32_t)(cal1_cycles - cal0_cycles), (double)(cal1_ns - cal0_ns) / 1.0e6,
           pl_hz / 1.0e6);

    Stats total = {0};
    for (unsigned call = 0; call < calls; ++call) {
        Stats one = {0};
        uint64_t tcall = now_ns();
        uint32_t apm_w0 = apm[APM_METRIC_COUNTER0 / 4u];
        uint32_t apm_x0 = apm[APM_METRIC_COUNTER1 / 4u];
        uint32_t apm_y0 = apm[APM_METRIC_COUNTER2 / 4u];
        unsigned nt = (active_n + TILE_N - 1u) / TILE_N;
        for (unsigned nbase = 0; nbase < active_n; nbase += TILE_N) {
            unsigned rows = active_n - nbase < TILE_N ? active_n - nbase : TILE_N;
            uint64_t pack0 = now_ns();
            for (unsigned n = 0; n < rows; ++n) {
                for (unsigned kw = 0; kw < K_WORDS; ++kw) {
                    size_t src = ((size_t)(nbase + n) * K + (size_t)kw * 8u) * sizeof(float);
                    size_t dst = ((size_t)n * K_WORDS + kw) * 32u;
                    memcpy((uint8_t *)xm + dst, (const uint8_t *)raw_x + src, 32u);
                }
            }
            one.pack_ns += now_ns() - pack0;
            size_t x_used = (size_t)rows * K * sizeof(float);
            one.input_bytes += x_used;
            if (sync_bo(dev, xbo, XCL_BO_SYNC_BO_TO_DEVICE, x_used, &one.sync_to_ns) != 0) {
                fprintf(stderr, "X buffer sync-to-device failed\n");
                return 10;
            }
            if (run_task(regs, apm, wp.paddr, xp.paddr, yp.paddr, TASK_STAGE_X,
                         active_n, nbase, 0, rows, &one) != 0) return 11;

            for (unsigned mbase = 0; mbase < M; mbase += M_BATCH) {
                pack0 = now_ns();
                for (unsigned bt = 0; bt < M_BATCH / TILE_M; ++bt) {
                    for (unsigned mi = 0; mi < TILE_M; ++mi) {
                        unsigned m = mbase + bt * TILE_M + mi;
                        for (unsigned kw = 0; kw < K_WORDS; ++kw) {
                            size_t src = ((size_t)m * K + (size_t)kw * 8u) * sizeof(uint16_t);
                            size_t dst = ((size_t)bt * TILE_M * K_WORDS +
                                          (size_t)mi * K_WORDS + kw) * 16u;
                            memcpy((uint8_t *)wm + dst, (const uint8_t *)raw_w + src, 16u);
                        }
                    }
                }
                one.pack_ns += now_ns() - pack0;
                one.input_bytes += WEIGHT_BATCH_BYTES;
                if (sync_bo(dev, wbo, XCL_BO_SYNC_BO_TO_DEVICE, WEIGHT_BATCH_BYTES,
                            &one.sync_to_ns) != 0) {
                    fprintf(stderr, "W buffer sync-to-device failed\n");
                    return 12;
                }
                if (run_task(regs, apm, wp.paddr, xp.paddr, yp.paddr, TASK_COMPUTE_W,
                             active_n, nbase, mbase, rows, &one) != 0) return 13;
                size_t y_payload = (size_t)rows * M_BATCH * sizeof(float);
                /* The HLS output has fixed 32-row strides between its eight 16-channel banks. */
                if (sync_bo(dev, ybo, XCL_BO_SYNC_BO_FROM_DEVICE, Y_BATCH_BYTES,
                            &one.sync_from_ns) != 0) {
                    fprintf(stderr, "Y buffer sync-from-device failed\n");
                    return 14;
                }
                one.output_bytes += y_payload;
                uint64_t unpack0 = now_ns();
                const float *yb = (const float *)ym;
                for (unsigned bt = 0; bt < M_BATCH / TILE_M; ++bt) {
                    for (unsigned n = 0; n < rows; ++n) {
                        for (unsigned mw = 0; mw < TILE_M / 8u; ++mw) {
                            size_t src = (size_t)bt * TILE_N * TILE_M +
                                         (size_t)n * TILE_M + (size_t)mw * 8u;
                            size_t dst = (size_t)(nbase + n) * M + mbase +
                                         (size_t)bt * TILE_M + (size_t)mw * 8u;
                            memcpy(result + dst, yb + src, 8u * sizeof(float));
                        }
                    }
                }
                one.unpack_ns += now_ns() - unpack0;
            }
        }
        one.wall_ns = now_ns() - tcall;
        one.apm_w_read_bytes = (uint32_t)(apm[APM_METRIC_COUNTER0 / 4u] - apm_w0);
        one.apm_x_read_bytes = (uint32_t)(apm[APM_METRIC_COUNTER1 / 4u] - apm_x0);
        one.apm_y_write_bytes = (uint32_t)(apm[APM_METRIC_COUNTER2 / 4u] - apm_y0);
        total.pack_ns += one.pack_ns;
        total.sync_to_ns += one.sync_to_ns;
        total.sync_from_ns += one.sync_from_ns;
        total.unpack_ns += one.unpack_ns;
        total.hls_wait_ns += one.hls_wait_ns;
        total.hls_cycles += one.hls_cycles;
        total.stage_wait_ns += one.stage_wait_ns;
        total.compute_wait_ns += one.compute_wait_ns;
        total.stage_cycles += one.stage_cycles;
        total.compute_cycles += one.compute_cycles;
        total.control_submit_ns += one.control_submit_ns;
        total.wall_ns += one.wall_ns;
        total.input_bytes += one.input_bytes;
        total.output_bytes += one.output_bytes;
        total.apm_w_read_bytes += one.apm_w_read_bytes;
        total.apm_x_read_bytes += one.apm_x_read_bytes;
        total.apm_y_write_bytes += one.apm_y_write_bytes;
        total.stage_commands += one.stage_commands;
        total.compute_commands += one.compute_commands;
        if (cma_free_kb() >= 0 && cma_free_kb() < cma_min_kb) cma_min_kb = cma_free_kb();
        double kernel_s = (double)one.hls_wait_ns / 1.0e9;
        double gmac_s = ((double)K * M * active_n) / (kernel_s * 1.0e9);
        double apm_gbps = (double)(one.apm_w_read_bytes + one.apm_x_read_bytes +
                                   one.apm_y_write_bytes) / (kernel_s * 1.0e9);
        printf("CALL=%u N=%u tiles=%u commands=%" PRIu64 "/%" PRIu64
               " pack_ms=%.3f xrt_sync_to_ms=%.3f xrt_sync_from_ms=%.3f "
               "control_submit_ms=%.3f hls_wait_ms=%.3f apm_cycles=%" PRIu64
               " compute_cycles=%" PRIu64 " stage_cycles=%" PRIu64
               " output_unpack_ms=%.3f wall_ms=%.3f input_bytes=%" PRIu64
               " output_bytes=%" PRIu64 " APM_W_read=%" PRIu64
               " APM_X_read=%" PRIu64 " APM_Y_write=%" PRIu64
               " APM_GBps=%.4f GMACps=%.3f CMA_current_kB=%ld CMA_min_kB=%ld\n",
               call + 1u, active_n, nt, one.stage_commands, one.compute_commands,
               one.pack_ns / 1.0e6, one.sync_to_ns / 1.0e6, one.sync_from_ns / 1.0e6,
               one.control_submit_ns / 1.0e6, one.hls_wait_ns / 1.0e6,
               one.hls_cycles, one.compute_cycles, one.stage_cycles,
               one.unpack_ns / 1.0e6, one.wall_ns / 1.0e6, one.input_bytes,
               one.output_bytes, one.apm_w_read_bytes, one.apm_x_read_bytes,
               one.apm_y_write_bytes, apm_gbps, gmac_s, cma_free_kb(), cma_min_kb);
    }

    double max_abs = 0.0, sum_sq = 0.0, dot = 0.0, ng = 0.0, nr = 0.0;
    size_t count = (size_t)active_n * M;
    for (size_t i = 0; i < count; ++i) {
        double got = result[i], ref = raw_y[i], e = got - ref;
        if (fabs(e) > max_abs) max_abs = fabs(e);
        sum_sq += e * e;
        dot += got * ref;
        ng += got * got;
        nr += ref * ref;
    }
    double rmse = sqrt(sum_sq / (double)count);
    double cosine = dot / sqrt(ng * nr);
    double hls_s = (double)total.hls_wait_ns / 1.0e9;
    double wall_s = (double)total.wall_ns / 1.0e9;
    double total_gmac_s = (double)calls * K * M * active_n / (hls_s * 1.0e9);
    double system_gmac_s = (double)calls * K * M * active_n / (wall_s * 1.0e9);
    printf("TOTAL calls=%u N=%u pack_ms=%.3f xrt_sync_to_ms=%.3f xrt_sync_from_ms=%.3f "
           "control_submit_ms=%.3f hls_wait_ms=%.3f cycles=%" PRIu64
           " compute_cycles=%" PRIu64 " stage_cycles=%" PRIu64
           " unpack_ms=%.3f wall_ms=%.3f input_bytes=%" PRIu64
           " output_bytes=%" PRIu64 " APM_W_read=%" PRIu64
           " APM_X_read=%" PRIu64 " APM_Y_write=%" PRIu64
           " kernel_GMACps=%.3f system_GMACps=%.3f max_abs=%.9g RMSE=%.9g cosine=%.15f\n",
           calls, active_n, total.pack_ns / 1.0e6, total.sync_to_ns / 1.0e6,
           total.sync_from_ns / 1.0e6, total.control_submit_ns / 1.0e6,
           total.hls_wait_ns / 1.0e6, total.hls_cycles, total.compute_cycles,
           total.stage_cycles, total.unpack_ns / 1.0e6, total.wall_ns / 1.0e6,
           total.input_bytes, total.output_bytes, total.apm_w_read_bytes,
           total.apm_x_read_bytes, total.apm_y_write_bytes, total_gmac_s, system_gmac_s,
           max_abs, rmse, cosine);

    int numeric_ok = isfinite(max_abs) && isfinite(rmse) && isfinite(cosine) &&
                     max_abs <= 1.0e-3 && rmse <= 1.0e-4 && cosine >= 0.999;
    if (!numeric_ok) fprintf(stderr, "numeric comparison outside RM08 smoke tolerance\n");

    xclUnmapBO(dev, wbo, wm);
    xclUnmapBO(dev, xbo, xm);
    xclUnmapBO(dev, ybo, ym);
    xclFreeBO(dev, wbo);
    xclFreeBO(dev, xbo);
    xclFreeBO(dev, ybo);
    xclClose(dev);
    printf("CMA after_release_kB=%ld pages_after_release=%ld allocated_total_bytes=%zu\n",
           cma_free_kb(), cma_pages_success(),
           page_round(WEIGHT_BATCH_BYTES) + page_round(X_TILE_BYTES) + page_round(Y_BATCH_BYTES));
    return numeric_ok ? 0 : 15;
}
