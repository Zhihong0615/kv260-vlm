set source_dir [file normalize $::env(RM07_HLS_SOURCE)]
set out_dir [file normalize $::env(RM07_HLS_ROOT)]
file mkdir $out_dir
cd $out_dir
open_project -reset [file join $out_dir project]
set_top vision_ffn_down_tile
add_files [file join $source_dir vision_ffn_down.cpp]
add_files -tb [file join $source_dir tb_tile_schedule.cpp]
open_solution -reset solution1
set_part xck26-sfvc784-2LV-c
create_clock -period 5.0 -name default
config_interface -m_axi_max_widen_bitwidth 512
csim_design
csynth_design
if {![info exists ::env(RM07_RUN_COSIM)] || $::env(RM07_RUN_COSIM) ne "0"} {
  cosim_design -rtl verilog
}
export_design -format ip_catalog
exit
