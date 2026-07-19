"""RAG Pipeline 业务逻辑 —— 接收上传文件，完成分割、向量化入库、删除操作。"""

import os
import asyncio
import yaml
from typing import Optional, Any

from fastapi import UploadFile
from langchain_chroma import Chroma
from langchain_core.documents import Document

from backend.api.markdown_rag import rag_setting as _rag
from backend.api.markdown_rag.save_VectorStore import (
    MarkdownSplitter,
    VectorStoreCreator,
)
from backend.api.schemas.rag_pipeline import (
    ChunkDetail,
    RAGProcessResult,
    RAGProcessResponse,
    RAGDeleteResponse,
    RAGHealthResponse,
    SplitConfig,
    RAGFullConfigModel,
    CollectionInfo,
    CollectionListResponse,
    CollectionStatsResponse,
    CollectionDocument,
    CollectionDocumentsResponse,
    DeleteDocsResponse,
    ClearCollectionResponse,
    DeleteCollectionResponse,
)
from backend.api.utils.exceptions import AppException, ErrorCode
from backend.config.logger import get_logger

logger = get_logger(__name__)

# ── 支持的扩展名 ──
SUPPORTED_RAG_EXTENSIONS = {".md"}

# ── 向量库单例 ──
_vectorstore: Optional[Chroma] = None


def _get_vectorstore() -> Chroma:
    """获取或初始化 Chroma 向量库实例（单例）。"""
    global _vectorstore
    if _vectorstore is None:
        try:
            creator = VectorStoreCreator(
                collection_name=_rag.RAG_COLLECTION_NAME,
                persist_directory=_rag.RAG_PERSIST_DIR,
                model=_rag.EMBEDDING_MODEL,
                base_url=_rag.EMBEDDING_BASE_URL,
            )
            _vectorstore = creator.vectorstore
            logger.info("向量库已初始化 | collection=%s | dir=%s", _rag.RAG_COLLECTION_NAME, _rag.RAG_PERSIST_DIR)
        except Exception as e:
            logger.exception("向量库初始化失败")
            raise AppException(
                status_code=500,
                error_code=ErrorCode.RAG_VECTORSTORE_ERROR,
                detail=f"向量库初始化失败: {e}",
            )
    return _vectorstore


def _build_split_config() -> SplitConfig:
    """构造当前分割配置（用于返回给前端）。"""
    return SplitConfig(
        headers=list(_rag.RAG_SPLITTER_HEADERS),
        return_each_line=_rag.RAG_SPLITTER_RETURN_EACH_LINE,
        strip_headers=_rag.RAG_SPLITTER_STRIP_HEADERS,
        enable_char_split=_rag.RAG_ENABLE_CHAR_SPLIT,
        chunk_size=_rag.RAG_CHUNK_SIZE,
        chunk_overlap=_rag.RAG_CHUNK_OVERLAP,
    )


def _extract_header_path(chunk: Document) -> Optional[str]:
    """从 Document.metadata 中提取标题路径。

    ExperimentalMarkdownSyntaxTextSplitter 会给每个 chunk 附加类似
    ``{"Header 1": "xxx", "Header 2": "yyy"}`` 的元数据，
    这里按层级拼接成 "# 概述 > ## 背景"。
    """
    path_parts: list[str] = []
    for level in range(1, len(_rag.RAG_SPLITTER_HEADERS) + 1):
        key = f"Header {level}"
        val = chunk.metadata.get(key)
        if val is not None:
            # ExperimentalMarkdownSyntaxTextSplitter 返回的是完整标题行
            val_str = str(val).strip()
            if val_str:
                path_parts.append(val_str)
    return " > ".join(path_parts) if path_parts else None


def _build_chunk_details(chunks: list[Document]) -> list[ChunkDetail]:
    """遍历分块列表，构造 ChunkDetail 列表。"""
    details: list[ChunkDetail] = []
    for i, chunk in enumerate(chunks):
        content = chunk.page_content
        header_path = _extract_header_path(chunk)
        # 如果 chunk 已经被二级字符切分切过，RecursiveCharacterTextSplitter
        # 不会添加新的元数据，但标题路径可能会保留下来
        details.append(ChunkDetail(
            index=i + 1,
            content_length=len(content),
            preview=content,
            header_path=header_path,
            is_char_split=bool(_rag.RAG_ENABLE_CHAR_SPLIT and len(content) <= _rag.RAG_CHUNK_SIZE),
        ))
    return details


