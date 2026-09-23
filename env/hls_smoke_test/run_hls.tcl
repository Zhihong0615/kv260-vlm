# Vitis HLS 2024.2 smoke test. Run only after sourcing env/setup_fpga.sh.
set script_dir [file normalize [file dirname [info script]]]
set project_dir [file join $script_dir build]
set evidence_dir [file join $script_dir evidence]
set part [expr {[info exists ::env(K26_PART)] ? $::env(K26_PART) : "xck26-sfvc784-2LV-c"}]

file mkdir $project_dir
file mkdir $evidence_dir
cd $project_dir
open_project -reset [file join $project_dir vector_add]
set_top vector_add
set project_source_dir [file join $project_dir vector_add src]
file mkdir $project_source_dir
file copy -force [file join $script_dir vector_add.cpp] $project_source_dir
file copy -force [file join $script_dir vector_add_tb.cpp] $project_source_dir
add_files [file join $project_source_dir vector_add.cpp]
add_files -tb [file join $project_source_dir vector_add_tb.cpp]
open_solution -reset solution1
set_part $part
create_clock -period 5.0 -name default
csim_design
csynth_design
export_design -format ip_catalog -output [file join $project_dir export]
file copy -force \
  [file join $project_dir vector_add solution1 csim report vector_add_csim.log] \
  [file join $evidence_dir vector_add_csim.log]
file copy -force \
  [file join $project_dir vector_add solution1 syn report vector_add_csynth.rpt] \
  [file join $evidence_dir vector_add_csynth.rpt]
file copy -force \
  [file join $project_dir vector_add solution1 solution1.log] \
  [file join $evidence_dir solution1.log]
file copy -force [file join $project_dir export.zip] [file join $evidence_dir export.zip]
exit
