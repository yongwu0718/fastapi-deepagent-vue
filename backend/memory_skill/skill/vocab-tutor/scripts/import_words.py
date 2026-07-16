"""从 Lesson.md 解析单词并导入 SQLite 数据库"""

import sqlite3
import re
from pathlib import Path

# 路径配置
MD_PATH = Path(r"f:\index_rag\knowledge-base\英语单词\Lesson.md")
DB_PATH = Path(r"f:\index_rag\word\data\vocab.db")


def parse_lesson_md(md_path: Path) -> list[tuple[int, str, str, str]]:
    """解析 Markdown 文件，返回 [(lesson, word, meaning, pos), ...]"""
    text = md_path.read_text(encoding="utf-8")
    words = []
    current_lesson = None

    for line in text.split("\n"):
        line = line.strip()

        # 匹配 **Lesson N** 行，确定当前课号
        lesson_match = re.search(r"\*\*Lesson\s+(\d+)\*\*", line)
        if lesson_match:
            current_lesson = int(lesson_match.group(1))
            continue

        # 匹配表格数据行: | 序号 | 词汇 | 释义 |
        # 序号是纯数字才算是数据行（跳过表头、分组标题等）
        data_match = re.match(
            r"\|\s*(\d+)\s*\|\s*([A-Za-z][\w\-]*)\s*\|\s*(.+?)\s*\|", line
        )
        if data_match and current_lesson:
            word = data_match.group(2).strip()
            meaning = data_match.group(3).strip()
            pos = extract_pos(meaning)
            words.append((current_lesson, word, meaning, pos))

    return words


def extract_pos(meaning: str) -> str:
    """从释义中提取词性缩写，如 'n.;v.'"""
    # 常见词性缩写
    pos_pattern = re.compile(
        r"\b(n\.|v\.|a\.|ad\.|prep\.|conj\.|pron\.|num\.|int\.|art\.|aux\.|interj\.)"
    )
    matches = pos_pattern.findall(meaning)
    seen = []
    for m in matches:
        if m not in seen:
            seen.append(m)
    return ";".join(seen)


def create_db(db_path: Path):
    """创建数据库和表"""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS words (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            lesson   INTEGER NOT NULL,
            word     TEXT    NOT NULL,
            meaning  TEXT    NOT NULL,
            pos      TEXT
        )
    """)
    # 删除旧数据（可重复执行）
    conn.execute("DELETE FROM words")
    conn.commit()
    return conn


def import_words(conn: sqlite3.Connection, words: list[tuple[int, str, str, str]]):
    """批量导入单词"""
    conn.executemany(
        "INSERT INTO words (lesson, word, meaning, pos) VALUES (?, ?, ?, ?)",
        words,
    )
    conn.commit()


def verify(conn: sqlite3.Connection):
    """打印导入统计和抽样"""
    total = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    lessons = conn.execute(
        "SELECT lesson, COUNT(*) FROM words GROUP BY lesson ORDER BY lesson"
    ).fetchall()

    print(f"\n=== 导入完成 ===")
    print(f"总单词数: {total}")
    print(f"总课数: {len(lessons)}")
    print(f"\n每课单词数:")
    for les, cnt in lessons:
        flag = " ❌ 异常" if cnt != 40 else ""
        print(f"  Lesson {les:>2}: {cnt} 词{flag}")

    # 抽样展示
    print(f"\n=== 抽样展示 (Lesson 1 前5个) ===")
    samples = conn.execute(
        "SELECT lesson, word, meaning, pos FROM words WHERE lesson=1 LIMIT 5"
    ).fetchall()
    for les, w, m, p in samples:
        print(f"  [{les}] {w}  ({p})  {m[:50]}...")

    print(f"\n=== 抽样展示 (Lesson 73 后5个) ===")
    samples = conn.execute(
        "SELECT lesson, word, meaning, pos FROM words WHERE lesson=73 ORDER BY id DESC LIMIT 5"
    ).fetchall()
    for les, w, m, p in reversed(samples):
        print(f"  [{les}] {w}  ({p})  {m[:50]}...")


def main():
    print(f"解析: {MD_PATH}")
    words = parse_lesson_md(MD_PATH)
    print(f"解析到 {len(words)} 个单词")

    conn = create_db(DB_PATH)
    import_words(conn, words)
    verify(conn)
    conn.close()


if __name__ == "__main__":
    main()
