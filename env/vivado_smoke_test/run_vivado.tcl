# Vivado 2024.2 KV260 smoke test.
# This creates a disposable project and performs synthesis/implementation only.
# It does not program a board or load a bitstream.
set script_dir [file normalize [file dirname [info script]]]
set project_dir [file join $script_dir build]
set part [expr {[info exists ::env(K26_PART)] ? $::env(K26_PART) : "xck26-sfvc784-2LV-c"}]

file mkdir $project_dir
set board_parts [get_board_parts *kv260*]
if {[llength $board_parts] == 0} {
  error "No KV260 board part found in Vivado device database"
}
set board_part [lindex $board_parts 0]

create_project kv260_smoke $project_dir -part $part -force
set_property board_part $board_part [current_project]
create_bd_design kv260_smoke_bd
create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.3 ps_0
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 axi_gpio_0
set_property -dict [list CONFIG.C_GPIO_WIDTH {32} CONFIG.C_ALL_INPUTS {0} CONFIG.C_ALL_OUTPUTS {0}] [get_bd_cells axi_gpio_0]
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e -config {apply_board_preset "1"} [get_bd_cells ps_0]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master "/ps_0/M_AXI_HPM0_FPD" Clk "/ps_0/pl_clk0"} [get_bd_intf_pins axi_gpio_0/S_AXI]
assign_bd_address
validate_bd_design
save_bd_design
make_wrapper -files [get_files [file join $project_dir kv260_smoke.srcs/sources_1/bd/kv260_smoke_bd/kv260_smoke_bd.bd]] -top
add_files -norecurse [file join $project_dir kv260_smoke.srcs/sources_1/bd/kv260_smoke_bd/hdl/kv260_smoke_bd_wrapper.v]
update_compile_order -fileset sources_1
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
if {[get_property STATUS [get_runs impl_1]] ne "write_bitstream Complete!"} {
  error "Vivado implementation/bitstream run failed"
}
report_utilization -file [file join $project_dir utilization.rpt]
report_timing_summary -file [file join $project_dir timing_summary.rpt]
close_project
exit
