# Files 文件管理模块

> 本文档描述文件管理模块，包含多标签页浏览、左右分屏、预览器、CRUD 操作、Markdown 渲染引擎和大纲导航。

---

## 模块架构

```
files/
├── useFileManager.ts        # 核心状态管理（模块级单例：目录浏览 + 标签页 + 分屏 + CRUD）
├── useMarkdownRenderer.ts   # markdown-it 渲染引擎 + 标题大纲提取
├── FileBrowser.vue          # 主容器（头部 + 模式切换 + 对话框 + 大纲面板）
├── FileList.vue             # 可复用文件列表组件
├── FileTabs.vue             # 可复用标签栏组件（支持跨窗格拖拽）
├── SplitFileView.vue        # 分屏模式主体（双标签栏 + SplitPane + 左右列表/预览）
├── FilePreview.vue          # 文件内容预览组件
├── FileBreadcrumb.vue       # 面包屑导航（纯展示）
├── FileCreateDialog.vue     # 新建文件/目录对话框
├── FileRenameDialog.vue     # 重命名对话框
└── FileDeleteDialog.vue     # 删除确认对话框
```

### 组件复用关系

```
FileBrowser.vue (主容器)
  ├─ 单屏模式 ────────────── FileTabs + FileList + FilePreview
  └─ 分屏模式 ─┐
               └── SplitFileView.vue
                     ├── FileTabs × 2 (左/右)
                     ├── FileList × 2 (左/右)
                     └── FilePreview × 2 (左/右)
```

---

## useFileManager（核心状态管理）

**模块级单例**，通过 `getFileManager()` 获取全局唯一实例。

### FileTab 接口

```typescript
interface FileTab {
  id: string          // 唯一标识
  entry: FileEntry    // 文件条目信息
  content: string     // 文件内容（文本）
  contentType: string // 内容类型: 'text' | 'binary' | 'image' | 'pdf' | ''
  fileUrl: string     // 二进制文件 blob URL
  contentLoading: boolean // 内容加载中
  pane: 'left' | 'right'  // 所属窗格（分屏时区分左右）
}
```

### 目录 + 搜索状态

| 字段 | 类型 | 说明 |
|------|------|------|
| `currentPath` | `Ref<string>` | 当前目录路径 |
| `entries` | `Ref<FileEntry[]>` | 当前目录条目列表 |
| `loading` | `Ref<boolean>` | 目录加载中 |
| `breadcrumbs` | `ComputedRef` | 面包屑路径数组 |
| `parentPath` | `ComputedRef<string \| null>` | 上级目录路径 |
| `searchQuery` | `Ref<string>` | 搜索关键词 |
| `searchLoading` | `Ref<boolean>` | 搜索加载中 |
| `filteredEntries` | `ComputedRef<FileEntry[]>` | 搜索时返回搜索结果，否则返回目录列表 |
| `fileCount` / `dirCount` | `ComputedRef<number>` | 文件/目录计数 |

### 标签页 + 分屏状态

| 字段 | 类型 | 说明 |
|------|------|------|
| `openTabs` | `Ref<FileTab[]>` | 所有已打开的标签页 |
| `activeTabId` | `Ref<string>` | 单屏模式活跃标签 ID |
| `activeTab` | `ComputedRef<FileTab \| null>` | 当前活跃标签（分屏时返回聚焦窗格的标签） |
| `splitMode` | `Ref<boolean>` | 是否处于分屏模式 |
| `activePane` | `Ref<'left' \| 'right'>` | 当前聚焦窗格 |
| `leftActiveTabId` | `Ref<string>` | 左窗格活跃标签 ID |
| `rightActiveTabId` | `Ref<string>` | 右窗格活跃标签 ID |
| `leftTabs` | `ComputedRef<FileTab[]>` | 左窗格标签列表 |
| `rightTabs` | `ComputedRef<FileTab[]>` | 右窗格标签列表 |
| `leftActiveTab` | `ComputedRef<FileTab \| null>` | 左窗格活跃标签 |
| `rightActiveTab` | `ComputedRef<FileTab \| null>` | 右窗格活跃标签 |

### 派生状态（从活跃标签计算）

