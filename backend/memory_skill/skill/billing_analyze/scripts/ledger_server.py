"""打工人小账本 · 本地桥接服务器

同时提供：
  1. 静态文件服务：让浏览器通过 http 打开 ledger.html（避免 file:// 下 fetch 被 CORS 拦截）
  2. JSON REST API：把前端数据读写落到 scripts/data/billing.db 与 ledger_settings.json

用法（在 scripts 目录下）:
    python ledger_server.py [--port 8230]

启动后浏览器访问:  http://127.0.0.1:8230/ledger.html

API 一览:
    GET  /api/state           ->  {records, fund, budget, savings}
    GET  /api/analyze-monthly?year=&month=  ->  调用 analyze_monthly.py 返回该月三层分析
    GET  /api/analyze-category-monthly?year=&month=  ->  调用 analyze_category_monthly.py 返回该月大类/细类汇总
    POST /api/records         ->  全量对账写入 billing.db，返回合并后的 records（含 _dbId）
    POST /api/settings        ->  写 fund/budget/savings 到 ledger_settings.json

records 字段约定（与前端 storage.js / save_bill / save_income 对齐）:
    { _dbId, _src, id, date, itemName, category, subcategory, direction,
      expenseType, platform, amount, note }
    _src: 'bill'（billing_records） | 'income'（income_records）
"""

import json
import os
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from sqlite_utils import Database

# ─── 分析脚本（直接复用，不重写逻辑） ──
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from billing.analyze_monthly import analyze_monthly  # noqa: E402
from billing.analyze_category_monthly import analyze_category_monthly  # noqa: E402

# ─── 路径常量 ───────────────────────────────────────────────
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.normpath(os.path.join(BASE_DIR, "data", "billing.db"))
SETTINGS_PATH = os.path.normpath(os.path.join(BASE_DIR, "data", "ledger_settings.json"))

PORT = 8230

# ─── 默认设置（对应前端 defaultSavings/defaultDebts）──
DEFAULT_SAVINGS = []
DEFAULT_DEBTS = {
    "balances": [],   # 余额列表: [{id, name, amount, platform, note}]
    "debts": [],      # 欠款列表: [{id, name, amount, type, dueDate, note}]
}


# ─── 数据库读写 ─────────────────────────────────────────────
CREATE_BILLING_RECORDS = """
CREATE TABLE IF NOT EXISTS "billing_records" (
    "id"            INTEGER PRIMARY KEY AUTOINCREMENT,
    "消费名称"       TEXT,
    "消费大类"       TEXT,
    "消费细类"       TEXT,
    "类型"           TEXT,
    "金额"           REAL,
    "支付平台"       TEXT,
    "日期"           TEXT,
    "消费类型"       TEXT,
    "备注"           TEXT
)
"""

CREATE_INCOME_RECORDS = """
CREATE TABLE IF NOT EXISTS "income_records" (
    "id"            INTEGER PRIMARY KEY AUTOINCREMENT,
    "消费名称"       TEXT,
    "消费大类"       TEXT,
    "消费细类"       TEXT,
    "类型"           TEXT,
    "金额"           REAL,
    "支付平台"       TEXT,
    "日期"           TEXT,
    "备注"           TEXT
)
"""

CREATE_RECORDS_VIEW = """
CREATE VIEW IF NOT EXISTS "records_view" AS
SELECT id,
       "消费名称" AS "名称", "消费大类" AS "大类", "消费细类" AS "细类",
       CASE WHEN "类型" = '支出' THEN -"金额" ELSE "金额" END AS "金额",
       "支付平台" AS "平台", "日期" AS "日期",
       "类型" AS "收支类型",
       COALESCE("消费类型", '') AS "分类",
       substr("日期", 1, 7) AS "年月"
FROM "billing_records"
UNION ALL
SELECT id,
       "消费名称", "消费大类", "消费细类",
       "金额", "支付平台", "日期", '收入', '', substr("日期", 1, 7)
FROM "income_records"
"""


