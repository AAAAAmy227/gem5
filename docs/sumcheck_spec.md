你现在位于我们 AI+X 课程项目使用的 gem5/Garnet repository 中。请直接完成下面的工程任务，而不只是分析或制定计划。

你拥有在当前项目分支中读取、修改、编译、测试和运行实验的权限。请持续推进所有能够完成的部分；只有遇到真正依赖外部信息、权限或不可用环境的阻塞时才跳过，并在最终报告中准确说明。不要修改或丢弃不相关的现有改动，尤其要保留之前 Lab3 的 Ring实现。不要执行 destructive git 操作，不要合并到 main。

如果 workspace 中存在 `sumcheck_noc_reference_bundle.zip`，先解压并完整阅读其中：

- `sumcheck_noc_design_contract_v0.1.md`
- `sumcheck_noc_reference/README.md`
- `sumcheck_noc_reference/sumcheck_noc.py`
- `sumcheck_noc_reference/DEADLOCK_PROOF.md`
- `sumcheck_noc_reference/EVALUATION_PLAN.md`
- `sumcheck_noc_reference/outputs/`

这些文件是 architecture 和逻辑行为的 reference specification，但不是 gem5 实现，也不是周期级性能结果。若 reference 与当前 prompt 冲突，以本 prompt 和实际 gem5 API 为准。

# 一、项目目标

课程 Topic 1 要求：

> Implement at least one new topology and the corresponding deadlock-free adaptive (non-deterministic) routing algorithm. Select appropriate baselines and compare performance.

我们要实现一套针对 Sumcheck reduction/broadcast 通信优化的分层 NoC：

\[
\text{64 worker PEs}
\rightarrow
\text{4 cluster gateways/controllers}
\rightarrow
\text{1 root controller}
\]

最终必须包含：

1. 新 topology；
2. deterministic routing baseline；
3. credit-aware adaptive/non-deterministic routing；
4. 实际执行的 `VC_U/VC_D` deadlock-prevention rule；
5. CDG 证明/自动验证；
6. causal Sumcheck traffic；
7. Mesh、p sweep、fixed/adaptive、placement、aggregation 等 baselines/ablations；
8. 可复现的 gem5 实验脚本和结果。

不要用“上层结构是树，所以 deadlock-free”作为证明。cluster 内部是 mesh，gateway-entry shortcut 也会形成物理环；wormhole deadlock 必须根据 channel dependency graph 和 VC 规则判断。

# 二、Architecture

## 2.1 Router 与节点编号

默认结构：

- 4 clusters；
- 每个 cluster 是 4×4 mesh；
- 每个 cluster 有 16 个 worker PE；
- 共 64 个 worker；
- 4 个 gateway router：`G0..G3`；
- 1 个 root router：`R`；
- 共 69 个 routers。

建议固定 router ID：

```text
worker router:
id = cluster * 16 + row * 4 + col
range = 0..63

G0..G3:
64..67

R:
68
```

请把映射集中封装，不要把 magic number 分散在 routing code 中。

每个 worker router 连接一个 worker endpoint。

每个 `G_i` 是：

```text
gateway router
+
与它相连的 controller/aggregator endpoint
```

`R` 同样要有 root controller endpoint。

Aggregation 必须发生在 endpoint/controller 中：

```text
packet eject
→ controller 等待所需输入
→ 计算/模拟 aggregation
→ inject 一条新 packet
```

不能让 router 在保持输入 VC 的同时完成 aggregation，也不能默默把 router 本身当作计算单元。这一 packet termination/reinjection 边界是 deadlock proof 的组成部分。

如果当前 tester/controller 框架不方便提供 69 个 endpoint，请实现最接近上述语义的方案，并明确记录 logical endpoint、NI、ExtLink 和 router 的映射。Mesh baseline 也必须承载相同的 64 worker + 4 gateway-controller + 1 root-controller 逻辑角色；如果采用 endpoint co-location 或多个 ExtLinks，共址造成的端口和注入竞争必须计入成本，不能悄悄忽略。

## 2.2 Internal links

