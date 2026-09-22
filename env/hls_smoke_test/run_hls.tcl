# Vitis HLS 2024.2 smoke test. Run only after sourcing env/setup_fpga.sh.
set script_dir [file normalize [file dirname [info script]]]
set project_dir [file join $script_dir build]
set part [expr {[info exists ::env(K26_PART)] ? $::env(K26_PART) : "xck26-sfvc784-2LV-c"}]

open_project -reset [file join $project_dir vector_add]
set_top vector_add
add_files [file join $script_dir vector_add.cpp]
open_solution -reset solution1
set_part $part
create_clock -period 5.0 -name default
csim_design
csynth_design
export_design -format ip_catalog -output [file join $project_dir export]
exit
