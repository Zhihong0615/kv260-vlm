set script_dir [file normalize [file dirname [info script]]]
set report_root [file join [file dirname $script_dir] reports $::env(RM04_REAL_CSIM_VARIANT)]
set k_lanes $::env(RM04_REAL_K_LANES)
set dynamic_partial $::env(RM04_REAL_DYNAMIC_PARTIAL)
set weight_path [file normalize $::env(RM04_REAL_WEIGHT)]
set activation_path [file normalize $::env(RM04_REAL_ACTIVATION)]
set output_path [file normalize $::env(RM04_REAL_OUTPUT)]
file mkdir $report_root
cd $report_root
open_project -reset [file join $report_root project]
set_top vision_gemm
set cflags "-DTILE_M=16 -DTILE_N=32 -DHLS_PE_M=4 -DHLS_PE_N=4 -DHLS_K_LANES=$k_lanes -DHLS_NO_FLATTEN=1"
if {$dynamic_partial eq "1"} { set cflags "$cflags -DHLS_DYNAMIC_PARTIAL=1" }
add_files [file join $script_dir vision_gemm.cpp] -cflags $cflags
add_files -tb [file join $script_dir tb_real_tensor.cpp] -cflags $cflags
open_solution -reset solution1
set_part xck26-sfvc784-2LV-c
create_clock -period 5.0 -name default
csim_design -argv "$weight_path $activation_path $output_path"
exit
