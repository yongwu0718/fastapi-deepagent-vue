# Shared 公共组件与工具

> 本文档描述跨模块共享的基础设施，包括日志系统、Toast 通知、Markdown 渲染（含 Mermaid 图表）、滚动控制和 Logo 组件。

---

## 模块架构

```
shared/
├── useLogger.ts          # 结构化日志系统
├── useToast.ts           # Toast 通知系统（发布-订阅）
├── ToastContainer.vue    # Toast UI 容器
├── Markdown.vue          # Markdown 渲染组件（含 Mermaid 图表）
├── ScrollToBottom.vue    # 滚动到底部按钮
└── AgentLogo.vue         # SVG Logo 组件（原子/轨道风格）
```

> **注意**：`useContentNav.ts` 已迁移至 `chat/core/` 目录，不再属于 shared 模块。

---

## useLogger.ts（结构化日志）

### 核心工厂：createLogger

```typescript
export function createLogger(prefix: string)
// 返回 { trace, debug, info, warn, error, level (getter), setLevel() }
```

所有预置模块 Logger 均由 `createLogger(prefix)` 工厂函数创建。

### 日志等级

| 等级 | 方法 | 生产环境 | DEV 环境 | 说明 |
|------|------|----------|----------|------|
| trace | `logger.trace()` | 默认关闭 | 默认关闭 | 最详细的调试信息 |
| debug | `logger.debug()` | 默认关闭 | ✓ | 调试信息 |
| info | `logger.info()` | 默认关闭 | ✓ | 一般信息 |
| warn | `logger.warn()` | ✓ | ✓ | 警告 |
| error | `logger.error()` | ✓ | ✓ | 错误 |

**默认级别判定逻辑**：
- URL 参数 `?log=trace`（最高优先级，可临时在生产开启）
- DEV 环境默认 `debug` 级别
- 生产环境默认 `warn` 级别

### 运行时控制

```typescript
// URL 参数启用全量日志（所有环境）
?log=trace

// 浏览器控制台动态调整
window.__setLogLevel('trace')   // 临时开启全量日志
window.__getLogLevel()          // 查看当前级别
window.__logLevels              // 列出所有可用级别: ['trace','debug','info','warn','error']
```

### Logger 实例方法

每个 Logger 实例除 5 个日志方法外，还有：

- `logger.level` — getter，获取当前全局日志级别
- `logger.setLevel(level)` — 运行时动态修改全局日志级别

### 预置模块 Logger

```typescript
export const loggerSSE         // createLogger('[SSE]')       — SSE 流通信
export const loggerChat        // createLogger('[Chat]')      — 聊天流程
export const loggerRetry       // createLogger('[Retry]')     — 重试逻辑
export const loggerFork        // createLogger('[Fork]')      — 分支操作
export const loggerCheckpoint  // createLogger('[Checkpoint]') — 检查点管理
export const loggerVue         // createLogger('[Vue]')       — Vue 框架绑定
export const loggerResume      // createLogger('[Resume]')    — 中断恢复
```

### 日志格式

```typescript
loggerSSE.info('connected', { threadId: 'xxx' })
// 输出: [14:32:05.123] [SSE] connected {"threadId":"xxx"}
```

格式为 `[HH:MM:SS.ms] [prefix] message args...`，对象自动 JSON 序列化，Error 对象输出 stack trace。

---

## useToast.ts（Toast 通知）

### 数据模型

```typescript
export interface Toast {
  id: string
  type: 'info' | 'success' | 'error' | 'warning'
  title: string
  description?: string
  duration?: number      // 默认 4000ms
  removing?: boolean     // 退出动画标记（内部使用）
}
```

### 设计模式：发布-订阅

```
toast.success(title, description)
  → addToast() 推入 toasts 数组
  → notify() 通知订阅者
  → ToastContainer 订阅并渲染
  → 超时后 removeToast() 标记 removing=true
  → 300ms 后真正移除（配合退出动画）
```

### Toast 类型

