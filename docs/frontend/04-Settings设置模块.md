# Settings 设置模块

> 本文档描述设置管理模块，包含模型配置、系统提示词、MCP 服务、记忆库/技能库文件管理、技能开关等功能。

---

## 模块架构

```
settings/
├── SettingsView.vue       # 设置主页面（6 Tab 导航）
├── ModelConfigForm.vue    # 模型配置（YAML ↔ 表单双向转换）
├── ConfigEditor.vue       # 通用配置编辑器（YAML/JSON/Markdown）
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

| # | Tab | 组件 | 说明 |
|---|-----|------|------|
| 1 | 模型配置 | `ModelConfigForm` | 管理 DeepSeek/Ollama/Aliyun/Moonshot 等模型参数 |
| 2 | 系统提示词 | `ConfigEditor` | 编辑 Agent 系统提示词（Markdown） |
| 3 | MCP 服务 | `ConfigEditor` | 编辑 MCP 服务配置（JSON） |
| 4 | 记忆库文件 | `FileManager` (`type="memory"`) | 管理记忆库 .md 文件 |
| 5 | 技能库文件 | `FileManager` (`type="skills"`) | 管理技能库文件 |
| 6 | 技能开关 | `SkillManager` | 启用/禁用各技能 |

### 顶部操作

- **返回聊天**：`router.push('/')`
- **保存并重建**：调用 `POST /settings/rebuild` 重新编译 LangGraph

---

## ModelConfigForm.vue（模型配置表单）

### YAML ↔ 表单双向转换

使用 `js-yaml` 库实现 `model_config.yaml` 与 Vue 表单的双向绑定：

```
YAML 文件 ← js-yaml.load → 响应式 formData ← v-model → 表单控件
           js-yaml.dump ↑
```

### 支持的模型厂商

| 厂商 | 说明 |
|------|------|
| **DeepSeek** | 主执行模型 |
| **Ollama** | 本地模型 |
| **Aliyun (DashScope)** | 阿里云模型（评估器） |
| **OpenAI Compatible** | 兼容 OpenAI 协议的模型 |
| **Moonshot** | Kimi 模型 |

### 厂商选择 UI

Radio 卡片形式切换激活厂商，点击卡片显示对应配置字段。

### 各厂商专属字段

| 厂商 | 专属配置 |
|------|----------|
| DeepSeek | `extra_body`、`json_kwargs`、`reasoning_effort` |
| Ollama | `base_url`、`model` |
| Aliyun | `model`、`enable_thinking` |
| Moonshot | `model` |

### 嵌入模型 & Reranker

独立配置区域，包含：
- 嵌入模型（model、base_url）
- Reranker（model、top_n）

### 保存流程

```
用户编辑表单
  → js-yaml.dump(formData) 生成 YAML 字符串
  → PUT /settings/model-config/write
```

---

## ConfigEditor.vue（通用配置编辑器）

### 功能

通过 props `load`/`save` 函数注入数据源，实现通用配置编辑。

### 支持的语言模式

| 模式 | 应用 |
|------|------|
| **YAML** | `model_config.yaml` |
| **JSON** | `mcp_server.json` |
| **Markdown** | `system_prompt.txt` |

### Props

```typescript
interface Props {
  load: () => Promise<string>   // 加载配置内容
  save: (content: string) => Promise<void>  // 保存配置内容
  language?: 'yaml' | 'json' | 'markdown'  // 语法高亮模式
}
```

### 状态管理

- `loading`：加载中
- `saving`：保存中
- `content`：当前编辑内容
- `originalContent`：原始内容（用于对比是否修改）
- `error`：错误信息

---

## FileManager.vue（记忆库/技能库文件管理）

### 双模式

通过 `type` prop 区分两种模式：

```html
<!-- 记忆库 -->
<FileManager type="memory" />
<!-- 技能库 -->
<FileManager type="skills" />
```

### API 端点

使用 `/settings/memory-and-skill/` 系列 API，与主文件管理 (`/api/files/`) 功能镜像但端点不同。

所有请求都需要 `type: 'memory' | 'skills'` 查询参数。

### 功能

| 功能 | 说明 |
|------|------|
| 目录导航 | 浏览记忆库或技能库的文件结构 |
| 文件上传 | 上传文件到对应的库 |
| 文件夹上传 | 支持递归上传目录（过滤 `.md`/`.txt`/`.py`/`.yaml` 等） |
| 新建文件 | 在指定目录下创建文件 |
| 编辑文件 | 打开、编辑并保存文件内容 |
| 删除文件 | 删除文件或目录 |

---

## SkillManager.vue（技能开关管理）

### 数据流

```
GET /settings/skills
  → 技能列表 [ { name, enabled, description }, ... ]
  → 渲染开关列表
  → 用户切换开关
  → PUT /settings/skills { enabled_skills: [...] }
  → "保存并重建"按钮 → POST /settings/rebuild
```

### UI

每个技能条目显示：
- 技能名称
- 技能描述
- Toggle 开关控件

批量编辑后通过 `PUT /settings/skills` 保存启用列表。修改技能开关后需要重建 LangGraph 才能生效，重建按钮提示用户执行 `POST /settings/rebuild`。
