# Task 4 报告：搭建 React + Vite + TypeScript 单页骨架，并完成前端 lint 收口

## 目标

基于已确认的中文 spec / plan，为 Dramaloop Web Demo 完成 Task 4，要求：

- 使用 React + Vite + TypeScript
- 落地单页布局：左侧输入、右侧运行区与结果区
- 保持“B 的信息架构 + A 的配色与气质”
- 先写失败测试，再实现最小骨架
- 不提前接 API / SSE 真实数据逻辑（留给 Task 5）
- 在任务收口阶段补齐最小前端 lint 基线

## RED -> GREEN 过程

### RED
先新增前端测试：
- `frontend/src/__tests__/App.test.tsx`

测试约束页面必须渲染：
- 标题 `Dramaloop Web Demo`
- `Idea` 输入框
- `Stage Timeline`
- `Event Stream`
- `Final Story`

随后运行：

```bash
npm --prefix frontend test -- --run
```

结果：
- 失败，`frontend/package.json` 不存在
- 说明测试确实钉住了“前端骨架尚未存在”的缺口

### GREEN
补齐最小前端工程与页面骨架：

- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/tsconfig.json`
- `frontend/tsconfig.app.json`
- `frontend/tsconfig.node.json`
- `frontend/vite.config.ts`
- `frontend/index.html`
- `frontend/src/test/setup.ts`
- `frontend/src/main.tsx`
- `frontend/src/types.ts`
- `frontend/src/App.tsx`
- `frontend/src/app.css`
- `frontend/src/components/RunForm.tsx`
- `frontend/src/components/RunTimeline.tsx`
- `frontend/src/components/EventFeed.tsx`
- `frontend/src/components/ResultPanel.tsx`

实现内容包括：
- Vite + React + TypeScript 前端工程初始化
- Vitest + Testing Library 测试环境
- 单页总体布局
- 左侧创作输入面板
- 右上阶段时间线占位视图
- 右上事件流占位视图
- 右下最终故事与 summary / artifacts 占位视图
- 暖米色纸感背景、深棕文字、清晰描边卡片风格

### GREEN 后修正
在第一次运行前端测试后，发现：
- `ReferenceError: test is not defined`

处理：
- 在 `frontend/vite.config.ts` 中为 Vitest 开启 `globals: true`

随后再次测试通过。

构建时又发现：
- `vite.config.ts` 上 `test` 字段类型不匹配

处理：
- 将 `defineConfig` 的导入从 `vite` 改为 `vitest/config`

随后构建通过。

## Task 4 收口：前端 lint 基线

Task 4 初次完成后，仍残留一个 Important：
- 前端缺少 lint 基线

本次收口目标只做最小护栏，不扩展到 Task 5：
- 支持 `ts` / `tsx`
- 接入 `react-hooks`
- 接入基础 `jsx-a11y`
- 忽略 `dist/**`、`node_modules/**`、`**/*.d.ts`、`**/*.tsbuildinfo`
- 保持当前前端单页骨架，不顺手接 API / SSE

### 本次 lint 收口实际改动

#### 1. `frontend/package.json`
- 增加并保留 `lint` script：`eslint .`
- 显式补齐 `@eslint/js`
- 保留 `@typescript-eslint/parser`
- 保留 `eslint-plugin-react-hooks`
- 保留 `eslint-plugin-jsx-a11y`
- 移除当前未实际使用的 `@typescript-eslint/eslint-plugin`

#### 2. `frontend/eslint.config.js`
新增最小 Flat Config：
- 以 `@eslint/js` 的 recommended 规则为基础
- 对 `ts` / `tsx` / `js` / `jsx` 文件启用 `@typescript-eslint/parser`
- 启用 `react-hooks` recommended 规则
- 启用基础 `jsx-a11y` 规则
- 对测试目录补齐 `test` / `expect` / `vi` 等 globals
- 忽略：
  - `dist/**`
  - `node_modules/**`
  - `**/*.d.ts`
  - `**/*.tsbuildinfo`

#### 3. `frontend/src/components/RunForm.tsx`
在 lint 验证阶段发现 `jsx-a11y/control-has-associated-label` warning，原因是三个 `input` 缺少可识别 label 关联。

处理：
- 为 `Style tags`
- `Audience`
- `Constraints`

三个输入框补充显式 `aria-label`，将 lint 从“有 warning”收敛到“0 warning, 0 error”。

## 实际改动

### 1. 前端工程配置
- 建立 Vite/React/TypeScript 工程结构
- 配置 Vitest + jsdom + jest-dom
- 生成 `package-lock.json` 以固定依赖安装结果

### 2. 页面结构
- `App.tsx`：搭建左侧输入 / 右侧运行与结果的总体布局
- `RunForm.tsx`：提供 `Idea`、`Style tags`、`Audience`、`Constraints` 输入区与 `Launch Run` 按钮
- `RunForm` 现已通过显式 `onSubmit` + `preventDefault()` 保证保持 SPA 交互，不会触发原生整页提交刷新
- `RunTimeline.tsx`：渲染 stage 列表占位
- `EventFeed.tsx`：渲染 event stream 占位
- `ResultPanel.tsx`：渲染 final story + summary / artifacts 占位

### 3. 视觉实现
- 使用暖米色背景、深棕文字、浅卡片阴影
- 通过 `app.css` 落地“控制台结构 + 编辑部气质”的初版页面基调
- 结果区采用主内容 + 侧栏双列结构，符合 spec 的右下区域拆分要求

### 4. 忽略本地构建产物
- 更新 `.gitignore`
- 新增忽略：
  - `frontend/node_modules/`
  - `frontend/dist/`
  - `frontend/*.tsbuildinfo`
  - `frontend/vite.config.js`
  - `frontend/vite.config.d.ts`
- 为支持本次隔离工作区，新增 `.worktrees/`

## 测试命令与结果

### 1. RED 验证
```bash
npm --prefix frontend test -- --run
```
结果：FAIL，报 `ENOENT`，因为 `frontend/package.json` 尚不存在。

### 2. Task 4 前端测试
```bash
npm --prefix frontend test -- --run
```
结果：PASS，2 个测试通过。

覆盖点包括：
- 单页骨架关键区域存在
- `Launch Run` CTA 存在
- `Summary / Artifacts` 结果侧栏存在
- timeline 中的代表性 stage 文本存在
- 表单提交不会触发原生页面导航

### 3. Task 4 构建验证
```bash
npm --prefix frontend run build
```
结果：PASS，成功产出 `frontend/dist`。

### 4. Task 4 收口验证
```bash
npm --prefix frontend install
npm --prefix frontend run lint
npm --prefix frontend test -- --run
npm --prefix frontend run build
```
结果：全部 PASS。

补充说明：
- 第一次 `npm --prefix frontend run lint` 曾出现 3 个 `jsx-a11y` warning
- 修复 `RunForm.tsx` 中三个输入框的 label 可访问性后，lint 收敛为 0 error / 0 warning
- `npm install` 仍输出依赖审计告警与 `allow-scripts` 提示，但不阻塞本任务验证

## 与计划差异

整体与计划一致，差异点较小：

1. 额外加入了：
   - `frontend/src/test/setup.ts`
   - `frontend/tsconfig.app.json`
   - `frontend/tsconfig.node.json`
   - `frontend/package-lock.json`
   - `frontend/eslint.config.js`

这些属于 Vite + Vitest + ESLint 最小落地所需文件，不改变任务边界。

2. 为保证仓库工作树整洁，补充更新了 `.gitignore`。
   - 这是 Task 4 实施过程中发现的必要收口项。
   - 不属于功能扩展。

## 风险 / 后续

1. 当前组件仍是占位式静态渲染。
   - 这是符合 Task 4 范围的。
   - 真实 API / SSE 接线留给 Task 5。

2. 当前 `RunTimeline` / `EventFeed` / `ResultPanel` 还没有数据驱动 props。
   - Task 5 接 API 时会继续演进。

3. `npm install` 输出了依赖审计告警与 `allow-scripts` 提示。
   - 当前未阻塞 lint、测试与构建。
   - 不在本任务范围内展开处理。

## 结论

Task 4 已收口完成：

- React + Vite + TypeScript 单页骨架已落地
- 单页布局与基础视觉方向已实现
- 前端失败测试已先写并验证
- 最小前端 lint 基线已补齐
- 前端 lint / test / build 全部通过
- Task 4 已达到可 review / 可归档状态
- 为 Task 5 的 API / SSE 接线提供了稳定骨架与基本工程护栏
