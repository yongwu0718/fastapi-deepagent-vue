# Agent 评估 (Agent Evals)

> 这是 LangChain / AgentEvals 中 **Agent 评估** 的胖索引，覆盖轨迹匹配评估器（trajectory match）、LLM-as-judge 评估器、异步支持及 LangSmith 集成。
> 阅读本文档可一次性掌握 Agent 评估体系的全部概念及其关联，为持续衡量 Agent 质量与发现回归问题提供决策支撑。

---

## 概念全景

Agent 评估通过对 Agent 生成的完整消息和工具调用序列（trajectory）进行评分，量化其行为质量。与验证基础正确性的集成测试不同，评估关注“好不好”，并借助预构建的评估器实现自动化。

| 评估方法                    | 原理                                                         | 优点                               | 适用场景                         |
| --------------------------- | ------------------------------------------------------------ | ---------------------------------- | -------------------------------- |
| **Trajectory match**        | 将 Agent 轨迹与参考轨迹进行确定性比较，检查工具调用与消息结构 | 快速、零成本、确定性强            | 已知预期工具调用序列的场景       |
| **LLM-as-judge**            | 使用另一个 LLM 对 Agent 轨迹进行定性评分                     | 灵活，可评估推理质量，无需精确参考 | 开放域、需评估整体合理性的场景   |

四种轨迹匹配模式：

| 模式        | 匹配规则                                         | 典型用途                                   |
| ----------- | ------------------------------------------------ | ------------------------------------------ |
| `strict`    | 消息结构、工具调用顺序完全一致（内容可不同）     | 验证关键操作的顺序，如审批前必须查询       |
| `unordered` | 工具调用集合相同，但顺序无关                     | 信息检索场景，验证是否调用了所需工具       |
| `subset`    | Agent 的工具调用是参考的子集（无多余调用）       | 确保 Agent 不越权，仅使用允许的工具        |
| `superset`  | Agent 的工具调用包含参考的所有调用（可有多余）   | 验证最低要求的工具被调用，允许额外探索     |

核心决策点：**针对特定测试目标选择匹配模式、何时引入 LLM judge、是否提供参考轨迹、如何将评估结果持续集成到 LangSmith**。

---

## 1. Trajectory match 评估器

通过 `agentevals.trajectory.match.create_trajectory_match_evaluator` 创建，需要提供参考轨迹（消息列表）。不同模式控制比较方式。

- 可以进一步通过 `tool_args_match_mode` 和 `tool_args_match_overrides` 自定义工具参数的匹配规则（默认严格相等）。
- 适用于希望快速、无额外 API 费用的回归测试。

---

## 2. LLM-as-judge 评估器

通过 `create_trajectory_llm_as_judge` 创建，需指定评判模型（如 `"openai:o3-mini"`）和提示词。可使用预置提示：
- `TRAJECTORY_ACCURACY_PROMPT`（无参考轨迹）
- `TRAJECTORY_ACCURACY_PROMPT_WITH_REFERENCE`（提供参考轨迹）

评判器根据提示对轨迹质量打分，适合评估推理过程、回答完整性等主观维度。

---

## 3. 异步支持

所有评估器均提供异步版本：在创建函数名中 `create_` 后插入 `async`，如 `create_async_trajectory_match_evaluator`。可在异步测试或流程中使用 `await evaluator(...)`。

---

## 4. 与 LangSmith 集成

将评估结果记录到 LangSmith 以跟踪实验效果：

- **pytest 集成**：使用 `@pytest.mark.langsmith` 标记测试，通过 `langsmith.testing` 记录输入、输出和参考，并调用评估器。
- **`evaluate` 函数**：创建 LangSmith 数据集（含输入/输出字段），使用 `client.evaluate` 批量运行并收集评分。

---

## 5. 关键约束与最佳实践

- **参考轨迹的管理**：轨迹匹配依赖准确的参考；一旦修改 Agent 行为（如改 prompt），参考可能需要更新。
- **LLM judge 的成本与延迟**：每次评估都会调用一次 LLM，产生费用和延迟，适合少量定性检查。
- **确定性优先**：优先使用轨迹匹配进行回归测试；在无法穷尽预期轨迹时再用 LLM judge。
- **异步版本对齐**：如果 Agent 自身使用 `ainvoke`，应使用异步评估器以避免阻塞事件循环。
- **评分标准化**：evaluator 返回的 `score` 通常为布尔值或连续值，确保统一解释。

---

## 6. 与全局概念的关联

- **测试 (Testing)**：评估是测试体系的上层，与单元测试、集成测试共同构成质量保障金字塔。
- **模型 (Models)**：LLM-as-judge 依赖另一个模型，需考虑评判模型的质量、偏差与成本。
- **工具 (Tools)**：轨迹匹配的核心是验证工具调用，与工具定义、参数模式紧密相关。
- **上下文工程**：更改提示、工具筛选等会影响轨迹，评估能捕捉这些变化带来的影响。
- **LangSmith**：作为实验跟踪和评估平台，与评估器深度集成，提供可视化比较。

---

## 链接原文

### 语义检索（聚焦查询）

- `trajectory match evaluator strict unordered subset superset` → 四种匹配模式
- `LLM-as-judge create_trajectory_llm_as_judge prompt` → LLM 评判
- `异步 async evaluator` → 异步评估器
- `LangSmith pytest langsmith evaluate` → 平台集成
- `tool_args_match_mode` → 自定义工具参数匹配

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## Trajectory match evaluator`、`### strict mode`、`## LLM-as-judge evaluator`），可用 `read_file` 精确定位对应章节。