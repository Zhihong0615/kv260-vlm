set script_dir [file normalize [file dirname [info script]]]
set run_name $::env(RM03_VARIANT)
set out_dir [file join [file dirname $script_dir] reports $run_name]
set pe_m $::env(RM03_PE_M)
set pe_n $::env(RM03_PE_N)
set k_lanes $::env(RM03_K_LANES)
set no_flatten $::env(RM03_NO_FLATTEN)
set dynamic_partial $::env(RM03_DYNAMIC_PARTIAL)
set tile_m 16
set tile_n 32
file mkdir $out_dir
cd $out_dir

open_project -reset [file join $out_dir project]
set_top vision_gemm
set cflags "-DTILE_M=$tile_m -DTILE_N=$tile_n -DHLS_PE_M=$pe_m -DHLS_PE_N=$pe_n -DHLS_K_LANES=$k_lanes"
if {$no_flatten eq "1"} { set cflags "$cflags -DHLS_NO_FLATTEN=1" }
if {$dynamic_partial eq "1"} { set cflags "$cflags -DHLS_DYNAMIC_PARTIAL=1" }
add_files [file join $script_dir vision_gemm.cpp] -cflags $cflags
add_files -tb [file join $script_dir tb.cpp] -cflags $cflags
open_solution -reset solution1
set_part xck26-sfvc784-2LV-c
create_clock -period 5.0 -name default
config_interface -m_axi_max_widen_bitwidth 512
csim_design
csynth_design
exit
