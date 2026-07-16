"""统一日志配置模块 —— 提供结构化日志记录。

输出到文件（均落在 ``logs/<日期>/`` 子目录中）：

1. **当日累计文件**：文件名 ``app.log``，按大小自动滚动；同一日期下多次启动
   会追加到同一文件，便于按天查看完整日志。
2. **本次启动文件**：每次进程启动生成一个独立文件
   ``run_<时间>_<pid>.log``（例如 ``run_14-30-22_pid6780.log``），
   仅记录本次启动期间的全部日志，便于按次溯源。进程退出后文件保留，
   并受 ``run_log_ttl_days`` TTL 控制——超过 TTL 的 run 文件在下次启动
   时自动清理。``<= 0`` 表示不清理。
"""

import logging
import os
import shutil
import time
from contextvars import ContextVar
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional

# ── 日志根目录 ──
LOG_ROOT = Path(__file__).resolve().parent.parent / "logs"
LOG_ROOT.mkdir(exist_ok=True)

# ── 日志级别常量 ──
TRACE = 5  # 比 DEBUG 更细粒度
logging.addLevelName(TRACE, "TRACE")


def _trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


logging.Logger.trace = _trace

# ── 默认格式 ──
_BASE_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


class ContextFormatter(logging.Formatter):
    """在日志末尾追加请求级上下文字段。

    如果当前请求通过 ``bind_context()`` 绑定了上下文，
    则在每条日志行末追加 ``| ctx: key1=val1 key2=val2``。
    """

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        ctx = get_context()
        if ctx:
            ctx_str = " ".join(f"{k}={v}" for k, v in ctx.items())
            base += f" | ctx: {ctx_str}"
        return base


_FILE_FORMAT = ContextFormatter(
    fmt=_BASE_FMT,
    datefmt=_DATE_FMT,
)

# ── 已初始化标记（幂等） ──
_initialized = False

# ── 请求级上下文（ContextVar，协程安全） ──
_request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "request_context", default=None
)


def bind_context(**kwargs: Any) -> None:
    """绑定键值对到当前请求的日志上下文。

    调用后，当前协程内所有日志记录都会自动携带这些字段。
    通常在请求进入时由中间件调用。

    用法::

        from backend.config.logger import bind_context, clear_context
        bind_context(thread_id="abc123", user_id="42")
        logger.info("processing")  # 自动带上 thread_id, user_id
        clear_context()
    """
    current = _request_context.get() or {}
    _request_context.set({**current, **kwargs})


def clear_context() -> None:
    """清除当前请求的所有日志上下文。"""
    _request_context.set(None)


def get_context() -> Dict[str, Any]:
    """获取当前请求的日志上下文。

    Returns:
        当前上下文字典，无上下文时返回空字典。
    """
    return _request_context.get() or {}


