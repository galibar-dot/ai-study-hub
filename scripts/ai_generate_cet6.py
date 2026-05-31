"""
使用 AI 生成六级阅读理解文章
支持选择不同的模型
"""

import sys
import json
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import reading
from openai import AsyncOpenAI


# 六级文章生成提示词（精心优化）
CET6_GENERATION_PROMPT = """You are an expert in creating CET-6 (College English Test Band 6) reading comprehension materials. Generate a high-quality article with questions that match the exact difficulty and style of real CET-6 exams.

ARTICLE REQUIREMENTS:
- Length: 400-500 words (strictly enforce this)
- Academic and formal tone
- Clear structure: Introduction → Body (evidence/research/analysis) → Conclusion
- Use CET-6 level vocabulary (avoid overly simple or overly complex words)
- Include complex sentence structures, subordinate clauses, and passive voice
- Present balanced perspectives or research findings
- Use transition words: however, moreover, furthermore, nevertheless, consequently
- Include specific examples, statistics, or expert opinions

TOPIC: {topic}

QUESTION REQUIREMENTS:
Generate exactly 5 multiple-choice questions following this pattern:

Question 1: Main idea / Author's purpose
- Test overall comprehension
- Options should paraphrase the main point

Question 2: Specific detail
- Ask about a specific fact or statement
- Require careful reading of a particular paragraph

Question 3: Inference / Implication
- Test ability to read between the lines
- Correct answer not explicitly stated but logically derived

Question 4: Vocabulary in context / Reference
- Test understanding of a word/phrase meaning
- Or ask what a pronoun/reference refers to

Question 5: Author's attitude / Suggestion
- Test understanding of tone or recommendation
- Options should be subtle differences

DISTRACTOR DESIGN (very important):
- Each wrong option should be plausible and related to the text
- Use paraphrasing and synonyms to create confusion
- Include options that are:
  * Partially correct but incomplete
  * True statements but don't answer the question
  * Opposite of the correct answer
  * Mix information from different parts of the text

OUTPUT FORMAT (JSON only, no markdown):
{{
  "title": "Engaging title that reflects the content",
  "content": "Full article text. Use \\n\\n to separate paragraphs. Ensure 400-500 words.",
  "difficulty": "advanced",
  "category": "{category}",
  "word_count": 450,
  "questions": [
    {{
      "question_text": "Complete question with proper grammar and punctuation",
      "options": [
        "Option A - plausible distractor",
        "Option B - correct answer",
        "Option C - plausible distractor",
        "Option D - plausible distractor"
      ],
      "correct_answer": "Option B - correct answer",
      "explanation": "Explain why this is correct and reference the specific part of the article. Mention why other options are wrong if helpful."
    }}
  ]
}}

IMPORTANT:
- Output ONLY valid JSON, no markdown code blocks
- Ensure all text is properly escaped for JSON
- Make questions challenging but fair
- Correct answer should be clearly supported by the text
- Aim for realistic CET-6 exam difficulty"""


# 主题和分类映射
TOPICS = {
    "education": [
        "online learning effectiveness",
        "student mental health",
        "education inequality",
        "standardized testing debate",
        "lifelong learning importance"
    ],
    "technology": [
        "artificial intelligence ethics",
        "privacy in digital age",
        "social media impact",
        "automation and employment",
        "cybersecurity challenges"
    ],
    "environment": [
        "climate change solutions",
        "renewable energy transition",
        "plastic pollution",
        "urban sustainability",
        "biodiversity conservation"
    ],
    "society": [
        "work-life balance",
        "income inequality",
        "aging population",
        "cultural diversity",
        "urbanization trends"
    ],
    "health": [
        "mental health awareness",
        "preventive healthcare",
        "nutrition and diet",
        "exercise benefits",
        "sleep importance"
    ],
    "economy": [
        "gig economy growth",
        "cryptocurrency debate",
        "consumer behavior changes",
        "global trade tensions",
        "sustainable business practices"
    ]
}


