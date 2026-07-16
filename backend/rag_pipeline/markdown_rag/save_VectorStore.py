from ast import Try
import json
import os
import argparse
from typing import List, Optional
from langchain_core.documents import Document
from langchain_text_splitters import (
    ExperimentalMarkdownSyntaxTextSplitter,
    RecursiveCharacterTextSplitter,
)
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from backend.config.env_settings import CHROMA_DB,COLLECTION_NAME
from backend.rag_pipeline.markdown_rag.rag_setting import (
    EMBEDDING_MODEL, EMBEDDING_BASE_URL,
    RAG_SPLITTER_HEADERS, RAG_SPLITTER_RETURN_EACH_LINE, RAG_SPLITTER_STRIP_HEADERS,
    RAG_HNSW_CONFIG, RAG_PROCESSING_PREVIEW_DIR, RAG_PROCESSING_INTERACTIVE,
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
        self.model = model or os.getenv("EMBEDDING_MODEL", "my-qwen3-embed:latest")
        self.base_url = base_url or os.getenv("EMBEDDING_BASE_URL", "http://localhost:11434")
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


def save_chunks_to_markdown(chunks: List[Document], output_path: str) -> None:
    """
    保存文档块到Markdown文件
    """
    try:
        with open(output_path, "w", encoding="utf-8") as f:
            for i, chunk in enumerate(chunks):
                f.write(f"# Chunk {i+1}\n\n")
                f.write(f"**Content:**\n\n{chunk.page_content}\n\n")
        print(f"✅ 分块 Markdown 已保存至: {output_path}")
    except Exception as e:
        raise Exception(f"保存分块到Markdown失败: {e}")


class DocumentProcessor:
    """
    文档处理器
    """
    def __init__(self, vectorstore: Chroma, splitter: MarkdownSplitter):
        self.vectorstore = vectorstore
        self.splitter = splitter

    def process(self, file_path: str, preview_dir: Optional[str] = None,
                interactive: bool = False) -> List[Document]:
        print(f"\n 处理文件: {file_path}")

        loader = MarkdownLoader(file_path)
        md_text = loader.load()
        print(f"✅ 文件加载成功，长度: {len(md_text)} 字符")

        print("📝 按标题分割文档.")
        chunks = self.splitter.split_by_headers(md_text)
        print(f"✅ 按标题分割完成，共 {len(chunks)} 个章节/块")

        if not chunks:
            print("⚠️ 警告：没有生成任何文档块")
            return []

        if preview_dir:
            os.makedirs(preview_dir, exist_ok=True)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            preview_path = os.path.join(preview_dir, f"{base_name}_chunks_preview.md")
            save_chunks_to_markdown(chunks, preview_path)

        should_save = True
        if interactive:
            response = input("\n❓ 是否将分块存入向量数据库？(y/n): ").strip().lower()
            should_save = (response == 'y')

        if should_save:
            print("💾 保存到向量数据库.")
            self.vectorstore.add_documents(chunks)
            print(f"✅ 成功添加 {len(chunks)} 个文档块到向量数据库")
        else:
            print("⏭️ 已跳过入库步骤")

        return chunks

# 主函数
def main(
    files: Optional[List[str]] = None,
):
    # 使用 YAML 配置，可通过环境变量覆盖
    model = EMBEDDING_MODEL
    base_url = EMBEDDING_BASE_URL
    collection_name = COLLECTION_NAME
    persist_directory = CHROMA_DB
    preview_output_dir = RAG_PROCESSING_PREVIEW_DIR
    enable_interactive = RAG_PROCESSING_INTERACTIVE

    try:
        print("创建向量存储.")
        store_creator = VectorStoreCreator(
            collection_name=collection_name,
            persist_directory=persist_directory,
            model=model,
            base_url=base_url
        )
        vectorstore = store_creator.vectorstore

        splitter = MarkdownSplitter()

        processor = DocumentProcessor(vectorstore=vectorstore, splitter=splitter)

        all_chunks = []
        for file_path in files:
            chunks = processor.process(
                file_path=file_path,
                preview_dir=preview_output_dir,
                interactive=enable_interactive
            )
            all_chunks.extend(chunks)

        count = vectorstore._collection.count()
        print(f"\n🎉 所有文档处理完成！向量库中现有文档块总数: {count}")

    except Exception as e:
        print(f"❌ 处理过程中发生错误: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    files=input("请输入文件路径（多个文件用逗号分隔）: ")
    files=[f.strip() for f in files.split()]

    main(
        files=files,
    )
