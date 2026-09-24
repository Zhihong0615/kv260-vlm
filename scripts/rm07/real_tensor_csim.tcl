set source_dir [file normalize $::env(RM07_CSIM_SOURCE)]
set out_dir [file normalize $::env(RM07_CSIM_ROOT)]
file mkdir $out_dir
cd $out_dir
open_project -reset [file join $out_dir project]
set_top vision_ffn_down_tile
add_files [file join $source_dir vision_ffn_down.cpp]
add_files -tb [file join $source_dir tb_real_tensor_extent.cpp]
open_solution -reset solution1
set_part xck26-sfvc784-2LV-c
create_clock -period 5.0 -name default
csim_design -argv "$::env(RM07_WEIGHT) $::env(RM07_ACTIVATION) $::env(RM07_CPU_OUTPUT) $::env(RM07_LAYER) $::env(RM07_ACTIVE_N)"
exit
