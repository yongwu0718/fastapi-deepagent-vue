"""查询今日待复习单词 — review 模式"""

import sqlite3
import json
import argparse
from pathlib import Path

DB_PATH = Path(r"f:\index_rag\word\data\vocab.db")


def get_review_queue(limit: int | None = None) -> dict:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row

    # 待复习：next_review 已到期 或 null（尚未建立进度）
    rows = conn.execute(
        """
        SELECT w.id, w.word, w.meaning, w.pos, w.lesson,
               COALESCE(p.review_level, 0) AS review_level,
               p.next_review, p.correct_count, p.total_attempts
        FROM words w
        LEFT JOIN progress p ON w.id = p.word_id
        WHERE p.word_id IS NULL          -- 从未学过
           OR p.next_review <= datetime('now', 'localtime')  -- 到期
        ORDER BY
            CASE WHEN p.word_id IS NULL THEN 0 ELSE p.review_level END ASC,
            w.lesson ASC
        """ + (f"LIMIT {limit}" if limit else ""),
    ).fetchall()
    conn.close()

    words = [dict(r) for r in rows]
    return {
        "due": len(words),
        "words": words,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None,
                        help="限制数量，默认全部")
    parser.add_argument("--stats", action="store_true",
                        help="只输出统计，不输出词列表")
    args = parser.parse_args()

    if args.stats:
        conn = sqlite3.connect(str(DB_PATH))
        total_words = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
        total_learned = conn.execute(
            "SELECT COUNT(*) FROM progress WHERE review_level > 0"
        ).fetchone()[0]
        by_level = conn.execute(
            """
            SELECT review_level, COUNT(*) as cnt
            FROM progress
            GROUP BY review_level
            ORDER BY review_level
            """
        ).fetchall()
        due_count = conn.execute(
            """
            SELECT COUNT(*) FROM words w
            LEFT JOIN progress p ON w.id = p.word_id
            WHERE p.word_id IS NULL
               OR p.next_review <= datetime('now', 'localtime')
            """
        ).fetchone()[0]
        conn.close()

        level_dist = {str(l): c for l, c in by_level}
        print(json.dumps({
            "total_words": total_words,
            "total_learned": total_learned,
            "total_unlearned": total_words - total_learned,
            "due_today": due_count,
            "level_distribution": level_dist,
        }, ensure_ascii=False, indent=2))
    else:
        result = get_review_queue(args.limit)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
