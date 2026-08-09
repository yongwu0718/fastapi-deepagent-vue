"""账单分析 CLI
用法:
    python cli.py analyze billing                # 账单综合分析
    python cli.py analyze expense                # 支出专项分析
    python cli.py analyze monthly                # 三层逐月分析
    python cli.py analyze category               # 每月大类/细类汇总
    python cli.py save-bill ...                  # 保存记录
    python cli.py save-income ...                # 保存收入记录
    python cli.py list-categories                # 列出所有分类约束
"""

import argparse
import json
import sys
import os

# 确保脚本目录在 path 中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from common import DB_PATH
from analyze_billing import _run_analysis as _run_billing
from analyze_expense import _run_analysis as _run_expense
from analyze_monthly import _run_analysis as _run_monthly
from analyze_category_monthly import _run_analysis as _run_category_monthly

from save_bill import save_bill as _save_bill, list_categories as _list_categories
from save_income import save_income as _save_income


def cmd_analyze_billing(args):
    result = _run_billing(DB_PATH, args.start, args.end)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_analyze_expense(args):
    result = _run_expense(DB_PATH, args.start, args.end)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_analyze_monthly(args):
    result = _run_monthly(DB_PATH, args.start, args.end)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_analyze_category(args):
    result = _run_category_monthly(DB_PATH, args.start, args.end)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_save_bill(args):
    result = _save_bill(
        item_name=args.item_name,
        category=args.category,
        amount=args.amount,
        date=args.date,
        platform=args.platform or None,
        subcategory=args.subcategory or None,
        expense_type=args.expense_type or None,
        direction=args.direction or "支出",
        note=args.note or None,
    )
    print(result)


def cmd_save_income(args):
    result = _save_income(
        item_name=args.item_name,
        category=args.category,
        amount=args.amount,
        date=args.date,
        platform=args.platform or None,
        subcategory=args.subcategory or None,
        note=args.note or None,
    )
    print(result)


def cmd_list_categories(args):
    print(json.dumps(_list_categories(), ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="账单分析")
    sub = parser.add_subparsers(dest="command")

    # === analyze ===
    p_analyze = sub.add_parser("analyze", help="分析")
    p_analyze_sub = p_analyze.add_subparsers(dest="analyze_type")

    for name, fn in [
        ("billing", cmd_analyze_billing),
        ("expense", cmd_analyze_expense),
        ("monthly", cmd_analyze_monthly),
        ("category", cmd_analyze_category),
    ]:
        p = p_analyze_sub.add_parser(name)
        p.add_argument("--start", help="起始日期 YYYY-MM-DD")
        p.add_argument("--end", help="结束日期 YYYY-MM-DD")
        p.set_defaults(func=fn)

    # === save-bill ===
    p_save = sub.add_parser("save-bill", help="保存账单记录")
    p_save.add_argument("--item-name", required=True)
    p_save.add_argument("--category", required=True)
    p_save.add_argument("--amount", type=float, required=True)
    p_save.add_argument("--date", required=True)
    p_save.add_argument("--platform", default="")
    p_save.add_argument("--subcategory", default="")
    p_save.add_argument("--expense-type", default="")
    p_save.add_argument("--direction", default="")
    p_save.add_argument("--note", default="")
    p_save.set_defaults(func=cmd_save_bill)

    # === list-categories ===
    p_cats = sub.add_parser("list-categories", help="列出所有分类约束")
    p_cats.set_defaults(func=cmd_list_categories)

    # === save-income ===
    p_inc = sub.add_parser("save-income", help="保存收入记录")
    p_inc.add_argument("--item-name", required=True)
    p_inc.add_argument("--category", required=True)
    p_inc.add_argument("--amount", type=float, required=True)
    p_inc.add_argument("--date", required=True)
    p_inc.add_argument("--platform", default="")
    p_inc.add_argument("--subcategory", default="")
    p_inc.add_argument("--note", default="")
    p_inc.set_defaults(func=cmd_save_income)

    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)
