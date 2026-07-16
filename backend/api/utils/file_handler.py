"""文件处理共享模块 —— PDF / DOCX 文本提取 & 保存。

interact.py（终端）和 graph_bot.py（微信 Bot）均从此处引用，
后续新增文件格式只需修改此文件。
"""

import base64
import io
import os

import aiofiles
import pdfplumber
from markitdown import MarkItDown
from PIL import Image
from backend.config.env_settings import UPLOADS_DIR

# 模块级单例，避免每次处理 DOCX 时重复初始化
_markitdown = MarkItDown()


def pdf_to_text(pdf_source):
    """从 PDF 文件中提取文本，支持文件路径或 bytes（BytesIO）。"""
    with pdfplumber.open(pdf_source) as pdf:
        pages = [page.extract_text() for page in pdf.pages]
    return "\n\n".join(p for p in pages if p)


def docx_to_text(docx_bytes):
    """从 DOCX 文件中提取文本，接受 bytes。"""
    result = _markitdown.convert(io.BytesIO(docx_bytes))
    return result.text_content


# 图片压缩参数
IMAGE_MAX_DIM = 1024        # 最大边长（px）
IMAGE_JPEG_QUALITY = 75     # JPEG 压缩质量


def compress_image(file_bytes: bytes) -> bytes:
    """压缩图片：缩放到 IMAGE_MAX_DIM 以内，JPEG 质量压缩，返回 bytes。"""
    img = Image.open(io.BytesIO(file_bytes))

    # 等比例缩放到最大边长以内
    w, h = img.size
    if max(w, h) > IMAGE_MAX_DIM:
        ratio = IMAGE_MAX_DIM / max(w, h)
        new_size = (int(w * ratio), int(h * ratio))
        img = img.resize(new_size, Image.LANCZOS)

    # 转 RGB（JPEG 不支持 RGBA/P）
    if img.mode in ("RGBA", "P", "LA"):
        img = img.convert("RGB")

    output = io.BytesIO()
    img.save(output, format="JPEG", quality=IMAGE_JPEG_QUALITY)
    return output.getvalue()


def image_to_base64_data_url(file_bytes: bytes, mime_type: str) -> str:
    """将图片 bytes 转换为 base64 data URL 字符串。"""
    encoded = base64.b64encode(file_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


# 图片 MIME 类型映射
IMAGE_MIME_MAP: dict[str, str] = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
}

# 图片扩展名集合
IMAGE_EXTENSIONS = frozenset(IMAGE_MIME_MAP.keys())

# 扩展名 → 提取函数 映射表，方便未来新增格式
FILE_EXTRACTORS: dict[str, callable] = {
    ".pdf": pdf_to_text,
    ".docx": docx_to_text,
}

# 支持的扩展名集合（文本提取 + 图片），供终端侧快速判断
SUPPORTED_EXTENSIONS = frozenset(FILE_EXTRACTORS.keys()) | IMAGE_EXTENSIONS


async def save_extracted_text(file_name: str, text: str) -> str:
    """将提取的文本保存为 .md 文件到 UPLOADS_DIR。

    Args:
        file_name: 原始文件名（如 report.pdf）
        text: 提取的文本内容

    Returns:
        写入的文件绝对路径
    """
    os.makedirs(UPLOADS_DIR, exist_ok=True)
    md_name = os.path.splitext(file_name)[0] + ".md"
    md_path = os.path.join(UPLOADS_DIR, md_name)
    async with aiofiles.open(md_path, "w", encoding="utf-8") as f:
        await f.write(text)
    return md_path