| 字段 | 类型 | 说明 |
|------|------|------|
| `selectedEntry` | `ComputedRef<FileEntry \| null>` | 聚焦窗格的活跃标签文件条目 |
| `fileContent` | `ComputedRef<string>` | 聚焦窗格的活跃标签文件内容 |
| `fileUrl` | `ComputedRef<string>` | 聚焦窗格的活跃标签 blob URL |
| `fileContentType` | `ComputedRef<string>` | 聚焦窗格的活跃标签内容类型 |
| `fileContentLoading` | `ComputedRef<boolean>` | 聚焦窗格的活跃标签加载状态 |

### 方法

#### 目录操作

```typescript
loadDirectory(path?: string)   // 加载目录列表
navigateTo(path: string)       // 进入子目录（单屏时取消活跃标签，分屏时保留）
goUp()                         // 返回上级目录
refresh()                      // 刷新当前目录
```

#### 标签页管理

```typescript
openFile(path: string)         // 打开文件（分屏时允许在另一窗格新建副本）
closeTab(tabId: string)        // 关闭标签（自动切换到相邻标签，无标签时退出分屏）
switchTab(tabId: string)       // 切换活跃标签
selectEntry(entry: FileEntry)  // 选中条目（目录进入，文件打开标签）
clearSelection()               // 清除选中（关闭活跃窗格的标签）
isFileOpen(path): boolean      // 检查文件是否已在任意标签中打开
```

**标签页生命周期：**
- 点击文件 → 检查是否已在**当前窗格**打开 → 已打开则激活，否则新建标签 + 异步加载内容
- **分屏时**：同一文件可在不同窗格各打开一份，互不影响
- 保存文件 → 同步更新所有标签中同一文件的内容（两个窗格同时更新）
- 关闭标签 → 清理 blob URL → 自动激活相邻标签 → 无标签时返回列表视图
- 删除文件/目录 → 自动关闭所有涉及该路径的标签
- 进入子目录 → 分屏时不取消活跃标签（列表始终可见）

#### 分屏操作

```typescript
splitToggle()                         // 开启/关闭分屏模式
moveTabToPane(tabId, targetPane)      // 移动标签到指定窗格
```

**分屏生命周期：**
- 开启：所有现有标签归左窗格，右窗格为空，`activePane` 切到右侧
- 退出：关闭所有右窗格标签，左窗格标签恢复为普通标签
- 无标签时自动退出分屏

#### 搜索

```typescript
setSearch(query: string)    // 300ms 防抖 → GET /api/files/search?q={query}
clearSearch()               // 清除搜索
```

#### 文件 CRUD

| 方法 | 端点 | 说明 |
|------|------|------|
| `createFile(path, content?)` | POST `/api/files/create-file` | 创建文件 |
| `createDirectory(path)` | POST `/api/files/create-directory` | 创建目录 |
| `uploadFile(file, targetPath?)` | POST `/api/files/upload` | 上传文件 |
| `renameEntry(path, newName)` | PUT `/api/files/rename` | 重命名 |
| `moveEntry(path, targetDir)` | PUT `/api/files/move` | 移动 |
| `saveFile(path, content)` | PUT `/api/files/modify` | 保存修改（同步更新所有标签中同一文件） |
| `deleteEntry(path)` | DELETE `/api/files/delete` | 删除（自动关闭关联标签） |

---

## useMarkdownRenderer（渲染引擎 + 大纲）

基于 `markdown-it` 的 Markdown 渲染引擎，采用 `ref` + `watch` 异步渲染模式支持 Mermaid 图表。

### 插件与依赖

| 插件/库 | 说明 |
|---------|------|
| `markdown-it-multimd-table` | 多行表格 + rowspan 支持 |
| `markdown-it-katex` | LaTeX 数学公式渲染 |
| `mermaid` | 图表渲染（flowchart、sequence 等） |

### Mermaid 初始化

```typescript
mermaid.initialize({
  startOnLoad: false,
  theme: 'default',
  securityLevel: 'loose',
  flowchart: {
    curve: 'step',          // 直角正交连线
    rankSpacing: 100,       // 层级间距
    nodeSpacing: 90,        // 节点间距
    useMaxWidth: false,     // 不限制宽度
  },
})
```

