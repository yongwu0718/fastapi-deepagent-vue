---
name: subagents
description: 配置 LangChain DeepAgents 子代理（SubAgent），实现主代理委派工作、上下文隔离和专业化任务处理。当需要添加、修改或禁用子代理，或设计多代理协作流程时使用此技能。
---

# SubAgent 配置指南

SubAgent（子代理）是 DeepAgents 中用于**委派工作**和**保持上下文干净**的核心机制。主代理通过 `task` 工具将复杂任务委派给子代理，子代理在独立的上下文中执行并返回简洁结果，避免主代理上下文被中间结果填满。

## 核心概念

```
主代理 → task(name="子代理名", task="任务描述") → 子代理（独立上下文）
                                                       ↓
                                                  执行工具 + 推理
                                                       ↓
                                                  返回简洁结果给主代理
```

### 何时使用子代理

✅ **适合**：
- 会产生大量中间结果的多步骤任务（网络搜索、数据分析、文件处理）
- 需要专门指令或工具的专业领域（财务分析、代码审查）
- 需要不同模型能力的任务（长文档用高上下文模型、数据分析用强推理模型）
- 希望主代理专注于高层协调时

❌ **不适合**：
- 简单的单步骤任务
- 需要保留中间上下文时
- 子代理开销大于收益时

## 项目配置方式

本项目使用 **Python 字典方式**定义子代理，通过 `importlib` 动态加载，支持热重载。

### 配置文件位置

```
/skill/subagents/scripts/subagents_config.py
```

### 配置结构

```python
# 每个子代理是一个字典，必须包含 name、description、system_prompt
# 可选字段：tools、model、middleware、skills、interrupt_on、response_format、permissions

my_subagent = {
    "name": "my-subagent",              # 必需：唯一标识符
    "description": "描述子代理的功能",    # 必需：主代理据此决定何时委派
    "system_prompt": "子代理的指令",     # 必需：定义行为和工作流
    "tools": [tool_func1, tool_func2],  # 可选：指定则覆盖继承，不填则继承主代理工具
    "model": llm_instance,              # 可选：覆盖主代理模型
    # "middleware": [...],              # 可选：额外中间件
    # "skills": ["/skills/xxx/"],       # 可选：技能源路径
}

# 激活列表：注释掉即禁用
subagents = [
    my_subagent,
]
```

### 字段详解

| 字段 | 类型 | 必需 | 说明 |
|------|------|:--:|------|
| `name` | `str` | ✅ | 唯一标识符，主代理调用时使用，同时出现在流式元数据中 |
| `description` | `str` | ✅ | 描述功能，**要具体面向操作**。主代理以此决定委派给谁 |
| `system_prompt` | `str` | ✅ | 子代理指令，包含工具使用指导和输出格式要求 |
| `tools` | `list[Callable]` | ❌ | 子代理可用工具列表。指定后完全覆盖继承 |
| `model` | `str \| BaseChatModel` | ❌ | 覆盖主代理模型。字符串格式 `"provider:model"` |
| `middleware` | `list` | ❌ | 额外中间件，不从主代理继承 |
| `skills` | `list[str]` | ❌ | 技能源路径，子代理拥有独立 SkillsMiddleware 实例 |
| `interrupt_on` | `dict` | ❌ | 人机协同配置 |
| `response_format` | `ResponseFormat` | ❌ | 结构化输出模式，父代理收到 JSON 而非自由文本 |
| `permissions` | `list` | ❌ | 文件系统权限规则 |

### 示例：账单分析子代理

```python
from backend.core.models.model_factory import llm_ali
from backend.core.utils import (
    analyze_billing, analyze_monthly, analyze_expense,
    analyze_monthly_categories, save_bill,
)

bill_analyzer = {
    "name": "bill-analyzer",
    "description": (
        "分析个人账单数据：收支总览、消费分类排名、各平台支出占比、"
        "食品消费习惯追踪、基于历史趋势的下月预算预测。"
    ),
    "system_prompt": """你是一位专业的个人财务分析师。

工作流程：
1. 使用 analyze_billing 获取整体收支概览
2. 使用 analyze_monthly 查看月度变化趋势
3. 使用 analyze_expense 获取消费分类明细
4. 使用 analyze_monthly_categories 分析各类消费的月度变化
5. 需要时使用 save_bill 保存分析结果

输出要求：
- 先给出核心数据摘要（总收入、总支出、结余）
- 再给出分类排名和趋势分析
- 最后给出建议或预警
- 保持回复简洁，控制在 500 字以内""",
    "tools": [
        analyze_billing, analyze_monthly, analyze_expense,
        analyze_monthly_categories, save_bill,
    ],
    "model": llm_ali,
}
```

### 示例：网络搜索子代理

```python
from backend.core.utils.some_search import web_search

research_agent = {
    "name": "research-agent",
    "description": "使用网络搜索对特定主题进行深入研究。需要经过多次搜索才能获取详细信息时使用。",
    "system_prompt": """你是一位细致的研究员。工作流程：
1. 将研究问题分解为多个搜索查询
2. 使用 web_search 逐个搜索并收集信息
3. 综合信息形成全面的摘要
4. 引用来源

输出格式：
- 摘要（2-3 段）
- 关键发现（要点列表）
- 来源列表

保持回复在 500 字以内。""",
    "tools": [web_search],
    "model": "openai:gpt-4o",
}
```

## 热重载机制

子代理配置支持**零停机热更新**，与 MCP 工具加载模式一致：

