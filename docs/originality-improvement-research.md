# Dramaloop 写作原创能力提升方案

> 调研日期：2026-08-03  
> 目标：评估现有小说 SFT 模型与 2 万条真实小说叙述的价值，并设计可验证的接入方案

## 1. 结论

SFT 模型值得接入，但不能直接推导出“原创性会更好”。

它最可能改善：

- 中文小说语感、场景展开和段落节奏。
- 题材术语与类型文学惯例。
- 从 outline 到正文的叙事完成度。

它不一定改善，甚至可能恶化：

- 核心冲突和人物关系的非模板性。
- 同一 prompt 下的方案多样性。
- 与训练小说的情节、措辞和结构距离。

原因是普通 SFT 的目标仍是提高训练答案的似然。若 2 万条数据集中存在大量相似网文
骨架，模型会更熟练地复现这些高频模式，而不是主动避开它们。领域适配研究支持
“领域数据能改善领域任务”，但不等价于“领域数据能增加创造性”
([Gururangan et al., ACL 2020](https://aclanthology.org/2020.acl-main.740/))。

对 Dramaloop，优先级应是：

1. 把 SFT 模型接成 premise/outline 候选生成器。
2. 一次生成多个结构差异明显的候选。
3. 用小说库做相似性检索，淘汰近邻和高频模板。
4. 用独立 writing reward model 或人工偏好选择候选。
5. 有稳定偏好数据后再做 DPO。

不建议第一步就用 SFT 模型替换所有 stage，也不建议立即把 2 万条正文再训练一轮。

## 2. 业界与研究界的主流技术栈

### 2.1 领域继续预训练或 SFT

领域继续预训练适合让模型学习小说语言分布；SFT 适合学习“输入要求 -> 指定形态输出”。
两者都更接近能力和行为适配，不直接优化偏好。

适用于：

- 原模型叙事语言生硬。
- 不理解小说结构或题材术语。
- 需要稳定输出 premise、outline、character card 等格式。

不适用于单独解决：

- 模板化。
- 训练数据复述。
- 同一输入多次生成高度相似。

### 2.2 Rejection sampling / Best-of-N

主流后训练系统不会只训练一次然后取单个输出。Meta 的 Llama 3 技术报告采用
SFT、rejection sampling 与 DPO 的组合，而不是只依赖 SFT
([Llama 3 Technical Report](https://arxiv.org/abs/2407.21783))。

对小说生成，Best-of-N 不应先生成 N 篇完整小说，而应生成 N 个便宜的结构计划：

- 核心冲突机制。
- 人物关系图。
- 三个不可逆选择。
- 关键场域与物件。
- 反转对前文细节的重新解释。
- payoff 的因果来源。

筛出最好的 1-2 个计划后再写正文，成本和可控性都优于 N 篇成稿。

### 2.3 Preference optimization

DPO 用偏好对直接训练策略模型，不需要单独运行 PPO。原论文将它描述为稳定且较轻量的
RLHF 替代，并在摘要、对话和情感控制任务上验证
([Rafailov et al., NeurIPS 2023](https://arxiv.org/abs/2305.18290))。

对原创性，训练样本应是：

```text
prompt
chosen: 具体、不可互换、由人物选择推动的方案
rejected: 语言流畅但只换名字的常见套路
```

chosen/rejected 必须尽量控制篇幅、文笔和完整度，避免模型只学会“更长就是更好”或
“行业术语更多就是原创”。

DPO 比继续堆正例 SFT 更接近真正目标，因为它明确告诉模型两个都能写通的方案中，
哪一个更值得偏好。

### 2.4 Writing reward model / verifier

创作没有唯一标准答案，单个零样本 LLM judge 并不稳定。LitBench 使用 43,827 个
人类偏好对训练创作 reward model；其报告中，最佳零样本 judge 与人类偏好一致率为
73%，训练后的 Bradley-Terry 和 generative reward model 达到 78%
([LitBench](https://arxiv.org/abs/2507.00769))。

这说明 Dramaloop 当前的 DeepSeek judge 适合做开发期信号，不应成为最终真值。
中期应训练一个独立 verifier：

- 输入同 prompt 下的两个故事计划或故事。
- 输出整体偏好和各维度偏好。
- 生成模型、verifier 和最终抽检模型相互隔离。
- 每次评估交换 A/B 位置。

### 2.5 分层规划、生成和重排

故事生成领域长期有效的方向是先规划再写作。Plan-and-Write 的人评和自动评测发现，
显式 storyline planning 比直接生成更具多样性、连贯性和主题相关性
([Yao et al., AAAI 2019](https://ojs.aaai.org/index.php/AAAI/article/view/4726))。

Re3 将长故事生成拆成：

1. 结构化总计划。
2. 按计划和当前故事状态递归生成。
3. 重排多个 continuation。
4. 对最佳 continuation 做一致性修订。

其人评中，整体情节连贯性提升 14 个百分点，premise relevance 提升 20 个百分点
([Yang et al., EMNLP 2022](https://arxiv.org/abs/2210.06774))。

Dramaloop 已有 plan、memory、critique 和 rewrite，但缺少“同一规划节点的多候选生成
与重排”。这是当前最值得补的环节。

### 2.6 多样性解码

contrastive search 和 diverse decoding 可以降低 token、短语层面的重复，并在保持
连贯性的同时增加候选差异
([Su et al., 2022](https://ar5iv.labs.arxiv.org/html/2202.06417))。

它们适合改善：

- 句式重复。
- 候选只有少量措辞差异。
- 高频表达占据所有采样结果。

但它们不能单独修复宏观情节模板。调高 temperature 也不能等同于原创，通常只是增加
随机性。宏观原创仍应在 premise/outline 层完成。

### 2.7 Critique-rewrite

Self-Refine 展示了无需额外训练的 generate-feedback-refine 循环，并在论文的七类任务
上报告平均约 20 个百分点提升
([Madaan et al., NeurIPS 2023](https://openreview.net/forum?id=S37hOerQLB))。

但 Dramaloop 的真实实验已经显示：正文 loop 的 overall `+0.44`，originality
scalar `+0`。这说明 loop 更擅长修补完整度，而不是替换已经确定的故事骨架。

原创性失败时应返回 outline 重规划，而不是继续润色正文。

## 3. 2 万条小说数据应该怎样处理

### 3.1 先核对“有效规模”

记录数不是最重要的量，至少要统计：

- 总 token 数和长度分布。
- 独立小说、作者、系列和来源数量。
- 每个题材与情节模板的占比。
- 同一本书被切成多少条。
- 精确重复、近重复和改写重复比例。
- 数据授权、可训练范围和产物使用限制。

如果 2 万条来自少数小说的切片，它的有效多样性远小于 2 万。训练/验证/测试必须按
小说、系列或作者分组，不能随机切 paragraph，否则相邻片段会泄漏到验证集。

### 3.2 去重不是可选项

Google Research 的研究发现，训练集去重可让模型输出记忆文本的频率降低 10 倍，
同时减少训练测试污染
([Lee et al., ACL 2022](https://aclanthology.org/2022.acl-long.577/))。

至少做三层检测：

1. 文本层：exact hash、MinHash / n-gram Jaccard。
2. 语义层：embedding 近邻。
3. 故事结构层：实体匿名化后的事件序列、关系图和反转类型。

只过滤逐字重复不够。研究已经指出，阻止 verbatim memorization 仍可能遗漏经过轻微
改写的训练内容泄漏
([Ippolito et al., INLG 2023](https://aclanthology.org/2023.inlg-main.3/))。

### 3.3 不要只保留正文

将每条小说叙述转换为可训练的结构：

```json
{
  "premise": "...",
  "conflict_mechanism": "...",
  "relationship_graph": ["..."],
  "setting_mechanics": ["..."],
  "irreversible_choices": ["..."],
  "causal_beats": ["..."],
  "reversal": "...",
  "payoff": "...",
  "motifs": ["..."],
  "template_tags": ["..."],
  "source_group": "book-or-series-id"
}
```

优先训练下列任务，而不是只训练 raw continuation：

- 给定约束，生成 5 个机制不同的 premise。
- 识别故事中的可替换模板骨架。
- 将模板 outline 重建为人物选择驱动的 outline。
- 从结构化 outline 写正文。
- 比较两个方案，解释哪一个更不可替换。
- 从 critique 回退并重建 outline。

### 3.4 建立长尾采样

对 conflict mechanism、relationship graph、reversal 和 setting mechanism 做聚类，
限制高频 cluster 的采样权重，并提高长尾结构的权重。目标不是让题材数量看起来多，
而是让核心因果结构分布更均衡。

## 4. 推荐接入 Dramaloop 的架构

### 4.1 Role routing

现有 `LLMClient` 调用已经带 `role`，可增加 `RoleRoutingLLMClient`：

| Stage | 第一版模型 |
|---|---|
| premise / season planning | SFT 模型 |
| outline / episode plan candidates | SFT 模型 |
| candidate critique / selection | 独立 DeepSeek 或 reward model |
| draft | SFT 与通用模型做 A/B |
| factual/continuity critique | 通用模型 |
| originality judge | 与生成模型隔离的模型 |

第一轮不要让 SFT 模型同时生成、批评和选择自己的输出。

### 4.2 Divergent planning stage

在 `premise_refinement` 之前或 `story_outline_generation` 内增加：

```text
request
  -> generate 8 candidate plans
  -> corpus similarity search
  -> quality/originality/constraint scoring
  -> diversity-aware selection
  -> selected premise + outline
  -> draft
```

每个候选必须声明：

- 与其他候选不同的 conflict mechanism。
- 哪个角色选择造成不可逆后果。
- 哪个关键物件无法被通用录音、监控或身份替换。
- 与最近训练语料近邻的差异。

### 4.3 Novelty retrieval

将 2 万条数据建立两个索引：

- 文本近邻索引：发现措辞与局部场景复用。
- 结构 fingerprint 索引：发现角色改名后的同构故事。

检索结果应作为 negative context：

```text
以下是最相似的三个已有结构。不得复述；说明新候选在因果机制上的实质差异。
```

不要把整段原小说作为正向 RAG 塞给写作模型，否则更容易诱发近似复述。

### 4.4 Quality-diversity selector

先设质量底线，再在合格候选中选最远的方案：

```text
hard gates:
  constraint_fidelity >= threshold
  causal_coherence >= threshold
  corpus_overlap <= threshold

soft objectives:
  writing_quality
  originality
  distance_from_other_candidates
  payoff_strength
```

这是 Pareto 问题，不应把所有指标简单平均。一个语义混乱但 n-gram 新颖的文本不是好
创作。2026 年针对文本创造力的研究也发现，处于 n-gram novelty 最高四分位的表达中，
约 91% 没有被专家作者判为 creative
([Saakyan et al., 2026](https://arxiv.org/html/2509.22641v2))。

### 4.5 Outline-level loop

增加两种 loop：

- `prose_revision`：修文笔、节奏、证据链。
- `structural_regeneration`：重建 premise/outline。

若 originality 低于底线，应触发后者。当前 `targeted_rewrite` 发生在正文阶段，已不足以
改变宏观模板。

## 5. 训练路线

### 阶段 0：不训练，先接入评测

对同一批 30-50 个 held-out prompt，每个重复 3 次：

| Variant | 说明 |
|---|---|
| A | 当前 DeepSeek pipeline |
| B | SFT 模型替换所有生成 stage |
| C | SFT 只负责 premise/outline |
| D | C + 8 个规划候选 + novelty selector |

先回答 SFT 模型到底改善了什么，再决定训练。

### 阶段 1：数据重构后的 SFT

用清洗后的结构化任务做轻量 LoRA/SFT：

- 保留一部分通用 instruction 数据，降低灾难性遗忘。
- 按 source group 去重与切分。
- 对高频模板降采样。
- 混入“多候选必须机制不同”和“模板重建”任务。

对照 raw-novel SFT，验证结构化任务是否更有效。

### 阶段 2：Rejection sampling

让阶段 1 模型为每个 prompt 生成 8 个 plan，用独立 verifier 与人工抽检选 winner。
winner 既可回灌为高质量 SFT 数据，也可和 loser 组成 preference pair。

这是风险最低、最接近主流工业后训练流程的一步。

### 阶段 3：DPO

收集 3k-10k 个高质量偏好对后再做 DPO。偏好标签至少分开记录：

- originality。
- causal coherence。
- prose quality。
- constraint fidelity。
- training-corpus overlap。

不要用当前单一 `originality` 分数自动制造全部 chosen/rejected。先用多 judge 产生候选，
再对不一致样本做人工标注。

### 阶段 4：Reward model 或在线 RL

只有在 reward model 与专业作者偏好有稳定一致率后，再考虑 GRPO/PPO 等在线优化。
创作 reward 容易被术语密度、长度、奇怪比喻等表面特征劫持。

近期创作 RL 研究开始使用“主观写作质量 + 客观约束”的混合 reward，而不是单一总分
([RLMR, 2025](https://arxiv.org/html/2508.18642v2))。这可以作为后续方向，不应作为
当前第一步。

## 6. 评测设计

### 6.1 三个独立目标

原创能力至少拆成：

1. Novelty：与训练库、历史输出和常见模板的距离。
2. Appropriateness：是否合理、可读、符合用户约束。
3. Diversity：同一 prompt 多次生成是否覆盖不同机制。

不能只看 Distinct-N、自 BLEU 或单个 LLM originality 分。

### 6.2 指标

自动指标：

- entity-masked n-gram overlap。
- 最长公共子串与 MinHash 相似度。
- embedding nearest-neighbor similarity。
- 匿名化 plot fingerprint similarity。
- 同 prompt 候选之间的 cluster entropy。
- constraint、continuity 和 causal coherence。
- provider token、latency、失败率。

偏好指标：

- 专业作者盲评 pairwise win rate。
- A/B 位置交换一致率。
- 生成模型之外的两个 judge。
- reward model 与人工偏好的一致率。

### 6.3 数据隔离

- 按作者/小说/系列分组切分。
- evaluation prompt 不从训练小说摘要直接改写。
- 检测输出与所有训练 split 的近邻，不只检测 test contamination。
- 保存最近邻证据，不能只输出一个无解释的 originality 分。

### 6.4 第一阶段通过门槛

建议在实验前固定：

- 人工 originality pairwise win rate 至少提高 10 个百分点。
- coherence 和 constraint fidelity 下降不超过 2 个百分点。
- 训练库最近邻相似度不能上升。
- 同 prompt 的结构 cluster 数显著增加。
- 总 token 成本不超过 baseline 的 2 倍。

具体门槛可以调整，但必须在看结果前确定。

## 7. 最实际的下一步

先做下面这个最小实验，不继续训练：

1. 为 SFT 模型提供一个兼容 Dramaloop `LLMClient` 的 endpoint adapter。
2. 增加按 role 路由的 client。
3. 让 SFT 模型只生成 8 个 premise/outline candidates。
4. 用 2 万条小说构建 MinHash + embedding 近邻索引。
5. 以质量底线、结构距离、corpus overlap 选择一个计划。
6. 用现有 writer 生成正文。
7. 对 30-50 个 prompt 跑 A/B/C/D 四组真实评测。

如果 D 明显胜过 A/C，再将筛选出来的 winner/loser 转成 DPO 数据。若 SFT 直接替换
只提高文笔而不提高结构原创性，就把它固定为 prose writer，不让它决定 premise。

这条路线能最快回答“2 万条数据和 SFT 模型是否有用”，同时避免在尚未建立可靠
原创性 reward 前继续训练并放大模板偏差。
