// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2024.2 (64-bit)
// Tool Version Limit: 2024.11
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
/***************************** Include Files *********************************/
#include "xvision_ffn_unified_tile.h"

/************************** Function Implementation *************************/
#ifndef __linux__
int XVision_ffn_unified_tile_CfgInitialize(XVision_ffn_unified_tile *InstancePtr, XVision_ffn_unified_tile_Config *ConfigPtr) {
    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(ConfigPtr != NULL);

    InstancePtr->Control_BaseAddress = ConfigPtr->Control_BaseAddress;
    InstancePtr->IsReady = XIL_COMPONENT_IS_READY;

    return XST_SUCCESS;
}
#endif

void XVision_ffn_unified_tile_Start(XVision_ffn_unified_tile *InstancePtr) {
    u32 Data;

    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_AP_CTRL) & 0x80;
    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_AP_CTRL, Data | 0x01);
}

u32 XVision_ffn_unified_tile_IsDone(XVision_ffn_unified_tile *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_AP_CTRL);
    return (Data >> 1) & 0x1;
}

u32 XVision_ffn_unified_tile_IsIdle(XVision_ffn_unified_tile *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_AP_CTRL);
    return (Data >> 2) & 0x1;
}

u32 XVision_ffn_unified_tile_IsReady(XVision_ffn_unified_tile *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_AP_CTRL);
    // check ap_start to see if the pcore is ready for next input
    return !(Data & 0x1);
}

void XVision_ffn_unified_tile_EnableAutoRestart(XVision_ffn_unified_tile *InstancePtr) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_AP_CTRL, 0x80);
}

void XVision_ffn_unified_tile_DisableAutoRestart(XVision_ffn_unified_tile *InstancePtr) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_AP_CTRL, 0);
}

u32 XVision_ffn_unified_tile_Get_return(XVision_ffn_unified_tile *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_AP_RETURN);
    return Data;
}
void XVision_ffn_unified_tile_Set_weight_batch_f16(XVision_ffn_unified_tile *InstancePtr, u64 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_WEIGHT_BATCH_F16_DATA, (u32)(Data));
    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_WEIGHT_BATCH_F16_DATA + 4, (u32)(Data >> 32));
}

u64 XVision_ffn_unified_tile_Get_weight_batch_f16(XVision_ffn_unified_tile *InstancePtr) {
    u64 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_WEIGHT_BATCH_F16_DATA);
    Data += (u64)XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_WEIGHT_BATCH_F16_DATA + 4) << 32;
    return Data;
}

void XVision_ffn_unified_tile_Set_activation_tile_f32(XVision_ffn_unified_tile *InstancePtr, u64 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVATION_TILE_F32_DATA, (u32)(Data));
    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVATION_TILE_F32_DATA + 4, (u32)(Data >> 32));
}

u64 XVision_ffn_unified_tile_Get_activation_tile_f32(XVision_ffn_unified_tile *InstancePtr) {
    u64 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVATION_TILE_F32_DATA);
    Data += (u64)XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVATION_TILE_F32_DATA + 4) << 32;
    return Data;
}

void XVision_ffn_unified_tile_Set_output_batch_f32(XVision_ffn_unified_tile *InstancePtr, u64 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_OUTPUT_BATCH_F32_DATA, (u32)(Data));
    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_OUTPUT_BATCH_F32_DATA + 4, (u32)(Data >> 32));
}

u64 XVision_ffn_unified_tile_Get_output_batch_f32(XVision_ffn_unified_tile *InstancePtr) {
    u64 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_OUTPUT_BATCH_F32_DATA);
    Data += (u64)XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_OUTPUT_BATCH_F32_DATA + 4) << 32;
    return Data;
}

void XVision_ffn_unified_tile_Set_task_r(XVision_ffn_unified_tile *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_TASK_R_DATA, Data);
}

u32 XVision_ffn_unified_tile_Get_task_r(XVision_ffn_unified_tile *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_TASK_R_DATA);
    return Data;
}

void XVision_ffn_unified_tile_Set_active_N(XVision_ffn_unified_tile *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVE_N_DATA, Data);
}

u32 XVision_ffn_unified_tile_Get_active_N(XVision_ffn_unified_tile *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVE_N_DATA);
    return Data;
}

void XVision_ffn_unified_tile_Set_active_K(XVision_ffn_unified_tile *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVE_K_DATA, Data);
}

u32 XVision_ffn_unified_tile_Get_active_K(XVision_ffn_unified_tile *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVE_K_DATA);
    return Data;
}

void XVision_ffn_unified_tile_Set_active_M(XVision_ffn_unified_tile *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVE_M_DATA, Data);
}

u32 XVision_ffn_unified_tile_Get_active_M(XVision_ffn_unified_tile *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ACTIVE_M_DATA);
    return Data;
}

void XVision_ffn_unified_tile_Set_n_base(XVision_ffn_unified_tile *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_N_BASE_DATA, Data);
}

u32 XVision_ffn_unified_tile_Get_n_base(XVision_ffn_unified_tile *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_N_BASE_DATA);
    return Data;
}

void XVision_ffn_unified_tile_Set_m_base(XVision_ffn_unified_tile *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_M_BASE_DATA, Data);
}

u32 XVision_ffn_unified_tile_Get_m_base(XVision_ffn_unified_tile *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_M_BASE_DATA);
    return Data;
}

void XVision_ffn_unified_tile_Set_tile_rows(XVision_ffn_unified_tile *InstancePtr, u32 Data) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_TILE_ROWS_DATA, Data);
}

u32 XVision_ffn_unified_tile_Get_tile_rows(XVision_ffn_unified_tile *InstancePtr) {
    u32 Data;

    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Data = XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_TILE_ROWS_DATA);
    return Data;
}

void XVision_ffn_unified_tile_InterruptGlobalEnable(XVision_ffn_unified_tile *InstancePtr) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_GIE, 1);
}

void XVision_ffn_unified_tile_InterruptGlobalDisable(XVision_ffn_unified_tile *InstancePtr) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_GIE, 0);
}

void XVision_ffn_unified_tile_InterruptEnable(XVision_ffn_unified_tile *InstancePtr, u32 Mask) {
    u32 Register;

    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Register =  XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_IER);
    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_IER, Register | Mask);
}

void XVision_ffn_unified_tile_InterruptDisable(XVision_ffn_unified_tile *InstancePtr, u32 Mask) {
    u32 Register;

    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    Register =  XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_IER);
    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_IER, Register & (~Mask));
}

void XVision_ffn_unified_tile_InterruptClear(XVision_ffn_unified_tile *InstancePtr, u32 Mask) {
    Xil_AssertVoid(InstancePtr != NULL);
    Xil_AssertVoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    XVision_ffn_unified_tile_WriteReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ISR, Mask);
}

u32 XVision_ffn_unified_tile_InterruptGetEnabled(XVision_ffn_unified_tile *InstancePtr) {
    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    return XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_IER);
}

u32 XVision_ffn_unified_tile_InterruptGetStatus(XVision_ffn_unified_tile *InstancePtr) {
    Xil_AssertNonvoid(InstancePtr != NULL);
    Xil_AssertNonvoid(InstancePtr->IsReady == XIL_COMPONENT_IS_READY);

    return XVision_ffn_unified_tile_ReadReg(InstancePtr->Control_BaseAddress, XVISION_FFN_UNIFIED_TILE_CONTROL_ADDR_ISR);
}

