set source_dir [file normalize $::env(RM06_K16_SOURCE)]
set out_dir [file normalize $::env(RM06_K16_HLS_ROOT)]
file mkdir $out_dir
cd $out_dir

open_project -reset [file join $out_dir project]
set_top vision_gemm
set cflags "-DTILE_M=16 -DTILE_N=32 -DHLS_PE_M=4 -DHLS_PE_N=4 -DHLS_K_LANES=16 -DHLS_NO_FLATTEN=1"
add_files [file join $source_dir vision_gemm.cpp] -cflags $cflags
add_files -tb [file join $source_dir tb.cpp] -cflags $cflags
open_solution -reset solution1
set_part xck26-sfvc784-2LV-c
create_clock -period 5.0 -name default
config_interface -m_axi_max_widen_bitwidth 512
csim_design
csynth_design
export_design -format ip_catalog
exit
