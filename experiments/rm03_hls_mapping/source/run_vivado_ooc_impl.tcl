set rtl_dir $::env(RM03_RTL_DIR)
set out_dir $::env(RM03_VIVADO_OUT)
file mkdir $out_dir
create_project -force rm03_ooc_feasibility [file join $out_dir project] -part xck26-sfvc784-2LV-c
set rtl_files [glob -nocomplain [file join $rtl_dir *.v]]
if {[llength $rtl_files] == 0} { error "No generated Verilog in $rtl_dir" }
add_files -norecurse $rtl_files
set_property top vision_gemm [current_fileset]
foreach ip_tcl [glob -nocomplain [file join $rtl_dir *_ip.tcl]] {
    source $ip_tcl
}
update_compile_order -fileset sources_1
synth_design -mode out_of_context -top vision_gemm -part xck26-sfvc784-2LV-c -flatten_hierarchy none
create_clock -name ap_clk -period 5.000 [get_ports ap_clk]
report_utilization -file [file join $out_dir utilization_post_synth.rpt]
report_timing_summary -delay_type max -report_unconstrained -file [file join $out_dir timing_post_synth.rpt]
opt_design
place_design
phys_opt_design
route_design
report_utilization -file [file join $out_dir utilization_post_route.rpt]
report_timing_summary -delay_type max -report_unconstrained -file [file join $out_dir timing_post_route.rpt]
report_clock_utilization -file [file join $out_dir clock_utilization_post_route.rpt]
write_checkpoint -force [file join $out_dir routed.dcp]
exit
