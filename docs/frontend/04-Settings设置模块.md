# Settings 设置模块

> 本文档描述设置管理模块，包含模型配置、系统提示词、MCP 服务、记忆库/技能库文件管理、技能开关等功能。

---

## 模块架构

```
settings/
├── SettingsView.vue       # 设置主页面（6 Tab 导航）
├── ModelConfigForm.vue    # 模型配置（YAML ↔ 表单双向转换）
├── ConfigEditor.vue       # 通用配置编辑器（JSON/Markdown）
├── FileManager.vue        # 记忆库/技能库文件管理
└── SkillManager.vue       # 技能开关管理
```

---

## SettingsView.vue（设置主页面）

### 布局

```
┌──────────┬───────────────────────────────────┐
│          │                                   │
│ 左侧导航  │         右侧内容区域               │
│          │                                   │
│ Tab 1    │   (根据当前 Tab 渲染对应组件)       │
│ Tab 2    │                                   │
│ Tab 3    │                                   │
│ Tab 4    │                                   │
│ Tab 5    │                                   │
│ Tab 6    │                                   │
│          │                                   │
└──────────┴───────────────────────────────────┘
  返回聊天        保存并重建按钮
```

### 6 个 Tab

| # | Tab Key | 标签 | 组件 | 说明 |
|---|---------|------|------|------|
| 1 | `model` | 模型配置 | `ModelConfigForm` | 管理 DeepSeek/Ollama/Aliyun/OpenAI/Moonshot 等模型参数 |
| 2 | `prompts` | 系统提示词 | `ConfigEditor` (`language="markdown"`) | 编辑 Agent 系统提示词（Markdown） |
| 3 | `mcp` | MCP 服务 | `ConfigEditor` (`language="json"`) | 编辑 MCP 服务配置（JSON） |
| 4 | `memory` | 记忆库文件 | `FileManager` (`type="memory"`) | 管理记忆库文件 |
| 5 | `skill-files` | 技能库文件 | `FileManager` (`type="skills"`) | 管理技能库文件 |
| 6 | `skill-manage` | 技能开关 | `SkillManager` | 启用/禁用各技能 |

### 顶部操作

- **返回聊天**：`router.push({ name: 'chat', params: { threadId: crypto.randomUUID() } })`
- **保存并重建**：调用 `POST /settings/rebuild` 重新编译 LangGraph

### 数据流：通过 Props 注入 load/save

`ModelConfigForm` 和 `ConfigEditor` 通过 props 接收 `load`/`save` 函数。SettingsView 负责定义这些函数，调用同一组后端 API 端点，通过 `path` 参数区分不同配置：

```
                  ┌── loadModelConfig()  ──  GET /settings/model-config/read?path=model
ModelConfigForm ──┤
                  └── saveModelConfig()  ──  PUT /settings/model-config/write { path: 'model', content }

                  ┌── loadPrompts()      ──  GET /settings/model-config/read?path=prompt
ConfigEditor     ──┤  (markdown)
(系统提示词)       └── savePrompts()      ──  PUT /settings/model-config/write { path: 'prompt', content }

                  ┌── loadMcpServer()    ──  GET /settings/model-config/read?path=mcp
ConfigEditor     ──┤  (json)
(MCP 服务)         └── saveMcpServer()    ──  PUT /settings/model-config/write { path: 'mcp', content }
```

---

## ModelConfigForm.vue（模型配置表单）

### YAML ↔ 表单双向转换

使用 `js-yaml` 库实现 `model_config.yaml` 与 Vue 表单的双向绑定：

```
YAML 文件 ← js-yaml.load → 响应式 formData ← v-model → 表单控件
           js-yaml.dump ↑
```

### Props

```typescript
interface Props {
  load: () => Promise<string>   // 从后端加载 YAML 内容
  save: (content: string) => Promise<void>  // 保存 YAML 内容到后端
}
```

组件内部使用 `js-yaml` 完成 YAML ↔ 表单的转换，对外只关心字符串。

### 支持的模型厂商（含独立配置区）

| 厂商 | 是否在激活 Radio 中 | 说明 |
|------|---------------------|------|
| **DeepSeek** | ✅ | 主执行模型 |
| **Ollama** | ✅ | 本地模型 |
| **Aliyun (DashScope)** | ✅ | 阿里云模型 |
| **OpenAI Compatible** | ✅ | 兼容 OpenAI 协议的模型 |
| **Moonshot** | ❌ | Kimi 模型（独立配置区，不在激活选择中） |
| **Embedding** | ❌ | 嵌入模型（独立配置区） |
| **Reranker** | ❌ | 重排序模型（独立配置区） |

