# KV260 board files

状态：`BLOCKED / UNKNOWN`。

当前主机没有 Vivado 2024.2，因此不能运行 `get_board_parts *kv260*`，也不能把 board definition 记为有效。当前也没有发现 `/tools/Xilinx`、`/opt/Xilinx` 或 AMD 安装目录。

待 Vivado 2024.2 安装后执行：

```tcl
get_board_parts *kv260*
```

并把真实 board part、安装路径、版本和来源写回本文件。若查询为空，只使用 AMD 官方 board files；不从不明 GitHub 仓库下载。