| 方法 | 左边框色 | 默认时长 | 图标 |
|------|----------|----------|------|
| `toast.success(title, desc?)` | 绿色 `#10b981` | 4 秒 | ✓ |
| `toast.error(title, desc?)` | 红色 `#ef4444` | 6 秒 | ✕ |
| `toast.warning(title, desc?)` | 黄色 `#f59e0b` | 5 秒 | ⚠ |
| `toast.info(title, desc?)` | 主题色 `--accent` | 4 秒 | ℹ |

### API

```typescript
import { toast, addToast, dismissToast, subscribeToasts } from '@/shared/useToast'
import type { Toast } from '@/shared/useToast'

// ── 快捷方法 ──
toast.success('保存成功')
toast.error('失败', error.message)
toast.warning('磁盘空间不足')
toast.info('模型已切换')

// ── 底层 API ──
const toastId = addToast({
  type: 'info',
  title: '自定义标题',
  description: '详细描述',
  duration: 8000,  // 可选，默认 4000；设 0 则不自动移除
})
// 返回 toast id，可用于手动移除

dismissToast(toastId)       // 手动关闭 Toast（含退出动画）

// ── 订阅通知变化 ──
const unsub = subscribeToasts((toasts: Toast[]) => {
  // toasts 为当前所有 Toast 的快照数组
})
// 返回取消订阅函数
```

### 退出动画机制

1. `removeToast(id)` 先将目标 Toast 的 `removing` 置为 `true`
2. 触发 `notify()`，容器组件收到带 `removing` 标记的数组
3. Vue `<TransitionGroup>` 播放离开动画（`toast-leave-active`，250ms）
4. 300ms 后从数组中真正删除，触发最终 `notify()`

---

## ToastContainer.vue（Toast UI 容器）

### 定位与挂载

使用 `<Teleport to="body">` 挂载到 body 下，固定在右下角（`position: fixed; bottom: 20px; right: 20px; z-index: 9999`），确保层级不受父组件影响。

### 结构

```vue
<template>
  <Teleport to="body">
    <div class="toast-container" aria-live="polite">
      <TransitionGroup name="toast">
        <div v-for="t in toasts" :key="t.id"
             :class="['toast', `toast--${t.type}`]"
             role="alert">
          <span class="toast-icon">{{ iconFor(t) }}</span>
          <div class="toast-body">
            <div class="toast-title">{{ t.title }}</div>
            <div v-if="t.description" class="toast-desc">{{ t.description }}</div>
          </div>
          <button class="toast-close" @click="dismiss(t.id)">✕</button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
```

### 关键细节

- **`aria-live="polite"`**：屏幕阅读器友好，Toast 变化时自动播报
- **`role="alert"`**：每个 Toast 项标记为语义化通知
- **类型修饰符**：`toast--{type}` 控制左边框颜色：`--success`（绿）、`--error`（红）、`--warning`（黄）、`--info`（主题色）
- **图标圆形背景**：与左边框颜色一致，白色文字
- **动画**：入场 `translateX(40px) scale(0.95)` → 原地，离场反向，均有 opacity 过渡

---

## Markdown.vue（Markdown 渲染 + Mermaid 图表）

### 内容来源（重要）

内容通过 **默认插槽（slot）** 传入，而非 `content` prop。这样可以响应流式更新的文本变化。

```vue
<!-- 使用方式 -->
<Markdown code-block-id-seed="msg-1">
  {{ streamingText }}
</Markdown>
```

### Props

| Prop | 类型 | 说明 |
|------|------|------|
| `codeBlockIdSeed` | `string` | 代码块锚点 ID 前缀（用于大纲导航定位），如 `msg-1` 生成 `id="msg-1-0"`, `id="msg-1-1"`... |

### 渲染流程

```
slot 默认内容（string）
  → marked.parse()           ← 配置: GFM + breaks
  → extractMermaidBlocks()   ← 提取 Mermaid 代码块，替换为占位容器
  → DOMPurify.sanitize()     ← XSS 防护
  → 注入代码块锚点 ID          ← 仅当有 codeBlockIdSeed
  → 异步 Mermaid 渲染          ← mermaid.render()，失败则显示错误信息
  → addCodeCopyButtons()     ← 给 <pre> 包裹 .code-block-wrapper + 复制按钮
  → innerHTML 注入
```

### Mermaid 图表支持

