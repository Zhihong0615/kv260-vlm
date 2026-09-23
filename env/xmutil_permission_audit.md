# KV260 xmutil least-privilege audit

审计日期：2026-09-23（Asia/Shanghai）

## 原始问题

板端 `/tmp/dfx-mgrd.socket` 为 `root:root 0755`。普通用户运行
`/usr/bin/xmutil listapps` 会收到 socket permission denied；这符合该版本
`xmutil` 需要 root 调用的行为，不能通过放宽 socket、加入 root 组或修改
`dfx-mgrd` 全局 umask 绕过。

## 最小授权

用户在板端终端交互式输入一次 sudo 密码后，安装了：

```text
/etc/sudoers.d/90-kv260-xmutil-listapps
root:root 0440
ubuntu ALL=(root) NOPASSWD: /usr/bin/xmutil listapps
```

候选规则与安装后的规则均使用 `/usr/sbin/visudo -cf` 校验。安装脚本在目标
文件已存在且内容不同时会拒绝覆盖。

## 独立复验

`scripts/check_kv260_env.sh` 使用精确路径执行：

```text
sudo -n /usr/bin/xmutil listapps
```

真实返回：

```text
Accelerator       Accel_type  Base              Base_type  #slots(PL+AIE)  Active_slot
k26-starter-kits  XRT_FLAT    k26-starter-kits  XRT_FLAT   (0+0)           0
```

同一轮复验确认 SSH、FPGA Manager、CMA 与 XRT Device Ready 均为 PASS。
`sudo -n -l` 显示的唯一 NOPASSWD xmutil 规则是精确的 `listapps` 命令；
`loadapp`、`unloadapp`、`bootfw_update` 仍只受板端原有“需要密码”的普通 sudo
策略控制，没有新增免密授权。

## 未采取的做法

- 未修改 `/tmp/dfx-mgrd.socket` 权限
- 未把 `ubuntu` 加入 root 组
- 未修改 `dfx-mgrd` umask 或 service
- 未授权任何 xmutil 写操作
- 未加载应用、bitstream、镜像、DTBO、boot firmware 或 QSPI 内容
