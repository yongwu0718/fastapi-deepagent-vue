from typing import Literal

from fastapi import APIRouter, Query, UploadFile, File as UploadFileParam
from fastapi.responses import FileResponse

from backend.api.services.memory_and_skill_service import (
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

router = APIRouter(prefix="/settings/memory-and-skill", tags=["memory-and-skill"])

_MemorySkillType = Literal["memory", "skills"]
_TYPE_DESC = "文件类型: 'memory'=记忆库, 'skills'=技能库"


# ════════════════ 读取 ════════════════
@router.get("/list")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="目录列表异常 | type={type} | path={path}",
    detail_msg="目录列表失败: path={path}",
)
async def list_directory_endpoint(
    type: _MemorySkillType = Query(..., description=_TYPE_DESC),
    path: str = Query(default="", description="相对于根目录的路径，空字符串表示根目录"),
):
    """返回指定目录的文件和子目录列表（文件夹优先、按名称排序）。"""
    logger.info("GET /settings/memory-and-skill/list | type=%s | path=%s", type, path or "/")
    return await list_directory(type, path)


@router.get("/file")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="文件读取异常 | type={type} | path={path}",
    detail_msg="文件读取失败: path={path}",
)
async def get_file_endpoint(
    type: _MemorySkillType = Query(..., description=_TYPE_DESC),
    path: str = Query(..., description="相对于根目录的文件路径"),
):
    """读取文件内容，直接返回文件（支持浏览器预览或下载）。"""
    logger.info("GET /settings/memory-and-skill/file | type=%s | path=%s", type, path)
    file_path = await get_file_path(type, path)
    return FileResponse(file_path)


@router.get("/read")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="文件读取异常 | type={type} | path={path}",
    detail_msg="文件读取失败: path={path}",
)
async def read_file_endpoint(
    type: _MemorySkillType = Query(..., description=_TYPE_DESC),
    path: str = Query(..., description="相对于根目录的文件路径"),
):
    """读取文件内容，返回 JSON（含内容、类型、是否可编辑）。"""
    logger.info("GET /settings/memory-and-skill/read | type=%s | path=%s", type, path)
    return await read_file_content(type, path)


@router.get("/search")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="文件搜索异常 | type={type} | q={q}",
    detail_msg="文件搜索失败: q={q}",
)
async def search_files_endpoint(
    type: _MemorySkillType = Query(..., description=_TYPE_DESC),
    q: str = Query(..., description="搜索关键词", min_length=1),
):
    """递归搜索根目录下所有匹配名称的文件和目录。"""
    logger.info("GET /settings/memory-and-skill/search | type=%s | q=%s", type, q)
    return await search_files(type, q)


# ════════════════ 上传 / 创建 ════════════════
@router.post("/create-file")
@handle_endpoint_errors(
    ErrorCode.FILE_CREATE_FAILED,
    log_msg="创建文件异常 | type={type} | path={body.path}",
    detail_msg="创建文件失败: path={body.path}",
)
async def create_file_endpoint(
    body: CreateFileRequest,
    type: _MemorySkillType = Query(..., description=_TYPE_DESC),
):
    """创建新文件（可指定初始内容）。"""
    logger.info("POST /settings/memory-and-skill/create-file | type=%s | path=%s", type, body.path)
    return await create_file(type, body.path, body.content)


@router.post("/create-directory")
@handle_endpoint_errors(
    ErrorCode.DIR_CREATE_FAILED,
    log_msg="创建目录异常 | type={type} | path={body.path}",
    detail_msg="创建目录失败: path={body.path}",
)
async def create_directory_endpoint(
    body: CreateDirectoryRequest,
    type: _MemorySkillType = Query(..., description=_TYPE_DESC),
):
    """创建新目录。"""
    logger.info("POST /settings/memory-and-skill/create-directory | type=%s | path=%s", type, body.path)
    return await create_directory(type, body.path)


@router.post("/upload")
@handle_endpoint_errors(
    ErrorCode.FILE_UPLOAD_FAILED,
    log_msg="文件上传异常 | type={type} | path={path}",
    detail_msg="文件上传失败: path={path}",
)
async def upload_file_endpoint(
    type: _MemorySkillType = Query(..., description=_TYPE_DESC),
    path: str = Query(..., description="目标相对路径（含文件名），如 docs/readme.md"),
    file: UploadFile = UploadFileParam(...),
):
    """上传文件到指定路径。"""
    logger.info("POST /settings/memory-and-skill/upload | type=%s | path=%s | filename=%s", type, path, file.filename)
    content = await file.read()
    return await upload_file(type, path, content)


# ════════════════ 修改 ════════════════
@router.put("/rename")
@handle_endpoint_errors(
    ErrorCode.FILE_MODIFY_FAILED,
    log_msg="重命名异常 | type={type} | path={body.path}",
    detail_msg="重命名失败: path={body.path}",
)
async def rename_endpoint(
    body: RenameRequest,
    type: _MemorySkillType = Query(..., description=_TYPE_DESC),
):
    """重命名文件或目录。"""
    logger.info("PUT /settings/memory-and-skill/rename | type=%s | %s → %s", type, body.path, body.new_name)
    return await rename_path(type, body.path, body.new_name)


@router.put("/move")
@handle_endpoint_errors(
    ErrorCode.FILE_MODIFY_FAILED,
    log_msg="移动异常 | type={type} | path={body.path}",
    detail_msg="移动失败: path={body.path}",
)
async def move_endpoint(
    body: MoveRequest,
    type: _MemorySkillType = Query(..., description=_TYPE_DESC),
):
    """移动文件或目录到目标目录。"""
    logger.info("PUT /settings/memory-and-skill/move | type=%s | %s → %s", type, body.path, body.target_dir or "/")
    return await move_path(type, body.path, body.target_dir)


@router.put("/modify")
@handle_endpoint_errors(
    ErrorCode.FILE_MODIFY_FAILED,
    log_msg="修改文件异常 | type={type} | path={body.path}",
    detail_msg="修改文件失败: path={body.path}",
)
async def modify_file_endpoint(
    body: ModifyFileRequest,
    type: _MemorySkillType = Query(..., description=_TYPE_DESC),
):
    """修改文件内容（覆盖写入）。"""
    logger.info("PUT /settings/memory-and-skill/modify | type=%s | path=%s | content_len=%d", type, body.path, len(body.content))
    return await modify_file_content(type, body.path, body.content)


# ════════════════ 删除 ════════════════
@router.delete("/delete")
@handle_endpoint_errors(
    ErrorCode.FILE_DELETE_FAILED,
    log_msg="删除异常 | type={type} | path={body.path}",
    detail_msg="删除失败: path={body.path}",
)
async def delete_endpoint(
    body: DeleteRequest,
    type: _MemorySkillType = Query(..., description=_TYPE_DESC),
):
    """删除文件或目录（递归删除目录及其所有内容）。"""
    logger.info("DELETE /settings/memory-and-skill/delete | type=%s | path=%s", type, body.path)
    return await delete_path(type, body.path)