检测 `<code class="language-mermaid">` 代码块，异步调用 `mermaid.render()` 渲染为 SVG。

- **成功**：在占位容器中插入 SVG + "源码"复制按钮
- **失败**：显示 `<pre class="mermaid-error">` 包含错误信息和源码片段（前 300 字符）

Mermaid 配置：

```typescript
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  flowchart: { curve: 'step', rankSpacing: 100, nodeSpacing: 90, useMaxWidth: false },
})
```

### 代码块复制

每个 `<pre>` 代码块（非 Mermaid）会被包裹在 `.code-block-wrapper` 中，并添加一个"复制"按钮。

- 按钮默认隐藏（`opacity: 0`），hover 包裹容器时显示
- 点击后通过 `navigator.clipboard.writeText()` 复制代码
- 复制成功后按钮文字变为"已复制"+ 绿色样式，2 秒后恢复

### 事件处理

| 事件 | 说明 |
|------|------|
| `@click` | 通过事件委托处理：代码块复制按钮 `.code-copy-btn` 和 Mermaid 源码复制按钮 `.mermaid-copy-btn` |

### marked 配置

```typescript
marked.setOptions({
  gfm: true,          // GitHub Flavored Markdown（表格、删除线、任务列表等）
  breaks: true,        // 单换行 → <br>
})
```

### 全局样式（非 scoped，因为 v-html 内容不继承 scoped）

组件通过全局 `.markdown-content` 选择器覆盖以下元素样式：

- **段落** `p`：8px 底部间距，末尾无间距
- **标题** `h1`~`h6`：紧凑尺寸（1.25em / 1.15em / 1.05em），首个标题无上边距
- **代码块** `pre`：圆角 8px，`--code-bg` 背景色
- **行内代码** `code`：圆角 4px，略微缩小字号
- **列表** `ul`/`ol`：20px 左缩进
- **引用** `blockquote`：左侧 3px 主题色边框 + 浅色背景
- **表格** `table`：全边框、表头有背景色、13px 字号
- **分割线** `hr`：细边框线
- **链接** `a`：主题色 + 下划线
- **图片** `img`：最大宽度 100% + 圆角 8px
- **删除线** `del`：opacity 0.6
- **强调** `strong`：标题色
- **任务列表** `input[type="checkbox"]`：主题色 accent-color
- **Mermaid 容器**：居中、可横向滚动、SVG 自适应宽度
- **Mermaid 错误**：红底红字 pre 块
- **代码复制按钮**：绝对定位右上角，默认透明，hover 显示，复制后绿色反馈
- **Mermaid 源码按钮**：同上，置于 Mermaid 容器右上角

---

## ScrollToBottom.vue（滚动到底部按钮）

### Props

| Prop | 类型 | 说明 |
|------|------|------|
| `visible` | `boolean` | 控制按钮显隐 |

### Emits

| Event | 说明 |
|-------|------|
| `click` | 触发滚动到底部 |

### UI

- Vue `<Transition name="scroll-fade">` 动画：入场/离场 `opacity 0` + `translateY(8px)` 过渡
- 圆形按钮（36×36px），位于父元素底部中心上方（`position: absolute; bottom: 100%; left: 50%; transform: translateX(-50%)`）
- 内嵌 SVG 向下箭头图标（18×18px，Lucide 风格 `chevron-down`）
- hover 时背景色变为 `--code-bg`

---

## AgentLogo.vue（SVG Logo）

### Props

| Prop | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `size` | `number` | `32` | Logo 宽高（px），通过 `??` 运算符取默认值 |

### SVG 结构

四层 SVG 元素组成的原子/轨道风格图标：

1. **外圆**：`r=14`，`stroke-width=2`，主题色描边
2. **内圆 / 核心**：`r=6`，主题色填充 `opacity=0.3` + `r=3` 实心核心
3. **轨道 1**：椭圆 `rx=11 ry=4`，虚线描边（`stroke-dasharray="4 3"`），旋转 `-30°`，`opacity=0.5`
4. **轨道 2**：同上椭圆参数，旋转 `45°`

所有颜色使用 CSS 变量 `var(--accent, #aa3bff)`，支持主题切换。