class ContextFilter(logging.Filter):
    """将请求级上下文注入每一条日志记录。

    作为 filter 添加到 handler 上，每条日志记录都会自动附加
    ``bind_context()`` 绑定的字段。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_context()
        for key, value in ctx.items():
            setattr(record, key, value)
        return True


# ── 当前会话日志目录 & 启动文件路径（供外部查询/调试） ──
CURRENT_DATE_DIR: Optional[Path] = None
CURRENT_RUN_LOG_FILE: Optional[Path] = None


def setup_logging(
    max_bytes: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5,
    run_log_ttl_days: int = 1,
    app_log_ttl_days: int = 7,
):
    """初始化全局日志配置。

    日志文件按日期隔离到 ``logs/<YYYY-MM-DD>/`` 子目录中；每次进程启动
    额外生成一个 ``run_HH-MM-SS_pid<pid>.log`` 独立文件。

    清理策略（启动时执行）：
        - ``run_log_ttl_days``：本次启动开始时，清理**所有**日期目录里
          mtime 超过该 TTL 的 ``run_*.log``，便于一天内多次启动时
          自动淘汰旧 run 文件。默认 1 天，``<= 0`` 表示不清理。
        - ``app_log_ttl_days``：保留最近 N 天的日期目录。**早于今天的
          第 N 天之外**的整个日期目录（含 ``app.log``、滚动备份及
          仍存的 ``run_*.log``）会被整目录删除。默认 7 天，
          ``<= 0`` 表示不清理。

    参数:
        max_bytes: 当日累计文件单个文件最大字节数。
        backup_count: 当日累计文件保留的历史文件数。
        run_log_ttl_days: run 启动日志的 TTL（天）。
        app_log_ttl_days: app.log 日期目录的保留天数。
    """
    global _initialized, CURRENT_DATE_DIR, CURRENT_RUN_LOG_FILE
    if _initialized:
        return

    # ── 启动时执行两类清理 ──
    _cleanup_expired_run_logs(run_log_ttl_days)
    _cleanup_expired_date_dirs(app_log_ttl_days)

    # ── 按日期创建子目录 ──
    date_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = LOG_ROOT / date_str
    date_dir.mkdir(parents=True, exist_ok=True)
    CURRENT_DATE_DIR = date_dir

    root_logger = logging.getLogger()
    root_logger.setLevel(TRACE)  # root 设最细粒度，由各 handler 控制过滤

    # ── 当日累计文件 handler（app.log） ──
    daily_path = date_dir / "app.log"
    daily_handler = RotatingFileHandler(
        filename=str(daily_path),
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    daily_handler.setLevel(TRACE)  # 文件记录所有级别
    daily_handler.setFormatter(_FILE_FORMAT)
    daily_handler.addFilter(ContextFilter())
    daily_handler.namer = _daily_namer  # 滚动后改名追加日期后缀
    root_logger.addHandler(daily_handler)

    # ── 本次启动文件 handler（run_HH-MM-SS_pid<pid>.log） ──
    run_stamp = datetime.now().strftime("%H-%M-%S")
    run_filename = f"run_{run_stamp}_pid{os.getpid()}.log"
    run_path = date_dir / run_filename
    run_handler = logging.FileHandler(
        filename=str(run_path),
        mode="w",  # 每次启动覆盖（文件本身已是唯一标识）
        encoding="utf-8",
    )
    run_handler.setLevel(TRACE)
    run_handler.setFormatter(_FILE_FORMAT)
    run_handler.addFilter(ContextFilter())
    root_logger.addHandler(run_handler)
    CURRENT_RUN_LOG_FILE = run_path

    # ── 抑制第三方库的噪音日志 ──
    for lib in ("httpx", "httpcore", "urllib3", "asyncio", "aiosqlite"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    _initialized = True
    logging.getLogger(__name__).info(
        "日志系统初始化完成 | 日期目录: %s | 本次启动文件: %s | "
        "run_ttl=%d 天 | app_dir_ttl=%d 天",
        date_dir, run_path, run_log_ttl_days, app_log_ttl_days,
    )


def _cleanup_expired_run_logs(ttl_days: int) -> None:
    """清理超过 TTL 的 run 启动日志（一次启动可以产生多个 run 文件）。

    扫描范围：
        - ``LOG_ROOT`` 根目录下的 ``run_*.log``（兼容历史平铺布局）。
        - 各日期子目录 ``LOG_ROOT/<YYYY-MM-DD>/`` 下的 ``run_*.log``。

    判定依据：文件 mtime 距今超过 ``ttl_days`` 天即视为过期。
    通过 mtime 而非目录名判定，保证一天内多次启动产生的多个 run 文件
    都能按各自写入时间被独立淘汰。

    ``ttl_days <= 0`` 时跳过整个清理流程。
    """
    if ttl_days <= 0:
        return

    cutoff = time.time() - ttl_days * 86400
    tmp_logger = logging.getLogger("core.logger._cleanup")
    removed = 0
    scanned = 0

    def _maybe_remove(p: Path) -> bool:
        nonlocal removed
        try:
            if p.is_file() and p.stat().st_mtime < cutoff:
                p.unlink()
                removed += 1
                return True
        except OSError as exc:
            tmp_logger.warning("清理 run 日志失败 | path=%s | err=%s", p, exc)
        return False

    # ── 1) 根目录下的历史 run_*.log（平铺布局） ──
    if LOG_ROOT.exists():
        for p in LOG_ROOT.glob("run_*.log"):
            scanned += 1
            if _maybe_remove(p):
                tmp_logger.debug("已清理过期 run 日志 | %s", p)

    # ── 2) 各日期子目录下的 run_*.log ──
    if LOG_ROOT.exists():
        for entry in LOG_ROOT.iterdir():
            if not entry.is_dir():
                continue
            for p in entry.glob("run_*.log"):
                scanned += 1
                if _maybe_remove(p):
                    tmp_logger.debug("已清理过期 run 日志 | %s", p)

    if removed:
        tmp_logger.info("run 日志 TTL 清理完成 | ttl=%d 天 | 删除 %d / 扫描 %d 个",
                        ttl_days, removed, scanned)


def _cleanup_expired_date_dirs(ttl_days: int) -> None:
    """清理超过 TTL 的整个日期目录（含 app.log 及残留 run 文件）。

    规则：
        - 只处理形如 ``YYYY-MM-DD`` 的日期目录。
        - 保留"今天"的目录不动。
        - 比今天早 N 天（``ttl_days``）以上的日期目录整目录删除：
          ``保留 = 今天, 今天-1, ., 今天-(ttl_days-1)`` 共 N 天。
        - ``ttl_days <= 0`` 时跳过。

    注意：run 文件的寿命由 ``run_log_ttl_days`` 单独控制；本函数只在
    app.log 日期目录 TTL 触发时才会连同目录里的 run 文件一起删除。
    """
    if ttl_days <= 0:
        return

    tmp_logger = logging.getLogger("core.logger._cleanup")
    today = datetime.now().date()
    # 保留 [today - ttl_days + 1, today] 共 ttl_days 天；早于该区间的目录整目录删除。
    expire_threshold = today - timedelta(days=ttl_days)
    removed_dirs = 0
    scanned_dirs = 0

    if not LOG_ROOT.exists():
        return

    for entry in LOG_ROOT.iterdir():
        if not entry.is_dir():
            continue
        scanned_dirs += 1
        try:
            dir_date = datetime.strptime(entry.name, "%Y-%m-%d").date()
        except ValueError:
            # 非日期命名目录（如其他用途的子目录）一律不动
            continue
        if dir_date >= today:
            # 今天及未来日期的目录不删
            continue
        if dir_date < expire_threshold:
            try:
                shutil.rmtree(entry)
                removed_dirs += 1
                tmp_logger.debug("已清理过期日期目录 | %s", entry)
            except OSError as exc:
                tmp_logger.warning("清理日期目录失败 | path=%s | err=%s", entry, exc)

    if removed_dirs:
        tmp_logger.info("app 日志目录 TTL 清理完成 | ttl=%d 天 | 删除 %d / 扫描 %d 个目录",
                        ttl_days, removed_dirs, scanned_dirs)


def _daily_namer(default_name: str) -> str:
    """RotatingFileHandler 滚动时使用本函数为备份文件命名。

    默认实现会把 ``app.log`` 滚动为 ``app.log.1``、``app.log.2``。
    这里改为追加日期后缀，便于按天辨识。
    """
    base, ext = os.path.splitext(default_name)
    # default_name 此时形如 "./2026-06-16/app.log"
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{base}.{timestamp}{ext or '.log'}"


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger（自动从 __name__ 派生模块名）。

    用法:
        from backend.core.logger import get_logger
        logger = get_logger(__name__)
        logger.info("xxx happened")
    """
    return logging.getLogger(name)
