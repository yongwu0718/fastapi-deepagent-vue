# 下月预算预测

## 第一阶段：多表组合数据准备与异常清洗

1. **并行调用工具**：`analyze_monthly` + `analyze_billing` + `analyze_monthly_categories`（可选加 `analyze_expense`）

2. **数据完整性校验**：
   - 刚性固定项环比下降 > 50% → ⚠️ 数据缺口
   - 食品占比 45%+ 且刚性固定暴跌 → 总支出失真
   - 收入 < 历史月均 70% → ⚠️ 收入断崖预警

## 第二阶段：分层计算

将清洗后的数据传入 `eval` 执行计算：

```javascript
const rigidFixedMonthly = [/* 从返回数据提取 */];
const rigidNecessaryMonthly = [/* 从返回数据提取 */];
const flexibleMonthly = [/* 从返回数据提取 */];

// 刚性固定：取最近3月中位数剔除异常
const lastRigid = rigidFixedMonthly[rigidFixedMonthly.length - 1].total;
const prevRigid = rigidFixedMonthly[rigidFixedMonthly.length - 2]?.total || lastRigid;
const rigidFixed = (lastRigid / prevRigid < 0.6) 
  ? (rigidFixedMonthly.slice(-3).reduce((s, m) => s + m.total, 0) / 3) 
  : lastRigid;
const rigidFixedPrev = prevRigid;

// 刚性必要：最近3月加权 (0.5/0.3/0.2)
const necMonths = rigidNecessaryMonthly.slice(-3).filter(m => m.total > 0);
const rigidNecessary = necMonths.length === 3
  ? necMonths[2].total * 0.5 + necMonths[1].total * 0.3 + necMonths[0].total * 0.2
  : (necMonths.length > 0 ? necMonths.reduce((s, m) => s + m.total, 0) / necMonths.length : 0);
const rigidNecessaryPrev = rigidNecessaryMonthly[rigidNecessaryMonthly.length - 1]?.total || 0;

// 弹性可选：最近3月均值
const flexMonths = flexibleMonthly.slice(-3);
let flexBase = flexMonths.reduce((s, m) => s + m.total, 0) / flexMonths.length;
const flexPrev = flexibleMonthly[flexibleMonthly.length - 1].total;
const flexIdeal = flexBase * 0.85;

// 趋势判断（近3月 vs 前3月）
const flexTrend = flexibleMonthly.length >= 6
  ? (() => {
      const recent = flexibleMonthly.slice(-3).reduce((s, m) => s + m.total, 0) / 3;
      const older = flexibleMonthly.slice(-6, -3).reduce((s, m) => s + m.total, 0) / 3;
      return recent / older > 1.15 ? '↑上升' : recent / older < 0.85 ? '↓下降' : '→平稳';
    })()
  : '数据不足';

{
  rigidFixed, rigidFixedPrev,
  rigidNecessary, rigidNecessaryPrev,
  flexBase, flexIdeal, flexPrev, flexTrend,
  totalAlgorithm: rigidFixed + rigidNecessary + flexBase,
  isAnomaly: lastRigid / prevRigid < 0.6
}
```

## 第三阶段：双轨输出

若存在异常缺口，必须给出两套预算：算法基准 + 人工修正。输出模板见 `assets/report_template.md`。

## 预测原则

1. 数据来源必须真实，所有数字来自工具 JSON + `eval` 计算
2. 必须组合校验，禁止只用 `analyze_monthly` 做黑盒运算
3. 异常必须暴露，月度波动超过 ±40% 需高亮提示
4. 输出双轨制，最终决策权留给用户
