set k26_parts [get_parts -quiet *xck26*]
set kv260_boards [get_board_parts -quiet *kv260*]

puts "K26_PART_COUNT=[llength $k26_parts]"
puts "KV260_BOARD_COUNT=[llength $kv260_boards]"
puts "K26_PARTS=$k26_parts"
puts "KV260_BOARDS=$kv260_boards"
exit
