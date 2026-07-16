"""记忆库 & 技能库文件管理服务 —— 目录列表、文件内容获取、增删改查。"""

import datetime
import io
import shutil
from pathlib import Path
from typing import Dict, List, Literal

from backend.api.utils.exceptions import ErrorCode, NotFoundException, AppException
from backend.config.env_settings import MEMORY_DIR, SKILLS_DIR
from backend.config.logger import get_logger

logger = get_logger(__name__)

# ── 类型 → 根目录映射 ──
_MemorySkillType = Literal["memory", "skills"]
_ROOTS: dict[_MemorySkillType, Path] = {}
if MEMORY_DIR:
    _ROOTS["memory"] = Path(MEMORY_DIR).resolve()
if SKILLS_DIR:
    _ROOTS["skills"] = Path(SKILLS_DIR).resolve()
logger.info("记忆库&技能库服务初始化 | roots=%s", {k: str(v) for k, v in _ROOTS.items()})


def _get_root(type: _MemorySkillType) -> Path:
    """根据类型获取对应的根目录。"""
    root = _ROOTS.get(type)
    if root is None:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.INVALID_OPERATION,
            detail=f"不支持的文件类型: {type}",
        )
    return root


def _safe_path(type: _MemorySkillType, sub_path: str) -> Path:
    """路径安全检查：防止目录遍历攻击。"""
    root = _get_root(type)
    full_path = (root / sub_path).resolve()
    root_str = str(root)
    # 两边都加分隔符，确保根目录自身也能通过检查
    sep = "\\" if "\\" in root_str else "/"
    if not (str(full_path) + sep).startswith(root_str + sep):
        logger.warning("[安全] 禁止访问 | type=%s | requested=%s | resolved=%s", type, sub_path, full_path)
        raise AppException(
            status_code=403,
            error_code=ErrorCode.FORBIDDEN_PATH,
            detail="禁止访问：路径超出允许范围",
        )
    logger.debug("[安全] 路径解析 | type=%s | sub=%s → %s", type, sub_path or "/", full_path)
    return full_path


async def list_directory(type: _MemorySkillType, sub_path: str = "") -> Dict:
    """列出指定目录下的文件和子目录。

    Args:
        type: 文件类型，'memory' 或 'skills'。
        sub_path: 相对于根目录的路径，空字符串表示根目录。

    Returns:
        {"path": str, "items": [{"name", "type", "size", "modified"}, ...]}
    """
    target = _safe_path(type, sub_path)

    if not target.exists():
        raise NotFoundException(
            error_code=ErrorCode.PATH_NOT_FOUND,
            detail=f"路径不存在: {sub_path or '/'}",
        )
    if not target.is_dir():
        raise AppException(
            status_code=400,
            error_code=ErrorCode.NOT_A_DIRECTORY,
            detail=f"不是目录: {sub_path}",
        )

    items: List[dict] = []
    try:
        for entry in target.iterdir():
            stat = entry.stat()
            items.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "path": entry.name,
                "size": stat.st_size if entry.is_file() else None,
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
            })
    except PermissionError:
        raise AppException(
            status_code=403,
            error_code=ErrorCode.PERMISSION_DENIED,
            detail=f"没有权限访问: {sub_path}",
        )

    # 文件夹优先，同类型按名称排序
    items.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["name"].lower()))

    dirs = sum(1 for i in items if i["type"] == "directory")
    files = sum(1 for i in items if i["type"] == "file")
    logger.debug("目录扫描完成 | type=%s | path=%s | dirs=%d | files=%d", type, sub_path or "/", dirs, files)
    return {"path": sub_path, "items": items}


# ── 可编辑文本文件扩展名 ──
_EDITABLE_EXTENSIONS = {
    ".md", ".txt", ".py", ".js", ".ts", ".html", ".css", ".json", ".xml",
    ".yaml", ".yml", ".toml", ".cfg", ".ini", ".env", ".sh", ".bat",
    ".sql", ".csv", ".log", ".vue", ".jsx", ".tsx", ".java", ".go",
    ".rs", ".cpp", ".c", ".h", ".rb", ".php", ".swift", ".kt",
}


