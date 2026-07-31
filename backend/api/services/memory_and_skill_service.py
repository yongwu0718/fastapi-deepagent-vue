"""记忆库 & 技能库文件管理服务 —— 基于 diskcache 的用户数据隔离。

每个用户拥有独立的记忆库/技能库文件目录：
    data/cache/<username>/memory/   # 用户的记忆库文件
    data/cache/<username>/skills/   # 用户的技能库文件
"""

import datetime
import io
import shutil
from pathlib import Path
from typing import Dict, List

from diskcache import Cache

from backend.api.utils.exceptions import ErrorCode, NotFoundException, AppException
from backend.config.env_settings import MEMORY_DIR, SKILLS_DIR
from backend.config.logger import get_logger

logger = get_logger(__name__)

# ── 共享文件根目录（用于首次初始化复制） ──
_SHARED_MEMORY = Path(MEMORY_DIR).resolve() if MEMORY_DIR else None
_SHARED_SKILLS = Path(SKILLS_DIR).resolve() if SKILLS_DIR else None

# ── 可编辑文本文件扩展名 ──
_EDITABLE_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".ts", ".html", ".css", ".json", ".xml",
    ".yaml", ".yml", ".toml", ".cfg", ".ini", ".env", ".sh", ".bat",
    ".sql", ".csv", ".log", ".vue", ".jsx", ".tsx", ".java", ".go",
    ".rs", ".cpp", ".c", ".h", ".rb", ".php", ".swift", ".kt",
}


# ═══════════════════════════════════════
#  用户隔离路径解析
# ═══════════════════════════════════════

def _get_user_root(cache: Cache, type_: str) -> tuple[Path, Path | None]:
    """获取用户的独立目录，同时返回共享根目录（用于首次初始化）。

    Args:
        cache: 当前用户的 diskcache 实例。
        type_: 'memory' 或 'skills'。

    Returns:
        (user_dir, shared_dir) — 用户专属目录和共享目录。
    """
    user_base = Path(cache.directory)
    shared = _SHARED_MEMORY if type_ == "memory" else _SHARED_SKILLS

    user_root = user_base / type_
    user_root.mkdir(parents=True, exist_ok=True)

    return user_root, shared


def _ensure_user_init(user_root: Path, shared: Path | None) -> None:
    """首次访问时从共享目录复制文件到用户目录。"""
    init_marker = user_root / ".initialized"
    if init_marker.exists():
        return

    if shared and shared.exists():
        logger.info("初始化用户目录 | target=%s | source=%s", user_root, shared)
        try:
            shutil.copytree(shared, user_root, dirs_exist_ok=True)
        except Exception:
            logger.warning("用户目录初始化失败", exc_info=True)

    # 写入标记文件
    init_marker.touch()


def _safe_path(user_root: Path, sub_path: str) -> Path:
    """路径安全检查：防止目录遍历攻击。"""
    full = (user_root / sub_path).resolve()
    root_str = str(user_root)
    sep = "\\" if "\\" in root_str else "/"
    if not (str(full) + sep).startswith(root_str + sep):
        logger.warning("[安全] 禁止访问 | requested=%s | resolved=%s", sub_path, full)
        raise AppException(
            status_code=403,
            error_code=ErrorCode.FORBIDDEN_PATH,
            detail="禁止访问：路径超出允许范围",
        )
    return full


# ═══════════════════════════════════════
#  目录列表
# ═══════════════════════════════════════

async def list_directory(cache: Cache, type_: str, sub_path: str = "") -> Dict:
    """列出指定目录下的文件和子目录。"""
    user_root, shared = _get_user_root(cache, type_)
    _ensure_user_init(user_root, shared)
    target = _safe_path(user_root, sub_path) if sub_path else user_root

    if not target.exists():
        raise NotFoundException(error_code=ErrorCode.PATH_NOT_FOUND, detail=f"路径不存在: {sub_path or '/'}")
    if not target.is_dir():
        raise AppException(status_code=400, error_code=ErrorCode.NOT_A_DIRECTORY, detail=f"不是目录: {sub_path}")

    items: List[dict] = []
    try:
        for entry in target.iterdir():
            if entry.name == ".initialized":
                continue
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "path": entry.name,
                "size": stat.st_size if entry.is_file() else None,
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    except PermissionError:
        raise AppException(status_code=403, error_code=ErrorCode.PERMISSION_DENIED, detail=f"没有权限访问: {sub_path}")

    items.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower()))
    dirs = sum(1 for i in items if i["type"] == "directory")
    files = sum(1 for i in items if i["type"] == "file")
    logger.debug("目录扫描 | type=%s | path=%s | dirs=%d | files=%d", type_, sub_path or "/", dirs, files)
    return {"path": sub_path, "items": items}


# ═══════════════════════════════════════
#  文件读取
# ═══════════════════════════════════════

