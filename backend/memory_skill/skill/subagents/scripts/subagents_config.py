"""
Subagent 配置文件 —— 通过 Python 字典定义子代理列表。

每个子代理字典支持以下字段（参考 DeepAgents SubAgent 规范）：

- name: str           必需，子代理唯一标识符
- description: str    必需，描述子代理功能（主代理据此决定何时委派）
- system_prompt: str  必需，子代理指令
- tools: list[Callable]  可选，子代理可用工具；不填则继承主代理工具
- model: str | BaseChatModel  可选，覆盖主代理模型
- middleware: list    可选，额外中间件
- skills: list[str]   可选，技能源路径

使用方式：
- 注释掉 subagents 列表中的对应条目即可禁用某个子代理
- 修改后调用 POST /settings/rebuild 或重启服务即可生效
"""

from backend.core.models.model_factory import llm_ali
from backend.core.utils import (
    analyze_billing,
    analyze_monthly,
    analyze_expense,
    analyze_monthly_categories,
    save_bill,
)

# ═══════════════════════════════════════════
#  子代理定义
# ═══════════════════════════════════════════

bill_analyzer = {
    "name": "bill-analyzer",
    "description": (
        "分析个人账单数据：收支总览、消费分类排名、各平台支出占比、"
        "食品消费习惯追踪、基于历史趋势的下月预算预测。"
        "当用户询问花了多少钱、钱花在哪、消费是否健康、下月该预算多少时使用此代理。"
    ),
    "system_prompt": (
        "你是一位专业的个人财务分析师，负责分析用户的账单数据。\n\n"
        "工作流程：\n"
        "1. 使用 analyze_billing 获取用户的整体收支概览\n"
        "2. 使用 analyze_monthly 查看月度收支变化趋势\n"
        "3. 使用 analyze_expense 获取消费分类明细\n"
        "4. 使用 analyze_monthly_categories 分析各类消费的月度变化\n"
        "5. 需要时使用 save_bill 保存分析结果\n\n"
        "输出要求：\n"
        "- 先给出核心数据摘要（总收入、总支出、结余）\n"
        "- 再给出分类排名和趋势分析\n"
        "- 最后给出建议或预警\n"
        "- 保持回复简洁，控制在 500 字以内\n"
    ),
    "tools": [
        analyze_billing,
        analyze_monthly,
        analyze_expense,
        analyze_monthly_categories,
        save_bill,
    ],
    "model": llm_ali,
}

# ═══════════════════════════════════════════
#  激活的子代理列表
# ═══════════════════════════════════════════
# 注释掉对应行即可禁用某个子代理

subagents = [
    bill_analyzer,
]