每个 4×4 cluster 内部使用普通二维 mesh：

- 水平边：4×3；
- 垂直边：4×3；
- 每 cluster 共 24 条 undirected mesh links；
- 四个 cluster 共 96 条。

每个 `G_i`：

- 与 `R` 有一条直接 undirected link；
- 与本 cluster 的 `p` 个 entry PE router 分别有一条直接 undirected link。

因此：

\[
N_{\text{routers}}=69
\]

\[
L_{\text{undirected}}
=
4(24+p+1)
\]

验收值：

| p | Routers | Undirected internal links |
|---:|---:|---:|
| 1 | 69 | 104 |
| 2 | 69 | 108 |
| 4 | 69 | 116 |

## 2.3 Entry placements

支持命令行参数：

```text
--entries-per-cluster=1|2|4
--entry-placement=staggered|corners
```

4×4 mesh 内坐标是 `(row, col)`。

默认 placements：

```text
p=1:
(1,1)

p=2:
(0,1), (3,2)

p=4 staggered:
(0,1), (1,3), (2,0), (3,2)

p=4 corners:
(0,0), (0,3), (3,0), (3,3)
```

`corners` 只用于 p=4 ablation。

请为所有方向使用清晰且稳定的 port names，例如：

```text
Local
Dim0Pos / Dim0Neg
Dim1Pos / Dim1Neg
Gateway
Entry0..Entry3
RootUp
RootToG0..RootToG3
```

根据当前 gem5 topology API 调整名字，但 routing code 不得依赖 Python dictionary 的偶然遍历顺序。

## 2.4 Link latency

主要实验可以使用所有 internal links latency=1 的抽象模型，但必须额外提供长链路 sensitivity 参数，例如：

```text
--gateway-entry-link-latency=1,2,4
--root-gateway-link-latency=1,2,4
```

不要把一条物理上可能很长的 gateway-entry shortcut 永久当作免费一周期链路而不报告假设。

# 三、Sumcheck workload

目标 workload 是 degree≤3 的 NoCap/Spartan 类 Sumcheck kernel：

- field element：256 bits = 32 bytes；
- partial polynomial：4 field elements = 128 bytes；
- challenge：1 field element = 32 bytes；
- flit size：使用当前 Garnet 配置；reference 假设 16 bytes/flit；
- 变量/数据规模：\(2^{20}\)；
- 位映射：

```text
[cluster: 2 bits][PE: 4 bits][local: 14 bits]
```

逻辑 round 划分：

```text
Phase A: 14 worker-distributed rounds
A→B boundary: worker state moves to cluster controller
Phase B: 4 cluster-controller rounds
B→C boundary: controller state moves to root
Phase C: 2 root-local rounds, no network messages
```

## 3.1 Phase A 每轮消息

对每个 cluster：

1. 每个非 entry worker 向分配给自己的 entry PE 发送一个 128-byte partial。
2. Entry PE 聚合它负责的 worker 以及自己的 partial。
3. 每个 entry PE 向 `G_i` 发送一个 128-byte entry aggregate。
4. `G_i` 聚合 p 个 entry aggregates。
5. `G_i` 向 `R` 发送一个 128-byte cluster aggregate。
6. `R` 等待四个 cluster aggregates，生成 challenge。
7. `R` 向每个 `G_i` 发送一个 32-byte challenge。
8. `G_i` 分别向 16 个 worker 发送 16 个 32-byte challenge packets。

不要假设硬件 multicast；除非项目另外实现 multicast，否则 `G_i→worker` 必须是独立 unicasts。

## 3.2 Phase boundary 与后四轮

14 轮之后：

- worker terminal state 先归约/打包到 entry；
- entry 把 state 送到 `G_i` controller；
- 接下来四轮，每个 `G_i` 向 root 发送一个 128-byte partial；
- root 向每个 `G_i` 返回一个 32-byte challenge；
- 四轮之后每个 `G_i` 向 root 发送 terminal state；
- 最后两轮 root 本地完成，不产生网络消息。

如果 reference JSONL traces 可用，优先读取并 replay 它们。

关键要求：

