"""清洗微信支付账单流水 → 标准记账格式（对齐 common.py 分类约束）。

源文件：微信支付账单流水文件(YYYYMMDD-YYYYMMDD)_*.xlsx
输出  ：清洗后的 Excel / CSV，字段：
        消费名称, 消费大类, 消费细类, 类型(支出/收入), 金额, 支付平台, 日期, 消费类型, 备注

清洗规则：
1. 跳过文件头部说明行，仅取"交易时间..."表头之后的明细。
2. 剔除「已全额退款」的对冲记录（支出+收入同时存在，净影响为 0）。
3. 交易对方去掉括号昵称（如 "白如滨 (大白)" → "白如滨"）。
4. 支付平台统一为"微信"（本账单为微信零钱流水）。
5. 按商品/交易对方映射到 common.py 的 9 大消费类 + 细类 + 消费类型。
6. 金额取绝对值，方向由 类型 列区分。
"""
import os
import re
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", ".."))    # billing_analyze 目录

# ─── 默认输入/输出路径（可被命令行参数覆盖） ───
DEFAULT_SRC = os.path.join(SRC_DIR, "微信支付账单流水文件(20260718-20260807)_20260807230559.xlsx")
DEFAULT_OUT_XLSX = os.path.join(SRC_DIR, "微信账单_清洗后.xlsx")
DEFAULT_OUT_CSV = os.path.join(SRC_DIR, "微信账单_清洗后.csv")

# ─── 消费类型 ───
TYPE_RIGID_FIXED = "刚性固定"
TYPE_RIGID_NEC = "刚性必要"
TYPE_FLEX = "弹性支出"
TYPE_UNKNOWN = "未分类"

# ─── 关键词 → (大类, 细类, 消费类型) 映射（按优先级，先匹配先得） ───
RULES = [
    # 交通
    (("汽车站", "客运", "大巴", "公交", "地铁", "打车"), ("交通", "大巴", TYPE_RIGID_NEC)),
    # 餐饮（饮料）
    (("售水站", "水站", "饮水"), ("餐饮", "饮料", TYPE_FLEX)),
    # 超市/便利店/京东 → 购物·日用消耗（先于美团外卖判断）
    (("超市", "便利", "京东便利店", "京东", "百货", "商超"), ("购物", "日用消耗", TYPE_FLEX)),
    # 美团等外卖平台餐饮订单（商品含"美团App"）→ 餐饮·外卖
    (("美团App", "外卖"), ("餐饮", "外卖", TYPE_FLEX)),
    # 餐饮（堂食）
    (("板面", "面", "老豆腐", "餐饮", "饭店", "食堂", "早餐", "手擀面", "烧饼", "肥蛤", "烤鸭", "手撕烤鸭", "青阳", "荆九爷", "里脊"), ("餐饮", "堂食", TYPE_FLEX)),
    # 转账支出 → 其他·人情红包
    (("转账",), ("其他", "人情红包", TYPE_FLEX)),
]


def clean_party(raw):
    """去掉交易对方括号内的昵称及多余空白，如 '白如滨 (大白)' → '白如滨'。"""
    if not isinstance(raw, str):
        return str(raw)
    s = re.sub(r"\s*[（(][^)）]*[)）]", "", raw)
    return re.sub(r"\s+", " ", s).strip()


def map_category(name, goods):
    """根据交易对方/商品名返回 (大类, 细类, 消费类型)。未命中 → 其他·杂项。"""
    text = f"{name} {goods or ''}"
    for keywords, cat in RULES:
        for kw in keywords:
            if kw in text:
                return cat
    return ("其他", "杂项", TYPE_FLEX)


def clean_wechat(src: str, out_xlsx: str = "", out_csv: str = "") -> pd.DataFrame:
    """读取微信账单，清洗，返回 DataFrame，并输出 Excel/CSV。"""
    df = pd.read_excel(src, header=None)

    # 找到表头行：包含「交易时间」且含「收/支」
    header_idx = None
    for i in range(min(30, len(df))):
        row = df.iloc[i].astype(str).tolist()
        if any("交易时间" in str(c) for c in row) and any("收/支" in str(c) for c in row):
            header_idx = i
            break
    if header_idx is None:
        raise ValueError("未找到账单表头行（交易时间/收/支）")

    cols = ["交易时间", "交易类型", "交易对方", "商品", "收/支",
            "金额(元)", "支付方式", "当前状态", "交易单号", "商户单号", "备注"]
    data = df.iloc[header_idx + 1:].copy()
    data.columns = cols[: data.shape[1]]
    data = data.dropna(subset=["交易时间"]).reset_index(drop=True)

    # 剔除已全额退款的对冲记录
    data = data[data["当前状态"] != "已全额退款"].copy()

    rows = []
    for _, r in data.iterrows():
        party = clean_party(r["交易对方"])
        goods = "" if pd.isna(r["商品"]) else str(r["商品"])
        direction = "收入" if str(r["收/支"]).strip() == "收入" else "支出"
        amount = abs(float(r["金额(元)"]))
        date = str(pd.Timestamp(r["交易时间"]).strftime("%Y-%m-%d"))

        # 收入来源映射（转账/红包/退款等）
        if direction == "收入":
            if "转账" in str(r["交易类型"]):
                cat, subcat, etype = ("转账收款", "他人转账", "")
            elif "退款" in str(r["交易类型"]):
                cat, subcat, etype = ("退款", "购物退款", "")
            else:
                cat, subcat, etype = map_category(party, goods)
        else:
            cat, subcat, etype = map_category(party, goods)

        rows.append({
            "消费名称": party,
            "消费大类": cat,
            "消费细类": subcat,
            "类型": direction,
            "金额": amount,
            "支付平台": "微信",
            "日期": date,
            "消费类型": etype,
            "备注": goods or ("" if pd.isna(r["备注"]) else str(r["备注"])),
        })

    out = pd.DataFrame(rows)
    # 收入记录无"消费类型"列值，统一填空字符串
    if "消费类型" in out.columns:
        out["消费类型"] = out["消费类型"].fillna("")

    if out_xlsx:
        out.to_excel(out_xlsx, index=False)
    if out_csv:
        out.to_csv(out_csv, index=False, encoding="utf-8-sig")

    return out


if __name__ == "__main__":
    import sys
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    out_xlsx = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_XLSX
    out_csv = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_OUT_CSV

    result = clean_wechat(src, out_xlsx, out_csv)
    print(f"清洗完成：共 {len(result)} 条")
    print(f"  支出 {len(result[result['类型']=='支出'])} 条 | "
          f"收入 {len(result[result['类型']=='收入'])} 条")
    print(f"  已输出: {out_xlsx}")
    print(f"  已输出: {out_csv}")
    print("\n分类汇总:")
    print(result.groupby("消费大类").size().to_string())
