# Export the already csynth'd RM09 static-extent solution as a Vivado catalog IP.
# This command packages the existing synthesis result; it does not run csynth.
set hls_project [file normalize $::env(RM09_STATIC_EXTENT_HLS_PROJECT)]
open_project $hls_project
open_solution solution1
export_design -format ip_catalog
exit