> 一个 trace event 只有在其全部 `depends_on` events 已经真正到达 destination 后才能 inject。

不接受仅按预先估计的时间戳发送、却不等待前驱 packet 到达的“伪 causal replay”。

Reference 验收值：

```text
p=1 aggregated trace: 2004 message events
p=2 aggregated trace: 2004 message events
p=4 aggregated trace: 2004 message events
```

同时实现/接入 pure-router/no-aggregation negative control：

- 前 14 轮每个 worker 直接向 root 发送 128-byte partial；
- root 分别向每个 worker发送 32-byte challenge；
- 每个 cluster 每轮 root cut：

```text
128 upward flits
32 downward flits
```

而 aggregation 版本是：

```text
8 upward flits
2 downward flits
```

两个方向均为 16× 差异。

无聚合 reference trace：

```text
1856 events
```

# 四、Deterministic routing

先实现并验证 fixed deterministic routing，再加入 adaptive。

## 4.1 基本规则

同 cluster 的 worker→worker：

```text
fixed dimension-order routing
dim0 first, then dim1
```

Worker→assigned entry：

```text
fixed dim0-then-dim1
```

Entry→gateway：

```text
direct entry-gateway link
```

Gateway→root：

```text
direct gateway-root link
```

Root→gateway：

```text
direct root-gateway link
```

Gateway→worker：

1. 选择距离 destination worker 最近的合法 entry；
2. 固定 tie-break，优先较小 entry index；
3. 从 gateway 走 direct entry link；
4. 进入 mesh 后固定 dim0-then-dim1 到 destination。

Cross-cluster generic traffic：

```text
source side → gateway → R → destination gateway → destination mesh
```

不得绕过 root 在 cluster 间横跳。

为所有合法源/目的组合提供明确规则；遇到未覆盖或非法组合时 assert/fatal，而不是静默返回随机端口。

# 五、Credit-aware adaptive routing

Adaptive freedom 只放在 gateway 向 destination mesh 选择 entry 的阶段。

进入 mesh 后仍然使用固定 dim0-then-dim1，不允许 XY/YX 自适应、non-minimal wandering、backtracking 或重新选入口。

对每个候选 entry 计算：

\[
score(e)
=
ManhattanDistance(e,destination)
+
\lambda
\left(
1-\frac{freeCredits(e)}{capacity(e)}
\right)
\]

默认：

```text
lambda = 4.0
```

做成命令行参数：

```text
--entry-congestion-weight
--sumcheck-routing=fixed|adaptive
```

Credit 状态必须来自 candidate output port 下游合法 `VC_D` 的实际 credit/buffer 状态，不能读取所有 VC 的总和。

如果当前 Garnet API 没有直接暴露 credit：

1. 先检查当前版本的 `RoutingUnit`、`Router`、`OutputUnit`、`CreditLink` 和 `SwitchAllocator`；
2. 增加一个最小、只读的 helper；
3. 不要根据其他 gem5 版本猜函数名。

选择规则：

1. 最小 score；
2. 相同 score 使用 per-gateway rotating round-robin pointer；
3. route computation 对一个 head flit 只决定一次；
4. 决定后的 outport 存在 input VC/route state 中；
5. 若所选输出暂时无法分配合法 VC，则等待，不允许持有旧资源时跨 class 或反复换入口。

这里的 non-deterministic 指 routing relation 对同一 destination 存在多个合法输出，实际结果可随 credit state 和仲裁历史变化；不要求不可复现的随机数。所有实验必须可以通过 seed/config 重现。

必须添加 instrumentation：

- 每个 gateway 对每个 entry 的选择次数；
- fixed nearest 与实际选择不同的次数；
- 选择时各 candidate credit/occupancy；
- adaptive reroute rate；
- tie arbitration 次数；
- 每条 root/gateway-entry link 的 flits/utilization。

# 六、Deadlock-free VC discipline

## 6.1 VC partition

在每个 protocol vnet 内划分：

```text
VC offsets 0,1 → VC_U
VC offsets 2,3 → VC_D
```

要求：

