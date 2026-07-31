"""设置管理服务 —— 基于 diskcache 的用户隔离配置读写。

每个用户的配置存储在自己的 diskcache 中：
- cfg:model      → 模型配置 YAML
- cfg:prompt     → 系统提示词
- cfg:mcp        → MCP 服务 JSON
- cfg:skills     → 技能开关配置 dict
"""

import yaml
from pathlib import Path
from typing import Dict

from diskcache import Cache

from backend.api.utils.exceptions import ErrorCode, NotFoundException, AppException
from backend.config.env_settings import (
    MODEL_CONFIG_PATH,
    SYSTEM_PROMPT_PATH,
    MCP_SERVER_PATH,
    SKILLS_DIR,
    SKILLS_CONFIG_PATH,
)
from backend.config.logger import get_logger

logger = get_logger(__name__)

# ── 共享文件路径映射（用于首次初始化） ──
_SHARED_FILES: dict[str, Path] = {}
if MODEL_CONFIG_PATH:
    _SHARED_FILES["model"] = Path(MODEL_CONFIG_PATH).resolve()
if SYSTEM_PROMPT_PATH:
    _SHARED_FILES["prompt"] = Path(SYSTEM_PROMPT_PATH).resolve()
if MCP_SERVER_PATH:
    _SHARED_FILES["mcp"] = Path(MCP_SERVER_PATH).resolve()
if SKILLS_CONFIG_PATH:
    _SHARED_FILES["skills_config"] = Path(SKILLS_CONFIG_PATH).resolve()

SKILLS_DIR_PATH = Path(SKILLS_DIR).resolve() if SKILLS_DIR else None
_EDITABLE_EXTENSIONS = {".yaml", ".yml", ".json", ".txt", ".md", ".toml", ".cfg", ".ini"}
CACHE_KEY_PREFIX = "cfg:"
INIT_KEY = "cfg:initialized"


def _get_user_skills_dir(cache: Cache) -> Path:
    """获取用户专属 skills 目录，首次访问时从全局目录初始化。

    Returns:
        用户 skills 目录路径（data/cache/<username>/skills/）。
    """
    user_root = Path(cache.directory) / "skills"
    user_root.mkdir(parents=True, exist_ok=True)

    # 首次访问时从全局共享目录复制 skill 文件
    init_marker = user_root / ".initialized"
    if not init_marker.exists():
        if SKILLS_DIR_PATH and SKILLS_DIR_PATH.exists():
            import shutil
            logger.info("初始化用户 skills 目录 | target=%s | source=%s", user_root, SKILLS_DIR_PATH)
            try:
                shutil.copytree(SKILLS_DIR_PATH, user_root, dirs_exist_ok=True)
            except Exception:
                logger.warning("用户 skills 目录初始化失败", exc_info=True)
        init_marker.touch()

    return user_root


# ═══════════════════════════════════════
#  用户初始化
# ═══════════════════════════════════════


def _ensure_initialized(cache: Cache) -> None:
    """首次访问时从共享文件复制初始配置到用户的缓存。"""
    if INIT_KEY in cache:
        return

    logger.info("初始化用户缓存 | 从共享文件复制配置")
    for key, file_path in _SHARED_FILES.items():
        try:
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                cache[CACHE_KEY_PREFIX + key] = content
                logger.debug("初始配置已复制 | key=%s | size=%d", key, len(content))
        except Exception:
            logger.warning("初始配置复制失败 | key=%s", key, exc_info=True)
    cache[INIT_KEY] = True


def _resolve_key(key: str) -> str:
    """解析请求 key 到缓存键。"""
    if key not in _SHARED_FILES:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.FORBIDDEN_PATH,
            detail=f"未配置的文件: {key}",
        )
    return CACHE_KEY_PREFIX + key


# ═══════════════════════════════════════
#  配置读取
# ═══════════════════════════════════════


async def read_config_file(cache: Cache, key: str) -> Dict:
    """从用户缓存中读取配置。

    Args:
        cache: 当前用户的 diskcache 实例。
        key: 配置标识（model / prompt / mcp / skills_config）。

    Returns:
        {"path", "content", "content_type", "size", "editable"}
    """
    _ensure_initialized(cache)
    cache_key = _resolve_key(key)

    content = cache.get(cache_key)
    if content is None:
        raise NotFoundException(
            error_code=ErrorCode.FILE_NOT_FOUND,
            detail=f"配置未初始化: {key}",
        )

    suffix = Path(key).suffix.lower() if "." in key else ".yaml"
    editable = suffix in _EDITABLE_EXTENSIONS
    logger.debug("配置读取 | key=%s | size=%d", key, len(content))
    return {
        "path": key,
        "content": content,
        "content_type": "text",
        "size": len(content.encode("utf-8")),
        "editable": editable,
    }


