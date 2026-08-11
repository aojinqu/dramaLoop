# Dramaloop 工程方法实测记录

> 实验日期：2026-08-03  
> 生成与评审模型：`deepseek-v4-flash`  
> 结论范围：单次真实 API 工程实验，不是统计显著的质量基准

## 1. 为什么做这组实验

Mock 测试可以证明 Schema、编排、trace 和报告能运行，不能证明故事更好。最初的真实输出
暴露了另一个问题：旧评测会把完成度很高、但只是替换人物和行业名的模板故事判成高分。

本轮实验因此回答四个可证伪的问题：

1. 反模板 Prompt 是否真的让输出更有辨识度。
2. critique-rewrite loop 对总分和目标弱项分别增加多少。
3. memory compression 与 context recall 是否真的工作，以及成本是多少。
4. full harness 相对 baseline 是否带来可观察的质量收益。

机器可读证据保存在
[`evals/reports/engineering-methods-20260803/`](../evals/reports/engineering-methods-20260803/)。

## 2. 本轮改动

### 2.1 把原创性变成一等指标

`originality` 被加入：

- 单篇与分集 critique Schema。
- DeepSeek judge 九维评分。
- position-swapped pairwise。
- expected contract `originality_not_template`。
- ablation summary 与 run summary。

评价不再只问“有没有行业名词”，而是检查冲突机制、人物关系、场景和关键物件是否
不可替换。退婚改嫁、豪门打脸、直播翻盘、重生复仇、大佬救场和证据大屏等骨架，
只换人名或职业仍然严格扣分。

### 2.2 改造生成 Prompt

premise、characters、outline、draft、season、episode plan 和 episode draft 都增加了
反模板约束：

- 冲突绑定具体职业、地域、制度、物件或习俗。
- 至少两个 beat 来自角色选择的不可逆后果。
- 反转必须重新解释已出现的细节。
- 禁止默认用万能录音、神秘身份、大佬救场或公开证据完成翻盘。
- 分集不得反复使用“受压制 -> 找证据 -> 公开打脸”。

rewrite 的 `originality_revision` 不是换措辞，而是用已有场域和人物选择重建因果。

### 2.3 记录真实 provider 成本

每次模型调用写入 `usage_trace.jsonl`：

- `input_tokens`
- `output_tokens`
- `cache_read_input_tokens`
- `stop_reason`
- `attempt`
- `role`

文本与结构化输出检测 `stop_reason=max_tokens`。截断不会再被误判为 completed，而会
重试或 blocked。超过 12k token 的长请求使用 streaming，绕开 Anthropic SDK 对
可能超过十分钟的非流式请求限制。

## 3. 指标口径

| 指标 | 定义 | 不能证明什么 |
|---|---|---|
| judge score | 九个质量维度的平均分 | 单模型自评不等于人工偏好 |
| originality | 设定与因果是否不可替换，1-10 | 单个分数不能覆盖所有创新形式 |
| pairwise | A/B 交换位置后比较；结论冲突则 tie | tie 不代表文本完全相同 |
| memory recall | 被 context 实际召回的 memory id / 可召回 memory id | 被召回不等于被模型正确使用 |
| compression ratio | memory 内容字符数 / 非 trace artifact 字节数 | 不是严格的同源压缩率 |
| unsupported memory | semantic fact 是否有存在于 run 内的 evidence path | 文件存在不代表语义蕴含成立 |
| provider tokens | provider 报告的 input + output | 不等于账单价格 |
| latency | pipeline wall-clock 秒数 | 单次网络延迟方差很大 |

当前 compression ratio 的分母包含该 run 的非 trace artifact，分子包含 raw artifact
索引、episode memory 和 semantic facts。它适合观察同一实现的趋势，不应与其他系统
的压缩率直接比较。

## 4. 实验 A：Prompt 改造前后

### 设计

- 旧 Prompt 输出：完成版单篇故事。
- 新 Prompt 输出：改造后 pipeline 的 `draft_v1`，尚未经过 loop。
- 使用新九维 judge 独立评分。
- 通过 position-swapped pairwise 复核。

两次生成不是固定随机种子的同源采样，因此这里只作为方向性证据。

### 结果

旧输出在旧口径下是 9.0 分；加入 originality 后重新评分：

| 版本 | judge 平均分 | originality |
|---|---:|---:|
| 旧 Prompt | 7.56 | 4 |
| 新 Prompt，loop 前 | 7.78 | 6 |
| 变化 | +0.22 | +2 |

position-swapped pairwise 两次都选择新 Prompt 输出，聚合结果也是新版本胜出；
`originality`、`continuity`、`context_fidelity` 和 `rewrite_effectiveness` 由新版本获胜。
两次评语都指出，新输出中的苏绣行会、双面三异绣、绣谱和师徒关系具有更强的
不可替换性；旧输出仍是退婚改嫁、豪门打脸和直播翻盘模板。

