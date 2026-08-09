"""账单数据库编辑器 — Streamlit + sqlite-utils"""
import streamlit as st
import pandas as pd
import sqlite3
from datetime import datetime
from sqlite_utils import Database
import os

try:
    from .common import CATEGORY_OPTIONS, EXPENSE_TYPE_OPTIONS, PLATFORM_OPTIONS, INCOME_CATEGORY_OPTIONS, SUBCATEGORY_OPTIONS, INCOME_SUBCATEGORY_OPTIONS
except ImportError:
    from common import CATEGORY_OPTIONS, EXPENSE_TYPE_OPTIONS, PLATFORM_OPTIONS, INCOME_CATEGORY_OPTIONS, SUBCATEGORY_OPTIONS, INCOME_SUBCATEGORY_OPTIONS  # type: ignore

# ==================== 数据库路径 ====================
DB_PATH = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "billing.db")
)

# ==================== 分类约束 ====================
CATEGORIES = CATEGORY_OPTIONS
EXPENSE_TYPES = EXPENSE_TYPE_OPTIONS
PLATFORMS = PLATFORM_OPTIONS
INCOME_SOURCES = INCOME_CATEGORY_OPTIONS
ALL_SUBCATEGORIES = sorted(set(
    sub for subs in SUBCATEGORY_OPTIONS.values() for sub in subs
))
INCOME_SUBS = sorted(set(
    sub for subs in INCOME_SUBCATEGORY_OPTIONS.values() for sub in subs
))


@st.cache_resource
def get_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    return Database(conn)


@st.cache_data(ttl=5)
def get_tables(_db):
    tables = [(t, "table") for t in _db.table_names() if t != "sqlite_sequence"]
    views = [(v, "view") for v in _db.view_names()]
    return sorted(tables + views, key=lambda x: (x[1], x[0]))


@st.cache_data(ttl=5)
def get_schema(_db, name):
    try:
        return [
            {"列名": c.name, "类型": c.type or "", "非空": "YES" if c.notnull else "NO"}
            for c in _db[name].columns
        ]
    except Exception:
        return []


def load_page(db, name, offset, limit, where_sql="", where_params=None,
              sort_col="", sort_asc=True, has_rowid=True):
    cols = "*, rowid" if has_rowid else "*"
    sql = f'SELECT {cols} FROM "{name}"'
    params = list(where_params) if where_params else []
    if where_sql.strip():
        sql += f" WHERE {where_sql}"
    if sort_col.strip():
        sql += f' ORDER BY "{sort_col}" ' + ("ASC" if sort_asc else "DESC")
    sql += " LIMIT ? OFFSET ?"
    params.extend([limit, offset])
    return pd.DataFrame(list(db.query(sql, params)))


def get_total(db, name, where_sql="", where_params=None):
    sql = f'SELECT COUNT(*) AS cnt FROM "{name}"'
    params = []
    if where_sql.strip():
        sql += f" WHERE {where_sql}"
        params = where_params or []
    r = list(db.query(sql, params)) if params else list(db.query(sql))
    return r[0]["cnt"] if r else 0


def export(df, fmt):
    if fmt == "CSV":
        return df.to_csv(index=False).encode("utf-8-sig")
    elif fmt == "JSON":
        return df.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8")
    elif fmt == "Excel":
        from io import BytesIO
        buf = BytesIO()
        with pd.ExcelWriter(buf, engine="openpyxl") as w:
            df.to_excel(w, index=False, sheet_name="data")
        return buf.getvalue()
    return b""


