"""
英语阅读专项模块
"""

import sqlite3
import time
import json
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).parent
READING_DB_PATH = BASE_DIR / "chats" / "reading.db"


class ReadingDB:
    def __init__(self, db_path: Path = READING_DB_PATH):
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

        # 创建文章表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                difficulty TEXT NOT NULL,
                category TEXT,
                word_count INTEGER,
                source TEXT,
                created_at INTEGER NOT NULL
            )
        """)

        # 创建题目表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS questions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                question_text TEXT NOT NULL,
                question_type TEXT NOT NULL,
                options TEXT,
                correct_answer TEXT NOT NULL,
                explanation TEXT,
                order_num INTEGER,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        """)

        # 创建答题记录表
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS reading_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_id INTEGER NOT NULL,
                started_at INTEGER NOT NULL,
                completed_at INTEGER,
                total_questions INTEGER,
                correct_answers INTEGER,
                score REAL,
                answers TEXT,
                FOREIGN KEY (article_id) REFERENCES articles(id)
            )
        """)

        # 创建索引
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_article_difficulty ON articles(difficulty)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_question_article ON questions(article_id)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_record_article ON reading_records(article_id)
        """)

        conn.commit()

    # ========== 文章管理 ==========

    def add_article(self, title: str, content: str, difficulty: str,
                   category: str = "", source: str = "", questions: List[Dict[str, Any]] = None) -> int:
        """添加文章（可选添加题目）"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            word_count = len(content.split())
            now = int(time.time())

            cursor.execute("""
                INSERT INTO articles (title, content, difficulty, category, word_count, source, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (title, content, difficulty, category, word_count, source, now))

            article_id = cursor.lastrowid

            # 添加题目
            if questions:
                for i, q in enumerate(questions):
                    options_json = json.dumps(q.get("options", {}), ensure_ascii=False)
                    cursor.execute("""
                        INSERT INTO questions (article_id, question_text, question_type, options,
                                             correct_answer, explanation, order_num)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        article_id,
                        q.get("question", ""),
                        q.get("type", "multiple_choice"),
                        options_json,
                        q.get("answer", ""),
                        q.get("explanation", ""),
                        i + 1
                    ))

            conn.commit()
            return article_id

        except Exception as e:
            print(f"添加文章错误: {e}")
            conn.rollback()
            return 0

    def get_articles(self, difficulty: Optional[str] = None) -> List[Dict[str, Any]]:
        """获取文章列表"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if difficulty:
                cursor.execute("""
                    SELECT a.*, COUNT(q.id) as question_count
                    FROM articles a
                    LEFT JOIN questions q ON a.id = q.article_id
                    WHERE a.difficulty = ?
                    GROUP BY a.id
                    ORDER BY a.created_at DESC
                """, (difficulty,))
            else:
                cursor.execute("""
                    SELECT a.*, COUNT(q.id) as question_count
                    FROM articles a
                    LEFT JOIN questions q ON a.id = q.article_id
                    GROUP BY a.id
                    ORDER BY a.created_at DESC
                """)

            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "content": row["content"],
                    "difficulty": row["difficulty"],
                    "category": row["category"] or "",
                    "word_count": row["word_count"],
                    "source": row["source"] or "",
                    "question_count": row["question_count"],
                    "created_at": row["created_at"],
                }
                for row in rows
            ]

        except Exception as e:
            print(f"获取文章列表错误: {e}")
            return []

    def get_article(self, article_id: int) -> Optional[Dict[str, Any]]:
        """获取文章详情"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM articles WHERE id = ?
            """, (article_id,))

            row = cursor.fetchone()

            if row is None:
                return None

            return {
                "id": row["id"],
                "title": row["title"],
                "content": row["content"],
                "difficulty": row["difficulty"],
                "category": row["category"] or "",
                "word_count": row["word_count"],
                "source": row["source"] or "",
                "created_at": row["created_at"],
            }

        except Exception as e:
            print(f"获取文章详情错误: {e}")
            return None

    def delete_article(self, article_id: int) -> bool:
        """删除文章（同时删除相关题目和记录）"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 删除相关题目
            cursor.execute("DELETE FROM questions WHERE article_id = ?", (article_id,))

            # 删除相关答题记录
            cursor.execute("DELETE FROM reading_records WHERE article_id = ?", (article_id,))

            # 删除文章
            cursor.execute("DELETE FROM articles WHERE id = ?", (article_id,))

            conn.commit()
            return cursor.rowcount > 0

        except Exception as e:
            print(f"删除文章错误: {e}")
            return False

    def update_article(self, article_id: int, title: Optional[str] = None,
                      content: Optional[str] = None, difficulty: Optional[str] = None) -> bool:
        """更新文章"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            updates = []
            params = []

            if title is not None:
                updates.append("title = ?")
                params.append(title)

            if content is not None:
                updates.append("content = ?")
                params.append(content)
                updates.append("word_count = ?")
                params.append(len(content.split()))

            if difficulty is not None:
                updates.append("difficulty = ?")
                params.append(difficulty)

            if not updates:
                return True

            params.append(article_id)
            sql = f"UPDATE articles SET {', '.join(updates)} WHERE id = ?"

            cursor.execute(sql, params)
            conn.commit()

            return cursor.rowcount > 0

        except Exception as e:
            print(f"更新文章错误: {e}")
            return False

    # ========== 题目管理 ==========

    def add_question(self, article_id: int, question_text: str, question_type: str,
                    options: List[str], correct_answer: str, explanation: str = "",
                    order_num: int = 0) -> int:
        """添加题目"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            options_json = json.dumps(options, ensure_ascii=False)

            cursor.execute("""
                INSERT INTO questions (article_id, question_text, question_type, options,
                                     correct_answer, explanation, order_num)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (article_id, question_text, question_type, options_json,
                  correct_answer, explanation, order_num))

            conn.commit()
            return cursor.lastrowid

        except Exception as e:
            print(f"添加题目错误: {e}")
            return 0

    def get_questions(self, article_id: int) -> List[Dict[str, Any]]:
        """获取文章的所有题目"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT * FROM questions
                WHERE article_id = ?
                ORDER BY order_num, id
            """, (article_id,))

            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "article_id": row["article_id"],
                    "question_text": row["question_text"],
                    "question_type": row["question_type"],
                    "options": json.loads(row["options"]) if row["options"] else [],
                    "correct_answer": row["correct_answer"],
                    "explanation": row["explanation"] or "",
                    "order_num": row["order_num"],
                }
                for row in rows
            ]

        except Exception as e:
            print(f"获取题目错误: {e}")
            return []

    # ========== 答题记录 ==========

    def create_record(self, article_id: int) -> int:
        """创建答题记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            now = int(time.time())

            cursor.execute("""
                INSERT INTO reading_records (article_id, started_at)
                VALUES (?, ?)
            """, (article_id, now))

            conn.commit()
            return cursor.lastrowid

        except Exception as e:
            print(f"创建答题记录错误: {e}")
            return 0

    def submit_answers(self, record_id: int, answers: Dict[str, str]) -> Dict[str, Any]:
        """提交答案并计算得分"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 获取记录
            cursor.execute("""
                SELECT article_id FROM reading_records WHERE id = ?
            """, (record_id,))

            row = cursor.fetchone()
            if not row:
                return {"ok": False, "error": "记录不存在"}

            article_id = row["article_id"]

            # 获取题目
            questions = self.get_questions(article_id)

            # 计算得分
            total = len(questions)
            correct = 0
            results = []

            for q in questions:
                q_id = str(q["id"])
                user_answer = answers.get(q_id, "")
                is_correct = user_answer == q["correct_answer"]

                if is_correct:
                    correct += 1

                results.append({
                    "question_id": q["id"],
                    "question_text": q["question_text"],
                    "user_answer": user_answer,
                    "correct_answer": q["correct_answer"],
                    "is_correct": is_correct,
                    "explanation": q["explanation"],
                })

            score = (correct / total * 100) if total > 0 else 0

            # 更新记录
            now = int(time.time())
            answers_json = json.dumps(answers, ensure_ascii=False)

            cursor.execute("""
                UPDATE reading_records
                SET completed_at = ?,
                    total_questions = ?,
                    correct_answers = ?,
                    score = ?,
                    answers = ?
                WHERE id = ?
            """, (now, total, correct, score, answers_json, record_id))

            conn.commit()

            return {
                "ok": True,
                "score": score,
                "total": total,
                "correct": correct,
                "results": results,
            }

        except Exception as e:
            print(f"提交答案错误: {e}")
            return {"ok": False, "error": str(e)}

    def get_stats(self) -> Dict[str, Any]:
        """获取学习统计"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # 总完成数
            cursor.execute("""
                SELECT COUNT(*) as total FROM reading_records WHERE completed_at IS NOT NULL
            """)
            total_completed = cursor.fetchone()["total"]

            # 总题目数和正确数
            cursor.execute("""
                SELECT SUM(total_questions) as total_q, SUM(correct_answers) as correct_q
                FROM reading_records WHERE completed_at IS NOT NULL
            """)
            row = cursor.fetchone()
            total_questions = row["total_q"] or 0
            correct_questions = row["correct_q"] or 0

            # 平均分
            cursor.execute("""
                SELECT AVG(score) as avg_score FROM reading_records WHERE completed_at IS NOT NULL
            """)
            avg_score = cursor.fetchone()["avg_score"] or 0

            # 各难度完成数
            cursor.execute("""
                SELECT a.difficulty, COUNT(*) as count
                FROM reading_records r
                JOIN articles a ON r.article_id = a.id
                WHERE r.completed_at IS NOT NULL
                GROUP BY a.difficulty
            """)
            difficulty_stats = {row["difficulty"]: row["count"] for row in cursor.fetchall()}

            return {
                "total_completed": total_completed,
                "total_questions": total_questions,
                "correct_questions": correct_questions,
                "accuracy": (correct_questions / total_questions * 100) if total_questions > 0 else 0,
                "avg_score": round(avg_score, 1),
                "difficulty_stats": difficulty_stats,
            }

        except Exception as e:
            print(f"获取统计错误: {e}")
            return {
                "total_completed": 0,
                "total_questions": 0,
                "correct_questions": 0,
                "accuracy": 0,
                "avg_score": 0,
                "difficulty_stats": {},
            }

    def get_records(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取答题记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT r.*, a.title, a.difficulty
                FROM reading_records r
                JOIN articles a ON r.article_id = a.id
                WHERE r.completed_at IS NOT NULL
                ORDER BY r.completed_at DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()

            return [
                {
                    "id": row["id"],
                    "article_id": row["article_id"],
                    "article_title": row["title"],
                    "difficulty": row["difficulty"],
                    "score": row["score"],
                    "total_questions": row["total_questions"],
                    "correct_answers": row["correct_answers"],
                    "completed_at": row["completed_at"],
                }
                for row in rows
            ]

        except Exception as e:
            print(f"获取记录错误: {e}")
            return []

    def close(self):
        """关闭数据库连接"""
        if self._conn:
            self._conn.close()
            self._conn = None


# 全局实例
_reading_instance: Optional[ReadingDB] = None


def get_reading_db() -> ReadingDB:
    """获取全局阅读数据库实例"""
    global _reading_instance
    if _reading_instance is None:
        _reading_instance = ReadingDB()
    return _reading_instance