async def get_file_path(type: _MemorySkillType, sub_path: str) -> Path:
    """获取文件的绝对路径（含安全检查）。

    Args:
        type: 文件类型，'memory' 或 'skills'。
        sub_path: 相对于根目录的文件路径。

    Returns:
        文件绝对路径 Path 对象。
    """
    target = _safe_path(type, sub_path)

    if not target.exists() or not target.is_file():
        raise NotFoundException(
            error_code=ErrorCode.FILE_NOT_FOUND,
            detail=f"文件不存在: {sub_path}",
        )

    logger.debug("文件路径解析 | type=%s | path=%s", type, sub_path)
    return target


async def read_file_content(type: _MemorySkillType, sub_path: str) -> Dict:
    """读取文件内容，返回结构化 JSON。"""
    target = await get_file_path(type, sub_path)
    suffix = target.suffix.lower()
    stat = target.stat()

    is_image = suffix in {".png", ".jpg", ".jpeg", ".gif", ".webp", ".svg", ".avif", ".bmp"}

    if is_image:
        logger.debug("文件读取 | type=%s | content_type=image | path=%s | size=%d", type, sub_path, stat.st_size)
        return {
            "path": sub_path,
            "content": "",
            "content_type": "image",
            "size": stat.st_size,
            "editable": False,
        }

    try:
        content = target.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        logger.debug("文件读取 | type=%s | content_type=binary | path=%s | size=%d", type, sub_path, stat.st_size)
        return {
            "path": sub_path,
            "content": "",
            "content_type": "binary",
            "size": stat.st_size,
            "editable": False,
        }

    editable = suffix in _EDITABLE_EXTENSIONS
    logger.debug("文件读取 | type=%s | content_type=text | path=%s | size=%d | editable=%s", type, sub_path, stat.st_size, editable)
    return {
        "path": sub_path,
        "content": content,
        "content_type": "text",
        "size": stat.st_size,
        "editable": editable,
    }


# ── 搜索 ──
async def search_files(type: _MemorySkillType, query: str) -> Dict:
    """递归搜索根目录下所有匹配名称的文件和目录。

    Args:
        type: 文件类型，'memory' 或 'skills'。
        query: 搜索关键词，匹配文件名/目录名（大小写不敏感）。

    Returns:
        {"query": str, "results": [{"name", "type", "size", "modified", "path"}, ...]}
    """
    if not query.strip():
        return {"query": query, "results": []}

    q = query.strip().lower()
    results: List[dict] = []
    root = _get_root(type)

    try:
        for entry in root.rglob("*"):
            # 跳过隐藏文件和 __pycache__ 等常见忽略目录
            if entry.name.startswith("."):
                continue
            if any(part.startswith(".") for part in entry.relative_to(root).parts):
                continue

            if q not in entry.name.lower():
                continue

            try:
                stat = entry.stat()
            except (PermissionError, OSError):
                continue

            rel_path = str(entry.relative_to(root)).replace("\\", "/")
            results.append({
                "name": entry.name,
                "type": "directory" if entry.is_dir() else "file",
                "size": stat.st_size if entry.is_file() else None,
                "modified": datetime.datetime.fromtimestamp(stat.st_mtime).isoformat(),
                "path": rel_path,
            })
    except PermissionError:
        pass

    # 先文件夹后文件，同类型按路径排序
    results.sort(key=lambda x: (0 if x["type"] == "directory" else 1, x["path"].lower()))

    logger.debug("搜索完成 | type=%s | query=%s | results=%d", type, query, len(results))
    return {"query": query, "results": results}


# ── 上传 / 创建 ──
async def create_file(type: _MemorySkillType, sub_path: str, content: str = "") -> Dict:
    """创建新文件。

    Args:
        type: 文件类型，'memory' 或 'skills'。
        sub_path: 相对路径（含文件名）。
        content: 文件内容，为空则创建空文件。

    Returns:
        操作结果字典。
    """
    target = _safe_path(type, sub_path)

    if target.exists():
        raise AppException(
            status_code=409,
            error_code=ErrorCode.FILE_ALREADY_EXISTS,
            detail=f"文件已存在: {sub_path}",
        )

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        logger.info("文件创建成功 | type=%s | path=%s | size=%d", type, sub_path, len(content))
        return {"success": True, "message": "文件创建成功", "path": sub_path}
    except Exception as e:
        logger.exception("文件创建失败 | type=%s | path=%s", type, sub_path)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.FILE_CREATE_FAILED,
            detail=f"文件创建失败: {sub_path} | {e}",
        )


