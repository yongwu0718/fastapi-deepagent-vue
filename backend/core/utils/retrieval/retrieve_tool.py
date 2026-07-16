import time
import traceback
from contextlib import contextmanager
from typing import Optional, TypedDict

from langchain_chroma import Chroma
from langchain.tools import tool

from backend.config.logger import get_logger
from backend.core.models.model_factory import embeddings, rerank_model
from backend.config.env_settings import CHROMA_DB, COLLECTION_NAME

logger = get_logger(__name__)

# 类型定义
class RetrieveResult(TypedDict):
    documents: list
    question: str
    error: Optional[str]

# 向量存储 —— 直接在主函数外初始化
logger.info("正在初始化 Chroma | collection=%s | path=%s", COLLECTION_NAME, CHROMA_DB)
_t0 = time.monotonic()
_vectorstore = Chroma(
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
    persist_directory=CHROMA_DB,
)
logger.info("Chroma 初始化完成 | 耗时=%.1fms", (time.monotonic() - _t0) * 1000)

# 计时工具
@contextmanager
def _timed(label: str, *args):
    """上下文管理器：记录步骤耗时。"""
    msg = label % args if args else label
    logger.debug("%s | 开始", msg)
    t0 = time.monotonic()
    try:
        yield
    finally:
        elapsed = (time.monotonic() - t0) * 1000
        logger.info("%s | 完成 | 耗时=%.1fms", msg, elapsed)

# 日志格式化
def _log_results(reranked_docs: list) -> None:
    """输出最终结果摘要日志。"""
    if not reranked_docs:
        return
    lines = []
    for i, doc in enumerate(reranked_docs):
        snippet = doc.page_content.replace("\n", " ")[:200]
        score = doc.metadata.get("relevance_score", "N/A")
        headers = {k: v for k, v in doc.metadata.items() if k.startswith("Header")}
        header_path = " > ".join(headers.values()) if headers else ""
        lines.append(f"【结果 {i + 1}】 (得分:{score}) {header_path} | {snippet}")
    logger.debug("检索并重排序后的结果：\n%s", "\n".join(lines))

# 合并后的唯一检索方法
def retrieve_with_rerank_text(
    question: str,
    rerank_threshold: float = 0.5,
    initial_k: int = 50,
) -> RetrieveResult:
    """检索管道：向量召回 → 重排序 → 分数过滤。

    所有步骤都在本方法内完成，向量数据库已在外部初始化。
    """
    overall_t0 = time.monotonic()
    logger.info(
        "========== 检索开始 ========== | question=%s | threshold=%.2f | k=%d",
        question, rerank_threshold, initial_k,
    )

    def _empty_result(error_msg: Optional[str] = None) -> RetrieveResult:
        return {"documents": [], "question": question, "error": error_msg}

    try:
        # ---------- 步骤1 向量检索 ----------
        with _timed("[步骤1/2] 向量检索 | k=%d", initial_k):
            docs = _vectorstore.similarity_search(question, k=initial_k)
        logger.info("[步骤1/2] 召回=%d 篇", len(docs))

        if not docs:
            logger.warning("========== 检索结束(召回为空) ========== | 总耗时=%.1fms",
                           (time.monotonic() - overall_t0) * 1000)
            return _empty_result("未召回任何文档。")

        # ---------- 步骤2 重排序 + 过滤 ----------
        try:
            with _timed("[步骤2/2] 重排序+过滤 | 候选=%d | threshold=%.2f", len(docs), rerank_threshold):
                compressed = rerank_model.compress_documents(docs, question)
            kept = []
            rejected = 0
            rejected_scores = []
            for doc in compressed:
                score = doc.metadata.get("relevance_score", 0)
                if isinstance(score, str):
                    score = 0
                if score >= rerank_threshold:
                    kept.append(doc)
                else:
                    rejected += 1
                    rejected_scores.append(score)
            reranked_docs = kept
            logger.info(
                "[步骤2/2] 通过=%d | 被过滤=%d | 过滤分数=%s",
                len(reranked_docs), rejected, rejected_scores,
            )
        except Exception as rerank_err:
            logger.warning("重排序失败，降级使用向量排序 | err=%s", rerank_err)
            top_n = getattr(rerank_model, "top_n", len(docs))
            reranked_docs = docs[:top_n]
            for doc in reranked_docs:
                doc.metadata.setdefault("relevance_score", "N/A")

        # 重排序后无结果达标时，兜底返回重排序分数最高的一条
        if not reranked_docs and compressed:
            best = compressed[0]
            best_score = best.metadata.get("relevance_score", "N/A")
            logger.warning(
                "重排序后无文档达标(threshold=%.2f)，兜底使用重排序最高分文档 | score=%s",
                rerank_threshold, best_score,
            )
            reranked_docs = [best]

        # 日志 & 返回
        _log_results(reranked_docs)

        overall_ms = (time.monotonic() - overall_t0) * 1000
        logger.info(
            "========== 检索结束 ========== | 返回=%d 篇 | 总耗时=%.1fms",
            len(reranked_docs), overall_ms,
        )

        return {"documents": reranked_docs, "question": question, "error": None}

    except Exception as e:
        logger.error("========== 检索异常 ========== | err=%s", e)
        logger.error("错误栈：\n%s", traceback.format_exc())
        return _empty_result(f"检索失败: {e}")

# LangChain 工具封装
@tool
def retriever_row_doc_tool(question: str) -> dict:
    """检索向量数据库，检索原始文档段落，返回相关文档内容及元数据。
    args:
        question: 用户查询的问题必须是连续的自然语言句子，用于检索相关的文档段落。
    return:
        dict: 包含相关文档内容及元数据的字典。
    """
    return retrieve_with_rerank_text(question)
