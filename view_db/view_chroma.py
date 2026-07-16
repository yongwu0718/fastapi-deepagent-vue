import streamlit as st
import chromadb
import pandas as pd
import sys
from pathlib import Path
# 将项目根目录（index_rag_agent）添加到 sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

CHROMA_DB=r"F:\index_rag\data\save_db\chroma_db"

st.set_page_config(page_title="Chroma 本地数据查看器", layout="wide")
st.title("\U0001f4ca ChromaDB 本地数据可视化")

client = chromadb.PersistentClient(path=CHROMA_DB)

collections = client.list_collections()
col_names = [col.name for col in collections]

# ===================== 侧边栏：刷新 & 危险操作 =====================
st.sidebar.button("🔄 刷新数据", use_container_width=True, on_click=st.rerun)

if col_names:
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 🗑️ 危险操作")

        delete_col_target = st.selectbox("选择要删除的集合", col_names, key="delete_col_target")

        if "show_delete_col_confirm" not in st.session_state:
            st.session_state.show_delete_col_confirm = False

        if st.button("🗑️ 删除整个集合", type="secondary", use_container_width=True):
            st.session_state.show_delete_col_confirm = True

        if st.session_state.show_delete_col_confirm:
            st.error(f"⚠️ 确认删除集合 **{delete_col_target}**？此操作不可恢复！")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 确认", key="confirm_delete_col", type="primary", use_container_width=True):
                    client.delete_collection(name=delete_col_target)
                    st.session_state.show_delete_col_confirm = False
                    st.rerun()
            with c2:
                if st.button("❌ 取消", key="cancel_delete_col", use_container_width=True):
                    st.session_state.show_delete_col_confirm = False
                    st.rerun()

if not col_names:
    st.warning("数据库中没有找到任何集合。")
else:
    selected_col = st.sidebar.selectbox("请选择要查看的集合 (Collection):", col_names)
    collection = client.get_collection(name=selected_col)
    total = collection.count()
    st.subheader(f"当前集合: `{selected_col}` (共 {total} 条数据)")

    # --- 清空集合 ---
    with st.sidebar:
        if "show_clear_confirm" not in st.session_state:
            st.session_state.show_clear_confirm = False

        if st.button("🧹 清空当前集合", type="secondary", use_container_width=True):
            st.session_state.show_clear_confirm = True

        if st.session_state.show_clear_confirm:
            st.error(f"⚠️ 确认清空 **{selected_col}** 的全部 {total} 条数据？")
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ 确认清空", key="confirm_clear", type="primary", use_container_width=True):
                    all_ids = collection.get(include=[])['ids']
                    if all_ids:
                        collection.delete(ids=all_ids)
                    st.session_state.show_clear_confirm = False
                    st.rerun()
            with c2:
                if st.button("❌ 取消清空", key="cancel_clear", use_container_width=True):
                    st.session_state.show_clear_confirm = False
                    st.rerun()