async def generate_article_with_ai(topic: str, category: str, model: str, api_config: dict):
    """
    使用 AI 生成文章

    Args:
        topic: 文章主题
        category: 文章分类
        model: 模型名称
        api_config: API 配置 {base_url, api_key}
    """

    print(f"\n{'='*60}")
    print(f"生成文章")
    print(f"{'='*60}")
    print(f"主题: {topic}")
    print(f"分类: {category}")
    print(f"模型: {model}")
    print(f"{'='*60}\n")

    # 创建 API 客户端
    client = AsyncOpenAI(
        base_url=api_config['base_url'],
        api_key=api_config['api_key']
    )

    # 生成提示词
    prompt = CET6_GENERATION_PROMPT.format(topic=topic, category=category)

    print("正在生成文章...")

    try:
        # 调用 API
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert CET-6 exam content creator."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )

        # 获取响应
        content = response.choices[0].message.content.strip()

        # 移除可能的 markdown 代码块标记
        if content.startswith("```json"):
            content = content[7:]
        if content.startswith("```"):
            content = content[3:]
        if content.endswith("```"):
            content = content[:-3]
        content = content.strip()

        # 解析 JSON
        article_data = json.loads(content)

        # 验证数据
        if not all(key in article_data for key in ['title', 'content', 'questions']):
            raise ValueError("生成的数据缺少必要字段")

        if len(article_data['questions']) != 5:
            raise ValueError(f"题目数量不正确: {len(article_data['questions'])}")

        print(f"\n✓ 文章生成成功: {article_data['title']}")
        print(f"  字数: {len(article_data['content'].split())} words")
        print(f"  题目数: {len(article_data['questions'])}")

        return article_data

    except json.JSONDecodeError as e:
        print(f"\n❌ JSON 解析失败: {e}")
        print(f"响应内容:\n{content[:500]}...")
        return None
    except Exception as e:
        print(f"\n❌ 生成失败: {e}")
        return None
    finally:
        await client.close()


def save_article_to_db(article_data: dict) -> bool:
    """保存文章到数据库"""

    try:
        reading_db = reading.get_reading_db()

        # 添加文章
        article_id = reading_db.add_article(
            title=article_data['title'],
            content=article_data['content'],
            difficulty='advanced',  # 六级统一为 advanced
            category=article_data.get('category', ''),
            source='AI Generated (CET-6)'
        )

        if article_id == 0:
            print("❌ 添加文章失败")
            return False

        print(f"✓ 文章已保存 (ID: {article_id})")

        # 添加题目
        for i, q in enumerate(article_data['questions'], 1):
            reading_db.add_question(
                article_id=article_id,
                question_text=q['question_text'],
                question_type='choice',
                options=q['options'],
                correct_answer=q['correct_answer'],
                explanation=q.get('explanation', ''),
                order_num=i
            )

        print(f"✓ 已添加 {len(article_data['questions'])} 道题目")
        return True

    except Exception as e:
        print(f"❌ 保存失败: {e}")
        return False


async def batch_generate(count: int, model: str, api_config: dict):
    """批量生成文章"""

    print(f"\n{'='*60}")
    print(f"批量生成 {count} 篇六级文章")
    print(f"{'='*60}\n")

    success_count = 0

    # 从所有主题中随机选择
    import random
    all_topics = []
    for category, topics in TOPICS.items():
        for topic in topics:
            all_topics.append((topic, category))

    random.shuffle(all_topics)
    selected = all_topics[:count]

    for i, (topic, category) in enumerate(selected, 1):
        print(f"\n[{i}/{count}] 生成文章...")

        article_data = await generate_article_with_ai(topic, category, model, api_config)

        if article_data:
            if save_article_to_db(article_data):
                success_count += 1

        # 避免请求过快
        if i < count:
            await asyncio.sleep(2)

    print(f"\n{'='*60}")
    print(f"✅ 完成！成功生成 {success_count}/{count} 篇文章")
    print(f"{'='*60}")


def interactive_mode():
    """交互式模式"""
    sys.stdout.reconfigure(encoding='utf-8')

    print("\n" + "="*60)
    print("六级文章 AI 生成工具")
    print("="*60)

    # 选择模型
    print("\n可用模型:")
    print("1. gpt-5.5 (richardsantoine7754)")
    print("2. deepseek-v4-pro")
    print("3. deepseek-v4-flash")
    print("4. 自定义")

    choice = input("\n选择模型 (1-4): ").strip()

    if choice == "1":
        model = "gpt-5.5"
        api_config = {
            "base_url": "https://vip-sg.freemodel.dev",
            "api_key": "fe_oa_3b39363a8064a728d7878081c883d67f31dcd62cd47ea73b"
        }
    elif choice == "2":
        model = "deepseek-v4-pro"
        api_config = {
            "base_url": "https://api.deepseek.com",
            "api_key": "sk-b30fff6c469641b68bf3dd71a2460ea2"
        }
    elif choice == "3":
        model = "deepseek-v4-flash"
        api_config = {
            "base_url": "https://api.deepseek.com",
            "api_key": "sk-b30fff6c469641b68bf3dd71a2460ea2"
        }
    else:
        model = input("输入模型名称: ").strip()
        api_config = {
            "base_url": input("输入 API 地址: ").strip(),
            "api_key": input("输入 API 密钥: ").strip()
        }

    # 选择生成数量
    print("\n生成数量:")
    print("1. 单篇")
    print("2. 批量 (5篇)")
    print("3. 批量 (10篇)")
    print("4. 自定义")

    count_choice = input("\n选择 (1-4): ").strip()

    if count_choice == "1":
        count = 1
    elif count_choice == "2":
        count = 5
    elif count_choice == "3":
        count = 10
    else:
        count = int(input("输入数量: ").strip())

    # 执行生成
    asyncio.run(batch_generate(count, model, api_config))


if __name__ == "__main__":
    interactive_mode()
