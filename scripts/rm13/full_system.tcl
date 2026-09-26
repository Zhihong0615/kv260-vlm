set root [file normalize $::env(RM13_REPO_ROOT)]
set out_dir [file normalize $::env(RM13_SYSTEM_ROOT)]
set base_dir [file normalize $::env(RM13_BASE_KV260_DIR)]
set ip_repo [file normalize $::env(RM13_IP_REPO)]
set proj_name kv260_rm13_w4a8_down
set board_part [get_board_parts "*:kv260_som:*" -latest_file_version]
if {$board_part eq ""} { error "No KV260 board part found in Vivado device database" }
set part_name [get_property PART_NAME [get_board_parts $board_part]]
if {$part_name ne "xck26-sfvc784-2LV-c"} { error "Unexpected KV260 part: $part_name" }
if {![file exists [file join $ip_repo component.xml]]} {
  error "RM13 W4A8 HLS IP component.xml missing: $ip_repo"
}

file mkdir $out_dir
create_project -force $proj_name $out_dir -part $part_name
set_property board_part $board_part [current_project]
set_property board_connections {som240_1_connector xilinx.com:kv260_carrier:som240_1_connector:1.3} [current_project]
set_property ip_repo_paths [list $ip_repo] [current_project]
update_ip_catalog
import_files -fileset constrs_1 [file join $base_dir xdc default.xdc]

set design_name $proj_name
set script_folder [file join $base_dir scripts]
set proj_dir $out_dir
set bd_tcl_dir [file join $base_dir scripts]
create_bd_design $proj_name
current_bd_design $proj_name
source [file join $base_dir scripts config_bd.tcl]
source [file join $root experiments rm13 hardware add_rm13_bd.tcl]
set bd_file [get_files $out_dir/${proj_name}.srcs/sources_1/bd/$proj_name/${proj_name}.bd]
generate_target all $bd_file
make_wrapper -files $bd_file -top
import_files -force -norecurse $out_dir/${proj_name}.srcs/sources_1/bd/$proj_name/hdl/${proj_name}_wrapper.v
update_compile_order
set_property top ${proj_name}_wrapper [current_fileset]
set_property synth_checkpoint_mode Hierarchical $bd_file
set_property platform.board_id $proj_name [current_project]
set_property platform.extensible false [current_project]
set_property platform.name $proj_name [current_project]
set_property platform.vendor xilinx [current_project]
set_property platform.version 1.0 [current_project]

launch_runs synth_1 -jobs 8
wait_on_run synth_1
set synth_status [get_property STATUS [get_runs synth_1]]
if {![string match "*Complete*" $synth_status]} { error "synth_1 did not complete: $synth_status" }
launch_runs impl_1 -to_step write_bitstream -jobs 8
wait_on_run impl_1
set impl_status [get_property STATUS [get_runs impl_1]]
if {![string match "*Complete*" $impl_status]} { error "impl_1 did not complete through bitgen: $impl_status" }

open_run impl_1
report_timing_summary -delay_type max -report_unconstrained -file [file join $out_dir timing_post_route_setup.rpt]
report_timing_summary -delay_type min -report_unconstrained -file [file join $out_dir timing_post_route_hold.rpt]
report_timing -delay_type max -max_paths 20 -nworst 2 -path_type full_clock_expanded -file [file join $out_dir critical_paths_post_route.rpt]
report_utilization -file [file join $out_dir utilization_post_route.rpt]
report_clock_utilization -file [file join $out_dir clock_utilization_post_route.rpt]
report_route_status -file [file join $out_dir route_status.rpt]
report_drc -file [file join $out_dir drc_post_route.rpt]
report_methodology -file [file join $out_dir methodology_post_route.rpt]
report_design_analysis -congestion -file [file join $out_dir congestion_post_route.rpt]
write_hw_platform -fixed -include_bit -force -file [file join $out_dir kv260_rm13_w4a8_down.xsa]
validate_hw_platform -verbose [file join $out_dir kv260_rm13_w4a8_down.xsa]
exit
