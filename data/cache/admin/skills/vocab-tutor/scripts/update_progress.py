"""批量更新复习进度 — Agent 汇报结果后写入"""

import sqlite3
import json
import random
import argparse
from datetime import datetime, timedelta
from pathlib import Path

DB_PATH = Path(r"f:\index_rag\word\data\vocab.db")

# 复习间隔（天）
INTERVALS = [0, 1, 2, 4, 7, 14]  # level 6 随机 20-30


def calc_next_review(level: int, now: datetime) -> str:
    """根据级别计算下次复习时间"""
    if level <= 0:
        return now.strftime("%Y-%m-%d %H:%M:%S")
    if level >= 6:
        days = random.randint(20, 30)
    else:
        days = INTERVALS[level]
    return (now + timedelta(days=days)).strftime("%Y-%m-%d %H:%M:%S")


def update_progress(results: list[dict]) -> dict:
    """
    results: [{"word_id": 1, "correct": true, "attempts": 2}, ...]
    correct=true  表示最终答对了（可能经过提示）
    attempts      试了几次（1=一次过, >1=有错误）
    """
    conn = sqlite3.connect(str(DB_PATH))
    now = datetime.now()
    now_str = now.strftime("%Y-%m-%d %H:%M:%S")
    stats = {"correct": 0, "wrong": 0}

    for r in results:
        word_id = r["word_id"]
        correct = r["correct"]
        attempts = max(1, r.get("attempts", 1))

        # 查当前进度
        row = conn.execute(
            "SELECT review_level, correct_count, total_attempts FROM progress WHERE word_id=?",
            (word_id,),
        ).fetchone()

        if row:
            old_level, old_correct, old_total = row
        else:
            old_level, old_correct, old_total = 0, 0, 0

        new_total = old_total + attempts
        new_level = old_level

        if correct:
            new_correct = old_correct + 1
            stats["correct"] += 1

            if attempts == 1:
                # 一次答对：升级
                new_level = min(old_level + 1, 6)
            elif old_level > 0:
                # 有提示但答对：降级但不归零
                new_level = max(old_level - 1, 1)
            else:
                new_level = 1
        else:
            # 最终答错：归零
            new_correct = old_correct
            new_level = 0
            stats["wrong"] += 1

        next_review = calc_next_review(new_level, now)

        conn.execute(
            """
            INSERT INTO progress (word_id, review_level, total_attempts,
                                  correct_count, streak, last_reviewed, next_review)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(word_id) DO UPDATE SET
                review_level  = excluded.review_level,
                total_attempts = excluded.total_attempts,
                correct_count = excluded.correct_count,
                streak        = CASE WHEN excluded.review_level = 0 THEN 0
                                     ELSE streak + 1 END,
                last_reviewed = excluded.last_reviewed,
                next_review   = excluded.next_review
            """,
            (word_id, new_level, new_total, new_correct,
             int(correct), now_str, next_review),
        )

    conn.commit()
    conn.close()
    return stats


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=str, required=True,
                        help='JSON: [{"word_id":1,"correct":true,"attempts":1},...]')
    args = parser.parse_args()

    results = json.loads(args.results)
    stats = update_progress(results)

    # 附加今日统计
    conn = sqlite3.connect(str(DB_PATH))
    mastered = conn.execute(
        "SELECT COUNT(*) FROM progress WHERE review_level >= 6"
    ).fetchone()[0]
    learned = conn.execute(
        "SELECT COUNT(*) FROM progress WHERE review_level > 0"
    ).fetchone()[0]
    conn.close()

    print(json.dumps({
        "ok": True,
        "correct": stats["correct"],
        "wrong": stats["wrong"],
        "total_learned": learned,
        "total_mastered": mastered,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
