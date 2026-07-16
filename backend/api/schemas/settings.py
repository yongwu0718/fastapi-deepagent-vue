"""Settings API 请求/响应模型。"""

from pydantic import BaseModel


class ContentBody(BaseModel):
    """通用文本内容请求体（YAML / TXT / JSON 配置）。"""
    content: str


class MemoryFileBody(BaseModel):
    """记忆库/技能库文件创建/更新请求体。"""
    filename: str
    content: str = ""


class SkillsUpdateRequest(BaseModel):
    """Skills 开关更新请求。"""
    enabled: list[str]
