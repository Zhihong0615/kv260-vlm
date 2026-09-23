# KV260 board files

状态：`PASS`（Vivado 2024.2 真实查询）。

项目本地 Vivado 位于
`/home/zhiro/research/kv260-vlm/tools/Xilinx/Vivado/2024.2/`。执行
`get_board_parts *kv260*` 返回 3 个 board part：

```text
xilinx.com:kv260_som:part0:1.2
xilinx.com:kv260_som:part0:1.3
xilinx.com:kv260_som:part0:1.4
```

Vivado smoke test 使用最新返回项 `1.4`，成功完成 implementation 和
bitstream 生成。K26 device database 同时返回
`xck26-sfvc784-2LV-c` 与 `xck26-sfvc784-2LVI-i`。未从第三方仓库下载 board
files。
