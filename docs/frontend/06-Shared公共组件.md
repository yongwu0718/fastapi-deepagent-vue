# Shared 公共组件与工具

> 本文档描述跨模块共享的基础设施，包括日志系统、Toast 通知、Markdown 渲染、滚动控制和 Logo 组件。

---

## 模块架构

```
shared/
├── useLogger.ts          # 结构化日志系统
├── useToast.ts           # Toast 通知系统（发布-订阅）
├── ToastContainer.vue    # Toast UI 容器
├── Markdown.vue          # Markdown 渲染组件
├── ScrollToBottom.vue    # 滚动到底部按钮
├── AgentLogo.vue         # SVG Logo 组件
└── useContentNav.ts      # 内容大纲导航（消费方：chat/core）
```

---

## useLogger.ts（结构化日志）

### 日志等级

| 等级 | 方法 | 生产环境 | 说明 |
|------|------|----------|------|
| trace | `logger.trace()` | 默认关闭 | 最详细的调试信息 |
| debug | `logger.debug()` | 默认关闭 | 调试信息 |
| info | `logger.info()` | ✓ | 一般信息 |
| warn | `logger.warn()` | ✓ | 警告 |
| error | `logger.error()` | ✓ | 错误 |

### 运行时控制

```typescript
// URL 参数启用全量日志（开发环境）
?log=trace

// 运行时调整日志等级
window.__setLogLevel('debug')
```

### 预置模块 Logger

```typescript
loggerSSE         // SSE 流通信
loggerChat        // 聊天流程
loggerRetry       // 重试逻辑
loggerFork        // 分支操作
loggerCheckpoint  // 检查点管理
loggerVue         // Vue 框架绑定（挂载到 app.config.errorHandler）
loggerResume      // 中断恢复
```

### 日志格式

```typescript
loggerSSE.info('[SSE] connected', { threadId: 'xxx', timestamp: Date.now() })
// 输出: [SSE] connected { threadId: 'xxx', timestamp: 1715900000000 }
```

---

## useToast.ts（Toast 通知）

### 设计模式：发布-订阅

```
toast.success(title, description)
  → 发布事件（推入 toasts 数组）
  → ToastContainer 订阅
  → 渲染 Toast UI
  → 自动过期移除
```

### Toast 类型

| 方法 | 颜色 | 默认时长 | 图标 |
|------|------|----------|------|
| `toast.success(title, desc?)` | 绿色 | 4 秒 | ✓ |
| `toast.error(title, desc?)` | 红色 | 6 秒 | ✕ |
| `toast.warning(title, desc?)` | 黄色 | 5 秒 | ⚠ |
| `toast.info(title, desc?)` | 蓝色 | 4 秒 | ℹ |

### API

```typescript
// 发布 Toast
import { toast } from '@/shared/useToast'

toast.success('保存成功')
toast.error('失败', error.message)
toast.warning('磁盘空间不足')
toast.info('模型已切换')

// 注册监听器（ToastContainer 内部使用）
subscribeToasts((toasts) => {
  // toasts: ToastItem[]
})
```

### 退出动画

Toast 过期时先设置 `removing=true`，300ms 后再从数组中移除，配合 Vue `<TransitionGroup>` 实现平滑退出动画。

---

## ToastContainer.vue（Toast UI 容器）

### 实现

```vue
<template>
  <Teleport to="body">
    <TransitionGroup name="toast">
      <div v-for="t in toasts" :key="t.id" :class="['toast', t.type]">
        <span class="toast-icon">{{ icon(t.type) }}</span>
        <div>
          <div class="toast-title">{{ t.title }}</div>
          <div v-if="t.description" class="toast-description">{{ t.description }}</div>
        </div>
        <button @click="dismiss(t.id)">✕</button>
      </div>
    </TransitionGroup>
  </Teleport>
</template>
```

使用 `<Teleport to="body">` 挂载到 body 下，确保 z-index 层级不受父组件影响。

---

## Markdown.vue（Markdown 渲染）

### Props

| Prop | 类型 | 说明 |
|------|------|------|
| `content` | `string` | Markdown 源文本 |
| `codeBlockIdSeed` | `string` | 代码块锚点 ID 前缀（用于大纲导航定位） |

### 渲染流程

```
content (string)
  → marked.parse()      ← 配置: GFM + breaks + 任务列表
  → DOMPurify.sanitize() ← XSS 防护
  → innerHTML 注入
```

### marked 配置

```typescript
marked.setOptions({
  gfm: true,          // GitHub Flavored Markdown
  breaks: true,        // 单换行 → <br>
  // 支持：表格、删除线、任务列表
})
```

### 全局样式

组件内部覆盖以下元素样式：
- `h1`~`h6`：标题层级 + 锚点
- `pre > code`：代码块（暗色背景 + 边框）
- `ul`/`ol`：列表缩进
- `blockquote`：引用（左边框 + 灰色）
- `table`：表格（全边框 + 斑马纹）
- `a`：链接（强调色）
- `img`：图片（最大宽度 100%）

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

带 Vue `<Transition>` 动画的圆形浮动按钮，固定在右下角。点击时触发 `click` 事件，父组件处理实际滚动逻辑。

---

## AgentLogo.vue（SVG Logo）

### Props

| Prop | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `size` | `number \| string` | `32` | Logo 尺寸 |

### 设计

原子/轨道风格 SVG 图标，用于 ChatHeader 显示。
