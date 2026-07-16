import streamlit as st
import sqlite3
import pandas as pd
import json
import sys
import time
from pathlib import Path
from datetime import datetime

from backend.config.env_settings import CHECKPOINT_DB, STORE_DB

# ==================== BLOB 解析工具 ====================
# LangGraph 使用 ormsgpack 序列化 checkpoint/metadata，type 列标记格式
try:
    import ormsgpack
    HAS_ORMSGPACK = True
except ImportError:
    HAS_ORMSGPACK = False

# 备用：纯 msgpack
try:
    import msgpack
    HAS_MSGPACK = True
except ImportError:
    HAS_MSGPACK = False

# 备用：langgraph 自带反序列化器
try:
    from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
    HAS_LANGGRAPH_SERDE = True
except ImportError:
    HAS_LANGGRAPH_SERDE = False


def parse_blob(raw: bytes, type_tag: str | None = None) -> dict:
    """根据 type 标签解析 BLOB 数据为可读字典

    LangGraph 表结构:
      checkpoints: type TEXT, checkpoint BLOB, metadata BLOB
      writes:       type TEXT, value BLOB
    """
    results = {"raw_size": len(raw)}

    if type_tag is None:
        type_tag = ""

    # 1. langgraph JsonPlusSerializer（最准确，支持 msgpack/json/pickle 等所有格式）
    if HAS_LANGGRAPH_SERDE:
        try:
            serde = JsonPlusSerializer()
            decoded = serde.loads_typed((type_tag, raw))
            results["langgraph"] = decoded
            return results
        except Exception:
            pass

    # 2. ormsgpack 解码（LangGraph 默认使用的 msgpack 库）
    if HAS_ORMSGPACK and (not type_tag or type_tag == "msgpack"):
        try:
            decoded = ormsgpack.unpackb(raw)
            results["ormsgpack"] = decoded
            return results
        except Exception:
            pass

    # 3. 纯 msgpack 解码
    if HAS_MSGPACK and (not type_tag or type_tag == "msgpack"):
        try:
            decoded = msgpack.unpackb(raw, raw=False)
            results["msgpack"] = decoded
            return results
        except Exception:
            pass

    # 4. JSON 解码
    if not type_tag or type_tag == "json":
        try:
            decoded = json.loads(raw.decode("utf-8"))
            results["json"] = decoded
            return results
        except Exception:
            pass

    # 5. pickle 解码
    if type_tag == "pickle":
        try:
            import pickle
            decoded = pickle.loads(raw)
            results["pickle"] = str(decoded)
            return results
        except Exception:
            pass

    # 6. 尝试 UTF-8 字符串
    try:
        text = raw.decode("utf-8")
        if text.strip():
            results["text"] = text
            return results
    except Exception:
        pass

    return results


def format_blob_summary(raw: bytes, type_tag: str | None = None, max_len: int = 120) -> str:
    """将 BLOB 解析为简短摘要，用于表格单元格"""
    parsed = parse_blob(raw, type_tag)

    if "langgraph" in parsed:
        s = json.dumps(parsed["langgraph"], ensure_ascii=False, default=str)
    elif "ormsgpack" in parsed:
        s = json.dumps(parsed["ormsgpack"], ensure_ascii=False, default=str)
    elif "msgpack" in parsed:
        s = json.dumps(parsed["msgpack"], ensure_ascii=False, default=str)
    elif "json" in parsed:
        s = json.dumps(parsed["json"], ensure_ascii=False)
    elif "pickle" in parsed:
        s = parsed["pickle"]
    elif "text" in parsed:
        s = parsed["text"]
    else:
        return f"<BLOB {len(raw)} bytes, hex={raw[:16].hex()}.>"

    if len(s) > max_len:
        s = s[:max_len] + "."
    return s