### 渲染流程

```
markdown-it.render()
  → extractMermaidBlocks()    // 提取 ```mermaid 代码块 → 占位 div
  → DOMPurify.sanitize()      // XSS 安全过滤
  → mermaid.render() 异步      // 逐个渲染为 SVG
  → addCodeCopyButtons()      // 给 <pre> 包裹 .code-block-wrapper + 复制按钮
  → renderedHtml.value        // 最终 HTML
```

- **异步渲染**：`renderedHtml` 从 `computed` 改为 `ref` + `watch`，兼容 `mermaid.render()` 的 Promise 语义
- **HTML 实体解码**：`decodeHtmlEntities()` 还原 markdown-it 对代码块内容的转义（`&lt;br/&gt;` → `<br/>`）
- **错误容错**：单个图表渲染失败显示错误提示，不影响其他图表和页面

### 代码块复制

每个 `<pre>` 代码块自动包裹为 `.code-block-wrapper` 容器，hover 时右上角显示「复制」按钮。通过事件委托处理点击，复制 `code.textContent` 到剪贴板，成功后显示「已复制」2 秒恢复。跳过 mermaid 图表和错误块。

### 预处理

- 表格连续性修复
- Unicode 制表符包裹为代码块

### 标题 ID 注入

覆盖 `heading_open` 渲染器，自动给 `h1`~`h6` 注入 `id` 属性。ID 由标题文本 slug 化生成，支持中文，同文档内自动去重（追加 `-1`, `-2` 后缀）。

### 大纲提取

```typescript
interface OutlineItem {
  level: number  // 1-6（对应 h1-h6）
  text: string   // 标题文本
  id: string     // 对应 HTML 中的 id 属性
}
```

composable 返回 `{ renderedHtml, outline }`，`outline` 从原始 markdown 内容中提取标题层级。

### 安全防护

- 所有链接自动添加 `target="_blank"` + `rel="noopener noreferrer"`
- `DOMPurify.sanitize()` XSS 过滤
- mermaid SVG 来自官方库，不在 DOMPurify 过滤范围

---

## FileBrowser.vue（主容器）

**职责**：头部栏 + 模式切换 + 对话框管理 + 大纲面板。

```
┌─────────────────────────────────────────────┐
│ 刷新 | 面包屑 | 状态 | 编辑/复制/保存 | 分屏 | 新建 | 上传 │  ← 头部（常驻）
├─────────────────────────────────────────────┤
│ [file1.md] [file2.txt]              [大纲]   │  ← 单屏标签栏
├─────────────────────────────────────────────┤
│  文件列表 / FilePreview                      │  ← 单屏内容区
└─────────────────────────────────────────────┘

                  ↓ 点击分屏按钮后 ↓

