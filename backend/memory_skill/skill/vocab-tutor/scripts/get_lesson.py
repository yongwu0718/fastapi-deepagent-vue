"""取课内单词 — Agent 用 JSON 接口"""

import sqlite3
import json
import sys
import argparse
from pathlib import Path

DB_PATH = Path(r"f:\index_rag\word\data\vocab.db")


def get_lesson(lesson: int) -> list[dict]:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT w.id, w.word, w.meaning, w.pos,
               COALESCE(p.review_level, 0) AS review_level,
               p.next_review
        FROM words w
        LEFT JOIN progress p ON w.id = p.word_id
        WHERE w.lesson = ?
        ORDER BY w.id
        """,
        (lesson,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--lesson", type=int, required=True, help="课号 1-73")
    args = parser.parse_args()

    words = get_lesson(args.lesson)
    if not words:
        print(json.dumps({"error": f"Lesson {args.lesson} 无数据"}, ensure_ascii=False))
        sys.exit(1)

    total = len(words)
    learned = sum(1 for w in words if w["review_level"] > 0)
    print(json.dumps({
        "lesson": args.lesson,
        "total": total,
        "learned": learned,
        "words": words,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
