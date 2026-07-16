"""RAG Pipeline 路由 —— Markdown 文档向量化入库、删除、健康检查及配置管理。"""

from fastapi import APIRouter, UploadFile, File, Query

from backend.api.services.rag_service import (
    process_files_by_path,
    process_uploaded_files,
    delete_documents,
    health_check,
    get_rag_config,
    update_rag_config,
)
from backend.api.schemas.rag_pipeline import (
    RAGProcessRequest,
    RAGProcessResponse,
    RAGDeleteRequest,
    RAGDeleteResponse,
    RAGHealthResponse,
    RAGFullConfigModel,
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


# ════════════════ 处理 / 入库（上传模式） ════════════════
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