async def get_file_path(cache: Cache, type_: str, sub_path: str) -> Path:
    """获取文件绝对路径。"""
    user_root, shared = _get_user_root(cache, type_)
    _ensure_user_init(user_root, shared)
    target = _safe_path(user_root, sub_path)
    if not target.exists() or not target.is_file():
        raise NotFoundException(error_code=ErrorCode.FILE_NOT_FOUND, detail=f"文件不存在: {sub_path}")
    return target


async def read_file_content(cache: Cache, type_: str, sub_path: str) -> Dict:
    """读取文件内容。"""
    target = await get_file_path(cache, type_, sub_path)
    suffix = target.suffix.lower()
    stat = target.stat()

    is_image = suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif", ".bmp"}
    if is_image:
        return {"path": sub_path, "content": "", "content_type": "image", "size": stat.st_size, "editable": False}

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return {"path": sub_path, "content": "", "content_type": "binary", "size": stat.st_size, "editable": False}

    editable = suffix in _EDITABLE_EXTENSIONS
    return {"path": sub_path, "content": content, "content_type": "text", "size": stat.st_size, "editable": editable}


# ═══════════════════════════════════════
#  搜索
# ═══════════════════════════════════════

async def search_files(cache: Cache, type_: str, query: str) -> Dict:
    """递归搜索用户目录下匹配名称的文件。"""
    if not query.strip():
        return {"query": query, "results": []}

    user_root, shared = _get_user_root(cache, type_)
    _ensure_user_init(user_root, shared)
    q = query.strip().lower()
    results: List[dict] = []

    try:
        for entry in user_root.rglob("*"):
            if entry.name == ".initialized" or entry.name.startswith("."):
                continue
            if any(part.startswith(".") for part in entry.relative_to(user_root).parts):
                continue
            if q not in entry.name.lower():
                continue
            try:
                stat = entry.stat()
            except (PermissionError, OSError):
                continue
            rel = str(entry.relative_to(user_root)).replace("\\", "/")
            results.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "size": stat.st_size if entry.is_file() else None,
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": rel,
            })
    except PermissionError:
        pass

    results.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["path"].lower()))
    logger.debug("搜索完成 | type=%s | query=%s | results=%d", type_, query, len(results))
    return {"query": query, "results": results}


# ═══════════════════════════════════════
#  创建 / 上传
# ═══════════════════════════════════════

async def create_file(cache: Cache, type_: str, sub_path: str, content: str = "") -> Dict:
    """创建新文件。"""
    user_root, shared = _get_user_root(cache, type_)
    _ensure_user_init(user_root, shared)
    target = _safe_path(user_root, sub_path)
    if target.exists():
        raise AppException(status_code=409, error_code=ErrorCode.FILE_ALREADY_EXISTS, detail=f"文件已存在: {sub_path}")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.info("文件创建成功 | type=%s | path=%s | size=%d", type_, sub_path, len(content))
        return {"success": True, "message": "文件创建成功", "path": sub_path}
    except Exception as e:
        raise AppException(status_code=500, error_code=ErrorCode.FILE_CREATE_FAILED, detail=f"文件创建失败: {sub_path} | {e}")


async def create_directory(cache: Cache, type_: str, sub_path: str) -> Dict:
    """创建新目录。"""
    user_root, shared = _get_user_root(cache, type_)
    _ensure_user_init(user_root, shared)
    target = _safe_path(user_root, sub_path)
    if target.exists():
        raise AppException(status_code=409, error_code=ErrorCode.DIR_ALREADY_EXISTS, detail=f"目录已存在: {sub_path}")
    try:
        target.mkdir(parents=True, exist_ok=False)
        logger.info("目录创建成功 | type=%s | path=%s", type_, sub_path)
        return {"success": True, "message": "目录创建成功", "path": sub_path}
    except Exception as e:
        raise AppException(status_code=500, error_code=ErrorCode.DIR_CREATE_FAILED, detail=f"目录创建失败: {sub_path} | {e}")


async def upload_file(cache: Cache, type_: str, sub_path: str, file_content: bytes) -> Dict:
    """上传文件到用户目录。"""
    from backend.api.utils.file_handler import FILE_EXTRACTORS, SUPPORTED_EXTENSIONS

    user_root, shared = _get_user_root(cache, type_)
    _ensure_user_init(user_root, shared)
    target = _safe_path(user_root, sub_path)
    suffix = Path(sub_path).suffix.lower()

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(file_content)
        logger.info("文件上传成功 | type=%s | path=%s | size=%d", type_, sub_path, len(file_content))

        result: Dict = {"success": True, "message": "文件上传成功", "path": sub_path}
        if suffix in SUPPORTED_EXTENSIONS:
            try:
                extractor = FILE_EXTRACTORS[suffix]
                source = io.BytesIO(file_content) if suffix == ".pdf" else file_content
                extracted = extractor(source)
                md_name = Path(sub_path).stem + ".md"
                md_path = target.parent / md_name
                md_path.write_text(extracted, encoding="utf-8")
                md_relative = str(md_path.relative_to(user_root)).replace("\\", "/")
                result["extracted_path"] = md_relative
            except Exception as extract_err:
                logger.warning("文本提取失败 | path=%s | error=%s", sub_path, extract_err)
        return result
    except Exception as e:
        raise AppException(status_code=500, error_code=ErrorCode.FILE_UPLOAD_FAILED, detail=f"文件上传失败: {sub_path} | {e}")


