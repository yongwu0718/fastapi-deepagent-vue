# 分析模式详解

根据用户问题，从以下三类模式中选择，优先推荐组合调用：

## 模式 A：快速总览

**触发**：用户问"花了多少/钱去哪了"

**工具组合**：`analyze_billing`（看结构） + `analyze_expense`（看商户细节）

**适用场景**：给出整体画像和 TOP 消费点

---

## 模式 B：时序趋势与异常监控

**触发**：用户问"这个月怎么超了/哪个月花最多"

**工具组合**：`analyze_monthly`（看三层波动） + `analyze_monthly_categories`（看类别此消彼长）

**适用场景**：发现月度突变、判断哪类支出失控

---

## 模式 C：预算预测与下月规划

**触发**：用户问"下个月该预算多少/如何省钱"

**工具组合**：必须组合 `analyze_monthly` + `analyze_billing` + `analyze_monthly_categories`，强烈建议加调 `analyze_expense`

**重要**：单表预测不可靠，组合校验是底线。详见 `references/budget_prediction.md`。
