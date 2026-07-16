"""文件目录相关 schema —— 目录列表 & 文件内容。"""

from typing import List, Optional
from pydantic import BaseModel, Field


class FileItem(BaseModel):
    """单个文件/目录条目"""
    name: str = Field(..., description="文件或目录名称")
    type: str = Field(..., description="类型：dir 或 file")
    size: Optional[int] = Field(default=None, description="文件大小（字节），目录为 None")
    modified: str = Field(..., description="最后修改时间（ISO 格式）")


class DirectoryListResponse(BaseModel):
    """目录列表响应"""
    path: str = Field(default="", description="当前请求的相对路径")
    items: List[FileItem] = Field(default_factory=list, description="目录内容列表")


# ── 上传 ──

class CreateFileRequest(BaseModel):
    """创建文件请求"""
    path: str = Field(..., description="相对路径（含文件名）", min_length=1)
    content: str = Field(default="", description="文件内容，为空则创建空文件")


class CreateDirectoryRequest(BaseModel):
    """创建目录请求"""
    path: str = Field(..., description="相对路径", min_length=1)


# ── 修改 ──

class RenameRequest(BaseModel):
    """重命名文件/目录请求"""
    path: str = Field(..., description="当前相对路径", min_length=1)
    new_name: str = Field(..., description="新名称（仅文件名/目录名，不含路径）", min_length=1)


class ModifyFileRequest(BaseModel):
    """修改文件内容请求"""
    path: str = Field(..., description="文件相对路径", min_length=1)
    content: str = Field(..., description="新的文件内容")


class MoveRequest(BaseModel):
    """移动文件/目录请求"""
    path: str = Field(..., description="当前相对路径", min_length=1)
    target_dir: str = Field(..., description="目标目录相对路径，空字符串表示根目录")


# ── 删除 ──

class DeleteRequest(BaseModel):
    """删除文件/目录请求"""
    path: str = Field(..., description="要删除的文件/目录相对路径", min_length=1)


# ── 操作结果 ──

class OperationResult(BaseModel):
    """通用操作结果"""
    success: bool = Field(..., description="操作是否成功")
    message: str = Field(default="", description="操作结果描述")
    path: str = Field(default="", description="操作的路径")

