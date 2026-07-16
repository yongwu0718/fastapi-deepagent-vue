import os
from pathlib import Path

import pdfplumber
import pymupdf4llm
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
    TableStructureV2Options,
    CodeFormulaVlmOptions,
)
from docling.datamodel.settings import settings
from docling.datamodel.base_models import InputFormat
from docling.document_converter import DocumentConverter, PdfFormatOption

# 指向手动下载的本地模型
settings.artifacts_path = Path(r"F:\index_rag\models")


def pdf_to_text(pdf_source):
    """从 PDF 文件中提取纯文本（pdfplumber），公式可能丢失/乱码。"""
    with pdfplumber.open(pdf_source) as pdf:
        pages = [page.extract_text() for page in pdf.pages]
    return "\n\n".join(p for p in pages if p)


def pdf_to_markdown_docling(pdf_path: str) -> str:
    """使用 docling 将 PDF 转为 Markdown，数学公式保留为 LaTeX（需开启公式检测）。"""
    pipeline_options = PdfPipelineOptions()
    pipeline_options.table_structure_options = TableStructureV2Options()

    # ✅ 开启数学公式检测，将公式转换为 LaTeX（docling ≥ 2.x 新 API）
    pipeline_options.do_formula_enrichment = True
    pipeline_options.code_formula_options = CodeFormulaVlmOptions.from_preset(
        "codeformulav2"
    )

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options),
        },
    )
    result = converter.convert(pdf_path)
    return result.document.export_to_markdown()


def pdf_to_markdown_fast(pdf_path: str) -> str:
    """使用 pymupdf4llm 将 PDF 转为 Markdown，无需模型但公式支持弱。"""
    return pymupdf4llm.to_markdown(pdf_path)


def main():
    """主函数，使用 docling 解析 PDF 并输出 Markdown。"""
    pdf_path = r"F:\index_rag\knowledge-base\page_16.pdf"

    print(f"[INFO] 正在解析: {pdf_path} ...")
    markdown = pdf_to_markdown_docling(pdf_path)

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(os.path.dirname(__file__), "output", f"{base_name}.md")
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(markdown)

    print(f"[DONE] Markdown 已保存到: {output_path}")
    print(f"[INFO] 总字符数: {len(markdown)}")
    print("\n--- 预览（前 500 字符）---")
    print(markdown[:500])


if __name__ == "__main__":
    main()