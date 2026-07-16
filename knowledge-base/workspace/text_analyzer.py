#!/usr/bin/env python3
"""text_analyzer.py — 文本统计分析工具（CLI）"""

import argparse
import os
import sys
from collections import Counter
from string import punctuation


def read_file(path: str) -> str:
    """读取文本文件，自动处理编码"""
    for encoding in ("utf-8", "gbk", "latin-1"):
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    raise RuntimeError(f"无法解码文件: {path}")


def analyze_text(text: str) -> dict:
    """对文本进行全方位统计分析"""
    lines = text.splitlines()
    words = text.split()

    # 字符统计
    char_count = len(text)
    char_no_space = len(text.replace(" ", "").replace("\n", "").replace("\r", ""))

    # 行统计
    line_count = len(lines)
    blank_lines = sum(1 for line in lines if line.strip() == "")
    non_blank_lines = line_count - blank_lines

    # 词统计
    word_count = len(words)
    unique_words = len(set(words))

    # 字符频率（排除空白）
    letters = [ch for ch in text if ch.strip() and ch not in punctuation]
    char_freq = Counter(letters).most_common(10)

    # 词频
    word_freq = Counter(words).most_common(10)

    # 最长行
    longest_line = max(lines, key=len) if lines else ""
    shortest_line = min((l for l in lines if l.strip()), key=len, default="")

    return {
        "char_count": char_count,
        "char_no_space": char_no_space,
        "line_count": line_count,
        "blank_lines": blank_lines,
        "non_blank_lines": non_blank_lines,
        "word_count": word_count,
        "unique_words": unique_words,
        "avg_word_length": round(sum(len(w) for w in words) / word_count, 2) if word_count else 0,
        "char_freq": char_freq,
        "word_freq": word_freq,
        "longest_line": (len(longest_line), longest_line.strip()[:80]),
        "shortest_line": (len(shortest_line), shortest_line.strip()[:80]),
    }


def print_report(stats: dict, filename: str) -> None:
    """格式化输出分析报告"""
    sep = "=" * 56
    print(f"\n{sep}")
    print(f"  文本分析报告 — {filename}")
    print(f"{sep}")
    print(f"  📄 行数统计")
    print(f"     总行数:         {stats['line_count']:>8}")
    print(f"     非空行:         {stats['non_blank_lines']:>8}")
    print(f"     空行:           {stats['blank_lines']:>8}")
    print()
    print(f"  🔤 字符统计")
    print(f"     总字符（含空格）: {stats['char_count']:>8}")
    print(f"     总字符（不含空格）:{stats['char_no_space']:>8}")
    print()
    print(f"  📝 词语统计")
    print(f"     总词数:         {stats['word_count']:>8}")
    print(f"     不重复词数:     {stats['unique_words']:>8}")
    print(f"     平均词长:       {stats['avg_word_length']:>8}")
    print()
    print(f"  🏆 高频字符 Top 10")
    for ch, cnt in stats["char_freq"]:
        print(f"     {repr(ch):>4}: {cnt}")
    print()
    print(f"  🏆 高频词语 Top 10")
    for w, cnt in stats["word_freq"]:
        print(f"     {w[:20]:>20}: {cnt}")
    print()
    print(f"  📏 最长行 ({stats['longest_line'][0]} 字符)")
    print(f"     {stats['longest_line'][1]}...")
    print(f"  📏 最短行 ({stats['shortest_line'][0]} 字符)")
    print(f"     {stats['shortest_line'][1]}")
    print(f"{sep}\n")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="文本统计分析工具 — 分析文件的字符、词语、行数等指标",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n  python text_analyzer.py article.txt\n  python text_analyzer.py *.txt --sort",
    )
    parser.add_argument("files", nargs="+", help="要分析的一个或多个文本文件")
    parser.add_argument("--sort", action="store_true", help="按词数降序排列输出")
    args = parser.parse_args()

    results = []
    for path in args.files:
        if not os.path.isfile(path):
            print(f"⚠ 跳过非文件: {path}", file=sys.stderr)
            continue
        try:
            text = read_file(path)
            stats = analyze_text(text)
            results.append((path, stats))
        except Exception as e:
            print(f"✗ 读取失败 {path}: {e}", file=sys.stderr)

    if args.sort:
        results.sort(key=lambda x: x[1]["word_count"], reverse=True)

    for path, stats in results:
        print_report(stats, path)

    # 多文件汇总
    if len(results) > 1:
        total_words = sum(r["word_count"] for _, r in results)
        total_chars = sum(r["char_count"] for _, r in results)
        print("=" * 56)
        print(f"  汇总 — {len(results)} 个文件")
        print(f"     总字数: {total_words}")
        print(f"     总字符: {total_chars}")
        print("=" * 56)


if __name__ == "__main__":
    main()
