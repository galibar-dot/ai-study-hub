"""
初始化阅读专项示例数据
运行此脚本将添加 3 篇示例文章和对应的题目
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

import reading


def init_sample_data():
    """初始化示例数据"""
    import sys
    sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 50)
    print("初始化阅读专项示例数据")
    print("=" * 50)

    reading_db = reading.get_reading_db()

    # 检查是否已有数据
    existing = reading_db.get_articles()
    if existing:
        print(f"\n已存在 {len(existing)} 篇文章，跳过初始化")
        return

    # 示例文章 1: 初级 - AI 的未来
    article1_content = """Artificial Intelligence (AI) is changing our world. AI helps us in many ways. It can recognize faces in photos. It can translate languages. It can even drive cars!

Many companies use AI today. Google uses AI for search. Netflix uses AI to recommend movies. Hospitals use AI to help doctors find diseases.

But AI also brings challenges. Some people worry about jobs. Will robots take our jobs? Others worry about privacy. How much should AI know about us?

Scientists are working hard to make AI safe and helpful. They want AI to make our lives better, not worse. The future of AI is exciting, but we must be careful."""

    article1_id = reading_db.add_article(
        title="The Future of Artificial Intelligence",
        content=article1_content,
        difficulty="beginner",
        category="tech",
        source="Sample Article"
    )

    if article1_id:
        print(f"\n✓ 添加文章 1: The Future of Artificial Intelligence (ID: {article1_id})")

        # 添加题目
        questions1 = [
            {
                "question_text": "What is the main topic of this article?",
                "options": ["AI history", "AI applications and challenges", "AI programming", "AI costs"],
                "correct_answer": "AI applications and challenges",
                "explanation": "The article discusses how AI is used today and the challenges it brings."
            },
            {
                "question_text": "According to the article, which company uses AI for search?",
                "options": ["Netflix", "Google", "Hospital", "Tesla"],
                "correct_answer": "Google",
                "explanation": "The article states 'Google uses AI for search.'"
            },
            {
                "question_text": "What do some people worry about regarding AI?",
                "options": ["AI is too expensive", "AI will take jobs", "AI is too slow", "AI is too complicated"],
                "correct_answer": "AI will take jobs",
                "explanation": "The article mentions 'Some people worry about jobs. Will robots take our jobs?'"
            },
            {
                "question_text": "What are scientists trying to do with AI?",
                "options": ["Make it faster", "Make it cheaper", "Make it safe and helpful", "Make it smaller"],
                "correct_answer": "Make it safe and helpful",
                "explanation": "The article says 'Scientists are working hard to make AI safe and helpful.'"
            },
            {
                "question_text": "What does the article say about the future of AI?",
                "options": ["It is dangerous", "It is exciting but we must be careful", "It is impossible", "It is too expensive"],
                "correct_answer": "It is exciting but we must be careful",
                "explanation": "The last sentence states 'The future of AI is exciting, but we must be careful.'"
            }
        ]

        for i, q in enumerate(questions1, 1):
            reading_db.add_question(
                article_id=article1_id,
                question_text=q["question_text"],
                question_type="choice",
                options=q["options"],
                correct_answer=q["correct_answer"],
                explanation=q["explanation"],
                order_num=i
            )

        print(f"  添加了 {len(questions1)} 道题目")

    # 示例文章 2: 中级 - 气候变化
    article2_content = """Climate change is one of the most pressing issues facing humanity today. The Earth's average temperature has risen by approximately 1.1°C since the pre-industrial era, primarily due to human activities such as burning fossil fuels, deforestation, and industrial processes.

The consequences of climate change are already visible worldwide. Extreme weather events, including hurricanes, droughts, and floods, have become more frequent and severe. Arctic ice is melting at an alarming rate, threatening polar ecosystems and contributing to rising sea levels. Many species are struggling to adapt to rapidly changing environments, leading to biodiversity loss.

However, there is hope. Renewable energy technologies like solar and wind power are becoming more affordable and efficient. Many countries have committed to reducing their carbon emissions through international agreements like the Paris Climate Accord. Individuals can also make a difference by reducing energy consumption, using public transportation, and supporting sustainable businesses.

