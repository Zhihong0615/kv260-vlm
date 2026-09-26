set source_dir [file normalize $::env(RM13_SOURCE)]
set out_dir [file normalize $::env(RM13_HLS_ROOT)]
set k $::env(RM13_K)
set do_synth $::env(RM13_DO_SYNTH)
set do_csim $::env(RM13_DO_CSIM)
set do_cosim $::env(RM13_DO_COSIM)
set debug_outputs $::env(RM13_DEBUG_OUTPUTS)
set tile_m $::env(RM13_TILE_M)
set tile_n $::env(RM13_TILE_N)
set processing_m $::env(RM13_PROCESSING_M)
set processing_n $::env(RM13_PROCESSING_N)

file mkdir $out_dir
cd $out_dir
open_project -reset [file join $out_dir project]
set_top rm13_w4a8_tile
set cflags "-I$source_dir -DRM13_K=$k -DRM13_DEBUG_OUTPUTS=$debug_outputs -DRM13_TILE_M=$tile_m -DRM13_TILE_N=$tile_n -DRM13_PROCESSING_M=$processing_m -DRM13_PROCESSING_N=$processing_n -ffp-contract=off"
add_files [file join $source_dir w4a8_tile.cpp] -cflags $cflags
add_files -tb [file join $source_dir tb_w4a8_tile.cpp] -cflags $cflags
open_solution -reset solution1
set_part xck26-sfvc784-2LV-c
create_clock -period 5.0 -name default
config_interface -m_axi_max_widen_bitwidth 512
if {$do_csim eq "1"} {
    csim_design
}
if {$do_synth eq "1"} {
    csynth_design
}
if {$do_cosim eq "1"} {
    if {$do_synth ne "1"} { error "C/RTL cosim requires RM13_DO_SYNTH=1" }
    cosim_design -rtl verilog
}
exit
