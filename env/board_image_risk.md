# Board image risk

当前板端镜像状态：`KEEP / no change`。

审计显示 FPGA Manager、device-tree overlay 目录、CMA、XRT 和 KV260 device 都存在；`xbutil examine` 报告 device Ready。因此没有触发更换镜像的条件。

原先普通用户无法访问 dfx-manager socket 的问题已通过精确、只读的 sudoers
规则解决：仅允许 `ubuntu` 免密执行 `/usr/bin/xmutil listapps`。真实应用列表
已返回，且未授予任何加载、卸载或 boot firmware 更新权限。因此仍没有更换
镜像、修改 bootloader、修改 DTBO 或更新 QSPI 的理由。