def format_blob_full(raw: bytes, type_tag: str | None = None) -> str:
    """将 BLOB 解析为完整 JSON 字符串，用于详情展示"""
    parsed = parse_blob(raw, type_tag)

    if "langgraph" in parsed:
        return json.dumps(parsed["langgraph"], ensure_ascii=False, indent=2, default=str)
    elif "ormsgpack" in parsed:
        return json.dumps(parsed["ormsgpack"], ensure_ascii=False, indent=2, default=str)
    elif "msgpack" in parsed:
        return json.dumps(parsed["msgpack"], ensure_ascii=False, indent=2, default=str)
    elif "json" in parsed:
        return json.dumps(parsed["json"], ensure_ascii=False, indent=2)
    elif "pickle" in parsed:
        return parsed["pickle"]
    elif "text" in parsed:
        return parsed["text"]
    else:
        return f"无法解析的二进制数据 ({len(raw)} bytes)\nHex 预览:\n{raw[:256].hex()}"

# ==================== 页面配置 ====================
st.set_page_config(page_title="SQLite 本地数据查看器", layout="wide")
st.title("📊 SQLite 本地数据可视化")

# ==================== 数据库配置 ====================
DB_MAP = {
    "checkpoints.db（对话检查点）": CHECKPOINT_DB,
    "store.db（持久化存储）": STORE_DB,
}


@st.cache_resource
def get_db_connection(db_path: str):
    """获取缓存的数据连接（只读模式，允许多线程访问）"""
    conn = sqlite3.connect(
        f"file:{db_path}?mode=ro", uri=True, check_same_thread=False
    )
    conn.row_factory = sqlite3.Row
    return conn


def get_tables(conn: sqlite3.Connection) -> list[str]:
    """获取数据库中所有用户表"""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    return [row[0] for row in cursor.fetchall()]


def get_table_schema(conn: sqlite3.Connection, table: str) -> list[dict]:
    """获取表结构信息"""
    cursor = conn.execute(f"PRAGMA table_info('{table}')")
    return [
        {"列名": row[1], "类型": row[2], "非空": "YES" if row[3] else "NO", "默认值": row[4]}
        for row in cursor.fetchall()
    ]


def get_table_data(
    conn: sqlite3.Connection, table: str, offset: int, limit: int,
    decode_blob: bool = True,
) -> pd.DataFrame:
    """分页读取表数据，可选解析 BLOB 字段"""
    cursor = conn.execute(
        f"SELECT *, rowid FROM '{table}' LIMIT ? OFFSET ?",
        (limit, offset),
    )
    columns = [desc[0] for desc in cursor.description]
    rows = cursor.fetchall()

    # 识别 BLOB 列与对应的 type 列映射
    # LangGraph 表: checkpoints {type, checkpoint, metadata}, writes {type, value}
    blob_cols = set()
    type_col = None
    for col in columns:
        cursor2 = conn.execute(f"PRAGMA table_info('{table}')")
        for info in cursor2.fetchall():
            if info[1] == col and "BLOB" in info[2].upper():
                blob_cols.add(col)
            if info[1] == "type":
                type_col = "type"

    data = []
    for row in rows:
        record = {}
        row_dict = dict(row)
        # 获取该行的 type 标签
        tag = row_dict.get(type_col) if type_col else None

        for col in columns:
            val = row_dict[col]
            if isinstance(val, bytes):
                if decode_blob:
                    record[col] = format_blob_summary(val, tag)
                else:
                    record[col] = f"<BLOB {len(val)} bytes>"
            else:
                record[col] = val
        data.append(record)
    return pd.DataFrame(data)


def get_row_raw(conn: sqlite3.Connection, table: str, rowid: int) -> dict:
    """获取单行原始数据（含完整 BLOB + type 标签），用于详情查看"""
    cursor = conn.execute(
        f"SELECT * FROM '{table}' WHERE rowid = ?", (rowid,)
    )
    columns = [desc[0] for desc in cursor.description]
    row = cursor.fetchone()
    if row is None:
        return {}
    return dict(zip(columns, row))


def export_data(df: pd.DataFrame, fmt: str) -> bytes:
    """将 DataFrame 导出为指定格式"""
    if fmt == "CSV":
        return df.to_csv(index=False).encode("utf-8-sig")
    elif fmt == "JSON":
        return df.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8")
    elif fmt == "Excel":
        from io import BytesIO
        buffer = BytesIO()
        with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="data")
        return buffer.getvalue()


