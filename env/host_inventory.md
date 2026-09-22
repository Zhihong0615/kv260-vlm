# Host inventory

审计时间：2026-09-22（Asia/Shanghai）

## 结论

- Ubuntu 工作站：`Ubuntu 24.04.5 LTS`，`x86_64`。
- CPU：Intel Core i7-14650HX，24 logical CPUs。
- 内存：31 GiB RAM，8 GiB swap，当前可用约 21 GiB。
- 根文件系统：444 GiB，总可用约 390 GiB（8% 使用率）。
- AMD FPGA 工具：`vivado`、`vitis`、`vitis_hls` 均未找到。
- 系统级 Python pip、CMake、Ninja、ccache、python3-venv 当前未安装；已在项目目录准备隔离的用户态 fallback，避免冒充系统包安装。
- `sudo apt update` 未执行成功：当前 sudo 需要交互式密码，自动化终端没有密码输入能力。状态：`BLOCKED`。

## 只读命令结果摘要

```text
PRETTY_NAME="Ubuntu 24.04.5 LTS"
VERSION_ID="24.04"
VERSION_CODENAME=noble
Linux zhiro-ThinkBook-16p-G5-IRX 7.0.0-31-generic #31~24.04.1-Ubuntu SMP PREEMPT_DYNAMIC ... x86_64
/bin/bash
git version 2.43.0
Python 3.12.3
gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
g++ (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0
```

## 已安装基础包

已有：`build-essential`、`gcc`、`g++`、`make`、`git`、`pkg-config`、`python3`、`curl`、`wget`、`rsync`、`unzip`、`zip`、`tar`、`xz-utils`、`jq`、`libssl-dev`、`sysstat`。

缺失或未安装：`cmake`、`ninja-build`、`ccache`、`python3-pip`、`python3-venv`、`tmux`、`screen`、`htop`、`libcurl4-openssl-dev`（包状态需在 apt 可用后复核）。

## FPGA 工具探测

```text
which vivado    -> not found
which vitis     -> not found
which vitis_hls -> not found
```

以下目录均不存在：`/tools/Xilinx/`、`/opt/Xilinx/`、`/opt/AMD/`、`/tools/AMD/`、`~/Xilinx/`、`~/AMD/`。

## 保护性约束

本次未执行 `apt full-upgrade`、`dist-upgrade`、系统升级、启动分区修改、QSPI/boot firmware 修改或板端 bitstream 加载。
