"""统一日志配置模块 —— 提供多租户日志隔离。

输出结构（按日期 + 用户隔离）：

    logs/<YYYY-MM-DD>/
    ├── admin/
    │   ├── app.log           # admin 当日日志（按大小滚动）
    │   └── run_14-30-22_pid1234.log  # 本次启动日志
    ├── user2/
    │   ├── app.log
    │   └── run_14-30-22_pid1234.log
    └── _system/
        └── app.log           # 无用户上下文的系统级日志

每条日志记录根据 ``username`` 上下文自动路由到对应用户目录。
"""

import logging
import os
import shutil
import threading
import time
from contextvars import ContextVar
from datetime import datetime, timedelta
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any, Dict, Optional

# ── 日志根目录 ──
LOG_ROOT = Path(__file__).resolve().parent.parent / "logs"
LOG_ROOT.mkdir(exist_ok=True)

# ── 日志级别常量 ──
TRACE = 5
logging.addLevelName(TRACE, "TRACE")


def _trace(self, message, *args, **kwargs):
    if self.isEnabledFor(TRACE):
        self._log(TRACE, message, args, **kwargs)


logging.Logger.trace = _trace

# ── 默认格式 ──
_BASE_FMT = "%(asctime)s | %(levelname)-7s | %(name)s | %(filename)s:%(lineno)d | %(funcName)s | %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


class ContextFormatter(logging.Formatter):
    """在日志末尾追加请求级上下文字段。"""

    def format(self, record: logging.LogRecord) -> str:
        base = super().format(record)
        ctx = get_context()
        if ctx:
            ctx_str = " ".join(f"{k}={v}" for k, v in ctx.items())
            base += f" | ctx: {ctx_str}"
        return base


_FILE_FORMAT = ContextFormatter(fmt=_BASE_FMT, datefmt=_DATE_FMT)

# ── 已初始化标记 ──
_initialized = False

# ── 请求级上下文（ContextVar，协程安全） ──
_request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar(
    "request_context", default=None
)


def bind_context(**kwargs: Any) -> None:
    """绑定键值对到当前请求的日志上下文。"""
    current = _request_context.get() or {}
    _request_context.set({**current, **kwargs})


def clear_context() -> None:
    """清除当前请求的所有日志上下文。"""
    _request_context.set(None)


def get_context() -> Dict[str, Any]:
    """获取当前请求的日志上下文。"""
    return _request_context.get() or {}


class ContextFilter(logging.Filter):
    """将请求级上下文注入每一条日志记录。

    将 bind_context() 绑定的字段作为 record 属性挂载上去，
    供 RoutingFileHandler 路由 + ContextFormatter 格式化使用。
    """

    def filter(self, record: logging.LogRecord) -> bool:
        ctx = get_context()
        for key, value in ctx.items():
            setattr(record, key, value)
        return True


class HeartbeatFilter(logging.Filter):
    """过滤 MCP 心跳/Ping 请求日志。"""

    _SKIP_KEYWORDS = ("PingRequest",)

    def filter(self, record: logging.LogRecord) -> bool:
        msg = record.getMessage()
        return not any(kw in msg for kw in self._SKIP_KEYWORDS)


# ── 当前会话日志目录 & 启动文件路径 ──
CURRENT_DATE_DIR: Optional[Path] = None
CURRENT_RUN_LOG_FILE: Optional[Path] = None


# ═══════════════════════════════════════════════════════
#  多租户路由 handler
# ═══════════════════════════════════════════════════════

class RoutingFileHandler(logging.Handler):
    """基于 record.username 动态路由日志到不同用户的文件。

    每个用户（及 _system）拥有独立的 RotatingFileHandler，
    在首次写日志时按需创建。
    """

    def __init__(self, date_dir: Path, max_bytes: int, backup_count: int):
        super().__init__()
        self._date_dir = Path(date_dir)
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._handlers: dict[str, RotatingFileHandler] = {}
        self._lock = threading.Lock()

    def _get_or_create_handler(self, username: str) -> RotatingFileHandler:
        """按需创建或返回指定用户的 RotatingFileHandler。"""
        if username not in self._handlers:
            user_dir = self._date_dir / username
            user_dir.mkdir(parents=True, exist_ok=True)
            h = RotatingFileHandler(
                filename=str(user_dir / "app.log"),
                maxBytes=self._max_bytes,
                backupCount=self._backup_count,
                encoding="utf-8",
            )
            # 继承 level / formatter / filters / namer
            h.setLevel(self.level)
            if self.formatter:
                h.setFormatter(self.formatter)
            for f in self.filters:  # type: ignore[attr-defined]
                h.addFilter(f)
            h.namer = _daily_namer
            self._handlers[username] = h
        return self._handlers[username]

    def emit(self, record: logging.LogRecord) -> None:
        username = getattr(record, "username", None)
        key = username if username else "_system"
        try:
            h = self._get_or_create_handler(key)
            h.emit(record)
        except Exception:
            self.handleError(record)

    def close(self) -> None:
        with self._lock:
            for h in list(self._handlers.values()):
                try:
                    h.close()
                except Exception:
                    pass
            self._handlers.clear()
        super().close()


# ═══════════════════════════════════════════════════════
#  日志初始化
# ═══════════════════════════════════════════════════════