```text
vcs_per_vnet >= 4
```

如果配置不足，启动时明确报错。

不要把不同 vnet 本身当作 U/D 分离；必须在每个 vnet 内分别保留非空 U、D subset。

## 6.2 Route phase

规则：

- worker→entry：U；
- entry→gateway：U；
- gateway→root：U；
- root→gateway：D；
- gateway→entry→worker：D；
- same-cluster generic PE→PE：固定 XY，并归入 U；
- cross-cluster：`U*D*`；
- `U→D` 只允许在 `R`；
- `D→U` 永远禁止。

Direct links 的方向类别：

```text
entry → G: U
G → entry: D
G → R: U
R → G: D
```

## 6.3 VC allocator enforcement

只在 route class 对应的 VC partition 中进行 output-VC allocation。

例如 packet 当前需要 D：

```text
只搜索当前 vnet 的 VC offsets 2,3
```

即使 offsets 0,1 有大量 credits，也不能 fallback 到 U。

需要在实际 `SwitchAllocator`/`OutputUnit` 路径中强制执行，而不是只在离线 checker 中标注。

Root 处的跨 cluster packet允许从 U input resource 申请 D output VC。任何其他 router 出现 U→D 或任意 D→U 都应 assert 或被 routing relation 排除。

# 七、CDG verification

把 reference CDG checker 移植或保留为独立验证脚本，枚举：

- 69 routers 的全部 ordered source/destination pairs；
- 每对节点的全部合法 entry choices；
- 每条 route 的 `(VC class, directed physical channel)`；
- 相邻 channel resource dependency；
- directed cycle detection。

验收规模：

```text
ordered pairs = 69 × 68 = 4692

p=1 legal routes = 4692
p=2 legal routes = 14548
p=4 legal routes = 52692
```

预期：

| p | U/D separated | Collapsed single VC |
|---:|---|---|
| 1 | acyclic | 可能仍 acyclic |
| 2 | acyclic | 必须找到 cycle |
| 4 | acyclic | 必须找到 cycle |

输出 single-VC cycle witness，作为“为什么不能只用一个 VC”的报告证据。

注意：

- Offline CDG 证明必须与最终 C++ routing 输出集合一致。
- 如果你改变任何 legal turn、entry choice 或 VC transition，必须同步更新 checker。
- 除 CDG 外，还要审查 Ruby protocol/message-class dependency；不能声称 CDG 自动证明整个 coherence protocol。
- Aggregator 必须 eject/reinject，不能在计算期间持有 wormhole channel。

# 八、Topology 与 routing 实现位置

先根据当前 repository 版本检查实际目录和 API；不要机械套用其他 gem5 版本。预计会涉及但不限于：

```text
configs/topologies/
configs/common/Options.py 或当前参数定义位置
src/mem/ruby/network/garnet/RoutingUnit.*
src/mem/ruby/network/garnet/Router.*
src/mem/ruby/network/garnet/OutputUnit.*
src/mem/ruby/network/garnet/SwitchAllocator.*
traffic generator / tester / controller
SConscript / SimObject declarations
```

建议新 topology 命名：

```text
SumcheckHierarchy
```

建议新增集中式配置/映射 helper，避免 topology Python 和 C++ routing 分别硬编码两套不同坐标。

如果 C++ 无法直接共享 Python mapping，至少生成/验证相同的 router-ID、cluster、entry table，并添加 regression test 检查二者一致。

# 九、Baselines 与 experiments

至少实现下面的实验矩阵：

| Variant | 目的 |
|---|---|
| Mesh_8x8_XY | conventional baseline |
| Hierarchy_p1_fixed | entry 数量 ablation |
| Hierarchy_p2_fixed | 中间点 |
| Hierarchy_p4_fixed | topology-only benefit |
| Hierarchy_p4_adaptive | adaptive 增量收益 |
| Hierarchy_p4_adaptive_buffer_matched | buffer cost sensitivity |
| Hierarchy_p4_corners | entry placement ablation |
| Hierarchy_p4_no_aggregation | aggregation semantic negative control |

