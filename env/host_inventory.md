# Host inventory

审计时间：2026-09-22 至 2026-09-23（Asia/Shanghai）

## 结论

- Ubuntu 工作站：`Ubuntu 24.04.5 LTS`，`x86_64`。
- CPU：Intel Core i7-14650HX，24 logical CPUs。
- 内存：31 GiB RAM，8 GiB swap，当前可用约 21 GiB。
- 根文件系统：444 GiB；AMD 2024.2 安装及验收后可用约 241 GiB。
- AMD FPGA 工具：项目本地 Vivado、Vitis、Vitis HLS 均为 2024.2，并已通过真实 smoke tests。
- 系统级 Python pip、CMake、Ninja、ccache、python3-venv 当前未安装；已在项目目录准备隔离的用户态 fallback，避免冒充系统包安装。
- 未执行系统升级；本轮验收所需功能由项目本地工具与依赖满足，不依赖
  host `sudo apt`。

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

## FPGA 工具探测（更新）

```text
source env/setup_fpga.sh
vivado    -> v2024.2 (Build 5239630)
vitis     -> v2024.2 (Build 5238363)
vitis_hls -> v2024.2 (Build 5238294)
```

安装根目录为
`/home/zhiro/research/kv260-vlm/tools/Xilinx/`。工具没有写入全局 PATH，必须
先 source 项目提供的 `env/setup_fpga.sh`；这是有意的项目隔离设计。

## 保护性约束

本次未执行 `apt full-upgrade`、`dist-upgrade`、系统升级、启动分区修改、QSPI/boot firmware 修改或板端 bitstream 加载。
