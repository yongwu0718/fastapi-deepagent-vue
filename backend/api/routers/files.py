"""文件目录路由 —— 目录浏览 & 文件下载 & 上传 & 修改 & 删除。"""

from fastapi import APIRouter, Query, UploadFile, File as UploadFileParam
from fastapi.responses import FileResponse

from backend.api.services.file_service import (
    list_directory,
    get_file_path,
    read_file_content,
    create_file,
    create_directory,
    upload_file,
    rename_path,
    move_path,
    modify_file_content,
    delete_path,
    search_files,
)
from backend.api.schemas.files import (
    CreateFileRequest,
    CreateDirectoryRequest,
    RenameRequest,
    ModifyFileRequest,
    MoveRequest,
    DeleteRequest,
)
from backend.api.utils.error_handlers import handle_endpoint_errors
from backend.api.utils.exceptions import ErrorCode
from backend.config.logger import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/files", tags=["files"])


# ════════════════ 读取 ════════════════
@router.get("/list")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="目录列表异常 | path={path}",
    detail_msg="目录列表失败: path={path}",
)
async def list_directory_endpoint(path: str = Query(default="", description="相对于根目录的路径，空字符串表示根目录")):
    """返回指定目录的文件和子目录列表（文件夹优先、按名称排序）。"""
    logger.info("GET /api/files/list | path=%s", path or "/")
    return await list_directory(path)


@router.get("/file")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="文件读取异常 | path={path}",
    detail_msg="文件读取失败: path={path}",
)
async def get_file_endpoint(path: str = Query(..., description="相对于根目录的文件路径")):
    """读取文件内容，直接返回文件（支持浏览器预览或下载）。"""
    logger.info("GET /api/files/file | path=%s", path)
    file_path = await get_file_path(path)
    return FileResponse(file_path)


@router.get("/read")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="文件读取异常 | path={path}",
    detail_msg="文件读取失败: path={path}",
)
async def read_file_endpoint(path: str = Query(..., description="相对于根目录的文件路径")):
    """读取文件内容，返回 JSON（含内容、类型、是否可编辑）。"""
    logger.info("GET /api/files/read | path=%s", path)
    return await read_file_content(path)


@router.get("/search")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="文件搜索异常 | q={q}",
    detail_msg="文件搜索失败: q={q}",
)
async def search_files_endpoint(q: str = Query(..., description="搜索关键词", min_length=1)):
    """递归搜索根目录下所有匹配名称的文件和目录。"""
    logger.info("GET /api/files/search | q=%s", q)
    return await search_files(q)


# ════════════════ 上传 / 创建 ════════════════
@router.post("/create-file")
@handle_endpoint_errors(
    ErrorCode.FILE_CREATE_FAILED,
    log_msg="创建文件异常 | path={body.path}",
    detail_msg="创建文件失败: path={body.path}",
)
async def create_file_endpoint(body: CreateFileRequest):
    """创建新文件（可指定初始内容）。"""
    logger.info("POST /api/files/create-file | path=%s", body.path)
    return await create_file(body.path, body.content)


@router.post("/create-directory")
@handle_endpoint_errors(
    ErrorCode.DIR_CREATE_FAILED,
    log_msg="创建目录异常 | path={body.path}",
    detail_msg="创建目录失败: path={body.path}",
)
async def create_directory_endpoint(body: CreateDirectoryRequest):
    """创建新目录。"""
    logger.info("POST /api/files/create-directory | path=%s", body.path)
    return await create_directory(body.path)


@router.post("/upload")
@handle_endpoint_errors(
    ErrorCode.FILE_UPLOAD_FAILED,
    log_msg="文件上传异常 | path={path}",
    detail_msg="文件上传失败: path={path}",
)
async def upload_file_endpoint(
    path: str = Query(..., description="目标相对路径（含文件名），如 docs/readme.md"),
    file: UploadFile = UploadFileParam(...),
):
    """上传文件到指定路径。"""
    logger.info("POST /api/files/upload | path=%s | filename=%s", path, file.filename)
    content = await file.read()
    return await upload_file(path, content)


# ════════════════ 修改 ════════════════
@router.put("/rename")
@handle_endpoint_errors(
    ErrorCode.FILE_MODIFY_FAILED,
    log_msg="重命名异常 | path={body.path}",
    detail_msg="重命名失败: path={body.path}",
)
async def rename_endpoint(body: RenameRequest):
    """重命名文件或目录。"""
    logger.info("PUT /api/files/rename | %s → %s", body.path, body.new_name)
    return await rename_path(body.path, body.new_name)


@router.put("/move")
@handle_endpoint_errors(
    ErrorCode.FILE_MODIFY_FAILED,
    log_msg="移动异常 | path={body.path}",
    detail_msg="移动失败: path={body.path}",
)
async def move_endpoint(body: MoveRequest):
    """移动文件或目录到目标目录。"""
    logger.info("PUT /api/files/move | %s → %s", body.path, body.target_dir or "/")
    return await move_path(body.path, body.target_dir)


@router.put("/modify")
@handle_endpoint_errors(
    ErrorCode.FILE_MODIFY_FAILED,
    log_msg="修改文件异常 | path={body.path}",
    detail_msg="修改文件失败: path={body.path}",
)
async def modify_file_endpoint(body: ModifyFileRequest):
    """修改文件内容（覆盖写入）。"""
    logger.info("PUT /api/files/modify | path=%s | content_len=%d", body.path, len(body.content))
    return await modify_file_content(body.path, body.content)


# ════════════════ 删除 ════════════════
@router.delete("/delete")
@handle_endpoint_errors(
    ErrorCode.FILE_DELETE_FAILED,
    log_msg="删除异常 | path={body.path}",
    detail_msg="删除失败: path={body.path}",
)
async def delete_endpoint(body: DeleteRequest):
    """删除文件或目录（递归删除目录及其所有内容）。"""
    logger.info("DELETE /api/files/delete | path=%s", body.path)
    return await delete_path(body.path)