Mesh baseline 必须使用相同 logical workload 和 packet sizes。

Worker 映射到 8×8 mesh 的四个象限：

```text
cluster 0 → rows 0..3, cols 0..3
cluster 1 → rows 0..3, cols 4..7
cluster 2 → rows 4..7, cols 0..3
cluster 3 → rows 4..7, cols 4..7
```

Reference static best-placement 是：

```text
G0=(2,2)
G1=(2,5)
G2=(5,2)
G3=(5,5)
R=(2,2)
```

可以把它作为 Mesh controller-placement baseline，但必须正确实现 co-location，并把额外 endpoint/ExtLink/local-port/NI 竞争计入成本。

不要直接复用 reference 中“288 input ports”的静态简化值。请根据实际 gem5 topology 中：

- routers；
- internal links；
- ExtLinks；
- local/network input ports；
- VCs；
- buffers；
- endpoint co-location；

重新计算真实成本。

## 9.1 Cost matching

Primary comparison：

- 相同 clock；
- 相同 internal-link latency；
- 相同 flit size；
- 相同 vnets；
- 每 vnet 4 VCs；
- 相同 per-VC buffer depth；
- 相同 offered application traffic。

另做 total-buffer-slot matched sensitivity：

1. 根据实际构建后的 Mesh 和 p=4 topology 统计所有实际 input buffers；
2. 计算总 buffer slots/bits；
3. 若当前 Garnet 支持 per-port/per-VC depth，构造精确相等配置并输出明确分配表；
4. 若不支持，不要伪称 exact cost matched：
   - 实现最小、局部的 per-port override；或
   - 做上下界/bracketing sensitivity，并明确仍非 exact match。

同时报告：

- routers；
- internal/external links；
- directed port ends；
- local ports；
- VC 数；
- buffer slots/bits；
- 最大 radix；
- \(\sum radix^2\) crossbar proxy；
- 长链路 latency 假设。

# 十、Traffic cases 与 metrics

至少运行：

1. causal Sumcheck trace；
2. uniform-random offered-load sweep；
3. cluster-skewed/bursty sweep。

Adaptive 的优势预计主要出现在 skewed/bursty 或接近 saturation 的负载；低负载下 fixed/adaptive 应大致相同。不要只选择对 adaptive 有利的一个点。

每个正式实验至少 5 个 seeds。如果完整 sweep 运行时间过长，先完成 smoke test 和较小 sweep，再提供可恢复的 batch script。

收集：

- 每 round completion cycles；
- total Sumcheck completion cycles；
- packets/flits injected and received；
- accepted throughput；
- saturation point；
- mean/P95/P99 latency；
- average hops；
- root-cut utilization；
- gateway-entry link utilization；
- maximum-link load；
- per-entry choice distribution；
- adaptive reroute rate；
- buffer/VC stalls；
- deadlock/livelock watchdog；
- topology/cost counters。

所有 variants 必须验证：

```text
packets_injected == packets_received
```

并设置合理 watchdog；超时必须输出未完成 packet、router、input VC、route class 和等待资源，便于诊断，不能只显示“simulation hung”。

# 十一、解析 regression oracle

下面是 reference 层的静态验收值，不是要求 gem5 cycles 相同：

| Variant | Mean PE→entry | Max distance | Max mesh-edge paths | Weighted flit-hop/cluster/round |
|---|---:|---:|---:|---:|
| p=1 | 2.00 | 4 | 8 | 370 |
| p=2 | 1.50 | 3 | 4 | 298 |
| p=4 staggered | 0.75 | 1 | 1 | 194 |
| p=4 corners | 1.00 | 2 | 2 | 234 |

注意 p=2 的 max mesh-edge paths 是 4，不是 3。达到 3 需要增加 XY/YX path adaptivity，而当前设计明确不这样做。

完整 reference trace 的静态结果：

| Variant | Total flit-hops | Peak undirected-link flits |
|---|---:|---:|
| Mesh 8×8 best controller placement | 16208 | 632 |
| Hierarchy p=1 fixed | 22448 | 1016 |
| Hierarchy p=2 fixed | 18160 | 536 |
| Hierarchy p=4 fixed | 11952 | 256 |
| Hierarchy p=4 no aggregation | 26048 | 2368 |

