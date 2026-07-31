"""FastAPI 入口 —— 负责组装应用、注册路由和中间件。"""

from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.auth.dependencies import get_current_user
from backend.api.auth.router import router as auth_router
from backend.api.services.graph import graph_lifespan
from backend.api.routers.chat import router as chat_router
from backend.api.routers.threads import router as threads_router
from backend.api.routers.checkpoints import router as checkpoints_router
from backend.api.routers.files import router as files_router
from backend.api.routers.settings import router as settings_router
from backend.api.routers.memory_and_skill import router as memory_and_skill_router
from backend.api.routers.rag_pipeline import router as rag_pipeline_router
from backend.api.scheduled_tasks.router import router as scheduled_tasks_router
from backend.api.scheduled_tasks.scheduler import start_scheduler, stop_scheduler
from backend.api.utils.error_handlers import register_exception_handlers
from backend.config.logger import get_logger, setup_logging
from backend.config.env_settings import CORS_ORIGINS
from backend.config.observability import langfuse_init
from backend.core.cache.manager import init_cache_manager
from backend.api.auth.db import init_users_db
from backend.api.auth.middleware import AuthLogMiddleware

# ── 日志初始化 ──
setup_logging()
logger = get_logger(__name__)

# ── Langfuse 初始化 ──
langfuse_init()

# ── 应用创建 & 生命周期（Graph 懒加载 + 定时任务调度器） ──
@asynccontextmanager
async def app_lifespan(app: FastAPI):
    """组合 lifespan：启动定时任务调度器 → Graph 生命周期 → 退出时清理。"""
    start_scheduler()
    try:
        async with graph_lifespan(app):
            yield
    finally:
        await stop_scheduler()

app = FastAPI(lifespan=app_lifespan)
logger.info("FastAPI 应用已创建")

# ── 缓存管理器初始化 ──
init_cache_manager()

# ── 用户数据库初始化（建表 + 创建管理员） ──
init_users_db()

# ── 全局异常处理器 ──
register_exception_handlers(app)

# ── CORS 配置 ──
_cors_origins = CORS_ORIGINS.split(",") if CORS_ORIGINS else [
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:3000",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info(f"CORS 中间件已配置 | origins={_cors_origins}")

# ── 日志多租户中间件（自动绑定 username 到日志上下文） ──
app.add_middleware(AuthLogMiddleware)
logger.info("AuthLog 中间件已注册")

# ── 路由注册 ──
# 认证路由（无需登录）
app.include_router(auth_router)
# 业务路由（需要认证）
app.include_router(chat_router, dependencies=[Depends(get_current_user)])
app.include_router(threads_router, dependencies=[Depends(get_current_user)])
app.include_router(checkpoints_router, dependencies=[Depends(get_current_user)])
app.include_router(files_router, dependencies=[Depends(get_current_user)])
app.include_router(settings_router, dependencies=[Depends(get_current_user)])
app.include_router(memory_and_skill_router, dependencies=[Depends(get_current_user)])
app.include_router(rag_pipeline_router, dependencies=[Depends(get_current_user)])
# 定时任务路由（需要认证）
app.include_router(scheduled_tasks_router, dependencies=[Depends(get_current_user)])

logger.info("路由已注册 | auth, chat, threads, checkpoints, files, settings, memory-and-skill, rag-pipeline, scheduled-tasks")
