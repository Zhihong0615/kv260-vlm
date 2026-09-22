# KV260 inventory

审计时间：2026-09-22；连接配置使用现有 SSH host `kria`（192.168.77.2，用户 `ubuntu`）。未修改板端镜像。

## 系统

```text
PRETTY_NAME="Ubuntu 22.04.4 LTS"
Linux kria 5.15.0-1027-xilinx-zynqmp #31-Ubuntu SMP Wed Feb 21 04:33:09 UTC 2024 aarch64 aarch64 aarch64 GNU/Linux
aarch64
nproc: 4
Memory: 3.8 GiB total, about 3.2 GiB available at audit time
Root filesystem: /dev/mmcblk1p2, 58 GiB total, 44 GiB available
Boot filesystem: /dev/mmcblk1p1, 1009 MiB total, 879 MiB available
```

## FPGA Manager / overlay / CMA

```text
/usr/bin/xmutil
/sys/class/fpga_manager/fpga0 -> .../fpga_manager/fpga0
/sys/class/fpga_manager/fpga0/state: operating
/sys/kernel/config/device-tree/overlays/
  k26-starter-kits_image_1/
  pynq/
CmaTotal: 1024000 kB
CmaFree: 1014300 kB
```

`dmesg | grep -i cma` 无法由普通用户读取内核 ring buffer，状态：`UNKNOWN（权限不足）`；`/proc/meminfo` 已明确 CMA 总量约 1 GiB。

## XRT / device

板端安装包包含：`xrt 2.13.479-0ubuntu2`、`fpga-manager-xlnx`、`xmutil` 等。

真实执行 `xbutil examine` 成功：

```text
XRT Version : 2.13.0
Model       : ZynqMP KV260 revB
Devices     : [0000:00:00.0] KV260
Device Ready: Yes
```

可执行文件：`/usr/bin/xbutil`、`/usr/bin/xclbinutil`。

## xmutil 权限问题

普通用户执行 `xmutil listapps` 时 dfx manager 返回：

```text
DFX-MGRD> ERROR:initSocket():374 connect(/tmp/dfx-mgrd.socket): Permission denied
write: Transport endpoint is not connected
```

`sudo -n xmutil listapps` 也因板端 sudo 需要密码而无法执行。虽然该命令的 shell return code 为 0，但错误文本表示不能将 `xmutil listapps` 记为 PASS。状态：`BLOCKED（需要用户在板端交互式授权或提供合适的只读权限）`。

## 设备节点

存在 `/dev/dma_heap/{system,reserved}`、`/dev/uio0` 至 `/dev/uio4`、`/dev/dri/card0`、`/dev/dri/card1` 和 `/dev/dri/renderD128`。多个节点仅 root 可访问；本阶段未修改权限。

## 保护性结论

本次未升级板端软件、未更换镜像、未修改 bootloader、未修改 DTBO、未更新 QSPI/boot firmware、未加载新 bitstream。