### 激活厂商选择 UI

4 个 Radio 卡片切换：`deepseek`、`ali`、`openai`、`ollama`。选中的厂商作为 `active_provider` 写入 YAML。

### 各厂商配置字段

#### DeepSeek

| 字段 | 类型 | 说明 |
|------|------|------|
| `base_url` | text | 服务地址 |
| `model` | text | 默认模型 |
| `json_model` | text | JSON 模式专用模型 |
| `reasoning_effort` | select | 推理强度（low / medium / max） |
| `extra_body` | textarea (JSON) | 额外请求体参数 |
| `json_kwargs` | textarea (JSON) | JSON 模式参数 |

#### Ollama

| 字段 | 类型 | 说明 |
|------|------|------|
| `base_url` | text | 服务地址 |
| `model` | text | 模型名称 |
| `reasoning` | select | 推理级别（low / medium / high） |

#### Aliyun (DashScope)

| 字段 | 类型 | 说明 |
|------|------|------|
| `base_url` | text | 服务地址 |
| `model` | text | 模型名称 |
| `enable_thinking` | checkbox | 启用 thinking 模式 |

#### OpenAI Compatible

| 字段 | 类型 | 说明 |
|------|------|------|
| `base_url` | text | 服务地址 |
| `model` | text | 模型名称 |
| `extra_body` | textarea (JSON) | 额外请求体参数 |

#### Moonshot

| 字段 | 类型 | 说明 |
|------|------|------|
| `model` | text | 模型名称 |
| `thinking` | checkbox | 启用 thinking 模式 |

#### 嵌入模型 (Embedding)

| 字段 | 类型 | 说明 |
|------|------|------|
| `model` | text | 模型名称 |
| `base_url` | text | 服务地址 |

#### Reranker

| 字段 | 类型 | 说明 |
|------|------|------|
| `model` | text | 模型名称 |
| `top_n` | number | 返回条数（1-100） |

### 保存流程

```
用户编辑表单
  → formToYaml() 将各 provider ref 合并为对象
  → js-yaml.dump() 生成 YAML 字符串
  → 调用 props.save(yamlStr)
  → PUT /settings/model-config/write { path: 'model', content }
```

---

## ConfigEditor.vue（通用配置编辑器）

### 功能

纯文本编辑器组件，通过 props `load`/`save` 函数注入数据源，实现通用配置编辑。无语法高亮，使用等宽字体 textarea。

### 支持的语言模式

当前在项目中作为两种用途：

| 模式 | `label` prop | 使用场景 |
|------|-------------|------|
| **Markdown** | `system_prompt.txt` | 系统提示词编辑 |
| **JSON** | `mcp_server.json` | MCP 服务配置编辑 |

> 注意：ConfigEditor 在此项目中**不用于 YAML** 编辑。YAML 由 `ModelConfigForm.vue` 内部使用 `js-yaml` 处理。

### Props

```typescript
interface Props {
  load: () => Promise<string>            // 加载配置内容
  save: (content: string) => Promise<void>  // 保存配置内容
  language: 'yaml' | 'json' | 'markdown'    // 语法模式（必填）
  label: string                              // 顶部标签文本（必填）
}
```

### 状态管理

| 状态 | 说明 |
|------|------|
| `content` | 当前编辑内容（v-model 绑定到 textarea） |
| `loading` | 加载中 |
| `saving` | 保存中 |
| `status` | 操作反馈信息（成功/失败） |

> 注意：此组件**不保留原始内容**作变更对比。错误信息统一通过 `status` 展示，无独立的 `error` 或 `originalContent` 状态。

### UI 结构

```
┌──────────────────────────────────────────────┐
│ label              [status文字]  [保存按钮]   │  ← toolbar
├──────────────────────────────────────────────┤
│                                              │
│          textarea (等宽字体，无边框)           │
│                                              │
└──────────────────────────────────────────────┘
```

---

## FileManager.vue（记忆库/技能库文件管理）

### 双模式

通过 `type` prop 区分两种模式：

```html
<!-- 记忆库 -->
<FileManager type="memory" label="记忆库" />
<!-- 技能库 -->
<FileManager type="skills" label="技能库" />
```

### Props

```typescript
interface Props {
  type: 'memory' | 'skills'
  label: string          // 用于导航路径前缀展示
}
```

### 数据结构

```typescript
interface FileItem {
  name: string
  type: 'file' | 'directory'
  path: string           // 相对于当前目录的路径
}
```

### API 端点

