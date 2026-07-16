from __future__ import annotations

import yaml
from pathlib import Path
from deepagents.backends.protocol import LsResult
from backend.config.env_settings import SKILLS_CONFIG_PATH
from backend.config.logger import get_logger

logger = get_logger(__name__)


class SkillFilteredBackend:
    """包装 FilesystemBackend，按 skills_config.yaml 过滤 ls 结果。

    仅代理 ls / als 两个方法进行过滤，其他调用透传给内部后端。
    """

    def __init__(self, backend):
        self._backend = backend
        self._config_path = Path(SKILLS_CONFIG_PATH) if SKILLS_CONFIG_PATH else None
        logger.info("SkillFilteredBackend 已初始化 | inner=%s | config=%s",
                     type(self._backend).__name__, self._config_path)

    def _read_enabled(self) -> set[str]:
        """读取当前启用的技能名称集合。"""
        if self._config_path is None or not self._config_path.exists():
            logger.info("技能配置文件不存在或无 SKILLS_CONFIG_PATH: %s", self._config_path)
            return set()
        try:
            config = yaml.safe_load(self._config_path.read_text(encoding="utf-8"))
            result = set(config.get("enabled", []))
            logger.info("已读取技能配置 | enabled=%s | path=%s", result, self._config_path)
            return result
        except (yaml.YAMLError, KeyError):
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
