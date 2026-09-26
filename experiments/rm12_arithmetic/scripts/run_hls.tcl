set source_dir [file normalize $::env(RM12_SOURCE)]
set out_dir [file normalize $::env(RM12_HLS_ROOT)]
set top $::env(RM12_TOP)

cd $out_dir
open_project -reset [file join $out_dir project]
set_top $top
add_files $::env(RM12_KERNEL) -cflags "-I$source_dir -ffp-contract=off -fno-fast-math"
add_files $::env(RM12_OTHER_KERNEL) -cflags "-I$source_dir -ffp-contract=off -fno-fast-math"
add_files -tb [file join $source_dir tb.cpp] -cflags "-I$source_dir -ffp-contract=off -fno-fast-math"
open_solution -reset solution1
set_part xck26-sfvc784-2LV-c
create_clock -period 10.0 -name default
csim_design
csynth_design
exit
