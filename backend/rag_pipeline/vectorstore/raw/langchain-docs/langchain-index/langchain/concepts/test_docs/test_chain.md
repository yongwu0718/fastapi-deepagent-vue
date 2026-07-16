# Testing

> 这是测试 LangChain Agent 的**胖索引**，覆盖单元测试、集成测试与轨迹评估三大策略，以及工具链、模拟技术与最佳实践。
> 阅读本文档可一次性掌握 Agent 测试领域的全部概念及其关联，为构建稳定、可验证的生产级 Agent 提供决策支撑。

---

## 概念全景

Agent 测试需要应对 LLM 的非确定性和多组件串行带来的不稳定性。测试策略从快速、确定性的单元测试，到验证真实交互的集成测试，再到评估端到端轨迹的评估体系，层层递进。

| 测试层次               | 目标                                                         | 关键方法 / 工具                                   |
| ---------------------- | ------------------------------------------------------------ | ------------------------------------------------- |
| **Unit tests**         | 独立、快速地验证单个节点、工具或逻辑分支                     | 模拟聊天模型 (`FakeChatModel`)、`InMemorySaver`、`InMemoryStore` |
| **Integration tests**  | 确认真实 API 调用、凭证、schema 及组件协作正确               | 真实 LLM API、`SqliteSaver`、环境隔离             |
| **Evals / Trajectory** | 评估 Agent 决策路径与最终输出的质量                         | 确定性匹配、LLM-as-judge、LangSmith                |

核心决策点：**何时使用模拟 vs 真实服务、如何构建可重复的测试环境、如何评估非确定性输出的质量**。

---

## 1. 单元测试

通过模拟聊天模型和内存持久化，将 Agent 的各个部分隔离测试。主要验证状态转换、工具调用逻辑和条件路由。

### 模拟模型

使用 `FakeChatModel` 或自定义模拟来预设 LLM 响应，使测试确定化：

```python
from langchain_core.language_models.fake_chat_models import FakeChatModel

fake_model = FakeChatModel(
    responses=["I am a mocked response"]
)
```

### 模拟存储与状态

- **Checkpointer**: `InMemorySaver` 用于测试线程级持久化。
- **Store**: `InMemoryStore` 用于长期记忆的读写测试。
- 通过 `thread_id` 隔离不同测试用例。

### 测试节点

将单个节点函数作为纯函数测试，传入特定状态，断言返回的更新字典或 `Command`：

```python
def test_node_a():
    state = {"messages": [HumanMessage(content="hi")]}
    result = node_a(state)
    assert result["messages"][0].content == "expected"
```

### 测试工具

利用 `ToolRuntime` 的模拟实现，注入预设的 `state`、`store` 和 `context`，验证工具逻辑与副作用。

---

## 2. 集成测试

使用真实 API 或受控的外部依赖，验证 Agent 的完整执行流程。

### 环境隔离

- 使用专用于测试的 API 密钥，并设置使用限制。
- 通过 `SqliteSaver` 将持久化隔离到临时数据库文件。
- 利用环境变量切换端点或模拟外部服务。

### 验证点

- **凭证与 schema**：确认工具输入输出与真实 API 一致。
- **延迟与超时**：设置合理的 `timeout` 和 `max_retries`，确保在可接受范围内。
- **错误处理**：测试重试策略、错误处理器是否按预期工作。

### 组织测试

- 将集成测试标记为 `pytest.mark.integration`，便于单独运行。
- 使用 `dotenv` 管理敏感信息，避免硬编码。

---

## 3. 轨迹评估 (Evals)

评估 Agent 的决策序列和最终输出质量，可通过确定性规则或 LLM 评判实现。

### 确定性匹配

对可预测的输出（如工具名称、参数、最终答案结构）进行精确断言：

```python
def test_agent_uses_calculator():
    result = agent.invoke(...)
    last_msg = result["messages"][-1]
    assert "42" in last_msg.content
```

### LLM-as-judge

使用另一个 LLM 评估输出是否满足定性标准（如准确性、无害性）。适合主观指标。

### LangSmith 集成

- 将评估脚本与 LangSmith 连接，记录每次运行的轨迹和指标。
- 对比不同实验（A/B 测试），跟踪指标随时间变化。

---

## 4. 关键约束与最佳实践

- **模拟要精准**：`FakeChatModel` 应按调用顺序返回预设响应，否则需使用更复杂的 mock。
- **隔离副作用**：单元测试中避免真实网络、文件系统调用；集成测试中确保测试数据可被清理。
- **管理密钥**：使用 CI/CD 的秘密管理，避免凭据泄露。
- **控制成本**：集成测试可能产生 API 费用，应限制输入长度和调用次数。
- **评估需持续**：将 evals 集成到 CI 流程，每次变更后自动运行。

---

## 5. 与全局概念的关联

- **模型 (Models)**：测试中可替换为模拟模型，以消除非确定性。
- **工具 (Tools)**：通过模拟 `ToolRuntime` 测试工具，确保其正确读写状态和存储。
- **持久化 (Persistence)**：`InMemorySaver` 和 `InMemoryStore` 是测试环境的标准配置。
- **中断 (Interrupts)**：模拟 `Command(resume=...)` 测试中断恢复流程。
- **容错 (Fault tolerance)**：测试重试策略、超时和错误处理器。
- **上下文工程**：验证动态提示、消息注入等中间件是否正确修改了模型上下文。
- **LangSmith**：统一评估和监控平台，连接测试与生产。

---

## 链接原文

### 语义检索（聚焦查询）

- `FakeChatModel InMemorySaver 单元测试` → 模拟环境搭建
- `集成测试 凭证 schema 延迟 timeout` → 真实交互验证
- `eval LLM judge 轨迹 确定性匹配` → 评估方法
- `LangSmith 实验对比` → 平台集成
- `测试工具 ToolRuntime 模拟` → 工具测试

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 测试`、`### 单元测试`、`### 集成测试`），可用 `read_file` 精确定位对应章节。