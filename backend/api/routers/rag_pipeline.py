"""RAG Pipeline 路由 —— Markdown 文档向量化入库、删除、健康检查及配置管理。"""

from fastapi import APIRouter, UploadFile, File, Query

from backend.api.services.rag_service import (
    process_files_by_path,
    process_uploaded_files,
    delete_documents,
    health_check,
    get_rag_config,
    update_rag_config,
    list_collections,
    get_collection_stats,
    get_collection_documents,
    delete_collection_docs,
    clear_collection,
    delete_collection,
)
from backend.api.schemas.rag_pipeline import (
    RAGProcessRequest,
    RAGProcessResponse,
    RAGDeleteRequest,
    RAGDeleteResponse,
    RAGHealthResponse,
    RAGFullConfigModel,
    CollectionListResponse,
    CollectionStatsResponse,
    CollectionDocumentsResponse,
    DeleteDocsRequest,
    DeleteDocsResponse,
    ClearCollectionResponse,
    DeleteCollectionResponse,
)
from backend.api.utils.error_handlers import handle_endpoint_errors
from backend.api.utils.exceptions import ErrorCode
from backend.config.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/rag", tags=["rag-pipeline"])


# ════════════════ 处理 / 入库（本地路径模式） ════════════════
@router.post("/process", response_model=RAGProcessResponse)
@handle_endpoint_errors(
    ErrorCode.RAG_PROCESS_FAILED,
    log_msg="RAG 处理异常（路径模式） | paths={body.files}",
    detail_msg="RAG 文档处理失败",
)
async def process_rag_endpoint(body: RAGProcessRequest):
    """通过文件路径处理 .md 文档（JSON body 模式）。"""
    logger.info("POST /api/rag/process | paths=%d | preview_only=%s", len(body.files), body.preview_only)
    return await process_files_by_path(
        file_paths=body.files,
        preview_dir=body.preview_dir,
        preview_only=body.preview_only,
    )

# ════════════════ 处理 / 入库（上传模式） ═══════════════
@router.post("/process/upload", response_model=RAGProcessResponse)
@handle_endpoint_errors(
    ErrorCode.RAG_PROCESS_FAILED,
    log_msg="RAG 处理异常（上传模式） | files={files}",
    detail_msg="RAG 文档处理失败",
)
async def process_upload_endpoint(
    files: list[UploadFile] = File(..., description="待处理的 .md 文件，支持批量上传"),
    preview_only: bool = Query(False, description="仅预览分块而不入库"),
):
    """上传 markdown 文件，完成分割、（可选）入库（multipart 模式）。"""
    logger.info("POST /api/rag/process/upload | files=%d | preview_only=%s", len(files), preview_only)
    return await process_uploaded_files(files=files, preview_only=preview_only)

# ════════════════ 删除 ════════════════
@router.post("/delete", response_model=RAGDeleteResponse)
@handle_endpoint_errors(
    ErrorCode.RAG_DELETE_FAILED,
    log_msg="RAG 删除异常 | ids={body.ids}",
    detail_msg="删除文档失败",
)
async def delete_rag_endpoint(body: RAGDeleteRequest):
    """按 ID 从向量库中删除文档。"""
    logger.info("POST /api/rag/delete | ids=%d", len(body.ids))
    return await delete_documents(ids=body.ids)

# ════════════════ 健康检查 ════════════════
@router.get("/health", response_model=RAGHealthResponse)
@handle_endpoint_errors(
    ErrorCode.RAG_VECTORSTORE_ERROR,
    log_msg="RAG 健康检查异常",
    detail_msg="向量库健康检查失败",
)
async def health_rag_endpoint():
    """检查向量库健康状态。"""
    logger.info("GET /api/rag/health")
    return await health_check()

# ════════════════ 配置管理 ════════════════
@router.get("/config")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="RAG 配置读取异常",
    detail_msg="RAG 配置读取失败",
)
async def get_rag_config_endpoint():
    """读取 rag_config.yaml 完整配置。"""
    logger.info("GET /api/rag/config")
    return await get_rag_config()

