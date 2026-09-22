# Board image risk

当前板端镜像状态：`KEEP / no change`。

审计显示 FPGA Manager、device-tree overlay 目录、CMA、XRT 和 KV260 device 都存在；`xbutil examine` 报告 device Ready。因此没有触发更换镜像的条件。

唯一待处理项是普通用户无法成功访问 dfx-manager socket，导致 `xmutil listapps` 不能作为用户态 PASS。该问题尚可通过板端交互式权限核验或只读权限配置处理，不应通过重刷镜像、修改 bootloader、修改 DTBO 或更新 QSPI 解决。
