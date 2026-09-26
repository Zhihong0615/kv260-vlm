// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2024.2 (64-bit)
// Tool Version Limit: 2024.11
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
#ifndef XVISION_FFN_UNIFIED_TILE_H
#define XVISION_FFN_UNIFIED_TILE_H

#ifdef __cplusplus
extern "C" {
#endif

/***************************** Include Files *********************************/
#ifndef __linux__
#include "xil_types.h"
#include "xil_assert.h"
#include "xstatus.h"
#include "xil_io.h"
#else
#include <stdint.h>
#include <assert.h>
#include <dirent.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/mman.h>
#include <unistd.h>
#include <stddef.h>
#endif
#include "xvision_ffn_unified_tile_hw.h"

/**************************** Type Definitions ******************************/
#ifdef __linux__
typedef uint8_t u8;
typedef uint16_t u16;
typedef uint32_t u32;
typedef uint64_t u64;
#else
typedef struct {
#ifdef SDT
    char *Name;
#else
    u16 DeviceId;
#endif
    u64 Control_BaseAddress;
} XVision_ffn_unified_tile_Config;
#endif

typedef struct {
    u64 Control_BaseAddress;
    u32 IsReady;
} XVision_ffn_unified_tile;

typedef u32 word_type;

/***************** Macros (Inline Functions) Definitions *********************/
#ifndef __linux__
#define XVision_ffn_unified_tile_WriteReg(BaseAddress, RegOffset, Data) \
    Xil_Out32((BaseAddress) + (RegOffset), (u32)(Data))
#define XVision_ffn_unified_tile_ReadReg(BaseAddress, RegOffset) \
    Xil_In32((BaseAddress) + (RegOffset))
#else
#define XVision_ffn_unified_tile_WriteReg(BaseAddress, RegOffset, Data) \
    *(volatile u32*)((BaseAddress) + (RegOffset)) = (u32)(Data)
#define XVision_ffn_unified_tile_ReadReg(BaseAddress, RegOffset) \
    *(volatile u32*)((BaseAddress) + (RegOffset))

#define Xil_AssertVoid(expr)    assert(expr)
#define Xil_AssertNonvoid(expr) assert(expr)

#define XST_SUCCESS             0
#define XST_DEVICE_NOT_FOUND    2
#define XST_OPEN_DEVICE_FAILED  3
#define XIL_COMPONENT_IS_READY  1
#endif

/************************** Function Prototypes *****************************/
#ifndef __linux__
#ifdef SDT
int XVision_ffn_unified_tile_Initialize(XVision_ffn_unified_tile *InstancePtr, UINTPTR BaseAddress);
XVision_ffn_unified_tile_Config* XVision_ffn_unified_tile_LookupConfig(UINTPTR BaseAddress);
#else
int XVision_ffn_unified_tile_Initialize(XVision_ffn_unified_tile *InstancePtr, u16 DeviceId);
XVision_ffn_unified_tile_Config* XVision_ffn_unified_tile_LookupConfig(u16 DeviceId);
#endif
int XVision_ffn_unified_tile_CfgInitialize(XVision_ffn_unified_tile *InstancePtr, XVision_ffn_unified_tile_Config *ConfigPtr);
#else
int XVision_ffn_unified_tile_Initialize(XVision_ffn_unified_tile *InstancePtr, const char* InstanceName);
int XVision_ffn_unified_tile_Release(XVision_ffn_unified_tile *InstancePtr);
#endif

void XVision_ffn_unified_tile_Start(XVision_ffn_unified_tile *InstancePtr);
u32 XVision_ffn_unified_tile_IsDone(XVision_ffn_unified_tile *InstancePtr);
u32 XVision_ffn_unified_tile_IsIdle(XVision_ffn_unified_tile *InstancePtr);
u32 XVision_ffn_unified_tile_IsReady(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_EnableAutoRestart(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_DisableAutoRestart(XVision_ffn_unified_tile *InstancePtr);
u32 XVision_ffn_unified_tile_Get_return(XVision_ffn_unified_tile *InstancePtr);

void XVision_ffn_unified_tile_Set_weight_batch_f16(XVision_ffn_unified_tile *InstancePtr, u64 Data);
u64 XVision_ffn_unified_tile_Get_weight_batch_f16(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_Set_activation_tile_f32(XVision_ffn_unified_tile *InstancePtr, u64 Data);
u64 XVision_ffn_unified_tile_Get_activation_tile_f32(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_Set_output_batch_f32(XVision_ffn_unified_tile *InstancePtr, u64 Data);
u64 XVision_ffn_unified_tile_Get_output_batch_f32(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_Set_task_r(XVision_ffn_unified_tile *InstancePtr, u32 Data);
u32 XVision_ffn_unified_tile_Get_task_r(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_Set_active_N(XVision_ffn_unified_tile *InstancePtr, u32 Data);
u32 XVision_ffn_unified_tile_Get_active_N(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_Set_active_K(XVision_ffn_unified_tile *InstancePtr, u32 Data);
u32 XVision_ffn_unified_tile_Get_active_K(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_Set_active_M(XVision_ffn_unified_tile *InstancePtr, u32 Data);
u32 XVision_ffn_unified_tile_Get_active_M(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_Set_n_base(XVision_ffn_unified_tile *InstancePtr, u32 Data);
u32 XVision_ffn_unified_tile_Get_n_base(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_Set_m_base(XVision_ffn_unified_tile *InstancePtr, u32 Data);
u32 XVision_ffn_unified_tile_Get_m_base(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_Set_tile_rows(XVision_ffn_unified_tile *InstancePtr, u32 Data);
u32 XVision_ffn_unified_tile_Get_tile_rows(XVision_ffn_unified_tile *InstancePtr);

void XVision_ffn_unified_tile_InterruptGlobalEnable(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_InterruptGlobalDisable(XVision_ffn_unified_tile *InstancePtr);
void XVision_ffn_unified_tile_InterruptEnable(XVision_ffn_unified_tile *InstancePtr, u32 Mask);
void XVision_ffn_unified_tile_InterruptDisable(XVision_ffn_unified_tile *InstancePtr, u32 Mask);
void XVision_ffn_unified_tile_InterruptClear(XVision_ffn_unified_tile *InstancePtr, u32 Mask);
u32 XVision_ffn_unified_tile_InterruptGetEnabled(XVision_ffn_unified_tile *InstancePtr);
u32 XVision_ffn_unified_tile_InterruptGetStatus(XVision_ffn_unified_tile *InstancePtr);

#ifdef __cplusplus
}
#endif

#endif
