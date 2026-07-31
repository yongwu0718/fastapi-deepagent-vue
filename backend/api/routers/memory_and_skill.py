"""记忆库 & 技能库文件管理路由 —— 基于用户缓存的隔离文件操作。"""

from typing import Annotated, Any

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
from backend.core.cache.dependencies import CurrentUserCacheDep

logger = get_logger(__name__)
router = APIRouter(prefix="/settings/memory-and-skill", tags=["memory-and-skill"])

_TYPE_DESC = "文件类型: 'memory'=记忆库, 'skills'=技能库"

# ════════════════ 读取 ════════════════
@router.get("/list")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="目录列表异常 | type={type} | path={path}",
    detail_msg="目录列表失败: path={path}",
)
async def list_directory_endpoint(
    type: Annotated[str, Query(description=_TYPE_DESC)],
    path: Annotated[str, Query(description="相对路径，空=根目录")] = "",
    cache: CurrentUserCacheDep = None,
) -> dict[str, Any]:
    logger.info("GET /settings/memory-and-skill/list | type=%s | path=%s", type, path or "/")
    return await list_directory(cache, type, path)


@router.get("/file")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="文件读取异常 | type={type} | path={path}",
    detail_msg="文件读取失败: path={path}",
)
async def get_file_endpoint(
    type: Annotated[str, Query(description=_TYPE_DESC)],
    path: Annotated[str, Query(description="相对路径")],
    cache: CurrentUserCacheDep = None,
) -> Any:
    logger.info("GET /settings/memory-and-skill/file | type=%s | path=%s", type, path)
    file_path = await get_file_path(cache, type, path)
    return FileResponse(file_path)


@router.get("/read")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="文件读取异常 | type={type} | path={path}",
    detail_msg="文件读取失败: path={path}",
)
async def read_file_endpoint(
    type: Annotated[str, Query(description=_TYPE_DESC)],
    path: Annotated[str, Query(description="相对路径")],
    cache: CurrentUserCacheDep = None,
) -> dict[str, Any]:
    logger.info("GET /settings/memory-and-skill/read | type=%s | path=%s", type, path)
    return await read_file_content(cache, type, path)


@router.get("/search")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="文件搜索异常 | type={type} | q={q}",
    detail_msg="文件搜索失败: q={q}",
)
async def search_files_endpoint(
    type: Annotated[str, Query(description=_TYPE_DESC)],
    q: Annotated[str, Query(description="搜索关键词", min_length=1)],
    cache: CurrentUserCacheDep = None,
) -> dict[str, Any]:
    logger.info("GET /settings/memory-and-skill/search | type=%s | q=%s", type, q)
    return await search_files(cache, type, q)


# ════════════════ 上传 / 创建 ════════════════
@router.post("/create-file")
@handle_endpoint_errors(
    ErrorCode.FILE_CREATE_FAILED,
    log_msg="创建文件异常 | type={type} | path={body.path}",
    detail_msg="创建文件失败: path={body.path}",
)
async def create_file_endpoint(
    body: CreateFileRequest,
    type: Annotated[str, Query(description=_TYPE_DESC)],
    cache: CurrentUserCacheDep = None,
) -> dict[str, Any]:
    logger.info("POST /settings/memory-and-skill/create-file | type=%s | path=%s", type, body.path)
    return await create_file(cache, type, body.path, body.content)


@router.post("/create-directory")
@handle_endpoint_errors(
    ErrorCode.DIR_CREATE_FAILED,
    log_msg="创建目录异常 | type={type} | path={body.path}",
    detail_msg="创建目录失败: path={body.path}",
)
async def create_directory_endpoint(
    body: CreateDirectoryRequest,
    type: Annotated[str, Query(description=_TYPE_DESC)],
    cache: CurrentUserCacheDep = None,
) -> dict[str, Any]:
    logger.info("POST /settings/memory-and-skill/create-directory | type=%s | path=%s", type, body.path)
    return await create_directory(cache, type, body.path)


@router.post("/upload")
@handle_endpoint_errors(
    ErrorCode.FILE_UPLOAD_FAILED,
    log_msg="文件上传异常 | type={type} | path={path}",
    detail_msg="文件上传失败: path={path}",
)
async def upload_file_endpoint(
    type: Annotated[str, Query(description=_TYPE_DESC)],
    path: Annotated[str, Query(description="目标相对路径")],
    file: Annotated[UploadFile, UploadFileParam()],
    cache: CurrentUserCacheDep = None,
) -> dict[str, Any]:
    logger.info("POST /settings/memory-and-skill/upload | type=%s | path=%s", type, path)
    content = await file.read()
    return await upload_file(cache, type, path, content)


# ════════════════ 修改 ════════════════
@router.put("/rename")
@handle_endpoint_errors(
    ErrorCode.FILE_MODIFY_FAILED,
    log_msg="重命名异常 | type={type} | path={body.path}",
    detail_msg="重命名失败: path={body.path}",
)
async def rename_endpoint(
    body: RenameRequest,
    type: Annotated[str, Query(description=_TYPE_DESC)],
    cache: CurrentUserCacheDep = None,
) -> dict[str, Any]:
    logger.info("PUT /settings/memory-and-skill/rename | type=%s | %s → %s", type, body.path, body.new_name)
    return await rename_path(cache, type, body.path, body.new_name)


@router.put("/move")
@handle_endpoint_errors(
    ErrorCode.FILE_MODIFY_FAILED,
    log_msg="移动异常 | type={type} | path={body.path}",
    detail_msg="移动失败: path={body.path}",
)
async def move_endpoint(
    body: MoveRequest,
    type: Annotated[str, Query(description=_TYPE_DESC)],
    cache: CurrentUserCacheDep = None,
) -> dict[str, Any]:
    logger.info("PUT /settings/memory-and-skill/move | type=%s | %s → %s", type, body.path, body.target_dir or "/")
    return await move_path(cache, type, body.path, body.target_dir)


@router.put("/modify")
@handle_endpoint_errors(
    ErrorCode.FILE_MODIFY_FAILED,
    log_msg="修改文件异常 | type={type} | path={body.path}",
    detail_msg="修改文件失败: path={body.path}",
)
async def modify_file_endpoint(
    body: ModifyFileRequest,
    type: Annotated[str, Query(description=_TYPE_DESC)],
    cache: CurrentUserCacheDep = None,
) -> dict[str, Any]:
    logger.info("PUT /settings/memory-and-skill/modify | type=%s | path=%s | content_len=%d", type, body.path, len(body.content))
    return await modify_file_content(cache, type, body.path, body.content)


# ════════════════ 删除 ════════════════
@router.delete("/delete")
@handle_endpoint_errors(
    ErrorCode.FILE_DELETE_FAILED,
    log_msg="删除异常 | type={type} | path={body.path}",
    detail_msg="删除失败: path={body.path}",
)
async def delete_endpoint(
    body: DeleteRequest,
    type: Annotated[str, Query(description=_TYPE_DESC)],
    cache: CurrentUserCacheDep = None,
) -> dict[str, Any]:
    logger.info("DELETE /settings/memory-and-skill/delete | type=%s | path=%s", type, body.path)
    return await delete_path(cache, type, body.path)
