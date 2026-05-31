"""
生词本数据库模块
"""

import sqlite3
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).parent
VOCAB_DB_PATH = BASE_DIR / "chats" / "vocabulary.db"


class VocabularyDB:
    def __init__(self, db_path: Path = VOCAB_DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            # 确保目录存在
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _init_db(self):
        """初始化数据库表"""
        conn = self._get_connection()
        cursor = conn.cursor()

        # 创建生词本表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                word TEXT NOT NULL UNIQUE,
                phonetic TEXT,
                translation TEXT,
                added_at INTEGER NOT NULL,
                review_count INTEGER DEFAULT 0,
                last_review_at INTEGER
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_word ON vocabulary(word)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_added_at ON vocabulary(added_at DESC)
        """)

        conn.commit()

    def add_word(self, word: str, phonetic: str = "", translation: str = "") -> bool:
        """
        添加单词到生词本

        Args:
            word: 单词
            phonetic: 音标
            translation: 翻译

        Returns:
            是否添加成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            now = int(time.time())

            cursor.execute("""
                INSERT OR IGNORE INTO vocabulary (word, phonetic, translation, added_at)
                VALUES (?, ?, ?, ?)
            """, (word.lower(), phonetic, translation, now))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            print(f"添加生词错误: {e}")
            return False

    def remove_word(self, word: str) -> bool:
        """
        从生词本删除单词

        Args:
            word: 单词

        Returns:
            是否删除成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM vocabulary WHERE word = ?", (word.lower(),))
            conn.commit()

            return cursor.rowcount > 0

        except Exception as e:
            print(f"删除生词错误: {e}")
            return False

    def get_all_words(self) -> List[Dict[str, Any]]:
        """
        获取所有生词

        Returns:
            生词列表
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT word, phonetic, translation, added_at, review_count, last_review_at
                FROM vocabulary
                ORDER BY added_at DESC
            """)

            rows = cursor.fetchall()

            return [
                {
                    "word": row["word"],
                    "phonetic": row["phonetic"] or "",
                    "translation": row["translation"] or "",
                    "added_at": row["added_at"],
                    "review_count": row["review_count"],
                    "last_review_at": row["last_review_at"],
                }
                for row in rows
            ]

        except Exception as e:
            print(f"获取生词列表错误: {e}")
            return []

    def is_word_in_vocab(self, word: str) -> bool:
        """
        检查单词是否在生词本中

        Args:
            word: 单词

        Returns:
            是否存在
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT 1 FROM vocabulary WHERE word = ? LIMIT 1", (word.lower(),))
            return cursor.fetchone() is not None

        except Exception as e:
            print(f"检查生词错误: {e}")
            return False

    def update_review(self, word: str) -> bool:
        """
        更新复习记录

        Args:
            word: 单词

        Returns:
            是否更新成功
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            now = int(time.time())

            cursor.execute("""
                UPDATE vocabulary
                SET review_count = review_count + 1,
                    last_review_at = ?
                WHERE word = ?
            """, (now, word.lower()))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            print(f"更新复习记录错误: {e}")
            return False

    def get_stats(self) -> Dict[str, Any]:
        """
        获取统计信息

        Returns:
            统计数据
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 总词数
            cursor.execute("SELECT COUNT(*) as total FROM vocabulary")
            total = cursor.fetchone()["total"]

            # 今日新增
            today_start = int(time.time() / 86400) * 86400
            cursor.execute("SELECT COUNT(*) as today FROM vocabulary WHERE added_at >= ?", (today_start,))
            today = cursor.fetchone()["today"]

            # 总复习次数
            cursor.execute("SELECT SUM(review_count) as total_reviews FROM vocabulary")
            total_reviews = cursor.fetchone()["total_reviews"] or 0

            return {
                "total_words": total,
                "today_added": today,
                "total_reviews": total_reviews,
            }

        except Exception as e:
            print(f"获取统计信息错误: {e}")
            return {"total_words": 0, "today_added": 0, "total_reviews": 0}

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None


# 全局生词本实例
_vocab_instance: Optional[VocabularyDB] = None


def get_vocabulary_db() -> VocabularyDB:
    """获取全局生词本实例"""
    global _vocab_instance
    if _vocab_instance is None:
        _vocab_instance = VocabularyDB()
    return _vocab_instance
