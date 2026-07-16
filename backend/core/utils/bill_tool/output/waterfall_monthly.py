"""
逐月支出瀑布图 — 总收入堆积柱 → 支出链 → 弹性可选堆积柱 → 净结余
"""
import json
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np

plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei", "WenQuanYi Micro Hei"]
plt.rcParams["axes.unicode_minus"] = False

# ── 读取数据 ──────────────────────────────────────────────
data_path = os.path.join(os.path.dirname(__file__), "output", "monthly_3layer.json")
with open(data_path, "r", encoding="utf-8") as f:
    data = json.load(f)

monthly = data["monthly_income_expense"]
rigid_detail = {m["month"]: m for m in data["rigid_fixed_monthly"]}
flex_detail = {m["month"]: m for m in data["flexible_monthly"]}

RIGID_ITEM_NAMES = ["房租", "手机分期", "嗖狗出行", "美团", "美团众包", "济南供电公司", "电费"]

# 弹性可选堆积顺序（底部→顶部）：食品 → 饮品 → 购物消费 → 服饰鞋包 → 数码电子 → 娱乐休闲 → 医疗健康 → 其他支出
FLEX_STACK_ORDER = ["食品", "饮品", "购物消费", "服饰鞋包", "数码电子", "娱乐休闲", "医疗健康", "其他支出"]
FLEX_COLORS = {
    "食品":   "#E24A33",  # 红
    "饮品":   "#F4A261",  # 橙
    "其他弹性": "#B0B0B0",  # 灰
}

output_dir = r"F:\index_rag\backend\memory_skill\skill\personal-bill-analyze\scripts\output"

