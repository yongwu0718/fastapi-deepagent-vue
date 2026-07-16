import json
import os
from typing import Any, Dict, Optional

from langchain.tools import tool, ToolRuntime
from langchain_chroma import Chroma
from langchain_core.documents import Document
from config.env import COLLECTION_MEMORY_NAME, CHROMA_MEMORY_DB
from config.model_config import embeddings


class MemoryStore:
    """记忆向量存储的封装，负责初始化和管理 Chroma 集合。"""

    def __init__(
        self,
        collection_name: str = "memory",
        persist_directory: str = "./chroma_db",
    ):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.vectorstore = self._create_vectorstore()

    def _create_vectorstore(self) -> Chroma:
        try:
            return Chroma(
                collection_name=self.collection_name,
                embedding_function=embeddings,
                persist_directory=self.persist_directory,
            )
        except Exception as e:
            raise RuntimeError(f"创建记忆向量存储失败: {e}")

    async def save(self, memory_key: str, memory_value: Dict[str, Any]) -> None:
        """保存一条记忆到向量数据库（存在则覆盖）。

        Args:
            memory_key: 记忆的唯一标识（作为文档 ID）。
            memory_value: 记忆内容，会被序列化为 JSON 存储。
        """
        memory_text = json.dumps(memory_value, ensure_ascii=False)

        # 显式设置 id 为 memory_key，确保后续可更新/删除
        doc = Document(
            page_content=memory_text,
            metadata={"type": "memory", "key": memory_key},
            id=memory_key,
        )

        if hasattr(self.vectorstore, "aadd_documents"):
            await self.vectorstore.aadd_documents([doc])
        else:
            import asyncio
            await asyncio.to_thread(self.vectorstore.add_documents, [doc])

    async def update(self, memory_key: str, memory_value: Dict[str, Any]) -> None:
        """更新指定 memory_key 的记忆内容。

        Args:
            memory_key: 要更新的记忆 ID。
            memory_value: 新的记忆内容（字典）。
        """
        memory_text = json.dumps(memory_value, ensure_ascii=False)
        doc = Document(
            page_content=memory_text,
            metadata={"type": "memory", "key": memory_key},
            id=memory_key,
        )

        if hasattr(self.vectorstore, "aupdate_documents"):
            # 如果有异步方法直接使用
            await self.vectorstore.aupdate_documents([memory_key], [doc])
        else:
            import asyncio
            await asyncio.to_thread(
                self.vectorstore.update_documents, [memory_key], [doc]
            )

    async def delete(self, memory_key: str) -> None:
        """删除指定 memory_key 的记忆。

        Args:
            memory_key: 要删除的记忆 ID。
        """
        if hasattr(self.vectorstore, "adelete"):
            await self.vectorstore.adelete(ids=[memory_key])
        else:
            import asyncio
            await asyncio.to_thread(self.vectorstore.delete, ids=[memory_key])

    async def search(self, query: str, k: int = 3) -> str:
        """搜索相关记忆。

        Args:
            query: 查询文本。
            k: 返回的最相关记忆数量。

        Returns:
            格式化的搜索结果字符串。
        """
        if hasattr(self.vectorstore, "asimilarity_search"):
            docs = await self.vectorstore.asimilarity_search(query, k=k)
        else:
            import asyncio
            docs = await asyncio.to_thread(
                self.vectorstore.similarity_search, query, k=k
            )

        if not docs:
            return "没有找到相关记忆。"

        results = []
        for doc in docs:
            results.append(f"[{doc.metadata.get('key', 'unknown')}]: {doc.page_content}")
        return "\n".join(results)

# ------------------ 全局单例 ------------------
memory_store = MemoryStore(
    collection_name=COLLECTION_MEMORY_NAME,
    persist_directory=CHROMA_MEMORY_DB,
)

# ------------------ 工具定义 ------------------
@tool
async def save_memory(
    memory_key: str,
    memory_value: Dict[str, Any],
) -> str:
    """将信息保存到长期记忆库（若 key 已存在则覆盖）。

    参数:
        memory_key: 记忆的唯一标识符（作为文档 ID）。
        memory_value: 需要持久化的记忆内容，可以是任意 JSON 可序列化的字典。
    """
    try:
        await memory_store.save(memory_key, memory_value)
        return f"✅ 记忆已保存: {memory_key}"
    except Exception as e:
        return f"❌ 保存记忆失败: {e}"


@tool
async def update_memory(
    memory_key: str,
    memory_value: Dict[str, Any],
) -> str:
    """更新已存在的记忆内容。

    参数:
        memory_key: 要更新的记忆 ID。
        memory_value: 新的记忆内容（字典）。
    """
    try:
        await memory_store.update(memory_key, memory_value)
        return f"✅ 记忆已更新: {memory_key}"
    except Exception as e:
        return f"❌ 更新记忆失败: {e}"


@tool
async def delete_memory(
    memory_key: str,
) -> str:
    """删除指定 ID 的记忆。

    参数:
        memory_key: 要删除的记忆 ID。
    """
    try:
        await memory_store.delete(memory_key)
        return f"✅ 记忆已删除: {memory_key}"
    except Exception as e:
        return f"❌ 删除记忆失败: {e}"


@tool
async def search_memory(
    query: str,
) -> str:
    """搜索长期记忆库中的相关信息。

    参数:
        query: 用于匹配记忆的自然语言查询。
    """
    try:
        return await memory_store.search(query)
    except Exception as e:
        return f"❌ 搜索记忆失败: {e}"