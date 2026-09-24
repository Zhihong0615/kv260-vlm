# 研究里程碑 RM01：从近作失效区间到 MiniCPM-V/KV260 可证伪假设

日期：2026-09-24
证据范围：已发表论文及其本地全文阅读笔记、冻结的 MiniCPM-V 4.6 host trace/profile、K26 器件资料。此文不是贡献声明。没有在 KV260 上执行推理、采集 PL/DDR 测量或加载 bitstream。

## 结论

目前没有足够证据选定论文 idea。最接近的 KV260 VLM 工作已经覆盖共享 ViT/LLM 矩阵资源、分相 overlay、Log8 attention、tile-major 流水、double buffering、矩阵级 host dispatch 和 PS–PL/DDR 数据移动。近作也已经覆盖 GDN 状态的片上驻留与融合。因此，“加一个调度器”“按阶段切 bitstream”“复用 buffer”“bank 分配”或“加速 Q4_K”都不能作为本项目的创新声明。

目前只保留三个待证伪的设备行为假设：多图组是否造成真实 PL 工作集溢出；GDN 状态是否在真实阶段边界产生额外交接成本；真实 MiniCPM-V 请求是否触达六个 full-attention 层的 K26 长上下文拐点。它们都要先与最强静态 null 比较；任何一个都可能被直接否定。优先级最高的第一项工作是满足所有既有门槛后，对板上 CPU-only 完整 VLM 请求做受控分阶段测量，以决定后续硬件方向，而不是先实现候选机制。

## 近作如何由现象推到机制

### 1. ReCoVLM：异构分工和固定形状视觉压缩