async def create_directory(type: _MemorySkillType, sub_path: str) -> Dict:
    """创建新目录。

    Args:
        type: 文件类型，'memory' 或 'skills'。
        sub_path: 相对路径。

    Returns:
        操作结果字典。
    """
    target = _safe_path(type, sub_path)

    if target.exists():
        raise AppException(
            status_code=409,
            error_code=ErrorCode.DIR_ALREADY_EXISTS,
            detail=f"目录已存在: {sub_path}",
        )

    try:
        target.mkdir(parents=True, exist_ok=False)
        logger.info("目录创建成功 | type=%s | path=%s", type, sub_path)
        return {"success": True, "message": "目录创建成功", "path": sub_path}
    except Exception as e:
        logger.exception("目录创建失败 | type=%s | path=%s", type, sub_path)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.DIR_CREATE_FAILED,
            detail=f"目录创建失败: {sub_path} | {e}",
        )


async def upload_file(type: _MemorySkillType, sub_path: str, content: bytes) -> Dict:
    """上传文件（二进制内容写入），PDF/DOCX 自动提取文本为 .md。

    Args:
        type: 文件类型，'memory' 或 'skills'。
        sub_path: 相对路径（含文件名）。
        content: 二进制文件内容。

    Returns:
        操作结果字典，含 extracted_path（如有提取文本）。
    """
    from backend.api.utils.file_handler import FILE_EXTRACTORS, SUPPORTED_EXTENSIONS

    target = _safe_path(type, sub_path)
    root = _get_root(type)
    suffix = Path(sub_path).suffix.lower()

    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        logger.info("文件上传成功 | type=%s | path=%s | size=%d", type, sub_path, len(content))
        result: Dict = {"success": True, "message": "文件上传成功", "path": sub_path}

        # 自动提取 PDF/DOCX 文本，保存同目录 .md
        if suffix in SUPPORTED_EXTENSIONS:
            try:
                extractor = FILE_EXTRACTORS[suffix]
                # pdfplumber 需要 BytesIO，docx_to_text 内部自行包装
                source = io.BytesIO(content) if suffix == ".pdf" else content
                extracted = extractor(source)
                md_name = Path(sub_path).stem + ".md"
                md_path = target.parent / md_name
                md_path.write_text(extracted, encoding="utf-8")
                md_relative = str(md_path.relative_to(root)).replace("\\", "/")
                logger.info("文本提取成功 | type=%s | source=%s | extracted=%s | chars=%d",
                            type, sub_path, md_relative, len(extracted))
                result["extracted_path"] = md_relative
            except Exception as extract_err:
                logger.warning("文本提取失败（原始文件已保存）| type=%s | path=%s | error=%s",
                               type, sub_path, extract_err)

        return result
    except Exception as e:
        logger.exception("文件上传失败 | type=%s | path=%s", type, sub_path)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.FILE_UPLOAD_FAILED,
            detail=f"文件上传失败: {sub_path} | {e}",
        )


# ── 修改 ──
async def rename_path(type: _MemorySkillType, sub_path: str, new_name: str) -> Dict:
    """重命名文件或目录。

    Args:
        type: 文件类型，'memory' 或 'skills'。
        sub_path: 当前相对路径。
        new_name: 新名称（仅名称，不含路径分隔符）。

    Returns:
        操作结果字典（含新旧路径）。
    """
    target = _safe_path(type, sub_path)
    root = _get_root(type)

    if not target.exists():
        raise NotFoundException(
            error_code=ErrorCode.PATH_NOT_FOUND,
            detail=f"路径不存在: {sub_path}",
        )

    # 新名称不能含路径分隔符，防止移动到其他目录
    if "/" in new_name or "\\" in new_name:
        raise AppException(
            status_code=400,
            error_code=ErrorCode.INVALID_OPERATION,
            detail="新名称不能包含路径分隔符",
        )

    new_target = target.parent / new_name
    if new_target.exists():
        raise AppException(
            status_code=409,
            error_code=ErrorCode.FILE_ALREADY_EXISTS,
            detail=f"目标名称已存在: {new_name}",
        )

    try:
        target.rename(new_target)
        new_relative = str(new_target.relative_to(root)).replace("\\", "/")
        logger.info("重命名成功 | type=%s | %s → %s", type, sub_path, new_relative)
        return {
            "success": True,
            "message": "重命名成功",
            "path": new_relative,
        }
    except Exception as e:
        logger.exception("重命名失败 | type=%s | path=%s", type, sub_path)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.FILE_MODIFY_FAILED,
            detail=f"重命名失败: {sub_path} | {e}",
        )


