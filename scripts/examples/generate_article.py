"""
使用 AI 生成英语六级阅读理解文章和题目
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import reading


# 六级文章生成提示词模板
ARTICLE_GENERATION_PROMPT = """Please generate a CET-6 (College English Test Band 6) level reading comprehension article and questions.

Requirements:
1. Article length: 400-500 words
2. Topic: Choose from: education, technology, environment, society, health, economy
3. Difficulty: CET-6 level (intermediate to advanced English)
4. Structure: Introduction → Evidence/Research → Conclusion/Suggestions
5. Vocabulary: Use CET-6 core vocabulary and academic terms
6. Sentence structure: Include complex sentences, clauses, and passive voice

Generate 5 multiple-choice questions:
- Question types: detail comprehension, inference, main idea
- 4 options per question (A, B, C, D)
- Include distractors that test careful reading
- Provide explanations for correct answers

Format your response as JSON:
{{
  "title": "Article Title",
  "content": "Full article text with paragraphs separated by \\n\\n",
  "difficulty": "intermediate",
  "category": "education/tech/environment/society/health/economy",
  "questions": [
    {{
      "question_text": "Question 1 text",
      "options": ["Option A", "Option B", "Option C", "Option D"],
      "correct_answer": "Option B",
      "explanation": "Why this is correct"
    }},
    ...
  ]
}}

Topic for this article: {topic}
"""


def generate_article_with_ai(topic="education"):
    """
    使用 AI 生成文章和题目

    注意：这个函数需要调用 Claude API
    由于项目中的 Claude 是通过 Agent SDK 调用的，
    这里提供一个示例框架，实际使用时需要集成 API 调用
    """

    prompt = ARTICLE_GENERATION_PROMPT.format(topic=topic)

    print("=" * 60)
    print("AI 文章生成提示词")
    print("=" * 60)
    print(prompt)
    print("\n" + "=" * 60)
    print("使用说明：")
    print("=" * 60)
    print("1. 将上面的提示词复制到 Claude 对话中")
    print("2. Claude 会生成 JSON 格式的文章和题目")
    print("3. 将生成的 JSON 保存为文件（例如：article.json）")
    print("4. 运行 add_article_from_json.py 将文章添加到数据库")
    print("=" * 60)


def add_article_from_json(json_file):
    """
    从 JSON 文件添加文章到数据库

    JSON 格式示例：
    {
      "title": "...",
      "content": "...",
      "difficulty": "intermediate",
      "category": "education",
      "questions": [...]
    }
    """
    import json

    with open(json_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    reading_db = reading.get_reading_db()

    # 添加文章
    article_id = reading_db.add_article(
        title=data['title'],
        content=data['content'],
        difficulty=data['difficulty'],
        category=data.get('category', ''),
        source='AI Generated'
    )

    if article_id == 0:
        print("❌ 添加文章失败")
        return

    print(f"✓ 添加文章: {data['title']} (ID: {article_id})")

    # 添加题目
    for i, q in enumerate(data['questions'], 1):
        reading_db.add_question(
            article_id=article_id,
            question_text=q['question_text'],
            question_type='choice',
            options=q['options'],
            correct_answer=q['correct_answer'],
            explanation=q.get('explanation', ''),
            order_num=i
        )

    print(f"  添加了 {len(data['questions'])} 道题目")
    print("\n✅ 完成！")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # 从 JSON 文件添加文章
        json_file = sys.argv[1]
        add_article_from_json(json_file)
    else:
        # 生成提示词
        topic = input("请输入文章主题 (education/tech/environment/society/health/economy): ").strip()
        if not topic:
            topic = "education"
        generate_article_with_ai(topic)
