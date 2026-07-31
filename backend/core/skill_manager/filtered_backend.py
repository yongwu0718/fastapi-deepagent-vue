from __future__ import annotations

import yaml
from pathlib import Path
from deepagents.backends.protocol import LsResult
from backend.config.logger import get_logger

logger = get_logger(__name__)

# 与 settings_service.py 中的键前缀保持一致
_CACHE_KEY_PREFIX = "cfg:"
SKILLS_CACHE_KEY = _CACHE_KEY_PREFIX + "skills"
INIT_KEY = "cfg:initialized"


class SkillFilteredBackend:
    """包装 FilesystemBackend，按用户 cache 中的 skills 配置过滤 ls 结果。

    仅代理 ls / als 两个方法进行过滤，其他调用透传给内部后端。

    Args:
        backend: 被包装的内部后端实例。
        cache: 当前用户的 diskcache 实例（含 cfg:skills 启用配置）。
    """

    def __init__(self, backend, cache=None):
        self._backend = backend
        self._cache = cache
        logger.info("SkillFilteredBackend 已初始化 | inner=%s | user_cache=%s",
                     type(self._backend).__name__, cache is not None)

    def _read_enabled(self) -> set[str]:
        """从用户 cache 读取当前启用的技能名称集合。

        若无 cache（向后兼容），回退到全局共享配置文件。
        """
        # 优先从用户 cache 读取
        if self._cache is not None:
            try:
                raw = self._cache.get(SKILLS_CACHE_KEY)
                if raw is not None:
                    config = yaml.safe_load(raw) or {}
                    result = set(config.get("enabled", []))
                    logger.debug("从用户 cache 读取技能配置 | enabled=%s", result)
                    return result
            except Exception:
                logger.warning("从用户 cache 读取技能配置失败", exc_info=True)

        # 回退：无 cache 或读取失败时返回空集（不过滤）
        logger.debug("无用户 cache 或配置为空，不过滤技能")
        return set()

    def _filter_entries(self, entries: list | None) -> list | None:
        """过滤掉不在启用列表中的技能目录。"""
        if not entries:
            return entries
        enabled = self._read_enabled()
        if not enabled:
            logger.info("技能启用集合为空，不过滤任何条目")
            return entries
        filtered = []
        for entry in entries:
            name = entry.get("path", "").rstrip("/").rsplit("/", 1)[-1]
            if entry.get("is_dir") and name not in enabled:
                logger.info("过滤未启用的技能: %s", name)
                continue
            filtered.append(entry)
        logger.info("技能过滤结果 | 原始=%d | 过滤后=%d", len(entries), len(filtered))
        return filtered

    def ls(self, path: str):
        """同步 ls，过滤结果。"""
        result = self._backend.ls(path)
        filtered = self._filter_entries(result.entries)
        return LsResult(error=result.error, entries=filtered)

    async def als(self, path: str):
        """异步 ls，过滤结果。"""
        result = await self._backend.als(path)
        filtered = self._filter_entries(result.entries)
        return LsResult(error=result.error, entries=filtered)

    def __getattr__(self, name: str):
        """其他所有方法/属性透传给内部后端。"""
        return getattr(self._backend, name)