def get_db():
    """确保表结构存在并返回 sqlite_utils.Database。"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    db = Database(conn)

    # 建表 / 视图（若不存在），结构与 init_db.py 完全一致
    db.execute(CREATE_BILLING_RECORDS)
    db.execute(CREATE_INCOME_RECORDS)
    db.execute(CREATE_RECORDS_VIEW)
    return db


# 前端记录 <-> 数据库行 的字段映射
def row_to_record(row, src):
    """把数据库行（dict）转成前端 records 记录。"""
    record = {
        "_dbId": row["id"],
        "_src": src,
        "id": str(row["id"]),
        "date": row.get("日期") or "",
        "itemName": row.get("消费名称") or "",
        "category": row.get("消费大类") or "",
        "subcategory": row.get("消费细类") or "",
        "direction": row.get("类型") or "支出",
        "expenseType": row.get("消费类型") or "",
        "platform": row.get("支付平台") or "",
        "amount": row.get("金额") or 0,
        "note": row.get("备注") or "",
    }
    return record


def load_records():
    """从 billing_records + income_records 读取全部记录，合并为前端结构。"""
    db = get_db()
    rows = []
    for r in db["billing_records"].rows:
        rows.append(row_to_record(dict(r), "bill"))
    for r in db["income_records"].rows:
        rows.append(row_to_record(dict(r), "income"))
    # 按日期倒序（新的在前），同日期按 id 倒序
    rows.sort(key=lambda r: (r["date"], int(r["_dbId"])), reverse=True)
    return rows


def save_records(records):
    """全量对账写入。

    对账规则：
      - 带 _dbId 且 _src 的记录：更新对应表对应行
      - 不带 _dbId 的记录：按 direction / _src 插入对应表
      - 数据库中存在但不在 records 里的行：删除（前端已删除）
    返回合并后的 records（补充新插入行的 _dbId）。
    """
    db = get_db()

    # 1) 收集数据库现有 id 集合，用于删除判断
    bill_ids = {r["id"] for r in db.query("SELECT id FROM billing_records")}
    income_ids = {r["id"] for r in db.query("SELECT id FROM income_records")}

    seen_bill, seen_income = set(), set()

    for r in records:
        amount = abs(float(r.get("amount") or 0))
        direction = r.get("direction") or "支出"
        src = r.get("_src")
        db_id = r.get("_dbId")

        # 目标表：收入只进 income_records；支出/未指明默认进 billing_records
        if direction == "收入" and src != "bill":
            target, is_income = "income_records", True
        else:
            target, is_income = "billing_records", False

        # 构造行数据（用数据库列名）
        row_data = {
            "消费名称": r.get("itemName") or None,
            "消费大类": r.get("category") or None,
            "消费细类": r.get("subcategory") or None,
            "类型": direction if not is_income else "收入",
            "金额": amount,
            "支付平台": r.get("platform") or None,
            "日期": r.get("date") or None,
            "备注": r.get("note") or None,
        }
        if not is_income:
            row_data["消费类型"] = r.get("expenseType") or None

        exists = False
        if db_id:
            # 若行仍在目标表则更新；否则（曾被删除）当作新记录插入
            db_id = int(db_id)
            hit = list(db.query(f'SELECT 1 FROM "{target}" WHERE id=:id', {"id": db_id}))
            exists = len(hit) > 0

        if exists:
            db[target].update(db_id, row_data)
            if is_income:
                seen_income.add(db_id)
            else:
                seen_bill.add(db_id)
        else:
            # 插入新行（新记录，或原行已被删除需重建）
            new_id = db[target].insert(row_data, pk="id").last_pk
            r["_dbId"] = new_id
            r["id"] = str(new_id)
            if is_income:
                r["_src"] = "income"
                seen_income.add(new_id)
            else:
                r["_src"] = "bill"
                seen_bill.add(new_id)

    # 3) 删除前端已移除的行
    for rid in bill_ids - seen_bill:
        db["billing_records"].delete(rid)
    for rid in income_ids - seen_income:
        db["income_records"].delete(rid)

    return records


# ─── 设置读写 ─────────────────────────────────────────────
def load_settings():
    """读取设置（savings/debts），缺失时给默认值。"""
    data = {}
    if os.path.isfile(SETTINGS_PATH):
        try:
            with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
        except (json.JSONDecodeError, OSError):
            data = {}

    result = {}
    # savings：缺失才给默认值
    if "savings" in data:
        result["savings"] = data["savings"] if isinstance(data["savings"], list) else []
    else:
        result["savings"] = list(DEFAULT_SAVINGS)

    # debts：缺失才给默认值
    if "debts" in data:
        result["debts"] = _deep_merge_debts(DEFAULT_DEBTS, data["debts"] or {})
    else:
        result["debts"] = dict(DEFAULT_DEBTS)

    return result


def _deep_merge_debts(default_debts, src):
    """合并余额/欠款数据，确保 balances 和 debts 都是列表。"""
    if not isinstance(src, dict):
        return dict(default_debts)
    return {
        "balances": src.get("balances") if isinstance(src.get("balances"), list) else [],
        "debts": src.get("debts") if isinstance(src.get("debts"), list) else [],
    }


def save_settings(savings, debts=None):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    payload = {
        "savings": savings,
        "debts": debts if debts is not None else DEFAULT_DEBTS,
    }
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return True


# ─── HTTP 服务 ─────────────────────────────────────────────
MIME = {
    ".html": "text/html; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".ico": "image/x-icon",
}


class Handler(BaseHTTPRequestHandler):
    server_version = "LedgerBridge/1.0"

    # 允许来自任意源的 fetch（静态页 + API 同源，仍保留以防直开）
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _send_error(self, msg, status=400):
        self._send_json({"ok": False, "error": msg}, status=status)

    def _send_file(self, rel_path):
        # 防止路径穿越
        abs_path = os.path.normpath(os.path.join(BASE_DIR, rel_path))
        if not abs_path.startswith(BASE_DIR):
            self._send_error("forbidden", 403)
            return
        if os.path.isdir(abs_path):
            abs_path = os.path.join(abs_path, "index.html")
        if not os.path.isfile(abs_path):
            self._send_error("not found", 404)
            return
        ext = os.path.splitext(abs_path)[1].lower()
        ctype = MIME.get(ext, "application/octet-stream")
        with open(abs_path, "rb") as f:
            body = f.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def _read_body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def do_OPTIONS(self):
        self.send_response(204)
        self._cors()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/state":
            state = load_settings()
            state["records"] = load_records()
            self._send_json({"ok": True, **state})
            return
        if path == "/api/analyze-monthly":
            self._handle_analyze_monthly(parsed.query)
            return
        if path == "/api/analyze-category-monthly":
            self._handle_category_monthly(parsed.query)
            return
        if path.startswith("/api/"):
            self._send_error("unknown api", 404)
        # 静态文件
        rel = path.lstrip("/")
        if rel == "":
            rel = "ledger.html"
        self._send_file(rel)

    def _parse_year_month(self, query):
        """解析 year/month 参数，返回 (year, month) 或 (None, None)。"""
        qs = parse_qs(query)
        try:
            year = int((qs.get("year") or [""])[0])
            month = int((qs.get("month") or [""])[0])
        except (TypeError, ValueError):
            return None, None
        if not (1 <= month <= 12):
            return None, None
        return year, month

    def _month_bounds(self, year, month):
        """返回该月起止日期（end_date 含当天，取当月最后一天）。"""
        start_date = f"{year:04d}-{month:02d}-01"
        if month == 12:
            return start_date, f"{year:04d}-12-31"
        import calendar
        return start_date, f"{year:04d}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"

    def _handle_analyze_monthly(self, query):
        """直接调用 analyze_monthly.py 脚本，返回指定月份的分析结果（不重写逻辑）。"""
        year, month = self._parse_year_month(query)
        if year is None:
            self._send_error("year/month required or month must be 1-12", 400)
            return
        start_date, last_day = self._month_bounds(year, month)
        try:
            get_db()   # 确保 records_view 视图存在
            result = analyze_monthly(start_date, last_day)
        except Exception as exc:  # 脚本内部异常透传
            self._send_error("analyze failed: " + str(exc), 500)
            return
        self._send_json({"ok": True, "result": result})

    def _handle_category_monthly(self, query):
        """直接调用 analyze_category_monthly.py 脚本，返回该月大类/细类汇总（不重写逻辑）。"""
        year, month = self._parse_year_month(query)
        if year is None:
            self._send_error("year/month required or month must be 1-12", 400)
            return
        start_date, last_day = self._month_bounds(year, month)
        try:
            get_db()   # 确保 records_view 视图存在
            result = analyze_category_monthly(start_date, last_day)
        except Exception as exc:
            self._send_error("analyze failed: " + str(exc), 500)
            return
        self._send_json({"ok": True, "result": result})

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path
        if path == "/api/records":
            body = self._read_body()
            records = body.get("records") if isinstance(body.get("records"), list) else []
            try:
                records = save_records(records)
                self._send_json({"ok": True, "records": records})
            except Exception as e:
                self._send_error(f"数据库写入失败: {e}", 500)
            return
        if path == "/api/settings":
            body = self._read_body()
            try:
                save_settings(
                    body.get("savings"),
                    body.get("debts"),
                )
                self._send_json({"ok": True})
            except OSError as e:
                self._send_error(f"设置保存失败: {e}", 500)
            return
        self._send_error("unknown api", 404)

    def log_message(self, fmt, *args):
        sys.stderr.write("[%s] %s\n" % (self.log_date_time_string(), fmt % args))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="打工人小账本桥接服务器")
    parser.add_argument("--port", type=int, default=PORT, help="监听端口，默认 %(default)s")
    args = parser.parse_args()

    # 启动前先初始化一次数据库（若无表则创建）
    get_db()

    httpd = ThreadingHTTPServer(("127.0.0.1", args.port), Handler)
    print("=" * 56)
    print(" 打工人小账本 · 桥接服务器已启动")
    print(f" 数据库  : {DB_PATH}")
    print(f" 设置文件: {SETTINGS_PATH}")
    print(f" 浏览器  : http://127.0.0.1:{args.port}/ledger.html")
    print(" 按 Ctrl+C 停止")
    print("=" * 56)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
        httpd.server_close()


if __name__ == "__main__":
    main()
