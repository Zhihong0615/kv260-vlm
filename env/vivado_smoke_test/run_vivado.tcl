# Vivado 2024.2 KV260 smoke test.
# This creates a disposable project and performs synthesis/implementation only.
# It does not program a board or load a bitstream.
set script_dir [file normalize [file dirname [info script]]]
set project_dir [file join $script_dir build]
set evidence_dir [file join $script_dir evidence]
set part [expr {[info exists ::env(K26_PART)] ? $::env(K26_PART) : "xck26-sfvc784-2LV-c"}]

file mkdir $project_dir
file mkdir $evidence_dir
set board_parts [get_board_parts *kv260*]
if {[llength $board_parts] == 0} {
  error "No KV260 board part found in Vivado device database"
}
set board_part [lindex $board_parts end]

create_project kv260_smoke $project_dir -part $part -force
set_property board_part $board_part [current_project]
create_bd_design kv260_smoke_bd
create_bd_cell -type ip -vlnv xilinx.com:ip:zynq_ultra_ps_e:3.5 ps_0
create_bd_cell -type ip -vlnv xilinx.com:ip:axi_gpio:2.0 axi_gpio_0
set_property -dict [list CONFIG.C_GPIO_WIDTH {32} CONFIG.C_ALL_INPUTS {0} CONFIG.C_ALL_OUTPUTS {0}] [get_bd_cells axi_gpio_0]
apply_bd_automation -rule xilinx.com:bd_rule:zynq_ultra_ps_e -config {apply_board_preset "1"} [get_bd_cells ps_0]
apply_bd_automation -rule xilinx.com:bd_rule:axi4 -config {Master "/ps_0/M_AXI_HPM0_FPD" Clk "/ps_0/pl_clk0"} [get_bd_intf_pins axi_gpio_0/S_AXI]
connect_bd_net [get_bd_pins ps_0/pl_clk0] [get_bd_pins ps_0/maxihpm1_fpd_aclk]
assign_bd_address
validate_bd_design
save_bd_design
make_wrapper -files [get_files [file join $project_dir kv260_smoke.srcs/sources_1/bd/kv260_smoke_bd/kv260_smoke_bd.bd]] -top
add_files -norecurse [file join $project_dir kv260_smoke.srcs/sources_1/bd/kv260_smoke_bd/hdl/kv260_smoke_bd_wrapper.v]
update_compile_order -fileset sources_1
launch_runs impl_1 -to_step write_bitstream -jobs 4
wait_on_run impl_1
set run_status [get_property STATUS [get_runs impl_1]]
if {$run_status ne "write_bitstream Complete!"} {
  error "Vivado implementation/bitstream run failed"
}
open_run impl_1
report_drc -file [file join $project_dir drc.rpt]
report_utilization -file [file join $project_dir utilization.rpt]
report_timing_summary -file [file join $project_dir timing_summary.rpt]
set drc_error_count [llength [get_drc_violations -quiet -filter {SEVERITY == Error}]]
set drc_critical_count [llength [get_drc_violations -quiet -filter {SEVERITY == {Critical Warning}}]]
set setup_paths [get_timing_paths -quiet -delay_type max -max_paths 1]
set hold_paths [get_timing_paths -quiet -delay_type min -max_paths 1]
if {[llength $setup_paths] == 0 || [llength $hold_paths] == 0} {
  error "Vivado implementation produced no setup or hold timing path"
}
set setup_wns [get_property SLACK [lindex $setup_paths 0]]
set hold_whs [get_property SLACK [lindex $hold_paths 0]]
if {$drc_error_count != 0 || $drc_critical_count != 0} {
  error "Vivado implementation has DRC errors or critical warnings"
}
if {$setup_wns < 0.0 || $hold_whs < 0.0} {
  error "Vivado implementation does not meet setup or hold timing"
}
set bitstream [file join $project_dir kv260_smoke.runs impl_1 kv260_smoke_bd_wrapper.bit]
if {![file exists $bitstream] || [file size $bitstream] == 0} {
  error "Vivado reported success but the expected bitstream is missing or empty"
}
file copy -force $bitstream [file join $evidence_dir kv260_smoke_bd_wrapper.bit]
file copy -force \
  [file join $project_dir drc.rpt] \
  [file join $evidence_dir drc.rpt]
file copy -force \
  [file join $project_dir utilization.rpt] \
  [file join $evidence_dir utilization.rpt]
file copy -force \
  [file join $project_dir timing_summary.rpt] \
  [file join $evidence_dir timing_summary.rpt]
set status_file [open [file join $evidence_dir run_status.txt] w]
puts $status_file "TOOL=Vivado 2024.2"
puts $status_file "PART=$part"
puts $status_file "BOARD_PART=$board_part"
puts $status_file "IMPL_STATUS=$run_status"
puts $status_file "BITSTREAM_BYTES=[file size $bitstream]"
puts $status_file "DRC_ERROR_COUNT=$drc_error_count"
puts $status_file "DRC_CRITICAL_WARNING_COUNT=$drc_critical_count"
puts $status_file "SETUP_WNS_NS=$setup_wns"
puts $status_file "HOLD_WHS_NS=$hold_whs"
close $status_file
close_project
exit
