"""多租户缓存管理器 —— 每个用户独立的 diskcache 实例。

数据隔离：
    data/cache/
    ├── admin/cache.db       # admin 用户的缓存
    ├── user2/cache.db       # user2 用户的缓存
    └── ...

使用方式：
    manager = get_cache_manager()
    cache = manager.get_user_cache("admin")
    cache["key"] = "value"
"""

import os
from pathlib import Path
from threading import Lock

import diskcache

from backend.config.logger import get_logger

logger = get_logger(__name__)


class _NoValue:
    """sentinel"""


class CacheManager:
    """多租户 diskcache 管理器（单例）。

    每个用户拥有独立的 diskcache 目录，数据完全隔离。
    """

    def __init__(self, base_dir: str):
        base = Path(base_dir)
        base.mkdir(parents=True, exist_ok=True)
        self._base = base
        self._caches: dict[str, diskcache.Cache] = {}
        self._lock = Lock()
        logger.info("CacheManager 初始化 | base=%s", self._base)

    # ── 目录 ──
    def _user_dir(self, username: str) -> Path:
        return self._base / username

    # ── 核心方法 ──
    def get_user_cache(self, username: str) -> diskcache.Cache:
        """获取指定用户的 diskcache 实例（已缓存或新建）。

        Args:
            username: 用户名（如 'admin'）。

        Returns:
            用户专属的 diskcache.Cache 实例。
        """
        with self._lock:
            if username not in self._caches:
                user_dir = self._user_dir(username)
                user_dir.mkdir(parents=True, exist_ok=True)
                logger.info("创建用户缓存 | user=%s | dir=%s", username, user_dir)
                self._caches[username] = diskcache.Cache(str(user_dir))
            return self._caches[username]

    def close_user_cache(self, username: str) -> None:
        """关闭指定用户的缓存。"""
        with self._lock:
            cache = self._caches.pop(username, None)
            if cache is not None:
                cache.close()
                logger.info("已关闭用户缓存 | user=%s", username)

    def close_all(self) -> None:
        """关闭所有用户的缓存（应用关闭时调用）。"""
        with self._lock:
            for username, cache in list(self._caches.items()):
                cache.close()
                logger.info("已关闭用户缓存 | user=%s", username)
            self._caches.clear()

    def clear_user_cache(self, username: str) -> None:
        """清空指定用户的所有缓存数据。"""
        with self._lock:
            cache = self._caches.pop(username, None)
            if cache is not None:
                cache.close()
            user_dir = self._user_dir(username)
            if user_dir.exists():
                import shutil
                shutil.rmtree(user_dir)
                logger.info("已清空用户缓存 | user=%s", username)

    def user_cache_exists(self, username: str) -> bool:
        """检查用户是否有缓存目录。"""
        return self._user_dir(username).exists()

    # ── 便捷操作（自动管理 cache 生命周期） ──
    def get(self, username: str, key: str, default=_NoValue):
        """读取缓存值。"""
        cache = self.get_user_cache(username)
        result = cache.get(key, default=default)
        if default is _NoValue:
            return result
        return result

    def set(self, username: str, key: str, value, expire: float | None = None):
        """写入缓存值。

        Args:
            username: 用户名。
            key: 缓存键。
            value: 缓存值。
            expire: 过期时间（秒），None 表示永不过期。
        """
        cache = self.get_user_cache(username)
        cache.set(key, value, expire=expire)

    def delete(self, username: str, key: str) -> bool:
        """删除缓存键。"""
        cache = self.get_user_cache(username)
        return cache.delete(key)

    def contains(self, username: str, key: str) -> bool:
        """检查缓存键是否存在。"""
        try:
            return key in self.get_user_cache(username)
        except Exception:
            return False


# ═════════════════════════════════════════════════
#  全局单例
# ═════════════════════════════════════════════════

_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """获取全局 CacheManager 单例。"""
    global _manager
    if _manager is None:
        from backend.config.env_settings import CACHE_DIR
        _manager = CacheManager(CACHE_DIR or "data/cache")
    return _manager


def init_cache_manager() -> CacheManager:
    """显式初始化缓存管理器（应用启动时调用）。"""
    return get_cache_manager()