# ═══════════════════════════════════════
#  配置写入
# ═══════════════════════════════════════


async def write_config_file(cache: Cache, key: str, content: str) -> Dict:
    """写入配置到用户缓存。

    Args:
        cache: 当前用户的 diskcache 实例。
        key: 配置标识。
        content: 新内容。
    """
    _ensure_initialized(cache)
    cache_key = _resolve_key(key)

    try:
        cache[cache_key] = content
        logger.info("配置写入成功 | key=%s | size=%d", key, len(content))
        return {"success": True, "message": "配置修改成功", "path": key}
    except Exception as e:
        logger.exception("配置写入失败 | key=%s", key)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.FILE_MODIFY_FAILED,
            detail=f"配置写入失败: {key} | {e}",
        )


# ═══════════════════════════════════════
#  获取用户配置（供 Graph 重建使用）
# ═══════════════════════════════════════


def get_user_config(cache: Cache, key: str) -> str:
    """直接获取用户配置文本内容（供其他模块调用）。

    Args:
        cache: 用户缓存实例。
        key: 配置标识（model / prompt / mcp）。

    Returns:
        配置内容字符串。
    """
    _ensure_initialized(cache)
    cache_key = _resolve_key(key)
    content = cache.get(cache_key)
    if content is None:
        # 回退到共享文件
        shared = _SHARED_FILES.get(key)
        if shared and shared.exists():
            return shared.read_text(encoding="utf-8")
        return ""
    return content

SKILLS_CACHE_KEY = CACHE_KEY_PREFIX + "skills"


def _read_cached_skills_config(cache: Cache) -> dict:
    """读取用户缓存中的 skills 配置。"""
    _ensure_initialized(cache)
    raw = cache.get(SKILLS_CACHE_KEY)
    if raw is None:
        # 首次：从共享文件复制
        config_path = _SHARED_FILES.get("skills_config")
        if config_path and config_path.exists():
            try:
                raw = config_path.read_text(encoding="utf-8")
            except Exception:
                raw = "{}"
        else:
            raw = "{}"
        cache[SKILLS_CACHE_KEY] = raw
    try:
        return yaml.safe_load(raw) or {"enabled": []}
    except (yaml.YAMLError, KeyError):
        return {"enabled": []}


def _write_cached_skills_config(cache: Cache, enabled: list[str]) -> None:
    """写入 skills 配置到用户缓存。"""
    _ensure_initialized(cache)
    content = yaml.dump({"enabled": enabled}, allow_unicode=True, default_flow_style=False)
    cache[SKILLS_CACHE_KEY] = content


async def get_skills_status(cache: Cache) -> Dict:
    """获取所有 skill 及其启用状态（启用状态从用户缓存读取）。

    Returns:
        {"skills": [{"name", "enabled"}, ...], "total": int, "enabled_count": int}
    """
    config = _read_cached_skills_config(cache)
    enabled_set = set(config.get("enabled", []))

    user_skills_dir = _get_user_skills_dir(cache)
    all_skills = []
    if user_skills_dir.exists():
        for item in sorted(user_skills_dir.iterdir()):
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


async def update_skills_status(cache: Cache, enabled: list[str]) -> Dict:
    """更新启用的 skill 列表（写入用户缓存）。

    Args:
        cache: 当前用户缓存。
        enabled: 需要启用的 skill 名称列表。

    Returns:
        操作结果。
    """
    valid_names = set()
    user_skills_dir = _get_user_skills_dir(cache)
    if user_skills_dir.exists():
        for item in user_skills_dir.iterdir():
            if item.is_dir() and (item / "SKILL.md").exists():
                valid_names.add(item.name)

    filtered = [name for name in enabled if name in valid_names]
    skipped = set(enabled) - set(filtered)
    if skipped:
        logger.warning("跳过不存在的 skill: %s", skipped)

    _write_cached_skills_config(cache, filtered)
    logger.info("Skills 配置已更新 | enabled=%s", filtered)
    return {"status": "ok", "enabled": filtered}
