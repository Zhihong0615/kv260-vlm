set project_dir [file normalize $::env(RM10_HLS_PROJECT)]
set output_dir [file normalize $::env(RM10_IP_OUTPUT)]
open_project $project_dir
open_solution solution1
export_design -format ip_catalog -output $output_dir
exit
