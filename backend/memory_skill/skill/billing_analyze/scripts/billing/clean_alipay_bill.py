"""清洗支付宝交易明细 CSV → 标准记账格式（对齐 common.py 分类约束）。

源文件：支付宝交易明细(YYYYMMDD-YYYYMMDD).csv（GBK 编码）
输出  ：清洗后的 Excel / CSV
字段  ：消费名称, 消费大类, 消费细类, 类型(支出/收入), 金额, 支付平台, 日期, 消费类型, 备注

清洗规则：
1. 跳过文件头部说明，取"交易时间,交易分类..."表头后的明细。
2. 剔除「不计收支」记录（提现、押金等，不计入收支）。
3. 交易对方去掉括号昵称、多余空白。
4. 支付平台统一为"支付宝"。
5. 依据支付宝自带"交易分类" + 商品说明 映射到 common.py 的 9 大消费类 + 细类。
6. 金额取绝对值，方向由 收/支 列区分；收入按来源分类。
"""
import os
import re
import sys
import pandas as pd

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.normpath(os.path.join(BASE_DIR, "..", ".."))    # billing_analyze 目录

# 支付宝账单位于 billing_analyze/scripts/ 下
ALIPAY_DIR = os.path.normpath(os.path.join(BASE_DIR, ".."))

DEFAULT_SRC = os.path.join(ALIPAY_DIR, "支付宝交易明细(20260718-20260807).csv")
DEFAULT_OUT_XLSX = os.path.join(SRC_DIR, "支付宝账单_清洗后.xlsx")
DEFAULT_OUT_CSV = os.path.join(SRC_DIR, "支付宝账单_清洗后.csv")

TYPE_RIGID_FIXED = "刚性固定"
TYPE_RIGID_NEC = "刚性必要"
TYPE_FLEX = "弹性支出"


def clean_party(raw):
    """去掉交易对方括号内昵称及多余空白，如 '白如滨 (大白)' → '白如滨'。"""
    if not isinstance(raw, str):
        return str(raw)
    s = re.sub(r"\s*[（(][^)）]*[)）]", "", raw)
    return re.sub(r"\s+", " ", s).strip()


def map_alipay(cat, name, goods):
    """支付宝交易分类 + 商品说明 → (大类, 细类, 消费类型)。"""
    g = goods or ""
    if "零食" in name or "零食" in g:
        return ("餐饮", "零食", TYPE_FLEX)          # 零食店统一归餐饮·零食
    if "外卖" in g:
        return ("餐饮", "外卖", TYPE_FLEX)          # 淘宝闪购/美团外卖餐饮
    if cat == "餐饮美食":
        return ("餐饮", "堂食", TYPE_FLEX)
    if cat == "日用百货":
        return ("购物", "日用消耗", TYPE_FLEX)
    if cat == "交通出行":
        return ("交通", "公交地铁", TYPE_RIGID_NEC)
    if cat == "爱车养车":
        return ("交通", "车辆维护", TYPE_RIGID_NEC)
    if cat == "文化休闲":
        if "超市" in g or "便利店" in g:
            return ("购物", "日用消耗", TYPE_FLEX)   # 美团超市/便利店订单
        if "麻辣烫" in g or "餐饮" in g or "外卖" in g:
            return ("餐饮", "外卖", TYPE_FLEX)       # 美团餐饮外卖
        if "网盘" in name or "会员" in g:
            return ("通讯", "AI服务", TYPE_FLEX)     # 夸克网盘等数字订阅
        return ("娱乐", "游戏充值", TYPE_FLEX)       # 兜底：精神消费
    if cat == "生活服务":
        return ("其他", "杂项", TYPE_FLEX)
    if cat == "其他":
        if "阿里云" in name or "云" in g:
            return ("通讯", "AI服务", TYPE_FLEX)
        return ("其他", "杂项", TYPE_FLEX)
    # 兜底
    return ("其他", "杂项", TYPE_FLEX)


def clean_alipay(src: str, out_xlsx: str = "", out_csv: str = "") -> pd.DataFrame:
    df = pd.read_csv(src, encoding="gbk", skiprows=23)
    # 去掉全空行
    df = df.dropna(subset=["交易时间"]).copy()

    # 剔除不计收支
    df = df[~df["收/支"].astype(str).str.contains("不计收支")].copy()

    rows = []
    for _, r in df.iterrows():
        party = clean_party(r["交易对方"])
        goods = "" if pd.isna(r["商品说明"]) else str(r["商品说明"])
        direction = "收入" if str(r["收/支"]).strip() == "收入" else "支出"
        amount = abs(float(r["金额"]))
        date = str(pd.Timestamp(r["交易时间"]).strftime("%Y-%m-%d"))
        note = "" if pd.isna(r["备注"]) else str(r["备注"])
        platform = "支付宝"

        if direction == "收入":
            cat, subcat, etype = ("转账收款", "他人转账", "")
        else:
            cat, subcat, etype = map_alipay(str(r["交易分类"]), party, goods)

        rows.append({
            "消费名称": party,
            "消费大类": cat,
            "消费细类": subcat,
            "类型": direction,
            "金额": amount,
            "支付平台": platform,
            "日期": date,
            "消费类型": etype,
            "备注": goods or note,
        })

    out = pd.DataFrame(rows)
    out["消费类型"] = out["消费类型"].fillna("")

    if out_xlsx:
        out.to_excel(out_xlsx, index=False)
    if out_csv:
        out.to_csv(out_csv, index=False, encoding="utf-8-sig")
    return out


if __name__ == "__main__":
    src = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SRC
    out_xlsx = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_OUT_XLSX
    out_csv = sys.argv[3] if len(sys.argv) > 3 else DEFAULT_OUT_CSV

    result = clean_alipay(src, out_xlsx, out_csv)
    print(f"清洗完成：共 {len(result)} 条")
    print(f"  支出 {len(result[result['类型']=='支出'])} 条 | "
          f"收入 {len(result[result['类型']=='收入'])} 条")
    print(f"  已输出: {out_xlsx}")
    print(f"  已输出: {out_csv}")
    print("\n分类汇总:")
    print(result.groupby("消费大类").size().to_string())
