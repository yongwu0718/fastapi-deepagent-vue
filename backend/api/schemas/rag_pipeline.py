"""RAG Pipeline 请求/响应 schema。"""

from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ═══════════════════════════════════════════
#  分块配置（告知前端当前分割策略）
# ═══════════════════════════════════════════

class SplitConfig(BaseModel):
    """当前生效的文档分割配置。"""

    headers: list[str] = Field(..., description="用于切分的标题层级，如 ['#', '##', '###']")
    return_each_line: bool = Field(default=False, description="是否逐行返回")
    strip_headers: bool = Field(default=False, description="是否剥离标题行")
    enable_char_split: bool = Field(default=True, description="是否启用二级字符切分")
    chunk_size: int = Field(..., description="字符切分的最大 chunk 大小（字符数）")
    chunk_overlap: int = Field(..., description="字符切分的重叠区间大小（字符数）")
    secondary_separators: list[str] = Field(
        default_factory=lambda: ["\n\n", "\n", "。", "，", " ", ""],
        description="二级字符切分的分隔符优先级",
    )


# ═══════════════════════════════════════════
#  分块详情
# ═══════════════════════════════════════════

class ChunkDetail(BaseModel):
    """单个 chunk 的详细信息。"""

    index: int = Field(..., description="分块序号，从 1 开始")
    content_length: int = Field(..., description="该 chunk 的字符数")
    preview: str = Field(..., description="前 120 个字符的摘要预览")
    header_path: Optional[str] = Field(
        default=None,
        description="该 chunk 所属的标题路径，如 '# 概述 > ## 背景'",
    )
    is_char_split: bool = Field(
        default=False,
        description="是否经过二级字符切分（true 表示该 chunk 来自字符级再分块）",
    )

    @field_validator("preview", mode="before")
    @classmethod
    def _truncate_preview(cls, v: str) -> str:
        if len(v) <= 120:
            return v
        return v[:120] + "..."


# ═══════════════════════════════════════════
#  处理请求
# ═══════════════════════════════════════════

class RAGProcessRequest(BaseModel):
    """处理 markdown 文件并存入向量库的请求（本地路径模式，保留兼容）。"""

    files: list[str] = Field(
        ...,
        min_length=1,
        description="待处理的 .md 文件绝对路径列表",
    )
    preview_dir: Optional[str] = Field(
        default=None,
        description="分块预览输出目录，不传则使用配置中的默认值",
    )
    preview_only: bool = Field(
        default=False,
        description="仅预览分块而不入库（true 时只切分不保存）",
    )


# ═══════════════════════════════════════════
#  删除请求
# ═══════════════════════════════════════════

class RAGDeleteRequest(BaseModel):
    """从向量库删除文档的请求。"""

    ids: list[str] = Field(
        ...,
        min_length=1,
        description="待删除的文档 ID 列表（可从向量库查询获取）",
    )


# ═══════════════════════════════════════════
#  处理结果
# ═══════════════════════════════════════════

class RAGProcessResult(BaseModel):
    """单个文件的处理结果。"""

    filename: str = Field(..., description="文件名")
    file_size: int = Field(..., description="原文件大小（字节）")
    chunks_count: int = Field(..., description="生成的分块数")
    status: str = Field(default="success", description="处理状态: success / error")
    error: Optional[str] = Field(default=None, description="失败时的错误信息")
    chunks: list[ChunkDetail] = Field(
        default_factory=list,
        description="每个 chunk 的详细信息（包含大小、标题路径等）",
    )


class RAGProcessResponse(BaseModel):
    """批量处理响应。"""

    total_files: int = Field(..., description="总文件数")
    success_count: int = Field(..., description="成功数")
    failed_count: int = Field(..., description="失败数")
    total_chunks: int = Field(..., description="总入库分块数")
    collection_count: int = Field(..., description="向量库当前文档块总数")
    split_config: SplitConfig = Field(..., description="本次处理使用的分割配置")
    results: list[RAGProcessResult] = Field(default_factory=list, description="每个文件的处理详情")


# ═══════════════════════════════════════════
#  删除结果
# ═══════════════════════════════════════════

class RAGDeleteResponse(BaseModel):
    """删除操作响应。"""

    deleted_count: int = Field(..., description="成功删除的文档数")
    collection_count: int = Field(..., description="向量库当前文档块总数")
    message: str = Field(default="删除成功", description="操作描述")


# ═══════════════════════════════════════════
#  健康检查
# ═══════════════════════════════════════════

class RAGHealthResponse(BaseModel):
    """向量库健康检查响应。"""

    collection_name: str = Field(..., description="集合名称")
    collection_count: int = Field(..., description="当前文档块总数")
    persist_directory: str = Field(..., description="持久化目录")
    embedding_model: str = Field(..., description="嵌入模型名称")
    embedding_base_url: str = Field(..., description="嵌入模型服务地址")


# ═══════════════════════════════════════════
#  rag_config.yaml 管理模型（前端可直接编辑）
# ═══════════════════════════════════════════

class RAGEmbeddingConfig(BaseModel):
    """嵌入模型配置。"""
    model: str = Field(default="my-qwen3-embed:latest", description="Ollama 嵌入模型名称")
    base_url: str = Field(default="http://localhost:11434", description="Ollama 服务地址")


class RAGSplitterConfig(BaseModel):
    """文档分割器配置。"""
    headers: list[str] = Field(
        default_factory=lambda: ["#", "##", "###"],
        description="用于切分的标题层级",
    )
    return_each_line: bool = Field(default=False, description="是否逐行返回")
    strip_headers: bool = Field(default=False, description="是否剥离标题行")
    enable_char_split: bool = Field(default=True, description="是否启用二级字符切分")
    chunk_size: int = Field(default=1000, ge=100, le=10000, description="字符切分最大 chunk 大小")
    chunk_overlap: int = Field(default=200, ge=0, le=2000, description="字符切分重叠区间大小")


class RAGHNSWConfig(BaseModel):
    """Chroma HNSW 索引参数。"""
    space: str = Field(default="cosine", description="距离度量: cosine / l2 / ip")
    ef_construction: int = Field(default=200, ge=10, le=2000, description="构建时的搜索深度")
    max_neighbors: int = Field(default=32, ge=4, le=256, description="最大邻居数")
    ef_search: int = Field(default=200, ge=10, le=2000, description="查询时的搜索深度")
    num_threads: int = Field(default=4, ge=1, le=64, description="构建时的线程数")
    batch_size: int = Field(default=100, ge=1, le=10000, description="批量入库大小")
    sync_threshold: int = Field(default=1000, ge=1, le=100000, description="同步阈值")
    resize_factor: float = Field(default=1.2, ge=1.0, le=5.0, description="扩容因子")


class RAGProcessingConfig(BaseModel):
    """处理参数配置。"""
    preview_output_dir: str = Field(default="preview", description="分块预览输出目录")
    enable_interactive: bool = Field(default=True, description="CLI 模式下是否交互确认")


class RAGPipelineSection(BaseModel):
    """rag_config.yaml 中 rag 段的配置。"""
    splitter: RAGSplitterConfig = Field(default_factory=RAGSplitterConfig)
    hnsw: RAGHNSWConfig = Field(default_factory=RAGHNSWConfig)
    processing: RAGProcessingConfig = Field(default_factory=RAGProcessingConfig)


class RAGFullConfigModel(BaseModel):
    """完整的 rag_config.yaml 结构 —— 读/写共用。"""
    embedding: RAGEmbeddingConfig = Field(default_factory=RAGEmbeddingConfig)
    rag: RAGPipelineSection = Field(default_factory=RAGPipelineSection)