def get_writes_for_checkpoint(conn, checkpoint_id: str) -> list[dict]:
    """查询 writes 表中属于某个 checkpoint 的所有写入记录"""
    try:
        cursor = conn.execute(
            "SELECT task_id, idx, channel, type, value FROM writes WHERE checkpoint_id = ? ORDER BY idx",
            (checkpoint_id,),
        )
        results = []
        for row in cursor.fetchall():
            tag = row["type"]
            raw = row["value"]
            if isinstance(raw, bytes) and raw:
                decoded = format_blob_full(raw, tag)
            else:
                decoded = str(raw) if raw else "(empty)"
            results.append({
                "task_id": row["task_id"],
                "idx": row["idx"],
                "channel": row["channel"],
                "type": tag,
                "value_parsed": decoded,
                "value_raw_size": len(raw) if isinstance(raw, bytes) else 0,
            })
        return results
    except Exception:
        return []


def get_thread_timeline(conn, thread_id: str) -> list[dict]:
    """获取一个线程的完整时间线：所有检查点按时间排序"""
    cursor = conn.execute(
        "SELECT rowid, checkpoint_id, parent_checkpoint_id, type, checkpoint, metadata "
        "FROM checkpoints WHERE thread_id = ? ORDER BY rowid",
        (thread_id,),
    )
    timeline = []
    for row in cursor.fetchall():
        tag = row["type"]
        cp_raw = row["checkpoint"]
        cp_str = format_blob_full(cp_raw, tag) if isinstance(cp_raw, bytes) else ""
        meta_raw = row["metadata"]
        meta_str = format_blob_full(meta_raw, tag) if isinstance(meta_raw, bytes) else ""
        timeline.append({
            "rowid": row["rowid"],
            "checkpoint_id": row["checkpoint_id"],
            "parent_checkpoint_id": row["parent_checkpoint_id"],
            "checkpoint_parsed": cp_str,
            "metadata_parsed": meta_str,
        })
    return timeline


def extract_messages_from_checkpoint(checkpoint_str: str) -> list[dict]:
    """从 checkpoint JSON 字符串中提取 messages"""
    try:
        cp = json.loads(checkpoint_str)
        messages = []
        for ch_name, ch_val in cp.get("channel_values", {}).items():
            if isinstance(ch_val, dict) and "messages" in ch_val:
                messages.extend(ch_val["messages"])
            elif isinstance(ch_val, list):
                for item in ch_val:
                    if isinstance(item, dict) and "content" in item:
                        messages.append(item)
        return messages
    except Exception:
        return []


def extract_messages_from_writes_json(json_str: str) -> list[dict]:
    """从 writes value JSON 字符串中提取消息"""
    try:
        data = json.loads(json_str)
        if isinstance(data, list):
            msgs = []
            for item in data:
                if isinstance(item, dict) and "content" in item:
                    msgs.append(item)
            return msgs
        elif isinstance(data, dict):
            if "messages" in data and isinstance(data["messages"], list):
                return data["messages"]
            if "content" in data:
                return [data]
        return []
    except Exception:
        return []


# ==================== 侧边栏：选择数据库和表 ====================
st.sidebar.header("🔍 数据源选择")
selected_db_name = st.sidebar.selectbox("选择数据库:", list(DB_MAP.keys()))
db_path = DB_MAP[selected_db_name]

try:
    conn = get_db_connection(db_path)
except Exception as e:
    st.error(f"无法连接数据库: {e}")
    st.stop()

tables = get_tables(conn)

if not tables:
    st.warning("数据库中没有找到任何表。")
    st.stop()

selected_table = st.sidebar.selectbox("选择表:", tables)

# 读取表结构
schema = get_table_schema(conn, selected_table)
total_rows = conn.execute(f"SELECT COUNT(*) FROM '{selected_table}'").fetchone()[0]

st.subheader(f"当前表: `{selected_table}`（共 {total_rows} 条数据）")

