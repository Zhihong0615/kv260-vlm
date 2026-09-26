#!/usr/bin/env python3
"""Export and cross-check a small real RM13 W4A8 C/RTL fixture.

The W4 pack and scales are regenerated from captured F16 source and compared
bitwise with Q Worker’s full packed cache before the tile slice is emitted.
"""

import argparse
import hashlib
import json
import math
import struct
from pathlib import Path


CONTRACT_ID = "rm13-vision-ffn-symmetric-g128-v1"
CACHE_MAGIC = b"RM13WQ1\0"
FIXTURE_MAGIC = b"R13W4T01"
K = 1152
M = 4304
N = 1120
GROUP_SIZE = 128
GROUPS = (K + GROUP_SIZE - 1) // GROUP_SIZE


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def f32(value: float) -> float:
    return struct.unpack("<f", struct.pack("<f", value))[0]


def quantize_weight_slice(raw: bytes, active_m: int) -> tuple[bytes, bytes]:
    codes = bytearray(active_m * GROUPS * (GROUP_SIZE // 2))
    scale_bytes = bytearray(active_m * GROUPS * 4)
    for m in range(active_m):
        for group in range(GROUPS):
            kbase = group * GROUP_SIZE
            valid_k = min(GROUP_SIZE, K - kbase)
            values = [struct.unpack_from("<e", raw, (m * K + kbase + kk) * 2)[0]
                      for kk in range(valid_k)]
            if not all(math.isfinite(value) for value in values):
                raise ValueError("nonfinite F16 weight in captured fixture")
            max_abs = max((abs(value) for value in values), default=0.0)
            scale = f32(1.0 if max_abs == 0.0 else max_abs / 7.0)
            struct.pack_into("<f", scale_bytes, (m * GROUPS + group) * 4, scale)
            group_offset = (m * GROUPS + group) * (GROUP_SIZE // 2)
            for kk, value in enumerate(values):
                ratio = f32(value / scale)
                code = max(-7, min(7, round(ratio)))  # Python round is ties-to-even.
                nibble = code & 0xF
                byte_index = group_offset + kk // 2
                if kk & 1:
                    codes[byte_index] |= nibble << 4
                else:
                    codes[byte_index] |= nibble
    return bytes(codes), bytes(scale_bytes)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--weight", type=Path, required=True,
                        help="captured little-endian F16 FFN-up W[K,M] payload")
    parser.add_argument("--activation", type=Path, required=True,
                        help="captured little-endian F32 token-major X[K,N] payload")
    parser.add_argument("--packed-cache", type=Path, required=True,
                        help="Q Worker full `ffn_up-0_w4_g128.bin` cache")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--active-m", type=int, default=7)
    parser.add_argument("--active-n", type=int, default=1)
    parser.add_argument("--source-capture-root", type=Path)
    args = parser.parse_args()

    if not 1 <= args.active_m <= 16 or not 1 <= args.active_n <= 16:
        parser.error("fixture tile M/N must be in 1..16")
    if args.weight.stat().st_size != K * M * 2:
        parser.error("unexpected full FFN-up weight tensor size")
    if args.activation.stat().st_size != K * N * 4:
        parser.error("unexpected full FFN-up activation tensor size")

    raw_w = args.weight.read_bytes()[:args.active_m * K * 2]
    raw_x = args.activation.read_bytes()[:args.active_n * K * 4]
    packed_codes, weight_scales = quantize_weight_slice(raw_w, args.active_m)

    cache = args.packed_cache.read_bytes()
    if len(cache) < 48 or cache[:8] != CACHE_MAGIC:
        parser.error("invalid Q Worker packed-cache magic/header")
    version, bits, group_size, group_count = struct.unpack_from("<IIII", cache, 8)
    cache_k, cache_m, source_fnv = struct.unpack_from("<qqQ", cache, 24)
    if (version, bits, group_size, group_count, cache_k, cache_m) != (1, 4, GROUP_SIZE, GROUPS, K, M):
        parser.error("Q Worker packed-cache header does not match contract/FFN-up shape")
    cache_scales_offset = 48
    cache_codes_offset = cache_scales_offset + M * GROUPS * 4
    cache_scales = cache[cache_scales_offset:cache_codes_offset]
    cache_codes = cache[cache_codes_offset:cache_codes_offset + M * GROUPS * (GROUP_SIZE // 2)]
    if len(cache_codes) != M * GROUPS * (GROUP_SIZE // 2):
        parser.error("truncated Q Worker packed-cache payload")
    slice_codes = bytearray(args.active_m * GROUPS * (GROUP_SIZE // 2))
    slice_scales = bytearray(args.active_m * GROUPS * 4)
    code_row_bytes = GROUPS * (GROUP_SIZE // 2)
    scale_row_bytes = GROUPS * 4
    for m in range(args.active_m):
        slice_codes[m * code_row_bytes:(m + 1) * code_row_bytes] = \
            cache_codes[m * code_row_bytes:(m + 1) * code_row_bytes]
        slice_scales[m * scale_row_bytes:(m + 1) * scale_row_bytes] = \
            cache_scales[m * scale_row_bytes:(m + 1) * scale_row_bytes]
    if bytes(slice_codes) != packed_codes:
        parser.error("independent F16→W4 codes differ from Q Worker packed cache slice")
    if bytes(slice_scales) != weight_scales:
        parser.error("independent F16→F32 W scales differ bitwise from Q Worker cache slice")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("wb") as target:
        target.write(FIXTURE_MAGIC)
        target.write(struct.pack("<III", K, args.active_m, args.active_n))
        target.write(packed_codes)
        target.write(weight_scales)
        target.write(raw_x)

    manifest = {
        "contract_id": CONTRACT_ID,
        "fixture_kind": "real-packed-ffn-up-W4A8-csim-input",
        "source": "RM11 Q37804 CPU board_capture q37804-cpu, ffn_up-0",
        "source_capture_root": str(args.source_capture_root) if args.source_capture_root else None,
        "source_weight_path": str(args.weight),
        "source_weight_sha256": sha256(args.weight),
        "source_activation_path": str(args.activation),
        "source_activation_sha256": sha256(args.activation),
        "q_worker_cache_path": str(args.packed_cache),
        "q_worker_cache_sha256": sha256(args.packed_cache),
        "q_worker_cache_source_fnv64": f"{source_fnv:016x}",
        "independent_w4_code_match": "bitwise exact for emitted M slice",
        "independent_weight_scale_match": "bitwise exact F32 for emitted M slice",
        "source_layout": {
            "weight": "GGML W[K,M], K contiguous within output row, little-endian F16",
            "activation": "token-major X[K,N], K contiguous within token, little-endian F32",
        },
        "dimensions": {"K": K, "M": args.active_m, "N": args.active_n},
        "slice": "first output rows and first token rows",
        "fixture_path": str(args.output),
        "fixture_bytes": args.output.stat().st_size,
        "fixture_sha256": sha256(args.output),
        "fixture_encoding": "R13W4T01 + u32_le K/M/N + packed W4 [M,G,64] + F32 scales [M,G] + F32 X [N,K]",
        "packed_layout": "m-major/group-major, low nibble even local K, signed twos-complement [-7,7]",
    }
    args.manifest.write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
