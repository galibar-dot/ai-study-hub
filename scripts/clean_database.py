"""
清理数据库，只保留六级文章
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import reading


def clean_database():
    """删除前3篇示例文章，只保留六级真题"""
    sys.stdout.reconfigure(encoding='utf-8')

    reading_db = reading.get_reading_db()

    print("=" * 60)
    print("清理数据库")
    print("=" * 60)

    # 获取所有文章
    articles = reading_db.get_articles()

    print(f"\n当前有 {len(articles)} 篇文章:")
    for a in articles:
        print(f"  ID {a['id']}: {a['title']} ({a['difficulty']})")

    # 删除前3篇（ID 1, 2, 3）
    conn = reading_db._get_connection()
    cursor = conn.cursor()

    for article_id in [1, 2, 3]:
        # 删除题目
        cursor.execute("DELETE FROM questions WHERE article_id = ?", (article_id,))
        # 删除答题记录
        cursor.execute("DELETE FROM reading_records WHERE article_id = ?", (article_id,))
        # 删除文章
        cursor.execute("DELETE FROM articles WHERE id = ?", (article_id,))
        print(f"\n✓ 删除文章 ID {article_id}")

    conn.commit()

    print("\n" + "=" * 60)
    print("✅ 清理完成！")
    print("=" * 60)

    # 显示剩余文章
    articles = reading_db.get_articles()
    print(f"\n剩余 {len(articles)} 篇文章:")
    for a in articles:
        print(f"  ID {a['id']}: {a['title']} ({a['difficulty']}, {a['question_count']}题)")


if __name__ == "__main__":
    clean_database()