def _write_enhanced_preview(
    chunks: list[Document],
    details: list[ChunkDetail],
    output_path: str,
    filename: str,
) -> None:
    """生成增强版预览 — 每块标注序号、大小、标题路径。"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    lines: list[str] = []
    lines.append(f"# 分块预览: {filename}")
    lines.append("")
    lines.append(f"**总块数**: {len(chunks)}")
    lines.append("")
    lines.append("---")
    lines.append("")

    for detail, chunk in zip(details, chunks):
        lines.append(f"## Chunk {detail.index}")
        lines.append("")
        lines.append(f"- **字符数**: {detail.content_length}")
        if detail.header_path:
            lines.append(f"- **标题路径**: {detail.header_path}")
        lines.append("")
        lines.append(chunk.page_content)
        lines.append("")
        lines.append("---")
        lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info("增强预览已写入 | path=%s | chunks=%d", output_path, len(details))


async def _process_one_file(
    filename: str,
    md_text: str,
    file_size: int,
    splitter: MarkdownSplitter,
    vectorstore: Chroma,
    output_preview_dir: str,
    loop: asyncio.AbstractEventLoop,
    preview_only: bool = False,
) -> RAGProcessResult:
    """处理单个文件的核心逻辑：格式校验 → 分块 → 预览 →（可选）入库。

    Args:
        filename: 文件名（用于日志和结果）
        md_text: 文件文本内容
        file_size: 文件字节数
        splitter: 已初始化的分割器
        vectorstore: 向量库实例
        output_preview_dir: 预览输出目录
        loop: 事件循环
        preview_only: True 时只预览分块，不写入向量库

    Returns:
        RAGProcessResult
    """
    # ── 1. 校验格式 ──
    ext = os.path.splitext(filename.lower())[1]
    if ext not in SUPPORTED_RAG_EXTENSIONS:
        raise ValueError(
            f"不支持的文件格式: {ext}（仅支持 {', '.join(SUPPORTED_RAG_EXTENSIONS)}）"
        )

    if not md_text.strip():
        raise ValueError("文件内容为空")

    # ── 2. 分块 ──
    chunks: list[Document] = await loop.run_in_executor(
        None, splitter.split_by_headers, md_text,
    )
    logger.info("分块完成 | file=%s | chunks=%d | preview_only=%s", filename, len(chunks), preview_only)

    # ── 3. 构建分块详情 ──
    chunk_details = _build_chunk_details(chunks)

    # ── 4. 生成预览文件 ──
    base_name = os.path.splitext(filename)[0]
    preview_path = os.path.join(output_preview_dir, f"{base_name}_chunks_preview.md")
    await loop.run_in_executor(
        None, _write_enhanced_preview, chunks, chunk_details, preview_path, filename,
    )

    # ── 5. 入库（preview_only 模式下跳过）──
    if not preview_only and chunks:
        await loop.run_in_executor(None, lambda: vectorstore.add_documents(chunks))
        logger.info("入库完成 | file=%s | chunks=%d", filename, len(chunks))

    return RAGProcessResult(
        filename=filename,
        file_size=file_size,
        chunks_count=len(chunks),
        status="success",
        chunks=chunk_details,
    )


async def _process_batch(
    items: list[tuple[str, str, int]],
    preview_dir: Optional[str] = None,
    preview_only: bool = False,
) -> RAGProcessResponse:
    """批量处理文件内容列表的可复用流水线。

    Args:
        items: [(filename, md_text, file_size), ...]
        preview_dir: 预览输出目录
        preview_only: True 时仅预览分块不写入向量库
    """
    results: list[RAGProcessResult] = []
    success_count = 0
    failed_count = 0
    total_chunks = 0
    split_config = _build_split_config()

    try:
        vectorstore = _get_vectorstore()
    except AppException:
        raise

    splitter = MarkdownSplitter()
    output_preview_dir = preview_dir or _rag.RAG_PROCESSING_PREVIEW_DIR
    loop = asyncio.get_running_loop()

    for filename, md_text, file_size in items:
        try:
            logger.info("开始处理 | file=%s | size=%d", filename, file_size)
            result = await _process_one_file(
                filename=filename,
                md_text=md_text,
                file_size=file_size,
                splitter=splitter,
                vectorstore=vectorstore,
                output_preview_dir=output_preview_dir,
                loop=loop,
                preview_only=preview_only,
            )
            results.append(result)
            success_count += 1
            total_chunks += result.chunks_count

        except UnicodeDecodeError:
            failed_count += 1
            logger.warning("文件编码错误 | file=%s", filename)
            results.append(RAGProcessResult(
                filename=filename, file_size=0, chunks_count=0,
                status="error", error="文件编码不是合法的 UTF-8",
            ))

        except ValueError as e:
            failed_count += 1
            logger.warning("文件校验失败 | file=%s | error=%s", filename, e)
            results.append(RAGProcessResult(
                filename=filename, file_size=0, chunks_count=0,
                status="error", error=str(e),
            ))

        except Exception:
            failed_count += 1
            logger.exception("文件处理异常 | file=%s", filename)
            results.append(RAGProcessResult(
                filename=filename, file_size=0, chunks_count=0,
                status="error", error="处理过程中发生未知错误",
            ))

    try:
        collection_count = vectorstore._collection.count()
    except Exception:
        collection_count = -1

    return RAGProcessResponse(
        total_files=len(items),
        success_count=success_count,
        failed_count=failed_count,
        total_chunks=total_chunks,
        collection_count=collection_count,
        split_config=split_config,
        results=results,
    )


# ═══════════════════════════════════════════
#  公开接口：两种输入模式
# ═══════════════════════════════════════════

async def process_files_by_path(
    file_paths: list[str],
    preview_dir: Optional[str] = None,
    preview_only: bool = False,
) -> RAGProcessResponse:
    """【本地路径模式】从磁盘读取 .md 文件并处理入库。

    Args:
        file_paths: 文件绝对路径列表。
        preview_dir: 预览输出目录。
        preview_only: True 时仅预览分块不写入向量库。
    """
    items: list[tuple[str, str, int]] = []

    for file_path in file_paths:
        try:
            if not os.path.isfile(file_path):
                raise FileNotFoundError(f"文件不存在: {file_path}")

            filename = os.path.basename(file_path)
            with open(file_path, "r", encoding="utf-8") as f:
                md_text = f.read()
            file_size = os.path.getsize(file_path)

            items.append((filename, md_text, file_size))

        except FileNotFoundError as e:
            logger.warning("文件未找到 | path=%s", file_path)
            items.append((os.path.basename(file_path), f"__ERROR__{e}", 0))

        except UnicodeDecodeError:
            logger.warning("文件编码错误 | path=%s", file_path)
            items.append((os.path.basename(file_path), "__ERROR_UTF8__", 0))

    return await _process_batch(items, preview_dir, preview_only)


async def process_uploaded_files(
    files: list[UploadFile],
    preview_dir: Optional[str] = None,
    preview_only: bool = False,
) -> RAGProcessResponse:
    """【上传模式】从 multipart form 解码 .md 文件并处理入库。

    Args:
        files: 上传的 UploadFile 列表。
        preview_dir: 预览输出目录。
        preview_only: True 时仅预览分块不写入向量库。
    """
    items: list[tuple[str, str, int]] = []

    for file in files:
        filename = file.filename or "unknown.md"
        try:
            content_bytes = await file.read()
            file_size = len(content_bytes)
            md_text = content_bytes.decode("utf-8")
            items.append((filename, md_text, file_size))
        except UnicodeDecodeError:
            logger.warning("文件编码错误 | file=%s", filename)
            items.append((filename, "__ERROR_UTF8__", 0))

    return await _process_batch(items, preview_dir, preview_only)


async def delete_documents(ids: list[str]) -> RAGDeleteResponse:
    """从向量库中删除指定 ID 的文档。"""
    try:
        vectorstore = _get_vectorstore()
    except AppException:
        raise

    try:
        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, vectorstore.delete, ids)
        deleted_count = len(ids)

        collection_count = vectorstore._collection.count()
        logger.info("文档删除成功 | deleted=%d | remaining=%d", deleted_count, collection_count)

        return RAGDeleteResponse(
            deleted_count=deleted_count,
            collection_count=collection_count,
            message=f"已删除 {deleted_count} 个文档",
        )

    except Exception as e:
        logger.exception("文档删除失败 | ids=%s", ids)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.RAG_DELETE_FAILED,
            detail=f"删除文档失败: {e}",
        )


async def health_check() -> RAGHealthResponse:
    """检查向量库健康状态。"""
    try:
        vectorstore = _get_vectorstore()
    except AppException:
        raise

    try:
        collection_count = vectorstore._collection.count()
    except Exception as e:
        logger.exception("向量库健康检查失败")
        raise AppException(
            status_code=500,
            error_code=ErrorCode.RAG_VECTORSTORE_ERROR,
            detail=f"无法获取向量库状态: {e}",
        )

    return RAGHealthResponse(
        collection_name=_rag.RAG_COLLECTION_NAME,
        collection_count=collection_count,
        persist_directory=_rag.RAG_PERSIST_DIR,
        embedding_model=_rag.EMBEDDING_MODEL,
        embedding_base_url=_rag.EMBEDDING_BASE_URL,
    )


# ═══════════════════════════════════════════
#  ChromaDB 直连（数据浏览）
# ═══════════════════════════════════════════

import chromadb
from chromadb.api import ClientAPI as ChromaClientAPI

_chroma_client: Optional[ChromaClientAPI] = None


def _get_chroma_client() -> ChromaClientAPI:
    """获取 chromadb.PersistentClient 直连实例（不经过 LangChain 封装）。"""
    global _chroma_client
    if _chroma_client is None:
        _chroma_client = chromadb.PersistentClient(path=_rag.RAG_PERSIST_DIR)
        logger.info("ChromaDB 直连客户端已初始化 | dir=%s", _rag.RAG_PERSIST_DIR)
    return _chroma_client


async def list_collections() -> CollectionListResponse:
    """列出 ChromaDB 中所有集合。"""
    try:
        client = _get_chroma_client()
        loop = asyncio.get_running_loop()
        collections = await loop.run_in_executor(None, client.list_collections)

        result: list[CollectionInfo] = []
        for col in collections:
            col_count = await loop.run_in_executor(None, col.count)
            result.append(CollectionInfo(name=col.name, count=col_count))

        logger.info("列出集合 | count=%d", len(result))
        return CollectionListResponse(collections=result)

    except Exception as e:
        logger.exception("列出集合失败")
        raise AppException(
            status_code=500,
            error_code=ErrorCode.RAG_VECTORSTORE_ERROR,
            detail=f"列出集合失败: {e}",
        )


async def get_collection_stats(collection_name: str, sample_limit: int = 5000) -> CollectionStatsResponse:
    """获取指定集合的统计信息。"""
    try:
        client = _get_chroma_client()
        loop = asyncio.get_running_loop()

        collection = await loop.run_in_executor(None, client.get_collection, collection_name)
        total_count = await loop.run_in_executor(None, collection.count)

        if total_count == 0:
            return CollectionStatsResponse(
                collection_name=collection_name,
                total_count=0,
                sampled_count=0,
                non_empty_count=0,
                empty_count=0,
                empty_rate="0%",
                avg_doc_length=0,
                vector_dimension=None,
                metadata_coverage=[],
            )

        actual_limit = min(total_count, sample_limit)
        sample = await loop.run_in_executor(
            None, lambda: collection.get(limit=actual_limit, include=["documents", "metadatas", "embeddings"]),
        )

        docs = sample.get("documents") or []
        metas = sample.get("metadatas") or []
        embeddings = sample.get("embeddings") or []

        # 文档统计
        non_empty = 0
        total_length = 0
        for doc in docs:
            if doc and isinstance(doc, str) and len(doc.strip()) > 0:
                non_empty += 1
                total_length += len(doc)
        empty_count = len(docs) - non_empty
        avg_length = total_length / non_empty if non_empty > 0 else 0
        empty_rate = f"{non_empty / len(docs) * 100:.1f}%" if docs else "0%"

        # 向量维度
        vector_dim = None
        if embeddings and len(embeddings) > 0 and embeddings[0]:
            vector_dim = len(embeddings[0])

        # 元数据覆盖率
        coverage_list: list[dict] = []
        if metas:
            all_keys: set[str] = set()
            key_counts: dict[str, int] = {}
            for meta in metas:
                if isinstance(meta, dict):
                    for k in meta.keys():
                        all_keys.add(k)
                        key_counts[k] = key_counts.get(k, 0) + 1
            for k in sorted(all_keys):
                cnt = key_counts.get(k, 0)
                coverage_list.append({
                    "field": k,
                    "count": cnt,
                    "coverage": f"{cnt / len(metas) * 100:.1f}%",
                })

        logger.info(
            "获取集合统计 | collection=%s | total=%d | sampled=%d | avg_len=%.0f | dim=%s",
            collection_name, total_count, actual_limit, avg_length, vector_dim,
        )

        return CollectionStatsResponse(
            collection_name=collection_name,
            total_count=total_count,
            sampled_count=actual_limit,
            non_empty_count=non_empty,
            empty_count=empty_count,
            empty_rate=empty_rate,
            avg_doc_length=round(avg_length, 1),
            vector_dimension=vector_dim,
            metadata_coverage=coverage_list,
        )

    except Exception as e:
        logger.exception("获取集合统计失败 | collection=%s", collection_name)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.RAG_VECTORSTORE_ERROR,
            detail=f"获取集合统计失败: {e}",
        )


async def get_collection_documents(
    collection_name: str, page: int = 1, page_size: int = 20,
) -> CollectionDocumentsResponse:
    """分页获取集合中的文档。"""
    try:
        client = _get_chroma_client()
        loop = asyncio.get_running_loop()

        collection = await loop.run_in_executor(None, client.get_collection, collection_name)
        total = await loop.run_in_executor(None, collection.count)

        offset = (page - 1) * page_size
        data = await loop.run_in_executor(
            None,
            lambda: collection.get(limit=page_size, offset=offset, include=["documents", "metadatas"]),
        )

        docs: list[CollectionDocument] = []
        ids = data.get("ids") or []
        documents = data.get("documents") or []
        metadatas = data.get("metadatas") or []

        for i in range(len(ids)):
            doc = CollectionDocument(
                id=ids[i],
                document=documents[i] if i < len(documents) else None,
                metadata=metadatas[i] if i < len(metadatas) else None,
            )
            docs.append(doc)

        logger.info("获取文档列表 | collection=%s | page=%d | size=%d | total=%d",
                     collection_name, page, page_size, total)

        return CollectionDocumentsResponse(
            collection_name=collection_name,
            page=page,
            page_size=page_size,
            total=total,
            documents=docs,
        )

    except Exception as e:
        logger.exception("获取文档列表失败 | collection=%s", collection_name)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.RAG_VECTORSTORE_ERROR,
            detail=f"获取文档列表失败: {e}",
        )


async def delete_collection_docs(collection_name: str, ids: list[str]) -> DeleteDocsResponse:
    """从指定集合中删除文档。"""
    try:
        client = _get_chroma_client()
        loop = asyncio.get_running_loop()

        collection = await loop.run_in_executor(None, client.get_collection, collection_name)
        await loop.run_in_executor(None, lambda: collection.delete(ids=ids))

        deleted_count = len(ids)
        logger.info("文档删除成功 | collection=%s | deleted=%d", collection_name, deleted_count)

        return DeleteDocsResponse(
            deleted_count=deleted_count,
            message=f"已从 {collection_name} 删除 {deleted_count} 个文档",
        )

    except Exception as e:
        logger.exception("删除文档失败 | collection=%s | ids=%s", collection_name, ids)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.RAG_DELETE_FAILED,
            detail=f"删除文档失败: {e}",
        )


async def clear_collection(collection_name: str) -> ClearCollectionResponse:
    """清空指定集合的全部数据。"""
    try:
        client = _get_chroma_client()
        loop = asyncio.get_running_loop()

        collection = await loop.run_in_executor(None, client.get_collection, collection_name)
        total = await loop.run_in_executor(None, collection.count)

        if total > 0:
            all_ids = await loop.run_in_executor(None, lambda: collection.get(include=[])["ids"])
            if all_ids:
                await loop.run_in_executor(None, lambda: collection.delete(ids=all_ids))

        logger.info("集合已清空 | collection=%s | deleted=%d", collection_name, total)

        return ClearCollectionResponse(
            deleted_count=total,
            collection_name=collection_name,
            message=f"集合 {collection_name} 已清空，共删除 {total} 条数据",
        )

    except Exception as e:
        logger.exception("清空集合失败 | collection=%s", collection_name)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.RAG_DELETE_FAILED,
            detail=f"清空集合失败: {e}",
        )


async def delete_collection(collection_name: str) -> DeleteCollectionResponse:
    """删除整个集合。"""
    try:
        client = _get_chroma_client()
        loop = asyncio.get_running_loop()

        await loop.run_in_executor(None, lambda: client.delete_collection(name=collection_name))

        # 如果删除的是当前 RAG 使用的集合，需要重置向量库单例
        if collection_name == _rag.RAG_COLLECTION_NAME:
            global _vectorstore
            _vectorstore = None
            logger.info("当前 RAG 集合已被删除，向量库单例已重置")

        logger.info("集合已删除 | collection=%s", collection_name)

        return DeleteCollectionResponse(
            collection_name=collection_name,
            message=f"集合 {collection_name} 已永久删除",
        )

    except Exception as e:
        logger.exception("删除集合失败 | collection=%s", collection_name)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.RAG_DELETE_FAILED,
            detail=f"删除集合失败: {e}",
        )


# ═══════════════════════════════════════════
#  rag_config.yaml 配置管理
# ═══════════════════════════════════════════

async def get_rag_config() -> dict[str, Any]:
    """读取 rag_config.yaml 配置（复用 rag_setting 的缓存，避免重复读取文件）。

    Returns:
        完整的配置 dict，可直接反序列化为 RAGFullConfigModel。
    """
    try:
        config = _rag.get_raw_rag_config()
        if not config:
            raise FileNotFoundError("RAG 配置为空，请检查 rag_config.yaml 和首次加载")
        logger.info("RAG 配置读取成功")
        return config

    except FileNotFoundError as e:
        raise AppException(
            status_code=404,
            error_code=ErrorCode.RAG_FILE_NOT_FOUND,
            detail=str(e),
        )
    except AppException:
        raise
    except Exception as e:
        logger.exception("RAG 配置读取异常")
        raise AppException(
            status_code=500,
            error_code=ErrorCode.INTERNAL_ERROR,
            detail=f"配置读取失败: {e}",
        )


async def update_rag_config(config: RAGFullConfigModel) -> dict[str, Any]:
    """验证并写入 rag_config.yaml，写入后自动重载配置。

    Args:
        config: 经过 Pydantic 校验的完整配置模型。

    Returns:
        {"status": "ok", "message": "..."}
    """
    try:
        config_path = _rag.get_rag_config_path()
        config_dir = os.path.dirname(config_path)

        # 确保目录存在
        os.makedirs(config_dir, exist_ok=True)

        # Pydantic model → dict（自动过滤 None 值）
        config_dict = config.model_dump(exclude_none=True)
        logger.info(
            "即将写入 YAML | collection=%s | persist=%s",
            config_dict.get("rag", {}).get("collection", {}).get("name", "N/A"),
            config_dict.get("rag", {}).get("collection", {}).get("persist_directory", "N/A"),
        )

        # 写入 YAML（保持可读性）
        yaml_content = yaml.dump(
            config_dict,
            allow_unicode=True,
            default_flow_style=False,
            sort_keys=False,
        )
        with open(config_path, "w", encoding="utf-8") as f:
            f.write(yaml_content)

        logger.info("RAG 配置文件写入成功 | path=%s | size=%d", config_path, len(yaml_content))

        # 重载运行时配置变量（先记下旧集合名，用于判断是否需要重置单例）
        old_collection = _rag.RAG_COLLECTION_NAME
        _rag.reload_rag_config()
        logger.info("RAG 运行时配置已重载")

        # 集合名称变了 → 重置向量库单例，下次自动连接新集合（旧集合数据不动）
        if _rag.RAG_COLLECTION_NAME != old_collection:
            global _vectorstore
            _vectorstore = None
            logger.info(
                "集合名称变更，向量库单例已重置 | old=%s | new=%s",
                old_collection, _rag.RAG_COLLECTION_NAME,
            )

        return {
            "status": "ok",
            "message": "RAG 配置已更新并生效",
            "path": config_path,
        }

    except yaml.YAMLError as e:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.VALIDATION_ERROR,
            detail=f"配置序列化失败: {e}",
        )
    except AppException:
        raise
    except Exception as e:
        logger.exception("RAG 配置写入异常")
        raise AppException(
            status_code=500,
            error_code=ErrorCode.INTERNAL_ERROR,
            detail=f"配置写入失败: {e}",
        )