# --------------------------数据统计面板-----------------
    with st.expander("📈 数据统计面板", expanded=False):
        if total == 0:
            st.info("集合为空，无统计信息。")
        else:
            sample_limit = st.number_input(
                "统计采样上限（取前N条）",
                min_value=100,
                max_value=100000,
                value=5000,
                step=1000,
                help="数据量大时，只取前N条做统计以避免卡顿。设大值可能影响性能。"
            )
            actual_limit = min(total, sample_limit)

            if st.button("开始统计", type="primary"):
                with st.spinner("正在获取数据..."):
                    sample = collection.get(
                        limit=actual_limit,
                        include=['documents', 'metadatas']
                    )
                docs = sample['documents']
                metas = sample['metadatas']

                non_empty_docs = 0
                total_length = 0
                for doc in docs:
                    if doc and isinstance(doc, str) and len(doc.strip()) > 0:
                        non_empty_docs += 1
                        total_length += len(doc)
                empty_docs = len(docs) - non_empty_docs
                avg_length = total_length / non_empty_docs if non_empty_docs > 0 else 0

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("采样文档数", f"{len(docs)} / {total}")
                col2.metric("文档非空率", f"{non_empty_docs/len(docs)*100:.1f}%")
                col3.metric("平均文档长度", f"{avg_length:.0f} 字符")
                col4.metric("空文档数", empty_docs)

                # 向量维度（安全取值）
                vec_sample = collection.get(limit=1, include=['embeddings'])
                embeddings = vec_sample.get('embeddings') if vec_sample else None
                if embeddings is not None and len(embeddings) > 0:
                    first_emb = embeddings[0]
                    if first_emb is not None and len(first_emb) > 0:
                        st.metric("向量维度", len(first_emb))
                    else:
                        st.info("向量数据为空")
                else:
                    st.info("该集合中未找到向量数据（embedding 为空）。")

                # 元数据字段覆盖率
                if metas:
                    all_keys = set()
                    key_counts = {}
                    for meta in metas:
                        if isinstance(meta, dict):
                            for k in meta.keys():
                                all_keys.add(k)
                                key_counts[k] = key_counts.get(k, 0) + 1
                    if all_keys:
                        st.markdown("**元数据字段覆盖率**")
                        coverage_data = []
                        for k in sorted(all_keys):
                            cnt = key_counts.get(k, 0)
                            coverage_data.append({
                                "字段名": k,
                                "出现次数": cnt,
                                "覆盖率": f"{cnt / len(metas) * 100:.1f}%"
                            })
                        coverage_df = pd.DataFrame(coverage_data)
                        st.dataframe(coverage_df, use_container_width=True, hide_index=True)
                    else:
                        st.info("未检测到任何元数据字段。")
                else:
                    st.info("该集合没有元数据。")

                if actual_limit < total:
                    st.caption(f"⚠️ 当前统计基于前 {actual_limit} 条采样数据，不代表全部 {total} 条。")
    
    # ======================== 分页浏览部分 ========================
    page_size = st.sidebar.number_input("每页条数", min_value=5, max_value=500, value=20, step=5)
    max_page = max(1, (total - 1) // page_size + 1)
    page = st.sidebar.number_input("页码", min_value=1, max_value=max_page, value=1, step=1)

    offset = (page - 1) * page_size
    data = collection.get(limit=page_size, offset=offset)

    if data['ids']:
        table_data = []
        for i in range(len(data['ids'])):
            row = {
                "ID": data['ids'][i],
                "文档内容 (Document)": data['documents'][i] if data['documents'] else "N/A",
            }
            if data['metadatas'] and data['metadatas'][i]:
                for k, v in data['metadatas'][i].items():
                    row[f"Meta: {k}"] = v
            table_data.append(row)

        df = pd.DataFrame(table_data)
        st.dataframe(df, use_container_width=True, height=600)
        st.caption(f"显示第 {offset + 1} – {min(offset + page_size, total)} 条，共 {total} 条")

        # --- 删除文档 ---
        st.markdown("---")
        with st.expander("🗑️ 删除文档", expanded=False):
            current_ids = data['ids']

            col_left, col_right = st.columns([1, 1])

            with col_left:
                selected_ids = st.multiselect(
                    f"从当前页选择要删除的 ID（第 {offset + 1} – {min(offset + page_size, total)} 条）",
                    options=current_ids,
                    placeholder="选择文档 ID..."
                )

            with col_right:
                manual_text = st.text_area(
                    "或手动输入 ID（每行一个）",
                    placeholder="例如:\nchunk_001\nchunk_002",
                    height=100,
                )
                manual_ids = [x.strip() for x in manual_text.split('\n') if x.strip()]

            ids_to_delete = list(set(selected_ids + manual_ids))

            if ids_to_delete:
                st.info(f"已选择 **{len(ids_to_delete)}** 个文档待删除")

                if "show_batch_delete_confirm" not in st.session_state:
                    st.session_state.show_batch_delete_confirm = False

                if st.button(f"🗑️ 删除这 {len(ids_to_delete)} 个文档", type="primary"):
                    st.session_state.show_batch_delete_confirm = True

                if st.session_state.show_batch_delete_confirm:
                    st.error(f"⚠️ 确认删除以下 {len(ids_to_delete)} 条文档？此操作不可恢复！")
                    preview = ids_to_delete[:30]
                    if len(ids_to_delete) > 30:
                        preview = preview + ["... 还有更多"]
                    st.code('\n'.join(preview))

                    c1, c2 = st.columns(2)
                    with c1:
                        if st.button("✅ 确认删除", key="confirm_batch_del", type="primary"):
                            try:
                                result = collection.delete(ids=ids_to_delete)
                                deleted = result.get('ids_count', len(ids_to_delete))
                                st.success(f"已删除 {deleted} 条文档")
                                st.session_state.show_batch_delete_confirm = False
                                st.rerun()
                            except Exception as e:
                                st.error(f"删除失败: {e}")
                    with c2:
                        if st.button("❌ 取消", key="cancel_batch_del"):
                            st.session_state.show_batch_delete_confirm = False
                            st.rerun()
    else:
        st.info("该集合目前为空。")