async def move_path(type: _MemorySkillType, sub_path: str, target_dir: str) -> Dict:
    """移动文件或目录到目标目录。

    Args:
        type: 文件类型，'memory' 或 'skills'。
        sub_path: 当前相对路径。
        target_dir: 目标目录相对路径，空字符串表示根目录。

    Returns:
        操作结果字典。
    """
    source = _safe_path(type, sub_path)
    root = _get_root(type)

    if not source.exists():
        raise NotFoundException(
            error_code=ErrorCode.PATH_NOT_FOUND,
            detail=f"路径不存在: {sub_path}",
        )

    dest_dir = _safe_path(type, target_dir)
    if not dest_dir.exists() or not dest_dir.is_dir():
        raise NotFoundException(
            error_code=ErrorCode.PATH_NOT_FOUND if not dest_dir.exists() else ErrorCode.NOT_A_DIRECTORY,
            detail=f"目标目录不存在或非目录: {target_dir or '/'}",
        )

    new_target = dest_dir / source.name
    if new_target.exists():
        raise AppException(
            status_code=409,
            error_code=ErrorCode.FILE_ALREADY_EXISTS,
            detail=f"目标位置已存在同名条目: {source.name}",
        )

    try:
        source.rename(new_target)
        new_relative = str(new_target.relative_to(root)).replace("\\", "/")
        logger.info("移动成功 | type=%s | %s → %s", type, sub_path, new_relative)
        return {
            "success": True,
            "message": "移动成功",
            "path": new_relative,
        }
    except Exception as e:
        logger.exception("移动失败 | type=%s | path=%s → %s", type, sub_path, target_dir)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.FILE_MODIFY_FAILED,
            detail=f"移动失败: {sub_path} → {target_dir or '/'} | {e}",
        )


async def modify_file_content(type: _MemorySkillType, sub_path: str, content: str) -> Dict:
    """修改文件内容（覆盖写入）。

    Args:
        type: 文件类型，'memory' 或 'skills'。
        sub_path: 文件相对路径。
        content: 新的文本内容。

    Returns:
        操作结果字典。
    """
    target = _safe_path(type, sub_path)

    if not target.exists() or not target.is_file():
        raise NotFoundException(
            error_code=ErrorCode.FILE_NOT_FOUND,
            detail=f"文件不存在: {sub_path}",
        )

    try:
        target.write_text(content, encoding="utf-8")
        logger.info("文件修改成功 | type=%s | path=%s | size=%d", type, sub_path, len(content))
        return {"success": True, "message": "文件修改成功", "path": sub_path}
    except Exception as e:
        logger.exception("文件修改失败 | type=%s | path=%s", type, sub_path)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.FILE_MODIFY_FAILED,
            detail=f"文件修改失败: {sub_path} | {e}",
        )


# ── 删除 ──
async def delete_path(type: _MemorySkillType, sub_path: str) -> Dict:
    """删除文件或目录（递归删除目录及其所有内容）。

    Args:
        type: 文件类型，'memory' 或 'skills'。
        sub_path: 要删除的相对路径。

    Returns:
        操作结果字典。
    """
    target = _safe_path(type, sub_path)

    if not target.exists():
        raise NotFoundException(
            error_code=ErrorCode.PATH_NOT_FOUND,
            detail=f"路径不存在: {sub_path}",
        )

    is_dir = target.is_dir()  # 在 try 前记录类型，避免 except 块中误判

    try:
        if is_dir:
            shutil.rmtree(target)
            logger.info("目录删除成功 | type=%s | path=%s", type, sub_path)
            return {"success": True, "message": "目录删除成功", "path": sub_path}
        else:
            target.unlink()
            logger.info("文件删除成功 | type=%s | path=%s", type, sub_path)
            return {"success": True, "message": "文件删除成功", "path": sub_path}
    except Exception as e:
        logger.exception("删除失败 | type=%s | path=%s", type, sub_path)
        raise AppException(
            status_code=500,
            error_code=ErrorCode.FILE_DELETE_FAILED if not is_dir else ErrorCode.DIR_DELETE_FAILED,
            detail=f"删除失败: {sub_path} | {e}",
        )
