"""按课号读取单词列表"""

import sqlite3
import sys
from pathlib import Path

DB_PATH = Path(r"f:\index_rag\word\data\vocab.db")


def read_lesson(lesson: int):
    conn = sqlite3.connect(str(DB_PATH))
    rows = conn.execute(
        "SELECT word, meaning, pos FROM words WHERE lesson=? ORDER BY id",
        (lesson,),
    ).fetchall()
    conn.close()

    if not rows:
        print(f"Lesson {lesson} 不存在或没有数据")
        return

    print(f"\n{'='*70}")
    print(f"  Lesson {lesson}  ({len(rows)} 词)")
    print(f"{'='*70}")

    for i, (word, meaning, pos) in enumerate(rows, 1):
        print(f"\n  {i:>2}. {word}  [{pos}]")
        # 按词性分段展示释义
        parts = meaning.split("  ")  # 尝试按双空格分割不同词性
        if len(parts) == 1:
            parts = [p.strip() for p in meaning.split(" / ") if "/" not in p or p]
            print(f"      {meaning}")
        else:
            for p in parts:
                if p.strip():
                    print(f"      {p.strip()}")


def main():
    if len(sys.argv) < 2:
        # 无参数时列出所有课号
        conn = sqlite3.connect(str(DB_PATH))
        lessons = [r[0] for r in conn.execute(
            "SELECT DISTINCT lesson FROM words ORDER BY lesson"
        ).fetchall()]
        conn.close()
        print(f"共 {len(lessons)} 课 (1-{lessons[-1]})")
        print("用法: python read_lesson.py <课号>")
        print("示例: python read_lesson.py 1")
        return

    try:
        lesson = int(sys.argv[1])
    except ValueError:
        print(f"无效课号: {sys.argv[1]}")
        return

    read_lesson(lesson)


if __name__ == "__main__":
    main()
