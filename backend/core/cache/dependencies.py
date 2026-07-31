"""缓存依赖注入 —— 自动绑定当前用户的 diskcache 实例。"""

from typing import Annotated

import diskcache
from fastapi import Depends

from backend.api.auth.dependencies import CurrentUserDep
from backend.api.auth.schemas import UserOut
from backend.core.cache.manager import get_cache_manager


def get_current_user_cache(current_user: CurrentUserDep) -> diskcache.Cache:
    """获取当前登录用户的专属 diskcache 缓存实例。

    自动按用户名隔离，每个用户拥有独立的缓存命名空间。
    """
    manager = get_cache_manager()
    return manager.get_user_cache(current_user.username)


# ── Annotated 类型别名 ──
CurrentUserCacheDep = Annotated[diskcache.Cache, Depends(get_current_user_cache)]
