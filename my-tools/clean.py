#!/usr/bin/env python3
"""
Markdown 文档清洗工具（交互式）
功能：移除 HTML 标签、链接、代码块声明中的冗余字符、特殊注释等，适合 RAG 预处理。
"""

import re
from pathlib import Path
from typing import Optional


class MarkdownCleaner:
    """
    Markdown 文档清洗器，专为 RAG 预处理设计。
    移除 HTML 标签、链接、代码块声明中的冗余内容（包括多余的 }）、代码内特殊注释等。
    """

    def __init__(self, keep_link_text: bool = True, max_consecutive_newlines: int = 2):
        """
        初始化清洗器。

        Args:
            keep_link_text: 是否保留链接的文本（默认 True）。
                            若为 True，[text](url) -> text；
                            若为 False，整个链接会被移除。
            max_consecutive_newlines: 允许的最大连续换行数，超过则压缩。
        """
        self.keep_link_text = keep_link_text
        self.max_consecutive_newlines = max_consecutive_newlines

    def clean(self, text: str) -> str:
        """
        清洗文本内容。
        Args:
            text: 原始 Markdown 文本。
        Returns:
            清洗后的纯文本。
        """
        text = re.sub(r'-\s*\d+\s*-', '', text)
        
        # 7. 压缩多余的空行
        if self.max_consecutive_newlines <= 0:
            pattern = r'\n\s*\n+'
            replacement = '\n'
        else:
            pattern = r'(\n\s*){' + str(self.max_consecutive_newlines + 1) + ',}'
            replacement = '\n' * self.max_consecutive_newlines
        text = re.sub(pattern, replacement, text)

        # 8. 去除首尾空白
        text = text.strip()
        return text

    def clean_file(self, input_path: str, output_path: Optional[str] = None, encoding: str = 'utf-8') -> None:
        """
        清洗 Markdown 文件并保存结果。

        Args:
            input_path: 输入文件路径。
            output_path: 输出文件路径。若为 None，则自动在输入文件名后添加 "_clean"。
            encoding: 文件编码，默认 utf-8。
        """
        input_path = Path(input_path)
        if output_path is None:
            output_path = input_path.parent / f"{input_path.stem}_clean{input_path.suffix}"
        else:
            output_path = Path(output_path)

        with open(input_path, 'r', encoding=encoding) as f:
            content = f.read()

        cleaned_content = self.clean(content)

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding=encoding) as f:
            f.write(cleaned_content)

        print(f"清洗完成: {input_path} -> {output_path}")

    def clean_text(self, text: str) -> str:
        """clean 方法的别名。"""
        return self.clean(text)


def main():
    """交互式入口：接收用户输入的源路径和目标路径，执行清洗。"""
    print("=== Markdown 文档清洗工具 ===")
    print("支持单个 .md 文件或包含 .md 文件的文件夹。")

    source = input("请输入源路径（文件或文件夹）：").strip()
    if not source:
        print("错误：源路径不能为空。")
        return

    target = input("请输入目标路径（文件或文件夹）：").strip()
    if not target:
        print("错误：目标路径不能为空。")
        return

    # 可选参数
    keep_link_text_input = input("是否保留链接中的文字？(y/n，默认 y)：").strip().lower()
    keep_link_text = keep_link_text_input != 'n'  # 默认 True

    max_newlines_input = input("最大连续空行数（默认 2）：").strip()
    try:
        max_newlines = int(max_newlines_input) if max_newlines_input else 2
    except ValueError:
        max_newlines = 2

    cleaner = MarkdownCleaner(
        keep_link_text=keep_link_text,
        max_consecutive_newlines=max_newlines
    )

    source_path = Path(source)
    target_path = Path(target)

    # 文件模式
    if source_path.is_file():
        if not source_path.suffix.lower() == '.md':
            print("警告：源文件不是 .md 文件，但仍将继续处理。")

        if target_path.is_dir():
            out_file = target_path / source_path.name
        else:
            out_file = target_path
        cleaner.clean_file(str(source_path), str(out_file))

    # 文件夹模式
    elif source_path.is_dir():
        if target_path.is_file():
            print("错误：源为文件夹时，目标路径必须是目录，不能是文件。")
            return
        target_path.mkdir(parents=True, exist_ok=True)
        md_files = list(source_path.glob("*.md"))
        if not md_files:
            print(f"警告：源文件夹中没有找到 .md 文件。")
        for md_file in md_files:
            out_file = target_path / md_file.name
            cleaner.clean_file(str(md_file), str(out_file))
        print(f"\n批量处理完成，共处理 {len(md_files)} 个文件，输出目录：{target_path}")

    else:
        print("错误：源路径不存在或既不是文件也不是文件夹。")
        return


if __name__ == "__main__":
    main()