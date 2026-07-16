"""设置管理服务 —— 精确读写 .env 中配置的特定文件。"""

import yaml
from pathlib import Path
from typing import Dict

from backend.api.utils.exceptions import ErrorCode, NotFoundException, AppException
from backend.config.env_settings import MODEL_CONFIG_PATH, SYSTEM_PROMPT_PATH, MCP_SERVER_PATH, SKILLS_DIR, SKILLS_CONFIG_PATH
from backend.config.logger import get_logger

logger = get_logger(__name__)

# ── 前端请求路径键 → .env 中配置的绝对路径 ──
_FILE_PATHS: dict[str, Path] = {}
if MODEL_CONFIG_PATH:
    _FILE_PATHS["model"] = Path(MODEL_CONFIG_PATH).resolve()
if SYSTEM_PROMPT_PATH:
    _FILE_PATHS["prompt"] = Path(SYSTEM_PROMPT_PATH).resolve()
if MCP_SERVER_PATH:
    _FILE_PATHS["mcp"] = Path(MCP_SERVER_PATH).resolve()
if SKILLS_CONFIG_PATH:
    _FILE_PATHS["skills_config"] = Path(SKILLS_CONFIG_PATH).resolve()

logger.info("设置服务初始化 | MAPPED_FILES=%d", len(_FILE_PATHS))

# ── 可编辑文本文件扩展名 ──
_EDITABLE_EXTENSIONS = {
    ".yaml", ".yml", ".json", ".txt", ".md", ".toml", ".cfg", ".ini",
    ".py", ".js", ".ts", ".html", ".css", ".xml",
}


def _resolve_path(key: str) -> Path:
    """根据前端请求键解析为已配置的绝对路径。"""
    resolved = _FILE_PATHS.get(key)
    if resolved is None:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.FORBIDDEN_PATH,
            detail=f"未配置的文件: {key}",
        )
    logger.debug("[路径] 解析 | key=%s → %s", key, resolved)
    return resolved


# ════════════════ 读取 ════════════════
async def read_config_file(key: str) -> Dict:
    """读取配置文件内容。

    Args:
        key: 前端文件标识（如 "model_config.yaml"、"backend/core/prompts/system_prompt.txt"）。

    Returns:
        {"path", "content", "content_type", "size", "editable"}
    """
    target = _resolve_path(key)

    if not target.exists() or not target.is_file():
        raise NotFoundException(
            error_code=ErrorCode.FILE_NOT_FOUND,
            detail=f"文件不存在: {key}",
        )

    suffix = target.suffix.lower()
    stat = target.stat()

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.debug("配置文件读取 | type=binary | key=%s | size=%d", key, stat.st_size)
        return {
            "path": key,
            "content": "",
            "content_type": "binary",
            "size": stat.st_size,
            "editable": False,
        }

    editable = suffix in _EDITABLE_EXTENSIONS
    logger.debug("配置文件读取 | type=text | key=%s | size=%d | editable=%s", key, stat.st_size, editable)
    return {
        "path": key,
        "content": content,
        "content_type": "text",
        "size": stat.st_size,
        "editable": editable,
    }


# ════════════════ 写入 ════════════════
async def write_config_file(key: str, content: str) -> Dict:
    """覆写配置文件内容。

    Args:
        key: 前端文件标识。
        content: 新内容。
    """
    target = _resolve_path(key)

    if not target.exists() or not target.is_file():
        raise NotFoundException(
            error_code=ErrorCode.FILE_NOT_FOUND,
            detail=f"文件不存在: {key}",
        )

    try:
        target.write_text(content, encoding="utf-8")
        logger.info("配置文件写入成功 | key=%s | size=%d", key, len(content))
        return {"success": True, "message": "配置文件修改成功", "path": key}
    except Exception as e:
        logger.exception("配置文件写入失败 | key=%s", key)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.FILE_MODIFY_FAILED,
            detail=f"配置文件写入失败: {key} | {e}",
        )


# ════════════════ Skills 开关管理 ════════════════
_skills_dir = Path(SKILLS_DIR) if SKILLS_DIR else None


def _read_skills_config() -> dict:
    """读取 skills_config.yaml，文件不存在时返回空配置。"""
    config_path = _FILE_PATHS.get("skills_config")
    if config_path is None or not config_path.exists():
        return {"enabled": []}
    try:
        return yaml.safe_load(config_path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, KeyError):
        return {"enabled": []}


def _write_skills_config(enabled: list[str]) -> None:
    """写入 skills_config.yaml。"""
    config_path = _FILE_PATHS.get("skills_config")
    if config_path is None:
        raise AppException(
            status_code=500,
            error_code=ErrorCode.INTERNAL_ERROR,
            detail="SKILLS_CONFIG_PATH 未配置",
        )
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        yaml.dump({"enabled": enabled}, allow_unicode=True, default_flow_style=False),
        encoding="utf-8",
    )


async def get_skills_status() -> Dict:
    """获取所有 skill 及其启用状态。

    Returns:
        {
            "skills": [{"name": str, "enabled": bool}, ...],
            "total": int,
            "enabled_count": int,
        }
    """
    config = _read_skills_config()
    enabled_set = set(config.get("enabled", []))

    # 扫描磁盘上所有有效 skill
    all_skills = []
    if _skills_dir and _skills_dir.exists():
        for item in sorted(_skills_dir.iterdir()):
            if item.is_dir() and (item / "SKILL.md").exists():
                all_skills.append({
                    "name": item.name,
                    "enabled": item.name in enabled_set,
                })

    enabled_count = sum(1 for s in all_skills if s["enabled"])
    logger.debug("Skills 状态查询 | total=%d | enabled=%d", len(all_skills), enabled_count)
    return {
        "skills": all_skills,
        "total": len(all_skills),
        "enabled_count": enabled_count,
    }


async def update_skills_status(enabled: list[str]) -> Dict:
    """更新启用的 skill 列表。

    Args:
        enabled: 需要启用的 skill 名称列表。

    Returns:
        操作结果。
    """
    # 校验：过滤掉磁盘上不存在的 skill 名称
    valid_names = set()
    if _skills_dir and _skills_dir.exists():
        for item in _skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                valid_names.add(item.name)

    filtered = [name for name in enabled if name in valid_names]
    skipped = set(enabled) - set(filtered)
    if skipped:
        logger.warning("更新 skills 状态时跳过不存在的 skill: %s", skipped)

    _write_skills_config(filtered)
    logger.info("Skills 配置已更新 | enabled=%s", filtered)
    return {"status": "ok", "enabled": filtered}
