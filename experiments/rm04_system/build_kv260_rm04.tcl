set root [file normalize $::env(RM04_REPO_ROOT)]
set proj_name kv260_rm04_dynamic8
set proj_dir [file join $root experiments rm04_system build]
set scripts_dir [file dirname [file normalize [info script]]]
set base_dir [file join $root vendor kria-base-hardware k26_starter_kits kv260]
set ip_repo [file join $root experiments rm03_hls_mapping reports rm04_real_ffn_up_dynamic8 project solution1 impl ip]
set board_part [get_board_parts "*:kv260_som:*" -latest_file_version]
set part_name [get_property PART_NAME [get_board_parts $board_part]]

create_project -force $proj_name $proj_dir -part $part_name
set_property board_part $board_part [current_project]
set_property board_connections {som240_1_connector xilinx.com:kv260_carrier:som240_1_connector:1.3} [current_project]
set_property ip_repo_paths [list $ip_repo] [current_project]
update_ip_catalog
import_files -fileset constrs_1 [file join $base_dir xdc default.xdc]

set design_name $proj_name
set script_folder [file join $base_dir scripts]
set proj_name $proj_name
set proj_dir $proj_dir
set bd_tcl_dir [file join $base_dir scripts]
create_bd_design $proj_name
current_bd_design $proj_name
source [file join $base_dir scripts config_bd.tcl]
source [file join $scripts_dir add_dynamic8_bd.tcl]

set bd_file [get_files $proj_dir/${proj_name}.srcs/sources_1/bd/$proj_name/${proj_name}.bd]
generate_target all $bd_file
make_wrapper -files $bd_file -top
import_files -force -norecurse $proj_dir/${proj_name}.srcs/sources_1/bd/$proj_name/hdl/${proj_name}_wrapper.v
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
launch_runs impl_1 -to_step write_bitstream -jobs 8
wait_on_run impl_1

write_hw_platform -fixed -include_bit -force -file [file join $proj_dir kv260_rm04_dynamic8.xsa]
validate_hw_platform -verbose [file join $proj_dir kv260_rm04_dynamic8.xsa]
exit
