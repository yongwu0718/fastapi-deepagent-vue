import json
import asyncio
from typing import Any, Dict, List, Optional, Union, TypedDict
from datetime import datetime
from zoneinfo import ZoneInfo

from fastmcp import FastMCP
from langchain_chroma import Chroma
from langchain_core.documents import Document

from backend.config.env_settings import COLLECTION_MEMORY_NAME, CHROMA_DB
from backend.config.logger import setup_logging, get_logger
from backend.core.models.model_factory import embeddings

logger = get_logger(__name__)

mcp = FastMCP("Memory")


# ------------------ 辅助函数：过滤复杂元数据 ------------------
def filter_complex_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """将元数据中的复杂值（dict、list 等）转换为 Chroma 可接受的简单类型。

    Chroma 允许的元数据值类型：str, int, float, bool, list(元素也需简单), None
    其他类型（如 dict）会被转为 JSON 字符串，若转换失败则丢弃该字段。
    """
    allowed_scalar = (str, int, float, bool, type(None))
    clean = {}
    for key, value in metadata.items():
        if isinstance(value, allowed_scalar):
            clean[key] = value
        elif isinstance(value, list):
            if all(isinstance(v, allowed_scalar) for v in value):
                clean[key] = value
            else:
                try:
                    clean[key] = json.dumps(value, ensure_ascii=False)
                except (TypeError, ValueError):
                    pass
        else:
            try:
                clean[key] = json.dumps(value, ensure_ascii=False)
            except (TypeError, ValueError):
                pass
    return clean