证据：

- [`prompt-pairwise.json`](../evals/reports/engineering-methods-20260803/prompt-pairwise.json)
- [`loop-independent-evaluation.json`](../evals/reports/engineering-methods-20260803/loop-independent-evaluation.json)

### 判断

这次 Prompt 改造有正向信号，尤其是 pairwise 的位置交换结果一致。但新输出仍保留
“退婚 + 协议结婚 + 隐藏证据 + 当众翻盘”的底层骨架，originality 只从 4 到 6，
尚未达到“摆脱模板”的目标。

## 5. 实验 B：critique-rewrite loop

### 设计

固定同一个 `draft_v1` 和 `critique_v1`，只执行一次
`originality_revision`，比较改写前后。这样 loop 的增益不会混入 premise、character
或 outline 的重新采样。

### 结果

| 评价方式 | loop 前 | loop 后 | 增益 |
|---|---:|---:|---:|
| pipeline critique overall | 6.88 | 7.75 | +0.87 |
| pipeline critique originality | 5 | 5 | 0 |
| independent judge average | 7.78 | 8.22 | +0.44 |
| independent judge originality | 6 | 6 | 0 |

pairwise 整体选择改写后版本。评审认为绣针、棠木绣绷和外婆证词的证据链更闭合，
但 scalar originality 没有提升，因为底层仍依赖退婚改嫁、隐藏遗物和公开打脸。

成功恢复的 loop 额外调用 2 次：

| stage | input | output | cache read |
|---|---:|---:|---:|
| targeted rewrite | 65 | 13,688 | 2,048 |
| post-rewrite critique | 2,279 | 2,419 | 512 |
| 合计 | 2,344 | 16,107 | 2,560 |

provider input + output 合计 18,451 tokens。这里 output 包含 DeepSeek 的推理消耗，
所以远大于最终正文的 2,471 字。

证据：

- [`loop-critique-before.json`](../evals/reports/engineering-methods-20260803/loop-critique-before.json)
- [`loop-critique-after.json`](../evals/reports/engineering-methods-20260803/loop-critique-after.json)
- [`loop-independent-evaluation.json`](../evals/reports/engineering-methods-20260803/loop-independent-evaluation.json)
- [`loop-provider-usage.json`](../evals/reports/engineering-methods-20260803/loop-provider-usage.json)

### 判断

loop 对完成度有可观察增益：内部评价 +0.87，独立 judge +0.44。但对被指定修复的
originality 没有 scalar 增益，因此不能把“总分提高”表述成“目标问题已解决”。

后续 loop 指标必须同时报告：

- 总分变化。
- target dimension 变化。
- pairwise 结果。
- 新增 token 与调用次数。

如果 target dimension 不升，应停止继续烧 token，转为重建 outline 或报告 blocked。

## 6. 实验 C：memory 与 full harness ablation

### 设计

固定一个两集职业悬疑 case：

> 汛期前夜，老泵站值班员失联。新调度员必须通过叶轮异响、闸门刻度和上游水位，
> 判断设备故障、值班事故或排水规则问题，并解释值班员的主动选择。

依次运行：

1. `baseline`
2. `memory_context_budgeted`
3. `full_harness`

三种模式使用相同模型、请求、judge 和 expected contracts。每种模式只有一次真实运行。

### 结果

| mode | judge | orig. | cont. | memory recall | compression | contracts | provider tokens | latency |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| baseline | 8.44 | 9 | 9 | 0.0 | 0.2747 | 100% | 16,503 | 113.14s |
| memory + context | 8.11 | 7 | 9 | 0.8 | 0.2868 | 100% | 17,125 | 79.64s |
| full harness | 8.44 | 6 | 9 | 0.8 | 0.2723 | 75% | 25,961 | 158.97s |

相对 baseline：

- memory + context：judge `-0.33`，provider tokens `+3.8%`，latency `-29.6%`。
- full harness：judge `+0.00`，provider tokens `+57.3%`，latency `+40.5%`。
- 两个启用 memory context 的模式都达到 0.8 recall。
- compression ratio 约 0.27-0.29，即当前口径下 memory 约为 artifact 体量的
  27%-29%。
- continuity 三者都是 9，没有观察到 continuity 净增益。
- full harness 的 originality 只有 6，导致 `originality_not_template` contract
  失败，合同通过率为 75%。

pairwise 的两个总体比较都是 tie：

- baseline vs memory + context：总体 tie，memory + context 只在 continuity 获胜。
- memory + context vs full harness：总体 tie，full harness 在 hook、conflict、
  pacing 和 short-drama feel 获胜。

证据：

- [`live-ablation-report.json`](../evals/reports/engineering-methods-20260803/live-ablation-report.json)
- [`live-ablation-report.md`](../evals/reports/engineering-methods-20260803/live-ablation-report.md)
- 数据集：[`engineering_methods_live_ablation.yaml`](../evals/datasets/engineering_methods_live_ablation.yaml)

