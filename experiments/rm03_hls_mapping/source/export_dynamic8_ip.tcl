set project_dir [file normalize $::env(RM04_HLS_PROJECT)]
open_project $project_dir
open_solution solution1
export_design -format ip_catalog
exit
