"""
ECDICT 词典查询模块
"""

import sqlite3
from pathlib import Path
from typing import Optional, Dict, Any

BASE_DIR = Path(__file__).parent
DICT_DB_PATH = BASE_DIR / "ecdict.db"


class Dictionary:
    def __init__(self, db_path: Path = DICT_DB_PATH):
        self.db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None

    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        if self._conn is None:
            if not self.db_path.exists():
                raise FileNotFoundError(
                    f"词典数据库不存在: {self.db_path}\n"
                    f"请从 https://github.com/skywind3000/ECDICT/releases 下载 ecdict-sqlite-28.zip\n"
                    f"解压后将 stardict.db 重命名为 ecdict.db 并放到项目根目录"
                )
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def lookup(self, word: str) -> Optional[Dict[str, Any]]:
        """
        查询单词

        Args:
            word: 要查询的单词

        Returns:
            包含单词信息的字典，如果未找到返回 None
        """
        if not word or not word.strip():
            return None

        word = word.strip().lower()

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 查询单词
            cursor.execute(
                "SELECT word, phonetic, translation, definition, pos, collins, oxford, tag, frq, exchange "
                "FROM stardict WHERE word = ? LIMIT 1",
                (word,)
            )

            row = cursor.fetchone()

            if row is None:
                return None

            # 格式化返回数据
            result = {
                "word": row["word"],
                "phonetic": row["phonetic"] or "",
                "translation": row["translation"] or "",  # 中文释义
                "definition": row["definition"] or "",    # 英文释义
                "pos": row["pos"] or "",                  # 词性
                "collins": row["collins"] or 0,           # 柯林斯星级
                "oxford": bool(row["oxford"]),            # 是否牛津3000词
                "tag": row["tag"] or "",                  # 标签
                "frequency": row["frq"] or 0,             # 词频
                "exchange": row["exchange"] or "",        # 时态变化
            }

            return result

        except Exception as e:
            print(f"词典查询错误: {e}")
            return None

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None


# 全局词典实例
_dict_instance: Optional[Dictionary] = None


def get_dictionary() -> Dictionary:
    """获取全局词典实例"""
    global _dict_instance
    if _dict_instance is None:
        _dict_instance = Dictionary()
    return _dict_instance


def lookup_word(word: str) -> Optional[Dict[str, Any]]:
    """便捷函数：查询单词"""
    return get_dictionary().lookup(word)