```
subagents_config.py  →  load_subagents() (importlib 强制重载)
                              ↓
              init_graph() → create_deep_agent(subagents=...)
                              ↓
                    POST /settings/rebuild → 配置即时生效
```

**修改流程**：

1. 编辑 `backend/memory_skill/skill/subagents/scripts/subagents_config.py`
2. 返回消息子代理列表，确认更新成功。
3. 无需重启服务器

## 通用子代理

DeepAgents 会自动添加一个 `general-purpose` 子代理，与主代理共享工具和系统提示。

### 覆盖通用子代理

如需替换默认通用子代理，添加一个 `name="general-purpose"` 的条目：

```python
general_purpose = {
    "name": "general-purpose",
    "description": "用于研究和多步骤任务的通用代理",
    "system_prompt": "你是一个通用助手。遇到复杂任务时，分步执行并返回简洁摘要。",
    "tools": [web_search],
    "model": llm_ali,
}

subagents = [
    general_purpose,
]
```

### 禁用通用子代理

如需完全移除默认通用子代理，从 `subagents` 列表中排除即可（列表为空或仅含自定义代理时不自动添加）。

## 最佳实践

### 1. 编写清晰的描述

主代理根据 `description` 决定调用哪个子代理，描述必须具体：

✅ **好**：`"分析财务数据并生成带有置信度分数的投资见解"`

❌ **差**：`"做财务方面的事情"`

### 2. 保持系统提示详细

包含工具使用指导和输出格式要求。越具体，子代理越可靠：

```python
"system_prompt": """你是一位细致的研究员。

工作流程：
1. 将问题分解为可搜索的查询
2. 使用对应工具查找信息
3. 综合发现形成摘要
4. 引用来源

输出格式：
- 摘要（2-3 段）
- 关键发现（要点列表）
- 来源

保持回复在 500 字以内。"""
```

### 3. 最小化工具集

只给子代理完成工作所必需的工具，提高专注度和安全性：

```python
# ✅ 好：专注的工具集
email_agent = {
    "name": "email-sender",
    "tools": [send_email, validate_email],
}

# ❌ 差：工具太多，不专注
email_agent = {
    "name": "email-sender",
    "tools": [send_email, web_search, database_query, file_upload],
}
```

### 4. 按任务选择模型

不同模型擅长不同任务：

```python
subagents = [
    {
        "name": "contract-reviewer",
        "description": "审查法律文件和合同",
        "tools": [read_document, analyze_contract],
        "model": "google_genai:gemini-3.1-pro-preview",  # 大上下文
    },
    {
        "name": "financial-analyst",
        "description": "分析财务数据和市场趋势",
        "tools": [get_stock_price, analyze_fundamentals],
        "model": "openai:gpt-5.1",  # 强推理
    },
]
```

### 5. 返回简洁的结果

指示子代理返回摘要而非原始数据：

```python
data_analyst = {
    "system_prompt": """分析数据并返回：
1. 关键见解（3-5 个要点）
2. 总体置信度分数
3. 推荐的下一步行动

不要包含：原始数据、中间计算、详细工具输出
保持回复在 300 字以内。"""
}
```

## 常见模式

### 多子代理流水线

为不同阶段创建专门子代理，主代理负责编排：

```python
subagents = [
    {
        "name": "data-collector",
        "description": "从各种来源收集原始数据",
        "tools": [web_search, api_call, database_query],
    },
    {
        "name": "data-analyzer",
        "description": "分析收集到的数据并提取见解",
        "tools": [statistical_analysis],
    },
    {
        "name": "report-writer",
        "description": "根据分析结果撰写格式化报告",
        "tools": [format_document],
    },
]
```

工作流：主代理创建计划 → 委派 collection → 委派 analysis → 委派 report → 汇总输出。

每个子代理在清洁的上下文中独立工作，互不污染。

### 上下文传递

父代理运行时上下文自动传播到所有子代理：

```python
# main_agent.py 中定义 context_schema
class Context:
    user_id: str
    researcher_max_depth: int = 5

# 子代理工具通过 runtime 访问
@tool
def search(query: str, runtime: ToolRuntime[Context]) -> str:
    max_depth = runtime.context.researcher_max_depth
    return perform_search(query, max_depth=max_depth)
```

### 识别调用者

当多个子代理共享工具时，通过 `lc_agent_name` 元数据区分：

```python
@tool
def shared_tool(query: str, runtime: ToolRuntime) -> str:
    agent_name = runtime.config.get("metadata", {}).get("lc_agent_name")
    if agent_name == "fact-checker":
        return strict_mode(query)
    return normal_mode(query)
```

## 故障排除

### 子代理未被调用

**原因**：描述不够具体，主代理不认为需要委派。

**解决**：
1. 使描述更具体，说明何时使用
2. 在主代理 system_prompt 中指示委派：
   ```
   重要：对于复杂任务，使用 task() 工具委派给子代理。
   这能保持上下文干净并改善结果。
   ```

### 上下文仍然膨胀

**解决**：
1. 在子代理 prompt 中明确要求简洁输出（如"500 字以内"）
2. 对大量数据使用文件系统暂存，子代理只返回摘要

### 选错子代理

**解决**：在描述中明确区分各子代理的能力边界：

```python
{
    "name": "quick-researcher",
    "description": "简单的、只需 1-2 次搜索的研究。用于基本事实查询。",
},
{
    "name": "deep-researcher",
    "description": "复杂的、需要多次搜索和综合分析的深度研究。用于综合报告。",
}
```
