"""创建/更新 progress 表 —— 艾宾浩斯记忆曲线追踪"""

import sqlite3
from pathlib import Path

DB_PATH = Path(r"f:\index_rag\word\data\vocab.db")

# 复习间隔（天）：答对后推进
INTERVALS = [0, 1, 2, 4, 7, 14, "20-30"]  # level 6 是维护模式，随机20-30天，永不停止


def setup_progress_table():
    conn = sqlite3.connect(str(DB_PATH))
    # 重建表（有数据时慎用，当前无记录，重建安全）
    conn.execute("DROP TABLE IF EXISTS progress")
    conn.execute("""
        CREATE TABLE progress (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            word_id       INTEGER NOT NULL UNIQUE,
            review_level  INTEGER NOT NULL DEFAULT 0,
            total_attempts INTEGER NOT NULL DEFAULT 0,
            correct_count INTEGER NOT NULL DEFAULT 0,
            streak        INTEGER NOT NULL DEFAULT 0,
            last_reviewed TEXT,
            next_review   TEXT,
            FOREIGN KEY (word_id) REFERENCES words(id)
        )
    """)
    conn.commit()
    conn.close()
    print("progress 表重建成功")


def show_schema():
    conn = sqlite3.connect(str(DB_PATH))
    cols = conn.execute("PRAGMA table_info(progress)").fetchall()
    print("\n表结构:")
    print(f"{'字段':<18} {'类型':<12} {'说明'}")
    print("-" * 55)
    for cid, name, ctype, notnull, default, pk in cols:
        desc = {
            "id": "主键",
            "word_id": "关联 words 表",
            "review_level": "复习级别 0=未学 1-5=加深 6=维护",
            "total_attempts": "总答题次数",
            "correct_count": "答对次数",
            "streak": "连续答对次数",
            "last_reviewed": "上次复习时间",
            "next_review": "下次应复习时间",
        }.get(name, "")
        print(f"  {name:<16} {ctype:<12} {desc}")

    print(f"\n复习间隔规则:")
    print(f"  Level 0: 未开始学习")
    for i, days in enumerate(INTERVALS[1:], 1):
        if i == len(INTERVALS) - 1:
            print(f"  Level {i}: 答对 → {days}天后复习（维护模式，永远循环）")
        else:
            print(f"  Level {i}: 答对 → {days}天后复习")
    print(f"\n  答错任一题 → 回退到 Level 0（立即重学）")

    # 统计
    total = conn.execute("SELECT COUNT(*) FROM words").fetchone()[0]
    has_progress = conn.execute("SELECT COUNT(*) FROM progress").fetchone()[0]
    print(f"\nwords 表: {total} 词 | progress 表: {has_progress} 条记录")
    conn.close()


def main():
    setup_progress_table()
    show_schema()


if __name__ == "__main__":
    main()