所有端点位于 `/settings/memory-and-skill/` 路径下，以 `?type=memory|skills` 查询参数区分记忆库/技能库：

| 操作 | 端点 | 方法 |
|------|------|------|
| 列出目录 | `/settings/memory-and-skill/list` | GET |
| 读取文件 | `/settings/memory-and-skill/read` | GET |
| 新建文件 | `/settings/memory-and-skill/create-file` | POST |
| 修改文件 | `/settings/memory-and-skill/modify` | PUT |
| 删除文件/目录 | `/settings/memory-and-skill/delete` | DELETE |
| 上传文件 | `/settings/memory-and-skill/upload` | POST |
| 创建目录 | `/settings/memory-and-skill/create-directory` | POST |

### 功能详解

#### 目录导航

- 默认加载根目录
- 点击 📁 目录项进入子目录
- 「← 上级」按钮返回上级目录（通过 `parentPath` 追踪）
- 路径面包屑显示：`/memory/path/to/dir` 或 `/skills/path/to/dir`

#### 文件上传

- **单文件上传**：选择文件后直接上传到当前目录
- **文件夹上传**（`webkitdirectory`）：递归上传整个目录，流程如下：
  1. 过滤文件类型，仅保留以下扩展名的文件：
     `.md`, `.txt`, `.py`, `.yaml`, `.yml`, `.json`, `.toml`, `.js`, `.ts`, `.html`, `.css`, `.xml`, `.cfg`, `.ini`, `.env`, `.sh`, `.bat`, `.ps1`, `.sql`
  2. 先批量创建所需的子目录（`POST create-directory`，已存在的忽略）
  3. 逐个上传文件，显示进度（如 "上传中 3/10..."）
  4. 完成后刷新当前目录

#### 新建/编辑文件

- **新建**：点击「+ 新建文件」进入编辑模式，需输入文件路径（如 `notes/todo.md`），若路径含目录会自动创建
- **编辑**：点击文件项进入编辑模式，在深色背景的 textarea 中编辑内容
- **保存**：新建走 `POST create-file`，编辑走 `PUT modify`
- **取消**：退出编辑模式，返回文件列表

#### 删除

- 每个文件/目录项悬停时显示 ✕ 删除按钮
- 点击后弹出 `confirm` 确认对话框
- 调用 `DELETE /settings/memory-and-skill/delete`

### UI 状态

- `loading` — 加载中
- `loadError` — 加载失败（含错误信息）
- `uploading` / `uploadMsg` — 上传中及进度提示
- `editing` — 是否在编辑模式
- `editStatus` — 编辑保存状态

---

## SkillManager.vue（技能开关管理）

### Props

无外部 props。组件自行调用后端 API。

### 数据流

```
GET /settings/skills
  → { skills: [{ name, enabled }, ...] }
  → 渲染技能列表（含统计计数）
  → 用户切换开关（本地立即生效）
  → 点击「保存」→ PUT /settings/skills { enabled: [...] }
  → 如需生效 → 回到 SettingsView 点击「保存并重建」
```

### API

| 操作 | 端点 | 方法 | 请求体 |
|------|------|------|--------|
| 获取技能列表 | `/settings/skills` | GET | — |
| 保存启用列表 | `/settings/skills` | PUT | `{ "enabled": ["skill1", "skill2"] }` |

> 注意：请求直接使用 `client.get/put` 而非生成的 SDK 函数。PUT 请求需手动设置 `Content-Type: application/json`。

### 数据结构

```typescript
interface SkillItem {
  name: string
  enabled: boolean
}
```

响应中**没有 `description` 字段**，仅展示技能名称。

### UI

#### 工具栏
- 左侧显示「技能开关管理」标签
- 统计信息：「共 N 项，已启用 M 项」（通过 `computed` 实时计算）
- 右侧显示保存状态和「保存」按钮

#### 技能列表
- 每行显示技能名称（等宽字体）和 Toggle 开关按钮
- 已启用的行背景变为淡绿色 (`#f0fdf4`)
- 悬浮时行背景高亮
- 开关为纯 CSS Toggle 按钮（40×22px 圆角滑块），无需外部组件库

#### 空状态
当技能列表为空时显示：
> 未找到任何技能，请确保 skills 目录中存在包含 SKILL.md 的子目录

### 关键实现细节

- `toggleSkill(name)` 直接修改本地 `skills` 数组的 `enabled` 字段，不立即提交
- `saveSkills()` 将 `enabled === true` 的技能名收集为数组，PUT 到后端
- 保存后通过 SettingsView 的「保存并重建」按钮使配置生效
