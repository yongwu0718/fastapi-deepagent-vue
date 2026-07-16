# 测试

> 测试 LangChain agent 的策略，包括 unit tests、integration tests 和 trajectory evaluations。

Agentic 应用让 LLM 自行决定解决问题的后续步骤。这种灵活性很强大，但模型的黑盒特性让我们很难预测 agent 某个部分的调整会如何影响整体。要构建可用于生产环境的 agent，全面的测试至关重要。

以下是几种测试 agent 的方法：

* **Unit tests** 使用内存中的模拟对象，独立地测试 agent 中规模较小、可确定的部分，以便快速、确定地断言确切行为。
* **Integration tests** 使用真实的网络调用来测试 agent，确认各组件能协同工作、凭证和 schema 一致，并且延迟在可接受范围内。
* **Evals** 借助 evaluator 评估 agent 的执行轨迹，可通过确定性匹配或 LLM 作为评判 (LLM judge) 来实现。

由于 agentic 应用需要将多个组件串联在一起，并且必须应对 LLM 的非确定性带来的不稳定性，因此往往会更多地依赖集成测试。

使用 LangSmith 大规模运行评估、跟踪结果随时间的变化并对比实验。请参阅“评估 LLM 应用”入门指南。

通过模拟聊天模型并使用内存持久化，在不进行 API 调用的情况下测试 agent 逻辑。

使用真实的 LLM API 测试您的 agent。组织测试、管理密钥、处理不稳定性并控制成本。

通过确定性匹配或 LLM-as-judge evaluator 来评估 agent 轨迹。