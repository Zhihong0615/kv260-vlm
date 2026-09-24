set rtl_dir $::env(RM02_RTL_DIR)
set out_dir $::env(RM02_VIVADO_OUT)
file mkdir $out_dir
create_project -force rm02_post_synth [file join $out_dir project] -part xck26-sfvc784-2LV-c
set rtl_files [glob -nocomplain [file join $rtl_dir *.v]]
if {[llength $rtl_files] == 0} { error "No generated Verilog in $rtl_dir" }
add_files -norecurse $rtl_files
set_property top vision_gemm [current_fileset]
foreach ip_tcl [glob -nocomplain [file join $rtl_dir *_ip.tcl]] {
    source $ip_tcl
}
update_compile_order -fileset sources_1
synth_design -top vision_gemm -part xck26-sfvc784-2LV-c -flatten_hierarchy none
create_clock -name ap_clk -period 5.000 [get_ports ap_clk]
report_utilization -file [file join $out_dir utilization.rpt]
report_timing_summary -delay_type max -report_unconstrained -file [file join $out_dir timing_summary.rpt]
report_clock_utilization -file [file join $out_dir clock_utilization.rpt]
