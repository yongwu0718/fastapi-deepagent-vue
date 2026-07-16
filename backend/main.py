"""FastAPI 入口 —— 负责组装应用、注册路由和中间件。"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.api.services.graph import graph_lifespan
from backend.api.routers.chat import router as chat_router
from backend.api.routers.threads import router as threads_router
from backend.api.routers.checkpoints import router as checkpoints_router
from backend.api.routers.files import router as files_router
from backend.api.routers.settings import router as settings_router
from backend.api.routers.memory_and_skill import router as memory_and_skill_router
from backend.api.routers.rag_pipeline import router as rag_pipeline_router
from backend.api.utils.error_handlers import register_exception_handlers
from backend.config.logger import get_logger, setup_logging
from backend.config.env_settings import CORS_ORIGINS
from backend.config.observability import langfuse_init

# ── 日志初始化 ──
setup_logging()
logger = get_logger(__name__)

# ── Langfuse 初始化 ──
langfuse_init()

# ── 应用创建 & 生命周期 ──
app = FastAPI(lifespan=graph_lifespan)
logger.info("FastAPI 应用已创建")

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

# ── 路由注册 ──
app.include_router(chat_router)
app.include_router(threads_router)
app.include_router(checkpoints_router)
app.include_router(files_router)
app.include_router(settings_router)
app.include_router(memory_and_skill_router)
app.include_router(rag_pipeline_router)

logger.info("路由已注册 | routers=chat, threads, checkpoints, files, settings, memory-and-skill, rag-pipeline")