1. **现象：** 视觉编码、跨模态 prefill、单 token decode 的算力/带宽平衡不同；视觉 token 剪枝又使送往 FPGA 的序列长度随输入变化，导致固定流水线负载不齐。
2. **原因：** 单一设备和单一精度/数据流无法同时适应三个阶段；下游 FPGA 解码器既受 DDR 带宽约束，也受可变 KV 长度影响。
3. **已有方法缺口：** 通用剪枝可能损失精度；剪枝后的可变 KV 长度不适合固定 FPGA 管线；GPU 的逐 token 解码也未充分利用吞吐型硬件。
4. **核心机制：** GPU 执行视觉编码和跨模态 prefill，FPGA 执行 decode，ARM 执行 LM head/sampling；先空间合并再 query-aware 过滤，将视觉 token 归一到中间/最终固定长度；另用静态 KV sink/ring、流式融合及按 DDR bank group 放置 MoE burst。
5. **证据：** 在 LLaVA-1.5-7B 和 MoE-LLaVA-1.8B-4e 上将 576 个视觉 token 减到 32 个，论文报告相对平均准确率分别为 89.4% 和 88.9%，GPU→FPGA KV 传输延迟下降 87.6%；硬件是 Orin Nano + PCIe + VU9P，batch=1。
6. **边界：** 这已占据“异构阶段分工、视觉 token 压缩、固定形状、静态 KV、bank-group 放置”等一般主张，但并未测量 MiniCPM-V 4.6 的混合视觉压缩和 KV260 PS–PL 成本。它的 PCIe/VU9P 结果不能外推到 K26。来源：[FCCM 2026 论文 DOI](https://doi.org/10.1109/FCCM68464.2026.00026)，本地核读卡：[recovlm.md](/home/zhiro/research/kv260-vlm/literature/notes/recovlm.md)。

### 2. UniVLM：在 KV260 共享视觉和语言矩阵硬件

1. **现象：** ViT 先运行、LLM 随后运行，矩阵计算资源在两阶段之间可复用；独立引擎和未融合的 attention/MLP 中间值增加逻辑与存储。
2. **原因：** 阶段时间上顺序执行，但分别配置硬件会让资源在另一阶段闲置；朴素切换和中间表示又增加数据搬运。
3. **已有方法缺口：** 独立视觉/语言矩阵引擎重复占用资源；通用混合精度如果在阶段间往返 FP16/BF16，也会增加开销。
4. **核心机制：** 在 KV260 上共享静态/动态 GEMM 单元，调整 Q/K/V 投影及 attention tile/head 顺序，并把 MLP Up/Gate/SiLU/Down 流水化；采用端到端 W5A8 路径。
5. **证据：** 作者在 SmolVLM2-500M-Video-Instruct 上报告 24.29 prefill、14.28 decode token/s；共享与分离引擎消融报告 LUT、DSP 和片上存储下降。量化相对 FP 的 OCRBench 与 ScienceQA-IMG 分别下降 3.4 和 5.9 个百分点。
6. **边界：** 已排除“首次在 K26 共享 ViT/LLM GEMM”“跨阶段矩阵资源复用”或“通用低 buffer MHA/MLP”为新 idea。不同模型/量化留下的只是待测 MiniCPM-V 工作负载约束，不能单靠模型不同主张新颖性。来源：[AICAS 2026 官方论文/论文集入口](https://2026.ieee-aicas.org/publication/)，本地全文卡：[aicas_univlm.md](/home/zhiro/research/kv260-vlm/literature/notes/aicas_univlm.md)。

### 3. VersaVLM：以测得的阶段差异选择两个 overlay

1. **现象：** 该 VLM 的 prefill 偏计算受限，decode 偏带宽受限；均匀 INT8 attention 数值表示会抹掉很小的 attention numerator。
2. **原因：** 一个数据表示损害数值质量；一个硬件/内存映射无法同时匹配两个阶段的复用和带宽行为。
3. **已有方法缺口：** 单一 INT8 表示造成质量损失；单一阶段映射承担另一阶段不需要的计算或存储组织。
4. **核心机制：** Log8 保存 attention numerator，并用独立 prefill/decode bitstream、阵列和存储调度；llama.cpp 在阶段边界装入第二个 bitstream，论文将 803.916 ms 切换时间计入。
5. **证据：** KV260/SmolVLM2 上，501-token prompt + 1024-token output 的作者结果为 CPU 350.7 s、VersaVLM 97.1 s；FP16 CPU 与 FPGA 的 OCRBench 分别 55/120 和 50/120。
6. **边界：** 双 overlay 是任何共享/动态架构必须击败的静态强基线，且切换时间必须计入。泛化的“prefill/decode 特化”已被覆盖；只有 MiniCPM-V 的实际工作负载证明现有两个 overlay 方案遇到新硬约束时才有后续问题。来源：[AICAS 2026 官方论文/论文集入口](https://2026.ieee-aicas.org/publication/)，本地全文卡：[aicas_versavlm.md](/home/zhiro/research/kv260-vlm/literature/notes/aicas_versavlm.md)。

### 4. Memory-Centric VLM：把带宽与控制粒度直接作为设计变量

1. **现象：** 论文估算 prefill tile 约需 40 B/cycle、decode tile 约需 129 B/cycle，超过其四通道 64 B/cycle 的接口预算；逐 tile 由 PS 配置也产生控制间隙。
2. **原因：** 不连续布局、重复 activation 搬运、decode 权重读取及细粒度握手把有效带宽和控制开销推到关键路径。
3. **已有方法缺口：** 增加 MAC 数不能弥补接口预算不足；逐 tile 的 host handshaking 也不能靠矩阵算力优化消除。
4. **核心机制：** 四路 AXI 读、double buffering、tile-major prefill activation、decode activation 一次 bulk load，并将 PS 配置从 tile 提升到 matrix 粒度。
5. **证据：** 作者在 KV260/SmolVLM2 报告 300 MHz 设计、分阶段 GEMM/GEMV 及 end-to-end ablation；官方赛道结果为 50.452 prefill 和 38.552 decode token/s。论文说明正式提交版仍有少量 GEMM 留在 APU，较高 prefill 数来自扩展构建，比较时须保留此限定。
6. **边界：** “批量 dispatch、四路读、双缓冲、布局转换或降低 PS–PL 搬运”本身不新。必须用 MiniCPM-V 实际阶段、每组实际字节数和 K26 可用存储，证明静态矩阵级控制仍存在特定失效区间。来源：[AICAS 2026 官方论文/论文集入口](https://2026.ieee-aicas.org/publication/)，本地全文卡：[aicas_memory_centric_vlm.md](/home/zhiro/research/kv260-vlm/literature/notes/aicas_memory_centric_vlm.md)。

### 5. Hummingbird：从 DDR 仲裁和事务对齐问题出发

1. **现象：** KV260 多个 AXI 端口并不能自动达到理论聚合带宽；端口争用、DRAM 行/列访问错位和 embedding 占用会降低有效带宽或挤压内存。
2. **原因：** 事务粒度与列窗口不对齐导致行切换/仲裁浪费；低比特模型中仍有较大的 FP16 embedding 占用。
3. **已有方法缺口：** 单纯增加端口不能解决 DDR 控制器争用；权重、KV 和 embedding 也不能在有限容量下全都静态常驻。
4. **核心机制：** 调整每端口 BTT 与列对齐基址，结合 GEMV activation reuse、GQA buffering 和 embedding 旁路/卸载。
5. **证据：** KV260 的 LLaMA3-8B 短上下文 prefill:decode=32:32 测量报告约 94% DDR 带宽效率；工作负载是文本 LLM，不能直接代表 VLM 图像组传递。
6. **边界：** DDR 优化已是 KV260 先例。项目需先测真实 MiniCPM-V 的 AXI/DDR 字节、stall、事务尺寸及相位间争用；仅用 host allocator range 或理论字节数不足以提出新 bank/带宽机制。来源：[Hummingbird 论文全文](https://arxiv.org/html/2507.03308v1)。

### 6. Persistent-State Dataflow：GDN 的状态往返可由驻留机制消除

1. **现象：** batch-one Gated DeltaNet 单层每 token 仅约 4.2M FLOPs，却读写 32 个 FP32 128×128 recurrent matrix，约 2 MiB 状态。
2. **原因：** 小算术强度下，反复从外存取回并写回同一 recurrent state 成为主要成本。
3. **已有方法缺口：** 普通步骤让状态经历多次完整读写；只优化算术但保留状态往返，未消除主要瓶颈。
4. **核心机制：** 在 U55C BRAM 驻留一层状态，融合递推读取/写回，并用 head 并行与流水处理；H_iter 受片上容量及布线资源限制。
5. **证据：** 论文实装的 H_iter=2 设计在 263 MHz 报告 161.7 μs；H_iter=4 未通过 routing。更激进设置部分为周期估算而非实测实现。
6. **边界：** 通用状态驻留和递推融合已被覆盖。MiniCPM-V 每请求状态远大于 K26 片上存储，也不能据此重新命名为 bank/state scheduler。只剩一个边界问题：模型真实阶段切换是否造成已测得的额外交接流量。来源：[IPDPSW 2026 DOI](https://doi.org/10.1109/IPDPSW71298.2026.00064)，[论文全文](https://arxiv.org/html/2603.05931v1)，本地核读卡：[persistent_state.md](/home/zhiro/research/kv260-vlm/literature/notes/persistent_state.md)。

### 7. DAMP：由 state 误差与衰减行为决定混合精度

1. **现象：** 统一降低 recurrent state 精度会在精度、存储和 token latency 之间产生不理想折衷；不同通道的误差敏感性和状态衰减并不相同。
2. **原因：** 线性递推状态的持久性与数值误差随通道变化，统一位宽会让不敏感通道浪费空间或让敏感通道过度量化。
3. **已有方法缺口：** uniform quantization 不利用校准误差及递推状态衰减差异；仅优化算子计算不减少状态保存和传输量。
4. **核心机制：** 用校准误差和衰减 persistence 给不同通道分配不同状态精度，再用压缩后的 recurrent state 执行推理。
5. **证据：** 作者在 GPU 线性注意力模型上报告 9.9 bit/value、状态存储减少 69.1%，并报告最高 10.9% full-model TPOT 改善，质量接近 FP32。
6. **边界：** 这是 GPU 工作而非 FPGA/K26 实现，但已覆盖“按 GDN 状态误差做混合精度”这一通用机制。即便按其压缩比例估算 MiniCPM-V，剩余 state 仍高于 K26 全部 BRAM+URAM，且精度与实测 K26 代价未知。来源：[DAMP 论文](https://arxiv.org/abs/2608.27513)。

### 8. StreamTensor：把 layout、融合与流速约束共同优化

1. **现象：** producer 和 consumer 对同一个逻辑 tensor 可能采用不兼容的迭代顺序；融合虽省中间存储，却可能引入 layout conversion、速率失配、stall 或死锁。
2. **原因：** 普通 shape/dtype 描述不包含 stream iteration map，而 layout、tile、FIFO、融合和片上存储预算相互耦合。
3. **已有方法缺口：** 独立调优每个 kernel 或直接做 naive fusion 看不到跨 kernel 的布局兼容和 token-rate 约束。
4. **核心机制：** 以迭代 tensor type 表达 affine stream layout，插入 ping-pong converter，在片上容量预算下搜索融合并求满足 token rate 的 FIFO 深度，同时生成 host/DMA runtime 支持。
5. **证据：** 论文在 U55C/Vitis、W4A8、16GB HBM 和约 41MB 片上资源条件下评估；GPT-2 latency 报告为 Allo 的 0.76 倍、A100 的 0.64 倍，且评估若干 layer 的中间存储。
6. **边界：** 不是 K26 完整 VLM 工作，但已覆盖通用 layout、融合、FIFO/速率与 runtime 支持。H1 只有在 MiniCPM-V 多图组的真实 K26 物理容量拐点未被最佳静态 layout/fusion/null 消除时才值得继续。来源：[MICRO 2025 StreamTensor](https://arxiv.org/html/2509.13694)。

### 9. Fermi MiniCPM-V 4.6 报告：作者如何用反常实验定位真正成本

1. **现象：** 手写 GEMM 仅达到 37% 峰值而 cuBLAS 达到 66%；初版 chunked GDN scan 慢 2.4×；4-bit decode 反比 8-bit 慢；2k prompt 隐藏了 10k 长上下文 prefill 崖点。
2. **原因：** GEMM 实现效率低于假设；GDN forward-substitution 子步骤单独占到约 92% 时间；低 bit unpack 的 shift 成本抵消访存收益；长序列 attention 的二次复杂度被短 prompt 掩盖。
3. **已有方法缺口：** 峰值算力、低比特字节数和短 prompt 结果不能替代端到端 profiling；复合 kernel 的平均耗时也隐藏单个坏组件。
4. **核心机制：** 分解组件并实测，先改变算法/缓冲策略，再测完整请求。例如重用已有 score buffer 做 attention，避免额外写读临时矩阵；并针对 GDN 单独修复耗时最高的递推步骤。
5. **证据：** 论文报告 10k prefill 从 479.3 s 降至 27.7 s，vision attention 从 5.7 s 降至 0.93 s；这是 C2075 GPU 的单机工程报告，不是 FPGA 或 K26 测量。
6. **边界：** 它给本项目的启发是如何由异常数据找瓶颈，不是可以直接移植的算法贡献。每次都要检查特定设备上的组件成本，并用强静态实现作 null；GPU 上的速度比不等于 K26 的设计变量或收益。来源：[Fermi MiniCPM-V 4.6 全文](https://arxiv.org/html/2607.14568)。

## MiniCPM-V 证据能够说什么

- 当前 pinned 模型是 SigLIP2-400M vision + Qwen3.5-0.8B language。文本侧 24 层中有 18 个 GDN/linear-attention 层、6 个 full-attention 层；vision encoder 为 27 层。官方仓库描述了混合 4x/16x 视觉压缩：[OpenBMB MiniCPM-V](https://github.com/OpenBMB/MiniCPM-V)。
- 三个选定 host 在线 trace 包含 3/5/7 次 encoder 调用；vision+projector 合并跨度中位数为 3.20–7.25 s，image-embedding prefill 为 0.45–1.02 s。跨度还包含图构建、scheduler、copy 等 host 工作，不可解释为纯算力或 KV260 时延。
- 选定 host trace 的 Q4_K image-prefill FFN N=60/64/66/70；解析式 padding screen 显示固定 N tile=8 的列占用为 97.3%。因此“宽度尾部必然要求动态 tile”目前不成立，静态 T=8 与 shape-keyed dispatch 是必比 null。
- host 图和 buffer 记录不能说明板上 kernel 放置、物理活跃区间、AXI/DDR 字节、PL stall、可用 BRAM/URAM 或 PS–PL copy。
- GDN backing allocation 的模型态估算为每层 1 MiB recurrent state ×18，加每层 72 KiB conv history ×18，总计约 19.266 MiB/活跃序列。K26 理论总 BRAM+URAM 约 2.883 MiB（144×36 Kb BRAM + 64×288 Kb URAM，尚未扣除计算/权重/FIFO）；全状态约为其 6.7 倍。来源：[AMD K26 数据手册](https://www.amd.com/content/dam/xilinx/support/documents/data_sheets/ds987-k26-som.pdf)。这否定“全模型状态可驻留”，但不证明发生 PS–PL copy。

## 可证伪的研究假设

下面三项是要用数据淘汰的假设，不是宣称新机制。共同筛选门槛暂定为：对完整请求，候选必须较最强静态对照至少降低 10% 配对中位时延且置信区间排除零，质量损失不超过 1 个百分点；正式实验前须冻结置信区间、质量集和误差边界。如果现有项目质量合同更严格，以既有合同为准。

### H1 — 多图组是否引发 K26 vision/projector 工作集溢出

- **假设 / 可观测差异：** 对 5 组 N≈70，或混合 7 组 [64,70,70,70,70,70,70]，完整 vision/projector 路径的并行活跃 tensor 超过实际可用 PL 存储，造成重复 PS DDR spill、回拷或 producer/consumer 闲置；且这类成本不是单组最大 shape 的固定静态分配能消除的。
- **与近作的实质差异：** ReCoVLM 已做 token 形状归一与 KV 传输压缩；UniVLM 已做共享 MHA/MLP 和 tile 化；Memory-Centric VLM 已做双缓冲、tile-major 与矩阵级 dispatch。剩余可研究点只能是 MiniCPM-V 多视觉组、混合压缩形状与 K26 实际 scratch capacity 的组合是否出现这些静态方案未覆盖的物理容量拐点，不能把 buffer/liveness allocator 本身作为新机制。
- **需要的真实 trace：** 同一冻结模型/请求上的 3 组、5×70 组与混合 7 组板上 trace；逐组输入/输出字节、实际 backend/op shape、PL 本地存储高水位、buffer owner/last-use、DMA/AXI read/write、DDR stall、submit/sync 和完整请求 TTFT/总时延。只保留能对齐到物理分配和传输的记录。
- **最强静态方案：** 固定最大 shape 的静态一/双缓冲 + 最佳矩阵级 dispatch；同时比较静态 shape bucket/full per-op key、固定 T=8 及经实际 timing 调优的 tile；与 CPU-only 完整请求对照。ReCoVLM 固定形状处理和 Memory-Centric VLM 的双缓冲/矩阵级 dispatch 是最近强控制。
- **否定结果：** 无实际 spill/拷贝/容量溢出；成本被固定最大 shape + 静态双缓冲完全覆盖；候选收益低于筛选门槛；或 vision/projector 不是请求关键路径。满足任一项即关闭该 idea，不开发动态分配/调度器。

### H2 — MiniCPM-V GDN 状态在 VLM 阶段边界是否有额外交接成本

- **假设 / 可观测差异：** 18 层 GDN 状态跨图像 embedding prefill、文本 prefill、首 token decode 的 PS/PL owner 变化会引发额外 copy/cache maintenance/synchronization；这部分开销超过每层正常 state update，并在完整请求中可见。
- **与近作的实质差异：** Persistent-State Dataflow 已覆盖 GDN state residency、融合和减少往返；DAMP 已覆盖按通道混合精度 state storage。项目不研究把状态驻留或压缩本身改名，而只检测 MiniCPM-V 多阶段边界是否额外迁移状态。当前估算约 19.266 MiB/序列，大于 K26 全部 BRAM+URAM，故全驻留不现实。
- **需要的真实 trace：** 按 18 层记录 state backing buffer 地址/所有者、每阶段读写字节、显式 copy 与 cache clean/invalidate、AXI 计数和 stall；跨 vision/text prefill/first decode/steady decode 关联同一 sequence/cache ID；再对齐阶段和完整请求 latency。host GDN node tensor 只能用于选点，不能代替板上流量。
- **最强静态方案：** 固定 CPU-only 完整 VLM；若已有合规 PL path，则以每层共享 DDR 的原位 state buffer、固定层顺序及 fused GDN kernel 为对照，并按相同硬件配置比较阶段边界策略。Persistent-State Dataflow 的单层 on-chip fused 实现是算法参照；不能拿它与不同平台 raw latency 直接比较。
- **否定结果：** 阶段间 buffer 地址/owner 不变且无额外交接；额外交接低于正常 state update/权重流量并对完整请求无显著影响；或共享 DDR 原位静态方案与任何边界处理相同。任一结果均关闭 state-boundary idea；不做普通状态驻留/银行分配。

### H3 — 真实 MiniCPM-V 长上下文是否碰到六个 full-attention 层的 K26 拐点

- **假设 / 可观测差异：** 实际部署的多图组 + 文本输入使六个 full-attention 层进入上下文长度阈值，在 K26 上产生可观测 score/temporary buffer spill 或 DDR 流量拐点，足以主导 TTFT；该拐点在同样精度和完整请求条件下不能由最佳固定 tiled/GEMM attention 缓冲消除。
- **与近作的实质差异：** Fermi 已针对同一 MiniCPM-V 4.6 在 C2075 上揭示长上下文 prefill 崖点并用 score buffer 复用大幅优化。差别必须来自 K26 的实际存储/带宽限制造成、且在真实 MiniCPM 视觉 token + 问题长度区间出现的另一种硬件失效，不能主张通用 attention tiling 或 score-buffer 复用。
- **需要的真实 trace：** 实际请求输入 token、切片/视觉 token、六层每层 Q/K/V 与 attention 时间、score 临时区分配和 spill 字节、PS–PL/DDR 流量/停顿、TTFT/总时延。长度扫描须覆盖真实请求分布，只在部署确有长输入时扩展到 2k/5k/8k/10k；不可用合成 10k 单独证明部署重要性。
- **最强静态方案：** CPU-only 完整请求；对任何 PL path，采用最佳固定 tile/GEMM attention、已有 score buffer 原位复用和静态 double buffering，并计入转换与 dispatch。把 Fermi 的 score-buffer 方法作为算法级对照，但重新在 K26 实测。
- **否定结果：** 真实请求远低于拐点；attention 不是关键路径；最佳静态 buffer/GEMM 已移除拐点并达到相同完整请求时间；或改进只存在于不真实的超长上下文。满足任一条件即拒绝该 idea。

## 已关闭或暂不进入候选的方向

- **通用 GDN 状态驻留/状态融合：拒绝。** Persistent-State Dataflow 已覆盖核心机制；MiniCPM-V 的状态体量只证明无法全量放入 K26 理论片上存储。只保留 H2 这项窄测量问题。
- **根据视觉组 ordinal/顺序选择 tile：关闭。** B03/B04/B05 的 24 个选中 group 中，group ordinal/sequence 未增加完整 per-op signature set/multiset/sequence 信息；image-prefill 固定 T=8 的解析式占用为 97.3%。没有板上成本前不重启该动态选择主张。
- **通用 phase scheduler/two-overlay/shared-GEMM、PS–PL dispatch aggregation、double buffer、bank placement、liveness reuse：已有直接近作。** 只有先测得新失效区间且胜过这些强静态实现才可重新讨论。
- **命令聚合/重放、CPU/PL 自动切换：暂不列为 idea。** Memory-Centric VLM 已做到 matrix-level dispatch，UniVLM/VersaVLM 已覆盖共享单 bitstream与 phase overlay；现有 host trace 不包含 K26 的每命令成本。

## 决定下一步与板卡状态

1. 先完成测量所需的软件输入与当前 SHA 绑定准备、synthetic ALPHA、fresh live-resource check 及 inference-specific owner window；只有满足 readiness map 并获得该次有界操作授权，才开始 CPU-only 完整模型测量。
2. 首个板测采用冻结的 3-group、5-group 和 mixed 7-group TextVQA 请求，记录每阶段 span、TTFT/总时延、实际执行 op/backend/shape、CPU/RSS/page fault/swap/frequency/temperature。CPU-only 只回答真实 KV260 瓶颈和是否继续，不证明 PL 性能。
3. 如 CPU 测量确认视觉路径关键，才进入预先批准的固定 PL prototype 和 H1 的物理 DMA/AXI/lifetime 测量；如果阶段不关键，则停止给它分配 PL 资源。
4. 目前板卡 **NOT READY FOR BOARD EXECUTION**：当前模型/attestation 受控 staging、synthetic ALPHA、fresh resource、inference-specific owner window 仍未满足；这次未访问板卡。P3 继续 **NO_GO_NOW**，没有研究 bitstream/已验证 rollback/physical recovery route。

里程碑决定：L01/W01/M01/G01 本轮已完成并合并为 RM01；不新增 parser/runner Builder→Reviewer 工作。下一件能改论文/架构结论的任务，是按 readiness gate 准备并请求一次有界 CPU-only KV260 完整 VLM 测量；在门槛满足之前继续做不依赖板卡的论文/trace 合成，不虚报硬件结论。