请在 gem5 injection 前或独立 test 中重算路径，确保 topology/mapping/packet size 没有偏离这些 reference assumptions。实际 Garnet latency/throughput不应被要求等于这些数字。

# 十二、必须添加的测试

至少覆盖：

1. p=1/2/4 router/link count；
2. 所有 entry coordinates；
3. 所有生成 route 只使用真实 physical links；
4. deterministic nearest-entry 和 tie-break；
5. 人工构造 credit 状态，使 adaptive 从最近入口改走另一个入口；
6. equal-score 连续 packets 能通过 round-robin 产生多个合法选择；
7. adaptive 只选择本 cluster 合法 entries；
8. 进入 mesh 后严格 dim0-then-dim1；
9. 每条 route 都是 `U*`、`D*` 或 `U*D*`；
10. 所有 U→D 只发生在 R；
11. 不存在 D→U；
12. output VC allocation 永不跨 U/D partition；
13. p=1/2/4 U/D CDG 无环；
14. p=2/4 collapsed single-VC CDG 有环；
15. trace dependency 无 forward/missing dependency；
16. aggregated trace event count；
17. no-aggregation trace event count和 root-cut traffic；
18. small smoke simulation 完成且 injected=received；
19. 相同 seed/config 的结果可复现；
20. 现有 Ring/Wormhole regression 不被破坏。

# 十三、执行顺序

严格按以下顺序实现，不要跳到画图或写报告：

1. 检查 repository、gem5 version、git status、现有 build/run 命令和 Lab3 改动。
2. 阅读 reference bundle，列出 reference 与实际 gem5 API 的映射。
3. 实现 topology 和 CLI 参数。
4. 添加 topology/path unit tests。
5. 实现 deterministic routing。
6. 编译并运行 deterministic smoke test。
7. 实现 credit state helper 和 adaptive entry choice。
8. 添加 adaptive instrumentation/tests。
9. 实现 VC_U/VC_D output allocation restriction。
10. 运行完整 CDG checker和 single-VC negative control。
11. 实现 causal trace replay 与 aggregation endpoints。
12. 实现 no-aggregation negative trace。
13. 实现 Mesh 和其他 baselines。
14. 运行 smoke experiments。
15. 运行可承受范围内的多 seed/sweep。
16. 汇总 CSV/JSON、图表和报告材料。
17. 最后重新运行全部 tests/regressions。

遇到编译或 API 错误时，应根据当前源码修复，不要通过删除功能、绕开 VC enforcement 或把 adaptive 改回 deterministic 来让测试通过。

# 十四、最终交付物

请在 repository 中留下：

1. 所有必要的 source modifications；
2. 新 topology；
3. routing 和 VC allocator 实现；
4. traffic generator/replayer；
5. CDG checker；
6. unit/regression tests；
7. 一键运行脚本，例如：

```text
scripts/run_sumcheck_smoke.sh
scripts/run_sumcheck_sweep.sh
scripts/collect_sumcheck_results.py
```

8. 原始 stats/CSV/JSON；
9. 必要图表；
10. `docs/sumcheck_architecture.md`；
11. `docs/sumcheck_deadlock_proof.md`；
12. `docs/sumcheck_evaluation.md`；
13. `SUMCHECK_STATUS.md`。

`SUMCHECK_STATUS.md` 必须逐项说明：

| Step | Completed | Missing | Evidence |
|---|---|---|---|

最终回复必须包括：

- architecture 最终实现版本；
- 修改/新增文件列表；
- 关键实现决策；
- build command；
- test command 与逐项结果；
- experiment commands；
- 实际测得的数据；
- 哪些结果只是静态分析；
- 哪些内容未完成及准确原因；
- 是否仍存在 correctness/deadlock/fairness 风险；
- 建议我们人工 review 的具体文件和函数。

不要只说“implemented successfully”。必须提供可核查的命令、输出、测试数量和结果文件路径。