The fight against climate change requires global cooperation and immediate action. While the challenge is enormous, human innovation and determination can help us create a more sustainable future for generations to come."""

    article2_id = reading_db.add_article(
        title="Understanding Climate Change",
        content=article2_content,
        difficulty="intermediate",
        category="environment",
        source="Sample Article"
    )

    if article2_id:
        print(f"\n✓ 添加文章 2: Understanding Climate Change (ID: {article2_id})")

        questions2 = [
            {
                "question_text": "By how much has Earth's average temperature risen since the pre-industrial era?",
                "options": ["0.5°C", "1.1°C", "2.0°C", "3.5°C"],
                "correct_answer": "1.1°C",
                "explanation": "The article states 'The Earth's average temperature has risen by approximately 1.1°C since the pre-industrial era.'"
            },
            {
                "question_text": "What is NOT mentioned as a cause of climate change?",
                "options": ["Burning fossil fuels", "Deforestation", "Industrial processes", "Volcanic eruptions"],
                "correct_answer": "Volcanic eruptions",
                "explanation": "The article mentions burning fossil fuels, deforestation, and industrial processes, but not volcanic eruptions."
            },
            {
                "question_text": "What is happening to Arctic ice according to the article?",
                "options": ["It is growing", "It is melting at an alarming rate", "It is stable", "It is freezing faster"],
                "correct_answer": "It is melting at an alarming rate",
                "explanation": "The article explicitly states 'Arctic ice is melting at an alarming rate.'"
            },
            {
                "question_text": "Which renewable energy technologies are mentioned?",
                "options": ["Nuclear and hydro", "Solar and wind", "Geothermal and tidal", "Biomass and hydrogen"],
                "correct_answer": "Solar and wind",
                "explanation": "The article mentions 'Renewable energy technologies like solar and wind power.'"
            },
            {
                "question_text": "What does the article say is required to fight climate change?",
                "options": ["More money", "New technology only", "Global cooperation and immediate action", "Government control"],
                "correct_answer": "Global cooperation and immediate action",
                "explanation": "The article states 'The fight against climate change requires global cooperation and immediate action.'"
            },
            {
                "question_text": "What is the tone of the article's conclusion?",
                "options": ["Pessimistic", "Neutral", "Hopeful", "Angry"],
                "correct_answer": "Hopeful",
                "explanation": "The conclusion expresses hope, mentioning 'human innovation and determination can help us create a more sustainable future.'"
            }
        ]

        for i, q in enumerate(questions2, 1):
            reading_db.add_question(
                article_id=article2_id,
                question_text=q["question_text"],
                question_type="choice",
                options=q["options"],
                correct_answer=q["correct_answer"],
                explanation=q["explanation"],
                order_num=i
            )

        print(f"  添加了 {len(questions2)} 道题目")

    # 示例文章 3: 高级 - 量子计算
    article3_content = """Quantum computing represents a paradigm shift in computational technology, leveraging the principles of quantum mechanics to process information in fundamentally different ways from classical computers. Unlike traditional bits that exist in states of either 0 or 1, quantum bits (qubits) can exist in superposition, simultaneously representing multiple states until measured.

This quantum superposition, combined with entanglement—a phenomenon where qubits become correlated in ways that have no classical analogue—enables quantum computers to explore vast solution spaces exponentially faster than classical machines for certain types of problems. Applications range from cryptography and drug discovery to optimization problems and artificial intelligence.

However, quantum computing faces significant technical challenges. Qubits are extremely fragile and susceptible to decoherence, where environmental interference causes them to lose their quantum properties. Maintaining quantum states requires temperatures near absolute zero and sophisticated error correction algorithms. Current quantum computers, while demonstrating "quantum supremacy" in specific tasks, remain far from practical, large-scale applications.

