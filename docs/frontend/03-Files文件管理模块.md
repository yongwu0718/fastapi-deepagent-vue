# Files 文件管理模块

> 本文档描述文件管理模块，包含文件浏览器、预览器、CRUD 操作和 Markdown 渲染引擎。

---

## 模块架构

```
files/
├── useFileManager.ts        # 核心状态管理（模块级单例）
├── useMarkdownRenderer.ts   # markdown-it 渲染引擎
├── FileBrowser.vue          # 主文件浏览组件（列表 + 预览双模式）
├── FilePreview.vue          # 文件内容预览组件
├── FileBreadcrumb.vue       # 面包屑导航
├── FileCreateDialog.vue     # 新建文件/目录对话框
├── FileRenameDialog.vue     # 重命名对话框
└── FileDeleteDialog.vue     # 删除确认对话框
```

---

## useFileManager（核心状态管理）

**模块级单例**，通过 `getFileManager()` 获取全局唯一实例。

### 状态字段

| 字段 | 类型 | 说明 |
|------|------|------|
| `currentPath` | `Ref<string>` | 当前目录路径 |
| `entries` | `Ref<FileEntry[]>` | 当前目录条目列表 |
| `loading` | `Ref<boolean>` | 目录加载中 |
| `selectedEntry` | `Ref<FileEntry \| null>` | 当前选中条目 |
| `fileContent` | `Ref<string>` | 文件内容（文本） |
| `fileUrl` | `Ref<string>` | 文件 URL（二进制，如 PDF blob URL） |
| `fileContentType` | `Ref<string>` | 文件内容类型（mime） |
| `fileContentLoading` | `Ref<boolean>` | 文件内容加载中 |
| `searchResults` | `Ref<FileEntry[]>` | 搜索结果 |
| `searching` | `Ref<boolean>` | 搜索中 |

### 关键方法

#### 目录操作

```typescript
loadDirectory(path?: string)   // 加载目录列表
navigateTo(path: string)       // 进入子目录
```

#### 条目选择

```typescript
selectEntry(entry: FileEntry)  // 选中条目
  → 目录: navigateTo(entry.path)
  → 文件: readFile(entry.path)
```

#### 文件读取

```typescript
readFile(path: string)
  → 文本文件 → GET /api/files/read → fileContent
  → 二进制文件 → GET /api/files/file → fileUrl (blob URL)
```

#### 文件 CRUD

| 方法 | 端点 | 说明 |
|------|------|------|
| `createFile(path, content?)` | POST `/api/files/create-file` | 创建文件 |
| `createDirectory(path)` | POST `/api/files/create-directory` | 创建目录 |
| `uploadFile(file, targetPath?)` | POST `/api/files/upload` | 上传文件 |
| `renameEntry(path, newName)` | PUT `/api/files/rename` | 重命名 |
| `moveEntry(path, targetDir)` | PUT `/api/files/move` | 移动 |
| `saveFile(path, content)` | PUT `/api/files/modify` | 保存修改 |
| `deleteEntry(path)` | DELETE `/api/files/delete` | 删除 |

#### 搜索

```typescript
searchFiles(query: string)
  → 300ms 防抖 → GET /api/files/search?q={query}
```

#### 面包屑

```typescript
breadcrumbs: computed  // 从 currentPath 计算面包屑路径数组
```

---

## useMarkdownRenderer（渲染引擎）

基于 `markdown-it` 的 Markdown 渲染引擎。

### 插件配置

| 插件 | 说明 |
|------|------|
| `markdown-it-multimd-table` | 多行表格 + rowspan 支持 |
| `markdown-it-katex` | LaTeX 数学公式渲染 |

### 预处理

- 表格连续性修复
- Unicode 制表符包裹为代码块

### 安全防护

- 所有链接自动添加 `target="_blank"` + `rel="noopener noreferrer"`
- `DOMPurify.sanitize()` XSS 过滤

---

## FileBrowser.vue（主文件浏览组件）

**双模式**：列表模式 + 预览模式

### 列表模式

```
┌─────────────────────────────────────────────┐
│ 刷新 | 面包屑 | 状态信息 | 搜索 | +新建/目录/上传 │
├─────────────────────────────────────────────┤
│ 📁 目录1                   4KB  2026-01-01  │
│ 📄 文件1.md                2KB  2026-01-01  │
│ ...                                         │
└─────────────────────────────────────────────┘
```

**交互功能：**
- 点击目录进入，点击文件预览
- 拖拽文件条目到聊天输入框（设置 `text/plain` dataTransfer）
- 拖拽文件到目录进行移动
- 每个条目显示操作按钮（重命名/删除，hover 显示）

### 预览模式

```
┌─────────────────────────────────────────────┐
│ ← 返回 | 文件名.md | 编辑/预览切换 | 复制/保存/下载 │
├─────────────────────────────────────────────┤
│          FilePreview 内容区域                 │
└─────────────────────────────────────────────┘
```

### 对话框管理

通过条件渲染管理三个对话框：
- `FileCreateDialog`：新建文件或目录
- `FileRenameDialog`：重命名确认
- `FileDeleteDialog`：删除确认（目录删除时提示递归删除）

---

## FilePreview.vue（文件预览）

### 内容类型路由

| 内容类型 | 展示方式 |
|----------|----------|
| **Markdown（可编辑）** | 编辑模式 `textarea` ↔ 预览模式 HTML |
| **普通文本（可编辑）** | `textarea` |
| **Markdown（只读）** | 渲染 HTML |
| **只读文本** | `<pre>` 标签 |
| **PDF** | `<iframe>` 内嵌预览 |
| **图片** | `<img>` 展示 |
| **二进制** | 下载提示 |

### 内部链接跳转

点击相对路径 `.md` 链接时，通过 `getFileManager().selectEntry()` 打开对应文件。

### 暴露的方法

```typescript
isEditing     // 是否编辑模式
handleSave()  // 保存文件
handleCopy()  // 复制内容
handleDownload()  // 下载文件
toggleEdit()  // 切换编辑/预览
```

---

## 其他组件

### FileBreadcrumb.vue

面包屑导航，纯展示组件：

```html
<FileBreadcrumb :items="['root', 'dir1', 'subdir']" @navigate="(idx) => ..." />
```

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
- 确认后调用 `fm.deleteEntry()`
