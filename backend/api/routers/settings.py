"""设置管理路由 —— 读写指定的配置文件。"""
from fastapi import APIRouter, Query

from backend.api.services.settings_service import (
    read_config_file,
    write_config_file,
    get_skills_status,
    update_skills_status,
)
from backend.api.services.graph import rebuild_graph
from backend.api.schemas.files import ModifyFileRequest
from backend.api.schemas.settings import SkillsUpdateRequest
from backend.api.utils.error_handlers import handle_endpoint_errors
from backend.api.utils.exceptions import ErrorCode
from backend.config.logger import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/settings", tags=["settings"])


# ════════════════ 读取 ════════════════
@router.get("/model-config/read")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="配置读取异常 | path={path}",
    detail_msg="配置读取失败: path={path}",
)
async def read_model_config_endpoint(path: str = Query(..., description="配置文件标识")):
    """读取指定配置文件内容。"""
    logger.info("GET /settings/model-config/read | path=%s", path)
    return await read_config_file(path)


# ════════════════ 写入 ════════════════
@router.put("/model-config/write")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="配置写入异常 | path={body.path}",
    detail_msg="配置写入失败: path={body.path}",
)
async def write_model_config_endpoint(body: ModifyFileRequest):
    """覆写指定配置文件内容。"""
    logger.info("PUT /settings/model-config/write | path=%s | content_len=%d", body.path, len(body.content))
    return await write_config_file(body.path, body.content)


# ═══════════════════════════════════════════
#  Skills 开关管理
# ═══════════════════════════════════════════
@router.get("/skills")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="Skills 状态查询异常",
    detail_msg="Skills 状态查询失败",
)
async def get_skills():
    """获取所有 skill 及其启用状态。"""
    logger.info("GET /settings/skills")
    return await get_skills_status()


@router.put("/skills")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="Skills 状态更新异常",
    detail_msg="Skills 状态更新失败",
)
async def update_skills(body: SkillsUpdateRequest):
    """更新启用的 skill 列表并重建 Graph。"""
    logger.info("PUT /settings/skills | enabled=%s", body.enabled)
    result = await update_skills_status(body.enabled)
    # 更新后自动重建 graph 使 junction 生效
    await rebuild_graph()
    return result


# ═══════════════════════════════════════════
#  Graph 重建
# ═══════════════════════════════════════════
@router.post("/rebuild")
@handle_endpoint_errors(
    ErrorCode.INTERNAL_ERROR,
    log_msg="Graph 重建失败",
    detail_msg="Graph 重建失败",
)
async def rebuild():
    """重新编译 LangGraph，使配置生效。"""
    return await rebuild_graph()