┌─────────────────────────────────────────────┐
│ 刷新 | 面包屑 | 状态 | 编辑/复制/保存 | [分屏] | 新建 | 上传 │
├─────────────────────────────────────────────┤
│ 左标签栏 [file1.md] [file2.md] │ 右标签栏 [file3.md]  │  ← 双标签栏
├───────────────────────────────┼──────────────────────┤
│ 文件列表 / FilePreview(左)     │ 文件列表 / FilePreview(右) │  ← SplitPane 分屏
└───────────────────────────────┴──────────────────────┘
```

分屏使用 `split-pane-v3` 库实现，分隔条可拖拽调整比例（最小 20%），hover 时高亮紫色。

### 拖拽功能

| 拖拽源 | 拖入目标 | 效果 |
|--------|----------|------|
| 文件列表条目 | 聊天输入框 | 插入 `/knowledge/{path}` 路径文本 |
| 标签页标签 | 聊天输入框 | 插入 `/knowledge/{path}` 路径文本 |
| 标签页标签 | 另一窗格标签栏 | 移动标签到目标窗格 |
| 面包屑导航项 | 聊天输入框 | 插入 `/knowledge/{path}` 目录路径 |
| 文件列表条目 | 目录条目 | 移动文件到目标目录 |

### 头部操作按钮与预览状态联动

- **Markdown（可编辑）**：编辑/预览切换、复制、保存
- **普通文本**：复制、保存
- **只读文本**：复制
- **二进制/PDF/图片**：下载
- **分屏按钮**：至少一个标签打开时显示，高亮表示当前处于分屏模式

### 对话框管理

通过条件渲染管理三个对话框：
- `FileCreateDialog`：新建文件或目录
- `FileRenameDialog`：重命名确认
- `FileDeleteDialog`：删除确认（目录删除时提示递归删除）

### 大纲面板

- 固定在面板右上角（`position: absolute`），不随内容滚动
- 标签栏右侧按钮切换显示/隐藏
- 按层级缩进显示所有标题（h1 加粗）
- 点击标题 → 平滑滚动到对应锚点
- 切换文件时自动关闭
- 分屏时追踪当前聚焦窗格的预览组件

---

## FileList.vue（可复用文件列表）

纯展示组件，接收 props 渲染文件列表。

**Props：**
| 字段 | 类型 | 说明 |
|------|------|------|
| `entries` | `FileEntry[]` | 目录条目列表 |
| `loading` | `boolean` | 加载中 |
| `searchQuery` | `string` | 搜索关键词 |
| `searchLoading` | `boolean` | 搜索加载中 |
| `parentPath` | `string \| null` | 上级目录路径 |
| `dragSourcePath` | `string` | 拖拽源文件路径（用于跨目录移动） |
| `isFileOpen` | `(path: string) => boolean` | 检查文件是否已打开 |

**Emits：**
| 事件 | 参数 | 说明 |
|------|------|------|
| `entry-click` | `FileEntry` | 点击条目 |
| `rename` | `FileEntry` | 请求重命名 |
| `delete` | `FileEntry` | 请求删除 |
| `go-up` | - | 返回上级目录 |
| `move-entry` | `{ sourcePath, targetDir }` | 文件移动到目录 |
| `update:dragSourcePath` | `string` | 拖拽开始时设置源路径 |

**内部管理** `dragOverDir` 本地状态，用于拖入目录时的视觉高亮。

**格式化函数** `fmtSize(bytes)` / `fmtTime(iso)` 内置在组件中。

---

## FileTabs.vue（可复用标签栏）

渲染标签按钮列表，支持点击切换、关闭，以及**跨窗格拖拽移动**。

**Props：**
| 字段 | 类型 | 说明 |
|------|------|------|
| `tabs` | `FileTab[]` | 标签列表 |
| `activeTabId` | `string` | 活跃标签 ID |
| `focused` | `boolean` | 是否聚焦（显示紫色下划线） |
| `pane` | `'left' \| 'right'` | 所属窗格 |
| `emptyText` | `string` | 无标签时显示的文字 |

**Emits：**
| 事件 | 参数 | 说明 |
|------|------|------|
| `switch-tab` | `tabId: string` | 切换标签 |
| `close-tab` | `tabId: string` | 关闭标签 |
| `activate` | - | 点击激活（mousedown） |
| `move-tab` | `tabId, targetPane` | 标签跨窗格移动 |

**拖拽机制：**
- 拖出时写入两套数据：`text/plain`（聊天框用）+ `application/x-file-tab-id`（跨窗格移动用）
- 接受拖入时检查 `application/x-file-tab-id`，匹配则高亮并允许 drop
- 拖入高亮：背景淡紫色 + 底部紫色边框
- 单屏模式下 `pane="left"`，`move-tab` 事件不会被触发（无目标窗格）

---

## SplitFileView.vue（分屏模式主体）

组装分屏模式的完整 UI：双标签栏 + `SplitPane` + 左右 `FileList`/`FilePreview`。

**对外暴露：**
- `leftPreviewRef` / `rightPreviewRef`（用于父组件访问预览引用、大纲等）

**内部职责：**
- 管理跨窗格 `dragSourcePath`（左右 FileList 共享）
- 对接 `FileTabs` 的 `move-tab` 事件，调用 `fm.moveTabToPane()`
- 透传 `@rename` / `@delete` 事件到父组件
- SplitPane 使用 `split-pane-v3` 库，分隔条自定义样式（4px 宽，hover 紫色）

**样式要点：**
- `.sv-pane` 使用 `height: 100%` 而非 `flex: 1`，适配 SplitPane 内部的 `position: absolute` 布局
- `.sv-content` 使用 `position: relative` 为 SplitPane 提供定位上下文

---

## FilePreview.vue（文件预览）

纯展示组件，接收 props 渲染文件内容。编辑状态由组件内部管理，编辑内容不跨标签保留（标签切换时组件重建）。

### 内容类型路由

| 内容类型 | 展示方式 |
|----------|----------|
| **Markdown（可编辑）** | 编辑模式 `textarea` ↔ 预览模式 HTML（含 Mermaid 图表、代码块复制） |
| **普通文本（可编辑）** | `textarea` |
| **Markdown（只读）** | 渲染 HTML（含 Mermaid 图表、代码块复制） |
| **只读文本** | `<pre>` 标签 |
| **PDF** | `<iframe>` 内嵌预览 |
| **图片** | `<img>` 展示 |
| **二进制** | 下载提示 |

### Mermaid 图表交互

Mermaid 图表渲染为 SVG，支持缩放和平移：

- **缩放**：右下角浮动工具栏，`−`/`+` 按钮（±10%）、滑块（30%~300%）、百分比文字（点击重置 140%）
- **平移**：点击手掌按钮切换拖拽模式（`grab` / `grabbing` 手型光标），拖拽图表平移位置，再次点击退出并归零
- **源码复制**：hover 图表右上角「源码」按钮，复制原始 mermaid 代码到剪贴板
- 工具栏仅在页面包含 mermaid 图表时显示

通过 CSS 自定义属性控制：`--mermaid-scale`（缩放）、`--mermaid-tx/ty`（平移偏移），`transform: translate() scale()` 应用到 SVG。

### 代码块复制

hover 代码块时右上角显示「复制」按钮，点击复制代码内容到剪贴板，成功后显示绿色「已复制」2 秒恢复。

### 内部链接跳转

点击相对路径 `.md` 链接时，通过 `getFileManager().selectEntry()` 打开对应文件。由于 selectEntry 对文件类型调用 `openFile()`，目标文件会在新标签中打开。

### 事件委托

`onMarkdownClick` 统一处理三类点击（优先级从高到低）：
1. `.code-copy-btn` → 代码块复制
2. `.mermaid-copy-btn` → mermaid 源码复制
3. `<a>` `.md` 链接 → 文件跳转

### 暴露的方法

```typescript
isEditing         // 是否编辑模式
isMarkdown        // 是否为 Markdown 文件
isTextEditable    // 是否可文本编辑
isText / isBinary / isPdf / isImage  // 内容类型判断
handleSave()      // 保存文件
handleCopy()      // 复制内容
handleDownload()  // 下载文件
copied            // 复制成功标记
toggleEdit()      // 切换编辑/预览
outline           // 当前文件的标题大纲（OutlineItem[]）
showOutline       // 大纲面板是否可见
// ── Mermaid 缩放/平移 ──
mermaidZoom       // 缩放百分比（Ref<number>，默认 140）
isPanMode         // 是否平移模式
panOffset         // 平移偏移量 { x, y }
hasMermaid        // Computed: 当前内容是否含 mermaid 图表
```

### blob URL 管理

blob URL 由标签管理器（`useFileManager.closeTab`）统一清理。FilePreview 组件销毁时不释放 URL，避免标签切换后 URL 失效。

---

## 其他组件

### FileBreadcrumb.vue

面包屑导航，纯展示组件：

```html
<FileBreadcrumb :items="['root', 'dir1', 'subdir']" @navigate="(idx) => ..." />
```

> 注：面包屑实际渲染在 `FileBrowser.vue` 头部中，支持拖拽到聊天输入框（插入目录路径 `/knowledge/{path}`）。

### FileCreateDialog.vue

新建文件/目录对话框：
- 支持文件名 + 初始内容输入
- 选择创建类型（文件/目录）

### FileRenameDialog.vue

重命名对话框：
- 显示当前完整路径
- 预填当前文件名
- 确认后调用 `fm.renameEntry()`

### FileDeleteDialog.vue

删除确认：
- 文件：简单确认
- 目录：提示"包含所有子文件和子目录将被递归删除"
- 确认后调用 `fm.deleteEntry()`，自动关闭关联标签