for month_entry in monthly:
    month = month_entry["month"]
    total_income = month_entry["total_income"]
    real_income = month_entry["real_income"]
    transfer_income = total_income - real_income
    rigid_necessary = month_entry["rigid_necessary"]
    flexible = month_entry["flexible"]

    # ── 刚性固定明细 ──────────────────────────────────────
    rd = rigid_detail.get(month, {})
    rigid_item_map = {name: 0.0 for name in RIGID_ITEM_NAMES}
    for it in rd.get("items", []):
        rigid_item_map[it["name"]] = it["amount"]

    rent_val = rigid_item_map["房租"]
    phone_val = rigid_item_map["手机分期"]
    commute_val = rigid_item_map["嗖狗出行"]
    other_rigid = sum(rigid_item_map[name] for name in RIGID_ITEM_NAMES[3:])

    # ── 弹性可选明细 ──────────────────────────────────────
    fd = flex_detail.get(month, {})
    flex_cat_map = {name: 0.0 for name in FLEX_STACK_ORDER}
    for cat in fd.get("category_breakdown", []):
        flex_cat_map[cat["category"]] = cat["amount"]

    # ── 构建瀑布列（不含收入柱和弹性柱内部） ──────────────
    # col_specs: list of (label, is_single, value_or_list, is_net)
    col_specs = []  # (x_label, type, data)  type: "bar"|"stack"|"net"
    x_labels = [f"总收入\n{total_income:,.0f}元"]

    if rent_val > 0:
        col_specs.append(("bar", -rent_val))
        x_labels.append(f"房租\n-{rent_val:,.0f}元")
    if phone_val > 0:
        col_specs.append(("bar", -phone_val))
        x_labels.append(f"手机分期\n-{phone_val:,.0f}元")
    if commute_val > 0:
        col_specs.append(("bar", -commute_val))
        x_labels.append(f"嗖狗出行\n-{commute_val:,.0f}元")
    if other_rigid > 0:
        col_specs.append(("bar", -other_rigid))
        x_labels.append(f"其他刚性固定\n-{other_rigid:,.0f}元")
    if rigid_necessary > 0:
        col_specs.append(("bar", -rigid_necessary))
        x_labels.append(f"刚性必要\n-{rigid_necessary:,.0f}元")

    # 弹性可选：堆积（底部食品 + 饮品 + 其他弹性汇总）
    flex_stack = []
    food_val = flex_cat_map["食品"]
    drink_val = flex_cat_map["饮品"]
    other_flex = sum(flex_cat_map[name] for name in FLEX_STACK_ORDER[2:])  # 购物消费+服饰+数码+娱乐+医疗+其他
    if food_val > 0:
        flex_stack.append(("食品", -food_val))
    if drink_val > 0:
        flex_stack.append(("饮品", -drink_val))
    if other_flex > 0:
        flex_stack.append(("其他弹性", -other_flex))
    if flexible > 0:
        col_specs.append(("stack", flex_stack))
        x_labels.append(f"弹性可选\n-{flexible:,.0f}元")

    # 净结余
    col_specs.append(("net", 0))
    x_labels.append("净结余")

    # ── 计算每列的底部/顶部 ───────────────────────────────
    n = len(col_specs) + 1  # +1 for income
    running = total_income
    bottoms = []   # 每列总底部
    tops = []      # 每列总顶部
    for spec in col_specs:
        t = spec[0]
        if t == "net":
            bottoms.append(0)
            tops.append(running)
        elif t == "bar":
            v = spec[1]
            bottoms.append(running)
            running += v
            tops.append(running)
        elif t == "stack":
            total_v = sum(item[1] for item in spec[1])
            bottoms.append(running)
            running += total_v
            tops.append(running)

    heights = [t - b for t, b in zip(tops, bottoms)]

    # ── 绘图 ───────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(13, 7))
    fig.patch.set_facecolor("#FAFAFA")
    ax.set_facecolor("#FAFAFA")

    x_all = np.arange(n)
    bar_width = 0.55
    color_real = "#3A7BD5"
    color_transfer = "#8ECAE6"
    color_deduct = "#DD4444"
    color_net = "#55A868" if running >= 0 else "#CC3333"

    # ── 第0列：堆积收入 ───────────────────────────────────
    ax.bar(0, real_income, bar_width, bottom=0, color=color_real,
           edgecolor="white", linewidth=1.0, zorder=3)
    ax.bar(0, transfer_income, bar_width, bottom=real_income,
           color=color_transfer, edgecolor="white", linewidth=1.0, zorder=3)
    ax.text(0, real_income / 2, f"真实\n{real_income:,.0f}元",
            ha="center", va="center", fontsize=8, fontweight="bold", color="white")
    if transfer_income > 0:
        ax.text(0, real_income + transfer_income / 2, f"转账\n{transfer_income:,.0f}元",
                ha="center", va="center", fontsize=8, fontweight="bold", color="#1A3A5C")
    ax.text(0, total_income, f"{total_income:,.0f}元",
            ha="center", va="bottom", fontsize=10, fontweight="bold", color="#1A3A5C")

    # ── 第1~n-1列 ──────────────────────────────────────────
    for i, spec in enumerate(col_specs):
        xi = i + 1
        t = spec[0]
        btm = bottoms[i]
        h = heights[i]

        if t == "net":
            ax.bar(xi, h, bar_width, bottom=btm, color=color_net,
                   edgecolor="white", linewidth=1.0, zorder=3)
            label = f"{running:+,.0f}元" if abs(h) > 20 else ""
            if label:
                ax.text(xi, btm + h / 2, label, ha="center", va="center",
                        fontsize=10, fontweight="bold",
                        color="white" if abs(h) > 300 else "#333333")

        elif t == "bar":
            v = spec[1]
            ax.bar(xi, h, bar_width, bottom=btm, color=color_deduct,
                   edgecolor="white", linewidth=1.0, zorder=3)
            if abs(v) > 20:
                ax.text(xi, btm + h / 2, f"{abs(v):,.0f}元",
                        ha="center", va="center", fontsize=10, fontweight="bold",
                        color="white" if abs(h) > 300 else "#333333")

        elif t == "stack":
            # 堆积弹性可选 — 每段从上往下落
            stack_top = btm  # 瀑布运行值(较高点)
            for cat_name, cat_v in spec[1]:
                abs_h = abs(cat_v)
                ax.bar(xi, -abs_h, bar_width, bottom=stack_top,
                       color=FLEX_COLORS.get(cat_name, "#CCCCCC"),
                       edgecolor="white", linewidth=0.5, zorder=3)
                if abs_h > 30:
                    ax.text(xi, stack_top - abs_h / 2, f"{cat_name}\n{abs_h:,.0f}元",
                            ha="center", va="center", fontsize=6.5, fontweight="bold",
                            color="white" if cat_name == "食品" else "#222222")
                stack_top -= abs_h

    # ── 瀑布连线 ──────────────────────────────────────────
    prev_top = total_income
    for i in range(len(col_specs)):
        curr_top = tops[i]
        ax.plot([i + bar_width / 2, i + 1 - bar_width / 2],
                [prev_top, prev_top], color="#999999", linewidth=0.8,
                linestyle="--", alpha=0.5)
        ax.plot([i + 1 - bar_width / 2, i + 1 - bar_width / 2],
                [prev_top, curr_top], color="#999999", linewidth=0.8,
                linestyle="--", alpha=0.5)
        prev_top = curr_top

    # ── 布局 ───────────────────────────────────────────────
    ax.set_xticks(x_all)
    ax.set_xticklabels(x_labels, fontsize=9)
    ax.set_ylabel("金额 (元)", fontsize=12)
    ax.set_title(f"{month} 月度支出瀑布图", fontsize=15, fontweight="bold", pad=15)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"{v:,.0f}元"))
    ax.axhline(y=0, color="#333333", linewidth=1.2, zorder=2)
    ax.grid(axis="y", linestyle="--", alpha=0.25, zorder=1)
    ax.set_axisbelow(True)
    for spine in ["top", "right"]:
        ax.spines[spine].set_visible(False)
    plt.tight_layout()

    fname = f"waterfall_{month}.png"
    fig.savefig(os.path.join(output_dir, fname), dpi=180,
                bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"✅ {fname}")

print(f"\n🎉 全部 11 张逐月瀑布图已保存到: {output_dir}")
