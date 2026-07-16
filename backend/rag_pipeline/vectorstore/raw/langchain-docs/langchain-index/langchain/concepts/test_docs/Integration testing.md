# 集成测试 (Integration Testing)

> 这是 LangChain Agent **集成测试** 的胖索引，覆盖测试组织、密钥管理、断言策略、成本控制、VCR 录制重放等关键实践。
> 阅读本文档可一次性掌握集成测试的全部概念及其关联，为构建可靠、可维护的 Agent 测试套件提供决策支撑。

---

## 概念全景

集成测试通过真实的网络调用验证 Agent 与 LLM API 及外部服务的协作。与单元测试不同，它接受 LLM 的非确定性，并侧重于确认组件连接、凭证有效性和响应结构，而非确切输出。

| 维度               | 描述                                                         | 关键工具 / 方法                                   |
| ------------------ | ------------------------------------------------------------ | ------------------------------------------------- |
| **测试组织**       | 使用 `pytest` marker 将集成测试与单元测试分离，按需运行       | `@pytest.mark.integration`、配置文件               |
| **密钥管理**       | 从环境变量加载 API 密钥，`conftest.py` 中跳过未配置的测试     | `.env`、`python-dotenv`、CI secrets                |
| **断言策略**       | 验证结构（消息类型、工具调用名称、参数形状），而非精确文本   | `isinstance`、`hasattr`、`tool_calls` 遍历          |
| **成本与延迟控制** | 使用小模型、限制 `max_tokens`、限制测试范围、选择性运行       | `gemini-3.1-flash-lite`、`model_kwargs`             |
| **录制重放**       | 通过 `vcrpy` / `pytest-recording` 录制 HTTP 交互，后续重放以减少成本与延迟 | `@pytest.mark.vcr()`、cassettes、过滤敏感头         |

核心决策点：**何时运行集成测试（CI/部署前）、如何设计断言以适应非确定性、是否使用 VCR 录制以加速回归**。

---

## 1. 测试组织

- 使用 `@pytest.mark.integration` 标记集成测试。
- 在 `pytest` 配置中将默认运行排除集成测试（`-m "not integration"`）。
- 通过 `pytest -m integration` 显式执行集成测试。

---

## 2. 密钥管理

- 始终从环境变量读取 API 密钥，严禁硬编码。
- 在 `conftest.py` 中使用 `autouse` fixture 检查密钥是否存在，若无则 `pytest.skip`。
- 本地开发通过 `.env` 文件加载，`.gitignore` 忽略此文件；CI 通过平台 secrets 注入。

---

## 3. 断言策略

- 不依赖精确输出字符串，改为验证：
  - 消息类型（如最后一条是 `AIMessage`）
  - 工具调用名称和参数形状
  - 消息数量范围
- 示例：遍历 `result["messages"]` 检查是否存在 `tool_calls`，并确认目标工具被调用。
- 如需更宽松的匹配，可使用 AgentEvals 提供的 `unordered`、`superset` 模式。

---

## 4. 降低成本和延迟

| 手段                   | 具体做法                                                     |
| ---------------------- | ------------------------------------------------------------ |
| 使用更小模型           | `gemini-3.1-flash-lite` 等轻量模型                           |
| 限制输出长度           | `model_kwargs={"max_tokens": 256}`                            |
| 缩小测试范围           | 每个测试只验证一种行为，避免串联多个 LLM 调用的端到端测试   |
| 选择性运行             | 仅在 CI 或部署前运行集成测试                                 |

---

## 5. 录制与重放 (VCR)

通过 `vcrpy` + `pytest-recording` 录制真实 HTTP 交互到 YAML cassette，后续运行直接重放，消除网络延迟与 API 费用。

- 在 `conftest.py` 中配置过滤敏感头（`authorization`、`x-api-key` 等）。
- 使用 `@pytest.mark.vcr()` 标记需录制的测试。
- 首次运行录制，后续运行重放；若修改 prompts 或工具，删除对应 cassette 重新录制。

---

## 6. 关键约束与最佳实践

- **分离执行**：单元测试与集成测试必须能独立运行，避免 CI 反馈过慢。
- **密钥安全**：绝不将密钥提交到仓库，CI 使用加密的 secrets。
- **断言稳健**：针对结构而非内容，避免因模型输出细微变化导致测试频繁失败。
- **成本意识**：录制模式显著降低重复运行的成本，但录制文件需随代码演进及时更新。
- **选择性录制**：仅对稳定且高频运行的集成测试使用 VCR，避免管理大量过时 cassette。

---

## 7. 与全局概念的关联

- **模型 (Models)**：集成测试直接调用真实 LLM，验证模型选择、参数传递和响应结构。
- **工具 (Tools)**：验证工具调用是否正确触发，参数是否与真实 API 兼容。
- **持久化 (Persistence)**：集成测试可使用真实 checkpointer（如 `SqliteSaver`）确认状态持久化行为。
- **上下文工程**：通过真实对话验证动态提示、消息注入和工具筛选的最终效果。
- **评估 (Evals)**：集成测试可与轨迹评估结合，在真实调用后通过 LLM-as-judge 或确定性规则进行质量评估。
- **容错 (Fault tolerance)**：集成测试是验证重试、超时和错误处理器实际表现的关键环节。

---

## 链接原文

### 语义检索（聚焦查询）

- `pytest.mark.integration addopts` → 测试分离配置
- `API keys 环境变量 conftest skip` → 密钥管理
- `断言 结构 工具调用 isinstance AIMessage` → 断言策略
- `max_tokens 小模型 成本` → 成本控制
- `vcrpy pytest-recording cassette filter_headers` → VCR 录制重放

### 标题路径兜底

语义检索返回的片段均携带原文标题路径（如 `## 分离 unit tests 和 integration tests`、`## 管理 API keys`、`## 录制并重放 HTTP calls`），可用 `read_file` 精确定位对应章节。