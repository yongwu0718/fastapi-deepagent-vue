"""
月度支出瀑布图 (Waterfall Chart)
可视化全周期支出因果链条：收入 → 房租 → 分期 → 通勤 → 其他 → 净结余
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

# ── 读取数据 ──────────────────────────────────────────────
data_path = os.path.join(os.path.dirname(__file__), "output", "monthly_3layer.json")
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

summary = data["summary"]

# ── 提取刚性固定明细（全周期汇总） ────────────────────────
# 从 rigid_fixed_monthly 累积各 item
rigid_items_accum = {}
for m in data["rigid_fixed_monthly"]:
    for item in m["items"]:
        name = item["name"]
        rigid_items_accum[name] = rigid_items_accum.get(name, 0) + item["amount"]

# 合并小项为"其他刚性固定"
rent = rigid_items_accum.get("房租", 0)
installment = rigid_items_accum.get("手机分期", 0)
commute = rigid_items_accum.get("嗖狗出行", 0)
meituan = rigid_items_accum.get("美团", 0)
meituan_zb = rigid_items_accum.get("美团众包", 0)
electric_company = rigid_items_accum.get("济南供电公司", 0)
electric = rigid_items_accum.get("电费", 0)
other_rigid = meituan + meituan_zb + electric_company + electric

# ── 构建瀑布图数据 ────────────────────────────────────────
income = summary["total_income"]          # 总收入口径 23558.89
real_income_val = 14879.89                # 真实收入（去转账）
transfer_income = income - real_income_val  # 转账收入 8679.0
total_expense = summary["total_expense"]   # 27304.64
rigid_fixed = summary["rigid_fixed_total"] # 13740.46
rigid_necessary = summary["rigid_necessary_total"]  # 2235.72
flexible = summary["flexible_total"]       # 11328.46
net_val = summary["net"]                   # -3745.75

# ── 弹性可选汇总（全周期叠加） ──────────────────────────────
FLEX_ALL = ["食品", "饮品", "购物消费", "服饰鞋包", "数码电子", "娱乐休闲", "医疗健康", "其他支出"]
FLEX_COLORS = {"食品": "#E24A33", "饮品": "#F4A261", "其他弹性": "#B0B0B0"}
flex_accum = {name: 0.0 for name in FLEX_ALL}
for fm in data["flexible_monthly"]:
    for cat in fm.get("category_breakdown", []):
        name = cat["category"]
        if name in flex_accum:
            flex_accum[name] += cat["amount"]

# 食品 + 饮品 单独显示，其余合并为"其他弹性"
flex_stack = []
if flex_accum["食品"] > 0:
    flex_stack.append(("食品", -flex_accum["食品"]))
if flex_accum["饮品"] > 0:
    flex_stack.append(("饮品", -flex_accum["饮品"]))
other_flex_sum = sum(flex_accum[name] for name in FLEX_ALL[2:])
if other_flex_sum > 0:
    flex_stack.append(("其他弹性", -other_flex_sum))

# 瀑布列定义（不含收入列）
# col_specs: (type, data)  type: "bar" value | "stack" [(name, val)] | "net"
col_specs = [("bar", -rent), ("bar", -installment), ("bar", -commute),
             ("bar", -other_rigid), ("bar", -rigid_necessary),
             ("stack", flex_stack), ("net", None)]

n_body = len(col_specs)
n = n_body + 1

# 支出柱 bottoms/tops
bottoms_body = []
tops_body = []
running = income
for i, spec in enumerate(col_specs):
    t, d = spec
    if t == "net":
        bottoms_body.append(0)
        tops_body.append(running)
    elif t == "bar":
        v = d
        bottoms_body.append(running)
        running += v
        tops_body.append(running)
    elif t == "stack":
        total_v = sum(item[1] for item in d)
        bottoms_body.append(running)
        running += total_v
        tops_body.append(running)
heights_body = [t - b for t, b in zip(tops_body, bottoms_body)]

# ── 绘图 ───────────────────────────────────────────────────
plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(16, 8))
fig.patch.set_facecolor("#FAFAFA")
ax.set_facecolor("#FAFAFA")

x_all = np.arange(n)
bar_width = 0.6

color_real = "#3A7BD5"       # 深蓝 — 真实收入
color_transfer = "#8ECAE6"   # 浅蓝 — 转账收入
color_deduct = "#DD4444"
color_net = "#55A868" if running >= 0 else "#CC3333"

# ── 第0列：堆积收入柱 ──────────────────────────────────────
ax.bar(0, real_income_val, bar_width, bottom=0, color=color_real,
       edgecolor="white", linewidth=1.2, zorder=3)
ax.bar(0, transfer_income, bar_width, bottom=real_income_val,
       color=color_transfer, edgecolor="white", linewidth=1.2, zorder=3)

ax.text(0, real_income_val / 2, f"真实收入\n{real_income_val:,.0f}元",
        ha="center", va="center", fontsize=9, fontweight="bold", color="white")
ax.text(0, real_income_val + transfer_income / 2, f"转账收入\n{transfer_income:,.0f}元",
        ha="center", va="center", fontsize=9, fontweight="bold", color="#1A3A5C")
ax.text(0, income, f"总收入 {income:,.0f}元",
        ha="center", va="bottom", fontsize=11, fontweight="bold", color="#1A3A5C")

# ── 支出柱（x=1~n-1） ──────────────────────────────────────
for i, spec in enumerate(col_specs):
    xi = i + 1
    t, d = spec
    btm = bottoms_body[i]
    h = heights_body[i]

    if t == "net":
        ax.bar(xi, h, bar_width, bottom=btm, color=color_net,
               edgecolor="white", linewidth=1.2, zorder=3)
        if abs(h) > 50:
            ax.text(xi, btm + h / 2, f"{running:+,.0f}元",
                    ha="center", va="center", fontsize=10, fontweight="bold",
                    color="white" if abs(h) > 500 else "#333333")

    elif t == "bar":
        ax.bar(xi, h, bar_width, bottom=btm, color=color_deduct,
               edgecolor="white", linewidth=1.2, zorder=3)
        if abs(d) > 50:
            ax.text(xi, btm + h / 2, f"{abs(d):,.0f}元",
                    ha="center", va="center", fontsize=10, fontweight="bold",
                    color="white" if abs(h) > 500 else "#333333")

    elif t == "stack":
        stack_top = btm
        for cat_name, cat_v in d:
            abs_h = abs(cat_v)
            ax.bar(xi, -abs_h, bar_width, bottom=stack_top,
                   color=FLEX_COLORS.get(cat_name, "#CCC"),
                   edgecolor="white", linewidth=0.5, zorder=3)
            if abs_h > 200:
                ax.text(xi, stack_top - abs_h / 2, f"{cat_name}\n{abs_h:,.0f}元",
                        ha="center", va="center", fontsize=7, fontweight="bold",
                        color="white" if cat_name == "食品" else "#222222")
            stack_top -= abs_h

# ── 瀑布连线 ──────────────────────────────────────────────
prev_top = income
for i in range(n_body):
    curr_top = tops_body[i]
    ax.plot([i + bar_width / 2, i + 1 - bar_width / 2],
            [prev_top, prev_top], color="#888888", linewidth=1, linestyle="--", alpha=0.6)
    ax.plot([i + 1 - bar_width / 2, i + 1 - bar_width / 2],
            [prev_top, curr_top], color="#888888", linewidth=1, linestyle="--", alpha=0.6)
    prev_top = curr_top

# ── X轴标签 ────────────────────────────────────────────────
all_labels = ["总收入",
    f"房租\n-{rent:,.0f}元",
    f"手机分期\n-{installment:,.0f}元",
    f"嗖狗出行\n-{commute:,.0f}元",
    f"其他刚性固定\n-{other_rigid:,.0f}元",
    f"刚性必要\n-{rigid_necessary:,.0f}元",
    f"弹性可选\n-{flexible:,.0f}元",
    "净结余\n{:.0f}元".format(net_val) if net_val >= 0 else "净结余\n-{:.0f}元".format(abs(net_val)),
]
ax.set_xticks(x_all)
ax.set_xticklabels(all_labels, fontsize=11)

# ── 右侧标注三大项占比 ────────────────────────────────────
total_expense_label = f"总支出 {total_expense:,.0f}元"
rent_pct = rent / total_expense * 100
install_pct = installment / total_expense * 100
commute_pct = commute / total_expense * 100
top3_pct = rent_pct + install_pct + commute_pct

annotation_text = (
    f"三大刚性支出合计: {top3_pct:.0f}%\n"
    f"├ 房租: {rent_pct:.1f}%  ({rent:,.0f}元)\n"
    f"├ 手机分期: {install_pct:.1f}%  ({installment:,.0f}元)\n"
    f"└ 通勤: {commute_pct:.1f}%  ({commute:,.0f}元)"
)
ax.text(0.98, 0.97, annotation_text, transform=ax.transAxes,
        fontsize=10, verticalalignment="top", horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.6", facecolor="#FFF8E1", edgecolor="#E6C300", alpha=0.9))

# ── 布局美化 ───────────────────────────────────────────────
ax.set_ylabel("金额 (元)", fontsize=13, labelpad=10)
ax.set_title("月度支出瀑布图 — 总收入 → 刚性支出 → 结余", fontsize=17, fontweight="bold", pad=20)

# Y 轴格式化
ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}元"))
ax.yaxis.set_major_locator(mticker.MaxNLocator(8))

# 添加 0 基线
ax.axhline(y=0, color="#333333", linewidth=1.5, linestyle="-", zorder=2)

# 网格
ax.grid(axis="y", linestyle="--", alpha=0.3, zorder=1)
ax.set_axisbelow(True)

# 边框
for spine in ["top", "right"]:
    ax.spines[spine].set_visible(False)

plt.tight_layout()

# ── 保存 ───────────────────────────────────────────────────
output_dir = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(output_dir, exist_ok=True)
output_path = os.path.join(output_dir, "waterfall_chart.png")
fig.savefig(output_path, dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
print(f"✅ 瀑布图已保存: {output_path}")
plt.close(fig)
