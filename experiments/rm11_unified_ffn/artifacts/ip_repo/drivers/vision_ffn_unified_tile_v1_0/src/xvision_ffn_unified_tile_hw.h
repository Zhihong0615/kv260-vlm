// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2024.2 (64-bit)
// Tool Version Limit: 2024.11
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
// control
// 0x00 : Control signals
//        bit 0  - ap_start (Read/Write/COH)
//        bit 1  - ap_done (Read/COR)
//        bit 2  - ap_idle (Read)
//        bit 3  - ap_ready (Read/COR)
//        bit 7  - auto_restart (Read/Write)
//        bit 9  - interrupt (Read)
//        others - reserved
// 0x04 : Global Interrupt Enable Register
//        bit 0  - Global Interrupt Enable (Read/Write)
//        others - reserved
// 0x08 : IP Interrupt Enable Register (Read/Write)
//        bit 0 - enable ap_done interrupt (Read/Write)
//        bit 1 - enable ap_ready interrupt (Read/Write)
//        others - reserved
// 0x0c : IP Interrupt Status Register (Read/TOW)
//        bit 0 - ap_done (Read/TOW)
//        bit 1 - ap_ready (Read/TOW)
//        others - reserved
// 0x10 : Data signal of ap_return
//        bit 31~0 - ap_return[31:0] (Read)
// 0x18 : Data signal of weight_batch_f16
//        bit 31~0 - weight_batch_f16[31:0] (Read/Write)
// 0x1c : Data signal of weight_batch_f16
//        bit 31~0 - weight_batch_f16[63:32] (Read/Write)
// 0x20 : reserved
// 0x24 : Data signal of activation_tile_f32
//        bit 31~0 - activation_tile_f32[31:0] (Read/Write)
// 0x28 : Data signal of activation_tile_f32
//        bit 31~0 - activation_tile_f32[63:32] (Read/Write)
// 0x2c : reserved
// 0x30 : Data signal of output_batch_f32
//        bit 31~0 - output_batch_f32[31:0] (Read/Write)
// 0x34 : Data signal of output_batch_f32
//        bit 31~0 - output_batch_f32[63:32] (Read/Write)
// 0x38 : reserved
// 0x3c : Data signal of task_r
//        bit 31~0 - task_r[31:0] (Read/Write)
// 0x40 : reserved
// 0x44 : Data signal of active_N
//        bit 31~0 - active_N[31:0] (Read/Write)
// 0x48 : reserved
// 0x4c : Data signal of active_K
//        bit 31~0 - active_K[31:0] (Read/Write)
// 0x50 : reserved
// 0x54 : Data signal of active_M
//        bit 31~0 - active_M[31:0] (Read/Write)
// 0x58 : reserved
// 0x5c : Data signal of n_base
//        bit 31~0 - n_base[31:0] (Read/Write)
// 0x60 : reserved
// 0x64 : Data signal of m_base
//        bit 31~0 - m_base[31:0] (Read/Write)
// 0x68 : reserved
// 0x6c : Data signal of tile_rows
//        bit 31~0 - tile_rows[31:0] (Read/Write)
// 0x70 : reserved
// (SC = Self Clear, COR = Clear on Read, TOW = Toggle on Write, COH = Clear on Handshake)

#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_AP_CTRL                  0x00
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_GIE                      0x04
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_IER                      0x08
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ISR                      0x0c
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_AP_RETURN                0x10
#define XVISION_FFN_UNIFIED_TILE_CONTROL_BITS_AP_RETURN                32
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_WEIGHT_BATCH_F16_DATA    0x18
#define XVISION_FFN_UNIFIED_TILE_CONTROL_BITS_WEIGHT_BATCH_F16_DATA    64
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVATION_TILE_F32_DATA 0x24
#define XVISION_FFN_UNIFIED_TILE_CONTROL_BITS_ACTIVATION_TILE_F32_DATA 64
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_OUTPUT_BATCH_F32_DATA    0x30
#define XVISION_FFN_UNIFIED_TILE_CONTROL_BITS_OUTPUT_BATCH_F32_DATA    64
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_TASK_R_DATA              0x3c
#define XVISION_FFN_UNIFIED_TILE_CONTROL_BITS_TASK_R_DATA              32
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVE_N_DATA            0x44
#define XVISION_FFN_UNIFIED_TILE_CONTROL_BITS_ACTIVE_N_DATA            32
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVE_K_DATA            0x4c
#define XVISION_FFN_UNIFIED_TILE_CONTROL_BITS_ACTIVE_K_DATA            32
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVE_M_DATA            0x54
#define XVISION_FFN_UNIFIED_TILE_CONTROL_BITS_ACTIVE_M_DATA            32
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_N_BASE_DATA              0x5c
#define XVISION_FFN_UNIFIED_TILE_CONTROL_BITS_N_BASE_DATA              32
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_M_BASE_DATA              0x64
#define XVISION_FFN_UNIFIED_TILE_CONTROL_BITS_M_BASE_DATA              32
#define XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_TILE_ROWS_DATA           0x6c
#define XVISION_FFN_UNIFIED_TILE_CONTROL_BITS_TILE_ROWS_DATA           32