# ------------------ 记忆向量存储封装 ------------------
class MemoryStore:
    """记忆向量存储的封装，负责初始化和管理 Chroma 集合。"""

    def __init__(
        self,
        collection_name: str = "memory",
        persist_directory: str = CHROMA_DB,
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.vectorstore = self._create_vectorstore()

    def _create_vectorstore(self) -> Chroma:
        try:
            vs = Chroma(
                collection_name=self.collection_name,
                embedding_function=embeddings,
                persist_directory=self.persist_directory,
                collection_configuration={
                    "hnsw": {
                        "space": "cosine",
                        "ef_construction": 200,
                        "max_neighbors": 32,
                        "ef_search": 200,
                        "num_threads": 4,
                        "batch_size": 100,
                        "sync_threshold": 1000,
                        "resize_factor": 1.2
                    }
                }
            )
            logger.info("向量存储创建成功 | collection=%s | persist_dir=%s",
                        self.collection_name, self.persist_directory)
            return vs
        except Exception as e:
            logger.error("创建记忆向量存储失败 | collection=%s | error=%s",
                         self.collection_name, e)
            raise RuntimeError(f"创建记忆向量存储失败: {e}")

    # ---------- 核心 upsert 方法 ----------
    async def upsert(self, memory_key: str, memory_value: Dict[str, Any]) -> None:
        """插入或覆盖一条记忆。"""
        logger.info("记忆 upsert | key=%s | 内容预览=%.100s...",
                     memory_key, json.dumps(memory_value, ensure_ascii=False))

        content = memory_value.pop("content", "")
        packed = {
            "key": memory_key,
            **memory_value,
        }
        metadata_json = json.dumps(packed, ensure_ascii=False)

        doc = Document(
            page_content=content,
            metadata={"metadata": metadata_json},
            id=memory_key,
        )

        if hasattr(self.vectorstore, "aadd_documents"):
            await self.vectorstore.aadd_documents([doc], ids=[memory_key])
        else:
            await asyncio.to_thread(
                self.vectorstore.add_documents, [doc], ids=[memory_key]
            )
        logger.info("记忆 upsert 成功 | key=%s", memory_key)

    # ---------- 搜索 ----------
    async def search(self, query: str, k: int = 5, threshold: float = 0.4) -> str:
        """语义搜索记忆库，返回格式化结果。"""
        logger.info("记忆搜索开始 | query=%s... | k=%d | threshold=%.2f", query[:50], k, threshold)
        try:
            docs_with_scores = await asyncio.to_thread(
                self.vectorstore.similarity_search_with_score,
                query,
                k=k * 2
            )
        except Exception as e:
            logger.error("向量搜索失败 | error=%s", e)
            return "❌ 搜索失败，请稍后重试。"

        if not docs_with_scores:
            return "没有找到相关记忆。"

        results = []
        for doc, score in docs_with_scores:
            if threshold is not None and score > threshold:
                continue
            key = doc.id or "unknown"
            results.append(f"[{key}] (距离:{score:.4f}) {doc.page_content}")
            if len(results) >= k:
                break

        if not results:
            logger.info("记忆搜索完成 | 返回 0 条 | 阈值过滤 %d 条", len(docs_with_scores))
            return "没有找到相关记忆（低于阈值）。"

        logger.info("记忆搜索完成 | 返回 %d 条", len(results))
        return "\n".join(results)

    # ---------- 删除 ----------
    async def delete(self, memory_key: str) -> None:
        """删除指定 memory_key 的记忆。"""
        logger.info("记忆删除 | key=%s", memory_key)
        if hasattr(self.vectorstore, "adelete"):
            await self.vectorstore.adelete(ids=[memory_key])
        else:
            await asyncio.to_thread(self.vectorstore.delete, ids=[memory_key])
        logger.info("记忆删除成功 | key=%s", memory_key)

    # ---------- 精确获取 ----------
    async def get(self, memory_key: str) -> Optional[Dict[str, Any]]:
        """根据 key 精确获取一条记忆，返回原始字典。"""
        logger.debug("记忆获取 | key=%s", memory_key)
        try:
            result = await asyncio.to_thread(
                self.vectorstore.get, ids=[memory_key]
            )
        except Exception as e:
            logger.error("获取记忆失败 | key=%s | error=%s", memory_key, e)
            raise RuntimeError(f"获取记忆失败 (key={memory_key}): {e}")

        documents = result.get("documents") or []
        metadatas = result.get("metadatas") or []
        if not documents or not metadatas or documents[0] is None:
            logger.debug("记忆不存在 | key=%s", memory_key)
            return None

        packed_str = metadatas[0].get("metadata", "{}")
        try:
            packed = json.loads(packed_str) if isinstance(packed_str, str) else {}
        except json.JSONDecodeError:
            packed = {}

        packed["content"] = documents[0]
        if "metadata" in packed and isinstance(packed["metadata"], str):
            try:
                packed["metadata"] = json.loads(packed["metadata"])
            except json.JSONDecodeError:
                pass

        logger.debug("记忆获取成功 | key=%s", memory_key)
        return packed

    # ---------- 列出所有 keys ----------
    async def list_keys(self, page_size: int = 100, max_keys: int = 1000) -> List[str]:
        """列出所有记忆 key（分页，最多返回 max_keys 个）。"""
        logger.info("列出记忆 key | page_size=%d | max_keys=%d", page_size, max_keys)
        all_ids = []
        offset = 0
        page_count = 0
        try:
            while len(all_ids) < max_keys:
                batch = await asyncio.to_thread(
                    self.vectorstore.get,
                    limit=min(page_size, max_keys - len(all_ids)),
                    offset=offset,
                    include=[],
                )
                ids = batch.get("ids", [])
                if not ids:
                    break
                all_ids.extend(ids)
                offset += len(ids)
                page_count += 1
            logger.info("列出记忆 key 完成 | 总数=%d | 分页数=%d", len(all_ids), page_count)
            return all_ids
        except Exception as e:
            logger.error("获取记忆 key 列表失败 | error=%s", e)
            raise RuntimeError(f"获取记忆 key 列表失败: {e}")


# ------------------ 全局单例 ------------------
memory_store = MemoryStore(
    collection_name=COLLECTION_MEMORY_NAME,
    persist_directory=CHROMA_DB,
)


# ------------------ MCP 工具定义 ------------------
@mcp.tool()
async def save_memory(memory_key: str, memory_value: str) -> str:
    """保存或更新一条结构化记忆（若 key 已存在则覆盖）。

    工具会自动处理以下字段：
    - timestamp: 填充当前时间，调用时无需提供。

    参数:
        memory_key: 记忆的唯一标识符。
        memory_value: JSON 字符串，包含以下可选字段：
            content (str):      核心记忆内容（自然语言描述）
            category (str):     分类，如 '用户偏好'、'决策历史'、'事实'
            importance (float): 0~1 重要性
            metadata (dict):    其他扩展元数据
    """
    try:
        # 解析 JSON 字符串输入
        try:
            parsed_value = json.loads(memory_value)
        except json.JSONDecodeError as e:
            return f"❌ memory_value 不是合法的 JSON 字符串: {e}"
        if not isinstance(parsed_value, dict):
            return "❌ memory_value 必须是一个 JSON 对象（字典）"

        entry = dict(parsed_value)
        entry.setdefault(
            "timestamp",
            datetime.now(ZoneInfo("Asia/Shanghai")).strftime("%Y-%m-%d %H:%M")
        )
        entry.setdefault("importance", 0.5)
        entry.setdefault("metadata", {})

        await memory_store.upsert(memory_key, entry)
        return f"✅ 记忆已保存: {memory_key}"
    except Exception as e:
        logger.error("工具 save_memory 异常 | key=%s | error=%s", memory_key, e)
        return f"❌ 保存记忆失败: {e}"


@mcp.tool()
async def delete_memory(memory_key: str) -> str:
    """删除指定 ID 的记忆。

    Args:
        memory_key: 要删除的记忆键
    """
    try:
        await memory_store.delete(memory_key)
        return f"✅ 记忆已删除: {memory_key}"
    except Exception as e:
        logger.error("工具 delete_memory 异常 | key=%s | error=%s", memory_key, e)
        return f"❌ 删除记忆失败: {e}"


@mcp.tool()
async def search_memory(query: str) -> str:
    """搜索长期记忆库中的相关信息。

    Args:
        query: 搜索查询字符串
    """
    try:
        return await memory_store.search(query)
    except Exception as e:
        logger.error("工具 search_memory 异常 | query=%.50s... | error=%s", query, e)
        return f"❌ 搜索记忆失败: {e}"


@mcp.tool()
async def get_memory(memory_key: str) -> str:
    """精确获取指定 key 的记忆内容。

    Args:
        memory_key: 要获取的记忆键
    """
    try:
        result = await memory_store.get(memory_key)
        if result is None:
            return f"⚠️ 未找到记忆: {memory_key}"
        return json.dumps(result, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error("工具 get_memory 异常 | key=%s | error=%s", memory_key, e)
        return f"❌ 获取记忆失败: {e}"


@mcp.tool()
async def list_memory_keys() -> str:
    """列出所有已保存的记忆 key（最多 1000 个）。"""
    try:
        keys = await memory_store.list_keys()
        if not keys:
            return "📭 记忆库为空。"
        return "已保存的记忆 key:\n" + "\n".join(keys)
    except Exception as e:
        logger.error("工具 list_memory_keys 异常 | error=%s", e)
        return f"❌ 列出记忆 key 失败: {e}"


if __name__ == "__main__":
    setup_logging()
    logger.info("Memory MCP Server 启动")
    mcp.run(transport="stdio")
