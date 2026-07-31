"""多租户缓存模块 —— 基于 diskcache 的用户数据隔离。"""

from backend.core.cache.manager import CacheManager, get_cache_manager
from backend.core.cache.dependencies import CurrentUserCacheDep, get_current_user_cache

__all__ = [
    "CacheManager",
    "get_cache_manager",
    "CurrentUserCacheDep",
    "get_current_user_cache",
]