# ==================== 数据统计面板 ====================
with st.expander("📈 表结构与统计信息", expanded=False):
    tab1, tab2, tab3 = st.tabs(["表结构", "数值统计", "数据概览"])

    with tab1:
        if schema:
            schema_df = pd.DataFrame(schema)
            st.dataframe(schema_df, use_container_width=True, hide_index=True)
        else:
            st.info("无法获取表结构信息。")

    with tab2:
        if total_rows > 0:
            # 获取所有列名
            col_cursor = conn.execute(f"PRAGMA table_info('{selected_table}')")
            columns = [(row[1], row[2]) for row in col_cursor.fetchall()]

            # 统计 TEXT 列的非空率
            text_cols = [name for name, ctype in columns if "TEXT" in ctype.upper() or "CHAR" in ctype.upper()]
            if text_cols:
                stats = []
                for col_name in text_cols:
                    try:
                        total = conn.execute(
                            f"SELECT COUNT(*) FROM '{selected_table}' WHERE {col_name} IS NOT NULL AND {col_name} != ''"
                        ).fetchone()[0]
                        stats.append({
                            "字段名": col_name,
                            "非空行数": total,
                            "非空率": f"{total / total_rows * 100:.1f}%" if total_rows > 0 else "0%",
                        })
                    except Exception:
                        pass
                if stats:
                    stats_df = pd.DataFrame(stats)
                    st.dataframe(stats_df, use_container_width=True, hide_index=True)

            # INTEGER 列统计
            int_cols = [name for name, ctype in columns if "INT" in ctype.upper() or "REAL" in ctype.upper() or "NUM" in ctype.upper()]
            if int_cols:
                st.markdown("**数值列摘要**")
                for col_name in int_cols:
                    try:
                        result = conn.execute(
                            f"SELECT MIN({col_name}), MAX({col_name}), AVG({col_name}) FROM '{selected_table}'"
                        ).fetchone()
                        col1, col2, col3 = st.columns(3)
                        col1.metric(f"{col_name} (最小值)", result[0])
                        col2.metric(f"{col_name} (最大值)", result[1])
                        col3.metric(f"{col_name} (平均值)", f"{result[2]:.2f}" if result[2] is not None else "N/A")
                    except Exception:
                        pass
        else:
            st.info("表为空，无统计信息。")

    with tab3:
        if total_rows > 0:
            sample = get_table_data(conn, selected_table, 0, min(5, total_rows))
            st.markdown("**前 5 条数据预览**")
            st.dataframe(sample, use_container_width=True)
        else:
            st.info("表为空。")

# ==================== 侧边栏：显示选项 ====================
st.sidebar.markdown("---")
st.sidebar.header("⚙️ 显示选项")
decode_blob = st.sidebar.checkbox(
    "解析 BLOB 数据（checkpoint / metadata）",
    value=True,
    help="将 msgpack/JSON 二进制数据解码为可读文本摘要",
)

# ==================== 自动刷新 ====================
st.sidebar.markdown("---")
st.sidebar.header("🔄 自动刷新")
auto_refresh = st.sidebar.checkbox(
    "启用自动刷新",
    value=False,
    help="SQLite 数据变化时，页面自动同步更新",
)
refresh_interval = st.sidebar.slider(
    "刷新间隔（秒）",
    min_value=2, max_value=60, value=5, step=1,
    disabled=not auto_refresh,
)

# 管理 session_state
if "last_refresh_time" not in st.session_state:
    st.session_state["last_refresh_time"] = time.time()

# 显示上次刷新时间
if auto_refresh:
    elapsed = time.time() - st.session_state["last_refresh_time"]
    remaining = max(0, refresh_interval - elapsed)
    st.sidebar.caption(
        f"⏱ 距上次刷新: {elapsed:.1f}s | 下次刷新: {remaining:.1f}s"
    )

