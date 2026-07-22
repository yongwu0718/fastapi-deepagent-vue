import os
from typing import List
from langchain_core.documents import Document
from langchain_text_splitters import (
    ExperimentalMarkdownSyntaxTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from backend.api.markdown_rag.rag_setting import (
    EMBEDDING_MODEL, EMBEDDING_BASE_URL,
    RAG_SPLITTER_HEADERS, RAG_SPLITTER_RETURN_EACH_LINE, RAG_SPLITTER_STRIP_HEADERS,
    RAG_HNSW_CONFIG,
    RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP, RAG_ENABLE_CHAR_SPLIT,
)

class MarkdownLoader:
    """
    Markdown文件加载器
    """
    def __init__(self, file_path: str):
        self.file_path = file_path

    def load(self) -> str:
        try:
            with open(self.file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            raise Exception(f"加载Markdown文件失败: {e}")

class MarkdownSplitter:
    """
    Markdown文本分割器（基于 ExperimentalMarkdownSyntaxTextSplitter）
    — 先按标题/代码块/水平分割线切分，再对超长 chunk 按字符长度二次切分
    """
    def __init__(self):
        headers_to_split_on = [
            (h, f"Header {i+1}") for i, h in enumerate(RAG_SPLITTER_HEADERS)
        ]
        self.header_splitter = ExperimentalMarkdownSyntaxTextSplitter(
            headers_to_split_on=headers_to_split_on,
            return_each_line=RAG_SPLITTER_RETURN_EACH_LINE,
            strip_headers=RAG_SPLITTER_STRIP_HEADERS,
        )
        self.char_splitter = RecursiveCharacterTextSplitter(
            chunk_size=RAG_CHUNK_SIZE,
            chunk_overlap=RAG_CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "，", " ", ""],
        )

    def split_by_headers(self, text: str) -> List[Document]:
        # 第一级：按标题/代码块/水平线切分
        header_chunks = self.header_splitter.split_text(text)
        if not RAG_ENABLE_CHAR_SPLIT:
            return header_chunks
        # 第二级：对超长 chunk 按字符长度二次切分（保留元数据）
        return self.char_splitter.split_documents(header_chunks)


class VectorStoreCreator:
    """
    向量存储创建器
    """
    def __init__(self, collection_name: str, persist_directory: str,
                 model: str = None,
                 base_url: str = None):
        self.collection_name = collection_name
        self.persist_directory = persist_directory
        self.model = model or EMBEDDING_MODEL
        self.base_url = base_url or EMBEDDING_BASE_URL
        self.vectorstore = self._create_vectorstore()

    def _create_vectorstore(self) -> Chroma:
        try:
            embeddings = OllamaEmbeddings(model=self.model, base_url=self.base_url)
            return Chroma(
                collection_name=self.collection_name,
                embedding_function=embeddings,
                persist_directory=self.persist_directory,
                collection_configuration={
                    "hnsw": dict(RAG_HNSW_CONFIG)
                }
            )
        except Exception as e:
            raise Exception(f"创建向量存储失败: {e}")

# ── CLI 入口：通过 HTTP API 调用入库（需先启动 FastAPI 服务） ──
if __name__ == "__main__":
    import sys
    import json
    import urllib.request
    import urllib.error

    if len(sys.argv) < 2:
        print("用法: python save_VectorStore.py <file_path1> [file_path2 ...]")
        print("说明: 通过 HTTP API 将指定 .md 文件入库，需确保 FastAPI 服务已启动。")
        sys.exit(1)

    file_paths = sys.argv[1:]
    api_url = os.getenv("RAG_API_URL", "http://localhost:8000/api/rag/process")

    payload = json.dumps({"files": file_paths, "preview_only": False}).encode("utf-8")
    req = urllib.request.Request(
        api_url, data=payload, headers={"Content-Type": "application/json"}, method="POST",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            result = json.loads(resp.read().decode("utf-8"))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        print(f"❌ API 返回错误 {e.code}: {body}")
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"❌ 无法连接 API 服务: {e.reason}")
        print(f"   请确认 FastAPI 服务已启动。API 地址: {api_url}")
        sys.exit(1)