@router.put("/config")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="RAG 配置写入异常",
    detail_msg="RAG 配置更新失败",
)
async def update_rag_config_endpoint(body: RAGFullConfigModel):
    """覆写 rag_config.yaml，自动重载运行时配置。"""
    logger.info("PUT /api/rag/config")
    return await update_rag_config(body)

# ═══════════════════════════════════════════
#  ChromaDB 数据浏览端点
# ═══════════════════════════════════════════
@router.get("/collections", response_model=CollectionListResponse)
@handle_endpoint_errors(
    ErrorCode.RAG_VECTORSTORE_ERROR,
    log_msg="列出集合异常",
    detail_msg="获取集合列表失败",
)
async def list_collections_endpoint():
    """列出 ChromaDB 中所有集合。"""
    logger.info("GET /api/rag/collections")
    return await list_collections()

@router.get("/collection/{collection_name}/stats", response_model=CollectionStatsResponse)
@handle_endpoint_errors(
    ErrorCode.RAG_VECTORSTORE_ERROR,
    log_msg="获取集合统计异常 | collection={collection_name}",
    detail_msg="获取集合统计信息失败",
)
async def collection_stats_endpoint(
    collection_name: str,
    sample_limit: int = Query(5000, ge=100, le=100000, description="统计采样上限"),
):
    """获取指定集合的统计信息（文档数、非空率、平均长度、向量维度、元数据覆盖率）。"""
    logger.info("GET /api/rag/collection/%s/stats | limit=%d", collection_name, sample_limit)
    return await get_collection_stats(collection_name, sample_limit)


@router.get("/collection/{collection_name}/documents", response_model=CollectionDocumentsResponse)
@handle_endpoint_errors(
    ErrorCode.RAG_VECTORSTORE_ERROR,
    log_msg="获取文档列表异常 | collection={collection_name}",
    detail_msg="获取文档列表失败",
)
async def collection_documents_endpoint(
    collection_name: str,
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=5, le=500, description="每页条数"),
):
    """分页获取集合中的文档（ID、内容、元数据）。"""
    logger.info("GET /api/rag/collection/%s/documents | page=%d | size=%d", collection_name, page, page_size)
    return await get_collection_documents(collection_name, page, page_size)


@router.post("/collection/{collection_name}/delete-docs", response_model=DeleteDocsResponse)
@handle_endpoint_errors(
    ErrorCode.RAG_DELETE_FAILED,
    log_msg="删除文档异常 | collection={collection_name} | ids={body.ids}",
    detail_msg="删除文档失败",
)
async def delete_collection_docs_endpoint(collection_name: str, body: DeleteDocsRequest):
    """从指定集合中批量删除文档。"""
    logger.info("POST /api/rag/collection/%s/delete-docs | ids=%d", collection_name, len(body.ids))
    return await delete_collection_docs(collection_name, body.ids)


@router.post("/collection/{collection_name}/clear", response_model=ClearCollectionResponse)
@handle_endpoint_errors(
    ErrorCode.RAG_DELETE_FAILED,
    log_msg="清空集合异常 | collection={collection_name}",
    detail_msg="清空集合失败",
)
async def clear_collection_endpoint(collection_name: str):
    """清空集合中的所有文档。"""
    logger.info("POST /api/rag/collection/%s/clear", collection_name)
    return await clear_collection(collection_name)


@router.delete("/collection/{collection_name}", response_model=DeleteCollectionResponse)
@handle_endpoint_errors(
    ErrorCode.RAG_DELETE_FAILED,
    log_msg="删除集合异常 | collection={collection_name}",
    detail_msg="删除集合失败",
)
async def delete_collection_endpoint(collection_name: str):
    """删除整个集合。"""
    logger.info("DELETE /api/rag/collection/%s", collection_name)
    return await delete_collection(collection_name)
