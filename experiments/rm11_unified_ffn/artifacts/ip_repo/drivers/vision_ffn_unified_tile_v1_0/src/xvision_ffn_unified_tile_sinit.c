// ==============================================================
// Vitis HLS - High-Level Synthesis from C, C++ and OpenCL v2024.2 (64-bit)
// Tool Version Limit: 2024.11
// Copyright 1986-2022 Xilinx, Inc. All Rights Reserved.
// Copyright 2022-2024 Advanced Micro Devices, Inc. All Rights Reserved.
// 
// ==============================================================
#ifndef __linux__

#include "xstatus.h"
#ifdef SDT
#include "xparameters.h"
#endif
#include "xvision_ffn_unified_tile.h"

extern XVision_ffn_unified_tile_Config XVision_ffn_unified_tile_ConfigTable[];

#ifdef SDT
XVision_ffn_unified_tile_Config *XVision_ffn_unified_tile_LookupConfig(UINTPTR BaseAddress) {
	XVision_ffn_unified_tile_Config *ConfigPtr = NULL;

	int Index;

	for (Index = (u32)0x0; XVision_ffn_unified_tile_ConfigTable[Index].Name != NULL; Index++) {
		if (!BaseAddress || XVision_ffn_unified_tile_ConfigTable[Index].Control_BaseAddress == BaseAddress) {
			ConfigPtr = &XVision_ffn_unified_tile_ConfigTable[Index];
			break;
		}
	}

	return ConfigPtr;
}

int XVision_ffn_unified_tile_Initialize(XVision_ffn_unified_tile *InstancePtr, UINTPTR BaseAddress) {
	XVision_ffn_unified_tile_Config *ConfigPtr;

	Xil_AssertNonvoid(InstancePtr != NULL);

	ConfigPtr = XVision_ffn_unified_tile_LookupConfig(BaseAddress);
	if (ConfigPtr == NULL) {
		InstancePtr->IsReady = 0;
		return (XST_DEVICE_NOT_FOUND);
	}

	return XVision_ffn_unified_tile_CfgInitialize(InstancePtr, ConfigPtr);
}
#else
XVision_ffn_unified_tile_Config *XVision_ffn_unified_tile_LookupConfig(u16 DeviceId) {
	XVision_ffn_unified_tile_Config *ConfigPtr = NULL;

	int Index;

	for (Index = 0; Index < XPAR_XVISION_FFN_UNIFIED_TILE_NUM_INSTANCES; Index++) {
		if (XVision_ffn_unified_tile_ConfigTable[Index].DeviceId == DeviceId) {
			ConfigPtr = &XVision_ffn_unified_tile_ConfigTable[Index];
			break;
		}
	}

	return ConfigPtr;
}

int XVision_ffn_unified_tile_Initialize(XVision_ffn_unified_tile *InstancePtr, u16 DeviceId) {
	XVision_ffn_unified_tile_Config *ConfigPtr;

	Xil_AssertNonvoid(InstancePtr != NULL);

	ConfigPtr = XVision_ffn_unified_tile_LookupConfig(DeviceId);
	if (ConfigPtr == NULL) {
		InstancePtr->IsReady = 0;
		return (XST_DEVICE_NOT_FOUND);
	}

	return XVision_ffn_unified_tile_CfgInitialize(InstancePtr, ConfigPtr);
}
#endif

#endif

