set source_dir [file normalize $::env(RM10_SOURCE)]
set out_dir [file normalize $::env(RM10_HLS_ROOT)]

file mkdir $out_dir
cd $out_dir
open_project -reset [file join $out_dir project]
set_top vision_ffn_down_tile
add_files [file join $source_dir vision_ffn_down.cpp] -cflags "-I$source_dir -DRM10_ARCH=4 -ffp-contract=off"
add_files -tb [file join $source_dir tb_rm10.cpp] -cflags "-I$source_dir -DRM10_ARCH=4 -ffp-contract=off"
open_solution -reset solution1
set_part xck26-sfvc784-2LV-c
create_clock -period 5.0 -name default
config_interface -m_axi_max_widen_bitwidth 512
csim_design
csynth_design
cosim_design -rtl verilog
exit
