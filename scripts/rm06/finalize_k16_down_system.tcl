set root [file normalize $::env(RM06_REPO_ROOT)]
set out_dir [file normalize $::env(RM06_SYSTEM_ROOT)]
set proj_name kv260_rm06_k16_down
open_project [file join $out_dir ${proj_name}.xpr]
open_run impl_1
report_timing_summary -delay_type max -report_unconstrained -file [file join $out_dir rm06_timing_post_route.rpt]
report_utilization -file [file join $out_dir rm06_utilization_post_route.rpt]
write_hw_platform -fixed -include_bit -force -file [file join $out_dir kv260_rm06_k16_down.xsa]
validate_hw_platform -verbose [file join $out_dir kv260_rm06_k16_down.xsa]
exit