def save_changes(db, table, df_orig, df_edited, editor_key):
    """写回数据库：新增 / 修改 / 删除
    删除通过对比 df_orig 和 df_edited 的 id 列来判断，不依赖 deleted_rows"""
    es = st.session_state.get(editor_key, {})
    edited_rows = es.get("edited_rows", {})
    added_rows = es.get("added_rows", [])

    ins = upd = dlt = 0
    errs = []

    # —— 删除：df_orig 中有但 df_edited 中没有的 id ——
    orig_ids = set()
    for _, r in df_orig.iterrows():
        rid = r.get("id")
        if not (rid is None or (isinstance(rid, float) and pd.isna(rid))):
            orig_ids.add(int(rid))

    edit_ids = set()
    for _, r in df_edited.iterrows():
        rid = r.get("id")
        if not (rid is None or (isinstance(rid, float) and pd.isna(rid))):
            edit_ids.add(int(rid))

    to_delete = orig_ids - edit_ids
    st.write(f"🔍 orig行数={len(df_orig)} edit行数={len(df_edited)} | orig_ids={orig_ids} edit_ids={edit_ids} | 待删={to_delete}")

    for rid in to_delete:
        try:
            db[table].delete(rid)
            dlt += 1
        except Exception as e:
            errs.append(f"删除 id={rid}: {e}")

    # —— 新增 ——
    for row in added_rows:
        clean = {}
        for k, v in row.items():
            if k in ("rowid", "id"):
                continue
            clean[k] = None if (v is None or (isinstance(v, float) and pd.isna(v))) else v
        try:
            db[table].insert(clean, pk="id")
            ins += 1
        except Exception as e:
            errs.append(f"新增: {e}")
            

    # —— 修改 ——
    for idx_s, ch in edited_rows.items():
        rid = df_orig.iloc[int(idx_s)].get("id")
        if rid is None or (isinstance(rid, float) and pd.isna(rid)):
            continue
        clean = {}
        for k, v in ch.items():
            if k in ("rowid", "id"):
                continue
            clean[k] = None if (v is None or (isinstance(v, float) and pd.isna(v))) else v
        try:
            db[table].update(int(rid), clean)
            upd += 1
        except Exception as e:
            errs.append(f"修改 id={rid}: {e}")

    if errs:
        st.warning("; ".join(errs))
    return ins, upd, dlt


def renumber_ids(db, table_name):
    """重排 ID 使其连续（1, 2, 3, ...），纯 UPDATE，不删行"""
    cnt = list(db.execute(f'SELECT COUNT(*) FROM "{table_name}"'))
    total = cnt[0][0] if cnt else 0
    if total == 0:
        return 0

    # 按当前 id 排名，直接更新为连续值
    db.execute(f'''
        UPDATE "{table_name}"
        SET id = (
            SELECT COUNT(*) FROM "{table_name}" AS t2
            WHERE t2.id <= "{table_name}".id
        )
    ''')

    # 更新 SQLite 自增计数器
    db.execute("DELETE FROM sqlite_sequence WHERE name = ?", [table_name])
    db.execute(
        "INSERT INTO sqlite_sequence (name, seq) VALUES (?, ?)",
        [table_name, total],
    )

    return total


# ==================== 页面 ====================
st.set_page_config(page_title="账单数据编辑", layout="wide")
st.title("💰 账单数据编辑器")

db = get_db()
tables = get_tables(db)

if not tables:
    st.error(f"无表/视图\n{DB_PATH}")
    st.stop()

# —— 侧边栏 ——
st.sidebar.header("📊 数据源")
labels = [f"{t} ({tp})" for t, tp in tables]
selected = st.sidebar.selectbox("选择:", labels)
sel_name = next(t for t, tp in tables if f"{t} ({tp})" == selected)
sel_type = next(tp for t, tp in tables if t == sel_name)
is_table = sel_type == "table"

# 切换表重置 key
if st.session_state.get("_cur_table") != sel_name:
    st.session_state["_cur_table"] = sel_name
    st.session_state["editor_key"] = 0
if "editor_key" not in st.session_state:
    st.session_state["editor_key"] = 0

# 筛选
st.sidebar.markdown("---")
st.sidebar.header("🔍 筛选")
schema = get_schema(db, sel_name)
fcol = st.sidebar.selectbox("列:", ["（无）"] + [c["列名"] for c in schema])

conditions = []
params = []
if fcol != "（无）":
    kw = st.sidebar.text_input("关键词:")
    if kw.strip():
        conditions.append(f'"{fcol}" LIKE ?')
        params.append(f"%{kw.strip()}%")

# —— 日期筛选（可选，按某一天）——
has_date_col = any(c["列名"] == "日期" for c in schema)
if has_date_col:
    st.sidebar.markdown("---")
    if st.sidebar.toggle("📅 按日期筛选", value=False):
        day = st.sidebar.date_input(
            "日期", value=datetime.now().date(),
            help="筛选该日期的数据",
        )
        conditions.append('"日期" = ?')
        params.append(day.strftime("%Y-%m-%d"))

