# RM09 static-extent baseline, routed for the board's observed 100 MHz PL0.
# Keep the RM07 K16 architecture, interfaces, and bounded staging unchanged.
set ps [get_bd_cells zynq_ultra_ps_e_0]
set_property -dict [list \
  CONFIG.PSU__USE__M_AXI_GP0 {1} \
  CONFIG.PSU__USE__S_AXI_GP2 {1} \
  CONFIG.PSU__CRL_APB__PL0_REF_CTRL__FREQMHZ {100.000} \
  CONFIG.PSU__MAXIGP0__DATA_WIDTH {32} \
] $ps

set vision [create_bd_cell -type ip -vlnv xilinx.com:hls:vision_ffn_down_tile:1.0 vision_ffn_down_tile_0]
set data_sc [create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 axi_smc_data]
set_property -dict [list CONFIG.NUM_SI {3} CONFIG.NUM_MI {1}] $data_sc
set ctrl_sc [create_bd_cell -type ip -vlnv xilinx.com:ip:smartconnect:1.0 axi_smc_control]
set_property -dict [list CONFIG.NUM_SI {1} CONFIG.NUM_MI {2}] $ctrl_sc
set apm [create_bd_cell -type ip -vlnv xilinx.com:ip:axi_perf_mon:5.0 axi_perf_mon_0]
set_property -dict [list \
  CONFIG.C_NUM_MONITOR_SLOTS {3} \
  CONFIG.C_ENABLE_ADVANCED {1} \
  CONFIG.C_ENABLE_EVENT_COUNT {1} \
  CONFIG.C_ENABLE_PROFILE {0} \
  CONFIG.C_NUM_OF_COUNTERS {8} \
  CONFIG.C_SLOT_0_AXI_PROTOCOL {AXI4} \
  CONFIG.C_SLOT_1_AXI_PROTOCOL {AXI4} \
  CONFIG.C_SLOT_2_AXI_PROTOCOL {AXI4} \
] $apm

# HPM0 carries control; three HLS masters share HP0 DDR through SmartConnect.
connect_bd_intf_net [get_bd_intf_pins $ps/M_AXI_HPM0_FPD] [get_bd_intf_pins $ctrl_sc/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins $ctrl_sc/M00_AXI] [get_bd_intf_pins $vision/s_axi_control]
connect_bd_intf_net [get_bd_intf_pins $ctrl_sc/M01_AXI] [get_bd_intf_pins $apm/S_AXI]
connect_bd_intf_net [get_bd_intf_pins $vision/m_axi_gmem_w] [get_bd_intf_pins $data_sc/S00_AXI]
connect_bd_intf_net [get_bd_intf_pins $vision/m_axi_gmem_x] [get_bd_intf_pins $data_sc/S01_AXI]
connect_bd_intf_net [get_bd_intf_pins $vision/m_axi_gmem_y] [get_bd_intf_pins $data_sc/S02_AXI]
connect_bd_intf_net [get_bd_intf_pins $data_sc/M00_AXI] [get_bd_intf_pins $ps/S_AXI_HP0_FPD]
connect_bd_intf_net [get_bd_intf_pins $vision/m_axi_gmem_w] [get_bd_intf_pins $apm/SLOT_0_AXI]
connect_bd_intf_net [get_bd_intf_pins $vision/m_axi_gmem_x] [get_bd_intf_pins $apm/SLOT_1_AXI]
connect_bd_intf_net [get_bd_intf_pins $vision/m_axi_gmem_y] [get_bd_intf_pins $apm/SLOT_2_AXI]

foreach pin [list \
  $vision/ap_clk $data_sc/aclk $ctrl_sc/aclk $apm/core_aclk $apm/s_axi_aclk \
  $apm/slot_0_axi_aclk $apm/slot_1_axi_aclk $apm/slot_2_axi_aclk \
  $ps/maxihpm0_fpd_aclk $ps/saxihp0_fpd_aclk] {
  connect_bd_net [get_bd_pins $ps/pl_clk0] [get_bd_pins $pin]
}
foreach pin [list \
  $vision/ap_rst_n $data_sc/aresetn $ctrl_sc/aresetn $apm/core_aresetn \
  $apm/s_axi_aresetn $apm/slot_0_axi_aresetn $apm/slot_1_axi_aresetn $apm/slot_2_axi_aresetn] {
  connect_bd_net [get_bd_pins $ps/pl_resetn0] [get_bd_pins $pin]
}

assign_bd_address
validate_bd_design
save_bd_design
