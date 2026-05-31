"""
添加六级真题到数据库
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import reading


def add_cet6_article():
    """添加六级真题文章"""
    sys.stdout.reconfigure(encoding='utf-8')

    reading_db = reading.get_reading_db()

    # 文章内容
    article_content = """Nationally, one in six children miss 15 or more days of school in a year. Education officials have deplored all this missed instruction.

These chronically absent students suffer academically because of all the classroom instruction they miss out on. In 2015, the U.S. secretary of education responded to this crisis urging communities to support every student to attend every day and be successful in school. His open letter stated that missing 10% of school days in a year for any reason — excused or unexcused — is a primary cause of low academic achievement.

Worrying about whether children attend school makes sense. After all, if students don't show up, teachers can't teach them.

But what if America's attendance crisis is about much more than students missing class? What if instead, it is a reflection of family and community crises these students face — such as being ejected from the family apartment, fearing for their safety in their neighborhood or suffering an illness?

As social scientists we investigated how excused and unexcused absences relate to children's academic achievement.

We find that absences excused by a parent do little to harm children's learning. In fact, children with no unexcused absences — but 15 to 18 excused absences — have test scores equal to their peers who have no absences.

Meanwhile, the average child with even just one unexcused absence does much worse academically than peers with none.

We believe unexcused absence is a strong signal of the many challenges children and families face, including economic and medical hardships. Unexcused absences can be a powerful signal of how those out-of-school challenges affect children's academic progress.

Our evidence suggests unexcused absences are problematic, but for a different reason than people often think. Absence from school and especially unexcused absence, matters mainly as a signal of many crises children and their families may be facing. It matters less as a cause of lower student achievement due to missed instruction.

How we choose to think of school absences matters for educational policy. School attendance policies typically hold schools and families accountable for the days children miss, regardless of whether they were excused or unexcused absences.

These policies assume that missing school for any reason harms children academically because they are missing classroom instruction. They also assume that schools will be able to effectively intervene by reducing student absences. We find neither to be the case.

As a result, these attendance policies end up disproportionately punishing families dealing with out-of-school crises in their lives and pressuring schools who serve them to get students to school more often.

We instead suggest using unexcused absence from school as a signal to channel resources to the children and families who need them most."""

    # 添加文章
    article_id = reading_db.add_article(
        title="School Absences and Academic Achievement",
        content=article_content,
        difficulty="advanced",
        category="education",
        source="CET-6 Real Test"
    )

    if article_id == 0:
        print("❌ 添加文章失败")
        return

    print(f"✓ 添加文章: School Absences and Academic Achievement (ID: {article_id})")

    # 添加题目
    questions = [
        {
            "question_text": "What does the U.S. secretary of education say in his open letter?",
            "options": [
                "It is of vital importance to respond promptly to the school absence crisis.",
                "The academic performance of chronically absent students is deplorable.",
                "Low academic achievement is mainly attributed to school absences.",
                "The effect of school absences on American education is worrisome."
            ],
            "correct_answer": "Low academic achievement is mainly attributed to school absences.",
            "explanation": "The letter stated that missing 10% of school days is a primary cause of low academic achievement."
        },
        {
            "question_text": "What do the authors find about school absences?",
            "options": [
                "Excused school absences have little impact on children's learning.",
                "There is little difference between unexcused and excused absences.",
                "Excused absences lead to comparatively better school performance.",
                "Unexcused absences are a big challenge to both schools and families."
            ],
            "correct_answer": "Excused school absences have little impact on children's learning.",
            "explanation": "The authors find that absences excused by a parent do little to harm children's learning."
        },
        {
            "question_text": "What do the authors believe concerning unexcused school absences?",
            "options": [
                "They are likely to cause a decrease in students' academic achievements due to missed instruction.",
                "They point directly to many of the out-of-school challenges confronting children and their families.",
                "They are matters the American government typically ignores when formulating educational policies.",
                "They give a clear signal to children and their families of the crises they are likely to face in the future."
            ],
            "correct_answer": "They point directly to many of the out-of-school challenges confronting children and their families.",
            "explanation": "The authors believe unexcused absence is a strong signal of the many challenges children and families face."
        },
        {
            "question_text": "What is the assumption underlying education policies in the U.S.?",
            "options": [
                "Children's academic performance depends on reducing the number of absences.",
                "Schools can boost children's academic performance by effective intervention.",
                "Schools as well as families should be held responsible for out-of-school crises.",
                "Children's academic performance is closely related to the quality of instruction."
            ],
            "correct_answer": "Children's academic performance depends on reducing the number of absences.",
            "explanation": "The policies assume that missing school for any reason harms children academically and that schools can effectively intervene by reducing absences."
        },
        {
            "question_text": "What do the authors suggest doing regarding school absences?",
            "options": [
                "Identifying their underlying causes.",
                "Reframing school attendance policies.",
                "Directing resources to helping needy children.",
                "Pressuring schools to reduce unexcused ones."
            ],
            "correct_answer": "Directing resources to helping needy children.",
            "explanation": "The authors suggest using unexcused absence as a signal to channel resources to the children and families who need them most."
        }
    ]

    for i, q in enumerate(questions, 1):
        reading_db.add_question(
            article_id=article_id,
            question_text=q['question_text'],
            question_type='choice',
            options=q['options'],
            correct_answer=q['correct_answer'],
            explanation=q['explanation'],
            order_num=i
        )

    print(f"  添加了 {len(questions)} 道题目")
    print("\n✅ 六级真题添加完成！")


if __name__ == "__main__":
    add_cet6_article()