where_sql = " AND ".join(conditions)
where_params = params

total = get_total(db, sel_name, where_sql, where_params)

# 分页
st.sidebar.markdown("---")
st.sidebar.header("📄 分页")
psize = st.sidebar.number_input("每页", 5, 500, 50, 5)
mpage = max(1, (total - 1) // psize + 1)
page = st.sidebar.number_input("页码", 1, mpage, 1, 1)
off = (page - 1) * psize

# 导出
st.sidebar.markdown("---")
st.sidebar.header("💾 导出")
efmt = st.sidebar.selectbox("格式:", ["CSV", "JSON", "Excel"])
if st.sidebar.button("📥 导出当前页", use_container_width=True):
    dfe = load_page(db, sel_name, off, psize, where_sql, where_params, has_rowid=is_table)
    data = export(dfe, efmt)
    ext = {"CSV": "csv", "JSON": "json", "Excel": "xlsx"}
    mt = {"CSV": "text/csv", "JSON": "application/json", "Excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    st.sidebar.download_button(
        f"⬇️ {sel_name}_{ts}.{ext[efmt]}", data,
        f"{sel_name}_{ts}.{ext[efmt]}", mt[efmt],
    )

# —— 主区域 ——
st.subheader(f"📋 `{sel_name}`  ({total} 条)")

with st.expander("📊 统计", expanded=True):
    has_filter = bool(where_sql.strip())
    st.caption(f"{'筛选后统计' if has_filter else '全部统计'}（共 {total} 条）")
    if total > 0:
            nc = [c["列名"] for c in schema if c["列名"] not in ("id", "rowid") and c["类型"] and any(
                t in c["类型"].upper() for t in ("INT", "REAL", "NUM", "FLOA")
            )]
            for cn in nc:
                stats_sql = f'SELECT MIN("{cn}") mn, MAX("{cn}") mx, AVG("{cn}") av, SUM("{cn}") sm FROM "{sel_name}"'
                stats_params = []
                if has_filter:
                    stats_sql += f" WHERE {where_sql}"
                    stats_params = list(where_params)
                r = list(db.query(stats_sql, stats_params))[0]
                c1, c2, c3, c4 = st.columns(4)
                c1.metric(f"{cn} 最小", r["mn"])
                c2.metric(f"{cn} 最大", r["mx"])
                c3.metric(f"{cn} 平均", f'{r["av"]:.2f}' if r["av"] is not None else "N/A")
                c4.metric(f"{cn} 合计", f'{r["sm"]:.2f}' if r["sm"] is not None else "N/A")

# —— 排序（表格上方）——
if total > 0:
    sort_opts = [c["列名"] for c in schema]
    default_col = "日期" if "日期" in sort_opts else (sort_opts[0] if sort_opts else "")
    sc1, sc2, sc3 = st.columns([2, 1, 5])
    with sc1:
        sort_col = st.selectbox("排序", sort_opts, index=sort_opts.index(default_col) if default_col in sort_opts else 0,
                                key="sort_col", label_visibility="collapsed")
    with sc2:
        sort_asc = st.selectbox("方向", ["↑ 升序", "↓ 降序"], key="sort_dir", label_visibility="collapsed")

# —— 数据 ——
if total == 0:
    st.info("无数据")
else:
    df = load_page(db, sel_name, off, psize, where_sql, where_params,
                   sort_col=sort_col, sort_asc=sort_asc == "↑ 升序", has_rowid=is_table)
    if df.empty:
        st.info("无匹配")
    else:
        dcols = [c for c in df.columns if c != "rowid"]

        if is_table:
            # 按表名区分下拉选项
            if sel_name == "income_records":
                cat_opts = INCOME_SOURCES
                sub_map = INCOME_SUBCATEGORY_OPTIONS
                all_sub_opts = INCOME_SUBS
                dir_opts = ["收入"]
            else:
                cat_opts = CATEGORIES
                sub_map = SUBCATEGORY_OPTIONS
                all_sub_opts = ALL_SUBCATEGORIES
                dir_opts = ["支出", "收入"]

            # —— 级联新增表单 ——
            with st.expander("➕ 新增记录（级联选择）", expanded=False):
                c1, c2, c3 = st.columns(3)
                with c1:
                    new_name = st.text_input("消费名称", key="new_name")
                    new_cat = st.selectbox("消费大类", [""] + cat_opts, key="new_cat")
                with c2:
                    # 根据消费大类动态筛选消费细类
                    sub_opts_filtered = [""] + (sub_map.get(new_cat, []) if new_cat else [])
                    new_sub = st.selectbox("消费细类", sub_opts_filtered, key="new_sub")
                    new_type = st.selectbox("消费类型", [""] + EXPENSE_TYPES, key="new_type")
                with c3:
                    new_dir = st.selectbox("类型", dir_opts, key="new_dir")
                    new_platform = st.selectbox("支付平台", [""] + PLATFORMS, key="new_platform")
                c4, c5, c6 = st.columns(3)
                with c4:
                    new_amount = st.number_input("金额", min_value=0.0, step=0.01, key="new_amount")
                with c5:
                    new_date = st.date_input("日期", value=datetime.now().date(), key="new_date")
                with c6:
                    new_note = st.text_input("备注", key="new_note")
                if st.button("✅ 新增", type="primary"):
                    if not new_name.strip():
                        st.warning("请填写消费名称")
                    elif not new_cat:
                        st.warning("请选择消费大类")
                    elif new_amount <= 0:
                        st.warning("金额必须大于 0")
                    else:
                        try:
                            db[sel_name].insert({
                                "消费名称": new_name.strip(),
                                "消费大类": new_cat,
                                "消费细类": new_sub or None,
                                "类型": new_dir,
                                "金额": new_amount,
                                "支付平台": new_platform or None,
                                "日期": new_date.strftime("%Y-%m-%d"),
                                "消费类型": new_type or None,
                                "备注": new_note or None,
                            })
                            st.success(f"✅ 已新增: {new_name.strip()}")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"新增失败: {e}")

            col_cfg = {
                "rowid": None,
                "消费大类": st.column_config.SelectboxColumn("消费大类", options=cat_opts, required=True),
                "消费细类": st.column_config.SelectboxColumn("消费细类", options=all_sub_opts),
                "消费类型": st.column_config.SelectboxColumn("消费类型", options=EXPENSE_TYPES),
                "类型": st.column_config.SelectboxColumn("类型", options=dir_opts, required=True),
                "支付平台": st.column_config.SelectboxColumn("支付平台", options=PLATFORMS),
            }

            edited = st.data_editor(
                df,
                column_config=col_cfg,
                disabled=["id", "年月"],
                num_rows="dynamic",
                key=f"editor_{st.session_state['editor_key']}",
                use_container_width=True,
                height=550,
            )

            c1, c2 = st.columns([1, 4])
            with c1:
                if st.button("💾 保存修改", type="primary", use_container_width=True):
                    st.write("✅ 按钮已触发")
                    ek = f"editor_{st.session_state['editor_key']}"
                    st.write(f"key={ek}, df行={len(df)}, edited行={len(edited)}")
                    ins, upd, dlt = save_changes(db, sel_name, df, edited, ek)
                    msgs = []
                    if ins:
                        msgs.append(f"新增 {ins}")
                    if upd:
                        msgs.append(f"修改 {upd}")
                    if dlt:
                        msgs.append(f"删除 {dlt}")
                        n = renumber_ids(db, sel_name)
                        msgs.append(f"ID 已重排（{n} 条）")
                    if msgs:
                        st.success(" / ".join(msgs))
                        st.cache_data.clear()
                        st.session_state["editor_key"] += 1
                        st.rerun()
                    else:
                        st.info("无变化")
                if st.button("🔢 重排 ID", use_container_width=True):
                    n = renumber_ids(db, sel_name)
                    if n:
                        st.success(f"ID 已重排为 1~{n}")
                        st.cache_data.clear()
                        st.session_state["editor_key"] += 1
                        st.rerun()
                    else:
                        st.info("表中无数据")
            with c2:
                st.caption(
                    f"{off + 1}–{min(off + psize, total)} / {total}  |  "
                    "双击编辑 · 底部加行 · 选中行按 Delete 删除"
                )
        else:
            st.warning("⚠️ 视图只读，请切换到 billing_records 表编辑。")
            st.dataframe(df[dcols], use_container_width=True, height=550)
            st.caption(f"{off + 1}–{min(off + psize, total)} / {total}  |  点击列头排序")