### 判断

本样本证明了 memory 的工程链路：

- artifact 被压缩进 run memory。
- semantic facts 带有可解析的 `evidence_refs`。
- context planner 实际召回了 80% 的 memory id。
- required context recall 为 100%，没有 required item 被预算器丢弃。

但它没有证明 memory 或 full harness 提高最终质量。baseline 已经有 9 分 continuity，
造成天花板效应；full harness 花费更多 token 后总分与 baseline 相同，原创性反而更低。

本轮 trajectory regulation 的 intervention 和 regulation action 都是 0，因此这次结果
也不能用于评价恢复策略的收益。它测到的是 context、memory 和 procedural skill 的
组合效果，不是主动纠偏效果。

## 7. 真实测试暴露的工程问题

### 7.1 Prompt 与 Schema 漂移

真实模型返回 `role="ally"`，而 Character Schema 只接受
`protagonist/antagonist/supporting`。Prompt 曾明确允许 ally，说明两者自相矛盾。
修复为 Prompt 收紧，并在 provider 边界兼容 `ally -> supporting`。

critique 还返回过 `rewrite_target="pacing"`，而执行器需要动作型 target。现在 provider
将维度映射为 `mid_conflict_escalation` 等动作，并为 `originality` 映射
`originality_revision`。

### 7.2 截断被误判为成功

一次 run 的 `final_story.md` 停在半句“眼底”，manifest 却是 completed。根因是文本
通道只检查非空，不检查 `stop_reason=max_tokens`。现在截断会重试；再次截断则失败，
不会产出伪完成。

### 7.3 原创性 Prompt 显著增加推理成本

新 Prompt 的 outline 和 draft 都出现过首轮 `max_tokens`，第二轮才成功。随后
targeted rewrite 在 6k 和 12k 预算下连续截断：

| attempt | input | output | cache read | stop |
|---|---:|---:|---:|---|
| 1 | 3,609 | 6,001 | 0 | max_tokens |
| 2 | 46 | 11,998 | 3,584 | max_tokens |

失败 rewrite 消耗 input + output 21,654 tokens，仍没有产物。提高预算到 16k 后，
Anthropic SDK 又要求改用 streaming；实现 streaming 后才完成恢复。

这说明“更严格 Prompt”不是免费改进。它可能增加推理长度、重试率、延迟和账单，
必须与质量收益一起评估。

### 7.4 平均分掩盖关键弱项

旧 loop 在 overall 达标时会停止，即使 originality 只有 4。现在停止条件要求：

- overall 达到目标。
- 所有维度达到 minimum dimension threshold。

critique 的 overall 由代码按维度重算，不再直接信任模型自报。

## 8. 本轮结论

### 已得到证据支持

- 新 Prompt 相对旧 Prompt 有原创性正向信号：judge `+2`，pairwise 一致胜出。
- loop 改善了整体完成度：内部 `+0.87`，独立 judge `+0.44`。
- memory compression、evidence path、context recall 和 provider usage trace 均真实工作。
- 截断、Schema 漂移和长请求 transport 限制可以通过 artifact 与 trace 定位。

### 未得到证据支持

- loop 没有提高目标 originality scalar。
- memory 没有在本样本提高 continuity，因为 baseline 已经是 9。
- full harness 没有提高总体 judge score，却增加 57.3% provider token。
- 单样本、同模型生成与评审不能证明普遍质量提升。

### 新发现的风险

- procedural skill 和更多上下文可能把模型推向更标准化的“正确答案”，损害原创性。
- `evidence_ref` 当前只验证路径存在，不验证 fact 是否被文件内容语义支持。
- judge scalar 与 pairwise 会出现差异：本次 loop originality scalar 不变，但
  pairwise 仍偏好改写后版本。
- latency 单次方差很大，不能仅凭一次 run 得出性能结论。

## 9. 下一轮实验门槛

只有满足以下设计，才把结果升级为项目质量基线：

1. 每个模式至少 20 个非模板 case，每个 case 重复 3 次。
2. Prompt A/B 使用相同输入、相同采样参数，并记录所有失败样本。
3. 生成模型与 judge 模型分离，再加入盲化人工抽检。
4. 单独消融 memory、procedural skill、context budget 和 trajectory regulation。
5. 增加 evidence entailment 检查，而不仅是文件存在检查。
6. loop 以 target dimension 的实际增益作为继续条件。
7. 同时报告均值、标准差、失败率、token、latency 和 pairwise tie rate。

在完成上述重复实验前，准确的工程表述是：

> Dramaloop 已建立可追溯、可消融、可失败复盘的 agent harness；Prompt 改造和 loop
> 显示局部质量收益，但 full harness 的普遍质量增益尚未被证明。
