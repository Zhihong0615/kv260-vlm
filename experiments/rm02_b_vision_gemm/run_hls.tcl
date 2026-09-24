set script_dir [file normalize [file dirname [info script]]]
set run_name $::env(RM02_VARIANT)
set tile_m $::env(RM02_TILE_M)
set tile_n $::env(RM02_TILE_N)
set project_dir [file join $script_dir reports $run_name]
file mkdir $project_dir
cd $project_dir

open_project -reset [file join $project_dir project]
set_top vision_gemm
set cflags "-DTILE_M=$tile_m -DTILE_N=$tile_n"
add_files [file join $script_dir vision_gemm.cpp] -cflags $cflags
add_files -tb [file join $script_dir tb.cpp] -cflags $cflags
open_solution -reset solution1
set_part xck26-sfvc784-2LV-c
create_clock -period 5.0 -name default
config_interface -m_axi_max_widen_bitwidth 512
csim_design
csynth_design
exit
