# DeepSeek API 接入指南

这份文档说明两件事：

1. **怎么开通 / 购买 DeepSeek API**
2. **怎么把 DeepSeek 配到 Dramaloop 里**

---

## 一、先说结论

如果你要把 Dramaloop 跑成真实模型版本，我建议你先用：

- `deepseek-v4-flash`

原因：
- 便宜很多，适合多阶段 harness + loop 的频繁调用
- 更适合开发、调 prompt、跑 eval dataset
- 后面如果要打磨高质量 showcase case，再切到 `deepseek-v4-pro`

---

## 二、怎么买 / 开通 DeepSeek API

### 1. 进入平台

打开：

- `https://platform.deepseek.com/`

### 2. 注册 / 登录账号

如果你还没有账号，先注册并登录。

### 3. 进入 API Key 页面

打开：

- `https://platform.deepseek.com/api_keys`

在这里创建你的 API Key。

### 4. 充值 / 购买额度

根据官方文档，DeepSeek 采用的是**余额扣费**模式：

- 按 token 计费
- 输入和输出 token 都会收费
- 费用从你充值余额里扣
- 如果有赠送余额，会优先消耗赠送余额

也就是说你需要先登录平台并充值，然后再开始调用 API。

---

## 三、推荐模型

### 默认推荐

- `deepseek-v4-flash`

### 什么时候用 `deepseek-v4-pro`

当你要：
- 做 showcase 样例
- 打磨最终稿质量
- 提高 critique / rewrite 的稳定性
- 跑少量但更重质量的 case

可以切到：

- `deepseek-v4-pro`

---

## 四、现在项目里的正确接法

Dramaloop 现在已经不是“单独做一个 DeepSeek provider”，而是改成了：

- **Anthropic-compatible backend**

也就是说：
- 如果目标服务兼容 Anthropic API
- 你只需要改 `API_KEY`、`BASE_URL`、`MODEL_NAME`
- 不需要重写整套调用协议

### DeepSeek 推荐 `.env`

```bash
DRAMALOOP_PROVIDER=anthropic-compatible
DRAMALOOP_MODEL_NAME=deepseek-v4-flash
DRAMALOOP_API_KEY=你的_key_填这里
DRAMALOOP_BASE_URL=https://api.deepseek.com/anthropic
DRAMALOOP_RUNS_DIR=runs
DRAMALOOP_EVALS_DIR=evals
```

### 如果你想继续保留平台专用变量
也可以额外保留：

```bash
DEEPSEEK_API_KEY=你的_key_填这里
DEEPSEEK_BASE_URL=https://api.deepseek.com/anthropic
```

但当前代码优先推荐你直接使用统一变量：
- `DRAMALOOP_API_KEY`
- `DRAMALOOP_BASE_URL`

---

## 五、为什么这样接最合适

因为 DeepSeek 文档提供了：

- Anthropic 格式 Base URL: `https://api.deepseek.com/anthropic`

所以当前项目最合理的方式是：

- 保留 Anthropic 风格客户端结构
- 把底层变成一个 **可配置的 Anthropic-compatible backend**

这样未来不仅能接 DeepSeek，也更容易接其他兼容 Anthropic 协议的服务。

---

## 六、推荐接入顺序

### 第一步：先拿到 key 并充值

你先完成：
- 注册 / 登录
- 创建 API key
- 充值余额

### 第二步：在本地写 `.env`

建议最小配置如下：

```bash
DRAMALOOP_PROVIDER=anthropic-compatible
DRAMALOOP_MODEL_NAME=deepseek-v4-flash
DRAMALOOP_API_KEY=你的_key_填这里
DRAMALOOP_BASE_URL=https://api.deepseek.com/anthropic
```

### 第三步：先跑一个单 case

```bash
uv run dramaloop run --input examples/inputs/revenge_story.yaml
```

先确认：
- 能不能通
- structured output 稳不稳
- critique / rewrite 是否正常

### 第四步：再跑 dataset eval

```bash
uv run dramaloop eval --dataset evals/datasets/mvp_cases.yaml
```

---

## 七、当前价格信息（便于估预算）

### `deepseek-v4-flash`
- input cache hit: `$0.0028 / 1M tokens`
- input cache miss: `$0.14 / 1M tokens`
- output: `$0.28 / 1M tokens`

### `deepseek-v4-pro`
- input cache hit: `$0.003625 / 1M tokens`
- input cache miss: `$0.435 / 1M tokens`
- output: `$0.87 / 1M tokens`

> 价格可能变化，真正使用前建议你再看一次官方 pricing 页面。

---

## 八、注意事项

### 1. 不要再用旧模型名
官方文档提到旧名字：
- `deepseek-chat`
- `deepseek-reasoner`

已经进入弃用流程。

请直接使用：
- `deepseek-v4-flash`
- `deepseek-v4-pro`

### 2. 先别一上来用 pro 跑全流程
因为 Dramaloop 是多阶段、多轮 loop，调用次数比单轮 prompt 多很多。MVP 阶段先用 flash 更合理。

### 3. 现在不需要再单独设计一套 DeepSeek 协议层
因为项目已经改成 anthropic-compatible backend 模式，所以你只需要配置：
- provider
- model name
- api key
- base url

---

## 九、你现在最该做的事

按优先级：

1. 去 `https://platform.deepseek.com/` 登录
2. 去 `https://platform.deepseek.com/api_keys` 创建 key
3. 充值余额
4. 在本地配置 `.env`
5. 然后告诉我“我已经配好 DeepSeek key 了”

我下一步就直接帮你跑 live case。

---

## 十、我推荐你现在直接使用的配置

```bash
DRAMALOOP_PROVIDER=anthropic-compatible
DRAMALOOP_MODEL_NAME=deepseek-v4-flash
DRAMALOOP_API_KEY=你的_key_填这里
DRAMALOOP_BASE_URL=https://api.deepseek.com/anthropic
```

这是当前对这个项目**最稳、最省钱、最适合 MVP** 的方案。