# ═══════════════════════════════════════
#  修改
# ═══════════════════════════════════════

async def rename_path(cache: Cache, type_: str, sub_path: str, new_name: str) -> Dict:
    """重命名文件或目录。"""
    user_root, shared = _get_user_root(cache, type_)
    _ensure_user_init(user_root, shared)
    target = _safe_path(user_root, sub_path)
    if not target.exists():
        raise NotFoundException(error_code=ErrorCode.PATH_NOT_FOUND, detail=f"路径不存在: {sub_path}")
    if "/" in new_name or "\\" in new_name:
        raise AppException(status_code=400, error_code=ErrorCode.INVALID_OPERATION, detail="新名称不能包含路径分隔符")

    new_target = target.parent / new_name
    if new_target.exists():
        raise AppException(status_code=409, error_code=ErrorCode.FILE_ALREADY_EXISTS, detail=f"目标名称已存在: {new_name}")

    try:
        target.rename(new_target)
        new_relative = str(new_target.relative_to(user_root)).replace("\\", "/")
        return {"success": True, "message": "重命名成功", "path": new_relative}
    except Exception as e:
        raise AppException(status_code=500, error_code=ErrorCode.FILE_MODIFY_FAILED, detail=f"重命名失败: {sub_path} | {e}")


async def move_path(cache: Cache, type_: str, sub_path: str, target_dir: str) -> Dict:
    """移动文件或目录。"""
    user_root, shared = _get_user_root(cache, type_)
    _ensure_user_init(user_root, shared)
    source = _safe_path(user_root, sub_path)
    if not source.exists():
        raise NotFoundException(error_code=ErrorCode.PATH_NOT_FOUND, detail=f"路径不存在: {sub_path}")

    dest_dir = _safe_path(user_root, target_dir) if target_dir else user_root
    if not dest_dir.exists() or not dest_dir.is_dir():
        raise NotFoundException(
            error_code=ErrorCode.PATH_NOT_FOUND if not dest_dir.exists() else ErrorCode.NOT_A_DIRECTORY,
            detail=f"目标目录不存在或非目录: {target_dir or '/'}",
        )

    new_target = dest_dir / source.name
    if new_target.exists():
        raise AppException(status_code=409, error_code=ErrorCode.FILE_ALREADY_EXISTS, detail=f"目标位置已存在同名: {source.name}")

    try:
        source.rename(new_target)
        new_relative = str(new_target.relative_to(user_root)).replace("\\", "/")
        return {"success": True, "message": "移动成功", "path": new_relative}
    except Exception as e:
        raise AppException(status_code=500, error_code=ErrorCode.FILE_MODIFY_FAILED, detail=f"移动失败: {sub_path} | {e}")


async def modify_file_content(cache: Cache, type_: str, sub_path: str, content: str) -> Dict:
    """修改文件内容（覆盖写入）。"""
    user_root, shared = _get_user_root(cache, type_)
    _ensure_user_init(user_root, shared)
    target = _safe_path(user_root, sub_path)
    if not target.exists() or not target.is_file():
        raise NotFoundException(error_code=ErrorCode.FILE_NOT_FOUND, detail=f"文件不存在: {sub_path}")
    try:
        target.write_text(content, encoding="utf-8")
        return {"success": True, "message": "文件修改成功", "path": sub_path}
    except Exception as e:
        raise AppException(status_code=500, error_code=ErrorCode.FILE_MODIFY_FAILED, detail=f"文件修改失败: {sub_path} | {e}")


# ═══════════════════════════════════════
#  删除
# ═══════════════════════════════════════

async def delete_path(cache: Cache, type_: str, sub_path: str) -> Dict:
    """删除文件或目录。"""
    user_root, shared = _get_user_root(cache, type_)
    _ensure_user_init(user_root, shared)
    target = _safe_path(user_root, sub_path)
    if not target.exists():
        raise NotFoundException(error_code=ErrorCode.PATH_NOT_FOUND, detail=f"路径不存在: {sub_path}")

    is_dir = target.is_dir()
    try:
        if is_dir:
            shutil.rmtree(target)
            return {"success": True, "message": "目录删除成功", "path": sub_path}
        else:
            target.unlink()
            return {"success": True, "message": "文件删除成功", "path": sub_path}
    except Exception as e:
        raise AppException(
            status_code=500,
            error_code=ErrorCode.FILE_DELETE_FAILED if not is_dir else ErrorCode.DIR_DELETE_FAILED,
            detail=f"删除失败: {sub_path} | {e}",
        )