Major technology companies and research institutions are investing billions in quantum computing research. IBM, Google, and Microsoft have developed quantum processors with increasing qubit counts, while startups are exploring novel approaches to quantum architecture. The race to build a fault-tolerant, universal quantum computer continues, with experts predicting that practical quantum computers may emerge within the next decade, potentially revolutionizing fields from materials science to financial modeling."""

    article3_id = reading_db.add_article(
        title="The Quantum Computing Revolution",
        content=article3_content,
        difficulty="advanced",
        category="tech",
        source="Sample Article"
    )

    if article3_id:
        print(f"\n✓ 添加文章 3: The Quantum Computing Revolution (ID: {article3_id})")

        questions3 = [
            {
                "question_text": "What is the key difference between qubits and classical bits?",
                "options": [
                    "Qubits are faster",
                    "Qubits can exist in superposition",
                    "Qubits are smaller",
                    "Qubits use less energy"
                ],
                "correct_answer": "Qubits can exist in superposition",
                "explanation": "The article explains that qubits 'can exist in superposition, simultaneously representing multiple states until measured.'"
            },
            {
                "question_text": "What is quantum entanglement?",
                "options": [
                    "A type of quantum computer",
                    "A programming language",
                    "A phenomenon where qubits become correlated",
                    "A cooling technique"
                ],
                "correct_answer": "A phenomenon where qubits become correlated",
                "explanation": "The article describes entanglement as 'a phenomenon where qubits become correlated in ways that have no classical analogue.'"
            },
            {
                "question_text": "What is decoherence?",
                "options": [
                    "A quantum algorithm",
                    "Loss of quantum properties due to environmental interference",
                    "A type of quantum gate",
                    "A measurement technique"
                ],
                "correct_answer": "Loss of quantum properties due to environmental interference",
                "explanation": "The article states 'decoherence, where environmental interference causes them to lose their quantum properties.'"
            },
            {
                "question_text": "What temperature is required to maintain quantum states?",
                "options": [
                    "Room temperature",
                    "Freezing point",
                    "Near absolute zero",
                    "Boiling point"
                ],
                "correct_answer": "Near absolute zero",
                "explanation": "The article mentions 'Maintaining quantum states requires temperatures near absolute zero.'"
            },
            {
                "question_text": "Which companies are mentioned as developing quantum processors?",
                "options": [
                    "Apple, Amazon, Facebook",
                    "IBM, Google, Microsoft",
                    "Intel, AMD, NVIDIA",
                    "Tesla, SpaceX, Neuralink"
                ],
                "correct_answer": "IBM, Google, Microsoft",
                "explanation": "The article specifically names 'IBM, Google, and Microsoft have developed quantum processors.'"
            },
            {
                "question_text": "When do experts predict practical quantum computers may emerge?",
                "options": [
                    "Within 5 years",
                    "Within the next decade",
                    "Within 50 years",
                    "Within a century"
                ],
                "correct_answer": "Within the next decade",
                "explanation": "The article states 'experts predicting that practical quantum computers may emerge within the next decade.'"
            },
            {
                "question_text": "What does 'quantum supremacy' refer to?",
                "options": [
                    "Quantum computers being better at all tasks",
                    "Demonstrating superiority in specific tasks",
                    "Having more qubits than classical bits",
                    "Being commercially available"
                ],
                "correct_answer": "Demonstrating superiority in specific tasks",
                "explanation": "The article mentions quantum computers 'demonstrating quantum supremacy in specific tasks,' implying superiority in particular applications."
            }
        ]

        for i, q in enumerate(questions3, 1):
            reading_db.add_question(
                article_id=article3_id,
                question_text=q["question_text"],
                question_type="choice",
                options=q["options"],
                correct_answer=q["correct_answer"],
                explanation=q["explanation"],
                order_num=i
            )

        print(f"  添加了 {len(questions3)} 道题目")

    print("\n" + "=" * 50)
    print("✅ 示例数据初始化完成！")
    print("=" * 50)
    print(f"\n共添加了 3 篇文章：")
    print("  1. The Future of Artificial Intelligence (初级, 5题)")
    print("  2. Understanding Climate Change (中级, 6题)")
    print("  3. The Quantum Computing Revolution (高级, 7题)")
    print("\n现在可以启动服务器并使用阅读专项功能了！")


if __name__ == "__main__":
    init_sample_data()