def setup_logging(
    max_bytes: int = 10 * 1024 * 1024,
    backup_count: int = 5,
    run_log_ttl_days: int = 1,
    app_log_ttl_days: int = 7,
):
    """初始化多租户日志系统。

    日志文件按日期 + 用户隔离到 ``logs/<YYYY-MM-DD>/<username>/`` 中；
    每次进程启动额外生成一个 ``run_HH-MM-SS_pid<pid>.log`` 启动日志。

    清理策略（启动时执行）：
        - ``run_log_ttl_days``：清理所有日期目录里 mtime 超期的 run_*.log。
        - ``app_log_ttl_days``：超出保留天数的整个日期目录（含所有用户子目录）
          会被整目录删除。``<= 0`` 表示跳过。
    """
    global _initialized, CURRENT_DATE_DIR, CURRENT_RUN_LOG_FILE
    if _initialized:
        return

    # ── 启动时清理 ──
    _cleanup_expired_run_logs(run_log_ttl_days)
    _cleanup_expired_date_dirs(app_log_ttl_days)

    # ── 按日期创建根目录 ──
    date_str = datetime.now().strftime("%Y-%m-%d")
    date_dir = LOG_ROOT / date_str
    date_dir.mkdir(parents=True, exist_ok=True)
    CURRENT_DATE_DIR = date_dir

    root_logger = logging.getLogger()
    root_logger.setLevel(TRACE)

    # ── 多租户路由 handler（按用户隔离 app.log） ──
    heartbeat_filter = HeartbeatFilter()
    routing_handler = RoutingFileHandler(
        date_dir=date_dir,
        max_bytes=max_bytes,
        backup_count=backup_count,
    )
    routing_handler.setLevel(TRACE)
    routing_handler.setFormatter(_FILE_FORMAT)
    routing_handler.addFilter(heartbeat_filter)
    routing_handler.addFilter(ContextFilter())
    root_logger.addHandler(routing_handler)

    # ── 本次启动文件 handler（存放在日期根目录下） ──
    run_stamp = datetime.now().strftime("%H-%M-%S")
    run_filename = f"run_{run_stamp}_pid{os.getpid()}.log"
    run_path = date_dir / run_filename
    run_handler = logging.FileHandler(
        filename=str(run_path),
        mode="w",
        encoding="utf-8",
    )
    run_handler.setLevel(TRACE)
    run_handler.setFormatter(_FILE_FORMAT)
    run_handler.addFilter(heartbeat_filter)
    run_handler.addFilter(ContextFilter())
    root_logger.addHandler(run_handler)
    CURRENT_RUN_LOG_FILE = run_path

    # ── 抑制第三方库噪音 ──
    for lib in ("httpx", "httpcore", "urllib3", "asyncio", "aiosqlite", "watchfiles"):
        logging.getLogger(lib).setLevel(logging.WARNING)

    _initialized = True
    logging.getLogger(__name__).info(
        "日志系统初始化完成 | 日期目录: %s | 本次启动文件: %s | "
        "run_ttl=%d 天 | app_dir_ttl=%d 天",
        date_dir, run_path, run_log_ttl_days, app_log_ttl_days,
    )


# ═══════════════════════════════════════════════════════
#  清理函数
# ═══════════════════════════════════════════════════════

def _cleanup_expired_run_logs(ttl_days: int) -> None:
    if ttl_days <= 0:
        return
    tmp_logger = logging.getLogger("core.logger._cleanup")
    today = datetime.now().date()
    cutoff_date = today - timedelta(days=ttl_days - 1)
    removed = 0
    scanned = 0

    if not LOG_ROOT.exists():
        return

    for entry in LOG_ROOT.iterdir():
        if not entry.is_dir():
            continue
        try:
            dir_date = datetime.strptime(entry.name, "%Y-%m-%d").date()
        except ValueError:
            continue
        # 递归扫描日期目录下所有子目录中的 run_*.log
        run_files = list(entry.rglob("run_*.log"))
        scanned += len(run_files)
        if dir_date < cutoff_date:
            for p in run_files:
                try:
                    p.unlink()
                    removed += 1
                except OSError:
                    pass
            if run_files:
                tmp_logger.debug(
                    "已清理过期 run 日志 | 目录=%s | 共%d个", entry.name, len(run_files)
                )

    # 根目录兼容
    cutoff_mtime = time.time() - ttl_days * 86400
    for p in LOG_ROOT.glob("run_*.log"):
        scanned += 1
        try:
            if p.is_file() and p.stat().st_mtime < cutoff_mtime:
                p.unlink()
                removed += 1
        except OSError:
            pass

    if removed:
        tmp_logger.info(
            "run 日志 TTL 清理完成 | ttl=%d 天 | 删除 %d / 扫描 %d 个",
            ttl_days, removed, scanned,
        )


def _cleanup_expired_date_dirs(ttl_days: int) -> None:
    if ttl_days <= 0:
        return
    tmp_logger = logging.getLogger("core.logger._cleanup")
    today = datetime.now().date()
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
            continue
        if dir_date >= today:
            continue
        if dir_date < expire_threshold:
            try:
                shutil.rmtree(entry)
                removed_dirs += 1
            except OSError:
                pass

    if removed_dirs:
        tmp_logger.info(
            "app 日志目录 TTL 清理完成 | ttl=%d 天 | 删除 %d / 扫描 %d 个目录",
            ttl_days, removed_dirs, scanned_dirs,
        )


def _daily_namer(default_name: str) -> str:
    """RotatingFileHandler 滚动时的备份文件命名。"""
    base, ext = os.path.splitext(default_name)
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{base}.{timestamp}{ext or '.log'}"


def get_logger(name: str) -> logging.Logger:
    """获取指定名称的 logger。"""
    return logging.getLogger(name)