# ==================== 分页浏览 ====================
st.sidebar.markdown("---")
st.sidebar.header("📄 分页浏览")
page_size = st.sidebar.number_input("每页条数", min_value=5, max_value=500, value=30, step=5)
max_page = max(1, (total_rows - 1) // page_size + 1)
page = st.sidebar.number_input("页码", min_value=1, max_value=max_page, value=1, step=1)

offset = (page - 1) * page_size

if total_rows > 0:
    df = get_table_data(conn, selected_table, offset, page_size, decode_blob=decode_blob)

    if not df.empty:
        st.dataframe(df, use_container_width=True, height=500)
        st.caption(f"显示第 {offset + 1} – {min(offset + page_size, total_rows)} 条，共 {total_rows} 条")

        # ==================== 单行详情查看 ====================
        st.markdown("---")
        st.subheader("🔎 单行详情查看（解析 checkpoint / metadata 完整内容）")

        # 获取当前页所有 rowid 供选择
        rowid_list = df["rowid"].tolist() if "rowid" in df.columns else []
        if rowid_list:
            selected_rowid = st.selectbox(
                "选择要查看的行 (rowid):",
                rowid_list,
                format_func=lambda x: f"rowid={x}",
            )

            if selected_rowid is not None:
                raw_row = get_row_raw(conn, selected_table, selected_rowid)
                if raw_row:
                    # 获取 type 标签（LangGraph 表有此列）
                    tag = raw_row.get("type", None)

                    for col_name, col_val in raw_row.items():
                        if isinstance(col_val, bytes):
                            # BLOB 列：使用 type 标签解码并展示完整内容
                            full_json = format_blob_full(col_val, tag)
                            with st.expander(
                                f"📦 {col_name} ({len(col_val)} bytes) [type={tag}]",
                                expanded=(col_name in ("checkpoint", "metadata")),
                            ):
                                st.code(full_json, language="json", line_numbers=True)
                        else:
                            # 普通列：直接展示
                            st.text(f"{col_name}: {col_val}")
        else:
            st.info("当前页无数据。")

        # ==================== 跨表关联：checkpoints ↔ writes ====================
        if selected_table == "checkpoints" and "writes" in tables:
            st.markdown("---")
            st.subheader("🔗 跨表关联查询（checkpoints ↔ writes）")

            tab_cross1, tab_cross2 = st.tabs(["📋 按线程查看完整对话", "📝 当前检查点的增量写入"])

            with tab_cross1:
                # 获取所有 thread_id
                thread_cursor = conn.execute(
                    "SELECT thread_id, MIN(rowid) AS first_row "
                    "FROM checkpoints GROUP BY thread_id ORDER BY first_row DESC LIMIT 50"
                )
                thread_ids = [r[0] for r in thread_cursor.fetchall()]
                if thread_ids:
                    selected_thread = st.selectbox(
                        "选择线程 (thread_id):", thread_ids,
                        key="cross_thread_select",
                    )
                    if selected_thread and st.button("🔍 加载完整对话时间线", type="primary"):
                        with st.spinner("正在查询 writes 表并重建对话."):
                            timeline = get_thread_timeline(conn, selected_thread)
                            all_messages = []

                            for step in timeline:
                                # 从 channel_values 提取消息（seed/snapshot）
                                cp_msgs = extract_messages_from_checkpoint(step["checkpoint_parsed"])
                                # 从 writes 提取增量
                                writes = get_writes_for_checkpoint(conn, step["checkpoint_id"])
                                write_msgs = []
                                for w in writes:
                                    if w["channel"] in ("messages", "branch:to:call_llm"):
                                        write_msgs.extend(
                                            extract_messages_from_writes_json(w["value_parsed"])
                                        )

                                all_messages.extend(cp_msgs)
                                all_messages.extend(write_msgs)

                            if all_messages:
                                st.success(f"共重建 {len(all_messages)} 条消息")
                                # 去重（基于内容+角色）
                                seen = set()
                                unique_msgs = []
                                for m in all_messages:
                                    key = (m.get("role", ""), str(m.get("content", ""))[:80])
                                    if key not in seen:
                                        seen.add(key)
                                        unique_msgs.append(m)

                                st.markdown("### 💬 完整对话")
                                for i, msg in enumerate(unique_msgs):
                                    role = msg.get("role", "unknown")
                                    content = msg.get("content", "")
                                    # 截断过长的内容
                                    display_content = content if len(str(content)) < 2000 else str(content)[:2000] + "\n.(截断)"

                                    if role == "user":
                                        with st.chat_message("user"):
                                            st.markdown(display_content)
                                    elif role == "assistant":
                                        with st.chat_message("assistant"):
                                            st.markdown(display_content)
                                    elif role == "system":
                                        with st.chat_message("user"):
                                            st.caption(f"[system] {display_content}")
                                    else:
                                        with st.expander(f"📦 消息 {i+1} - {role}", expanded=False):
                                            st.json(msg)

                                # 同时显示原始时间线
                                with st.expander("📊 原始时间线详情", expanded=False):
                                    for step in timeline:
                                        cid_short = step["checkpoint_id"][:12]
                                        st.markdown(f"**checkpoint: `{cid_short}.`**")
                                        col_a, col_b = st.columns(2)
                                        with col_a:
                                            st.caption("channel_values 中的消息数: "
                                                       f"{len(extract_messages_from_checkpoint(step['checkpoint_parsed']))}")
                                        with col_b:
                                            writes_count = len(get_writes_for_checkpoint(conn, step["checkpoint_id"]))
                                            st.caption(f"writes 记录数: {writes_count}")
                                        st.divider()
                            else:
                                st.info("未提取到消息内容。")
                else:
                    st.info("没有线程数据。")

            with tab_cross2:
                # 使用当前选中的行
                if rowid_list and selected_rowid is not None:
                    checkpoint_id = raw_row.get("checkpoint_id", "") if raw_row.get("checkpoint_id") is not None else ""
                    if checkpoint_id:
                        writes_data = get_writes_for_checkpoint(conn, checkpoint_id)
                        if writes_data:
                            st.markdown(f"**checkpoint_id:** `{checkpoint_id}` 共 {len(writes_data)} 条写入")
                            for w in writes_data:
                                with st.expander(
                                    f"📝 channel=`{w['channel']}` task=`{w['task_id'][:16]}.` idx={w['idx']} ({w['value_raw_size']}B)",
                                    expanded=(w["channel"] in ("messages",)),
                                ):
                                    st.code(w["value_parsed"], language="json", line_numbers=False)
                        else:
                            st.info("该检查点在 writes 表中无关联记录。")
                    else:
                        st.info("当前行无有效的 checkpoint_id。")
                else:
                    st.info("请先在「单行详情查看」中选择一行。")

        # ==================== 导出保存功能 ====================
        st.sidebar.markdown("---")
        st.sidebar.header("💾 导出数据")
        export_format = st.sidebar.selectbox("导出格式:", ["CSV", "JSON", "Excel"])

        # 导出范围
        export_scope = st.sidebar.radio(
            "导出范围:",
            ["当前页", "全部数据"],
            horizontal=True,
        )

        if st.sidebar.button("📥 生成导出文件", type="primary", use_container_width=True):
            if export_scope == "全部数据":
                export_df = get_table_data(conn, selected_table, 0, total_rows, decode_blob=decode_blob)
            else:
                export_df = df

            export_bytes = export_data(export_df, export_format)

            ext_map = {"CSV": "csv", "JSON": "json", "Excel": "xlsx"}
            mime_map = {"CSV": "text/csv", "JSON": "application/json", "Excel": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{selected_table}_{timestamp}.{ext_map[export_format]}"

            st.sidebar.download_button(
                label=f"⬇️ 下载 {filename}",
                data=export_bytes,
                file_name=filename,
                mime=mime_map[export_format],
            )

    else:
        st.info("该表目前为空。")
else:
    st.info("该表目前为空。")

# ==================== 自动刷新触发器（放在最后） ====================
if auto_refresh:
    elapsed = time.time() - st.session_state["last_refresh_time"]
    if elapsed >= refresh_interval:
        st.session_state["last_refresh_time"] = time.time()
        time.sleep(0.3)  # 短暂延迟避免闪烁
        st.rerun()
    else:
        time.sleep(0.5)
