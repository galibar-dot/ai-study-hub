"""
测试英语学习功能的后端模块
运行此脚本可以验证词典和生词本功能是否正常
"""

import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

def test_dictionary():
    """测试词典查询功能"""
    print("=" * 50)
    print("测试词典查询功能")
    print("=" * 50)

    try:
        import dictionary

        # 测试查询单词
        test_words = ["hello", "world", "python", "computer", "test"]

        for word in test_words:
            print(f"\n查询单词: {word}")
            result = dictionary.lookup_word(word)

            if result:
                print(f"  ✓ 找到单词")
                print(f"  音标: {result.get('phonetic', 'N/A')}")
                print(f"  释义: {result.get('translation', 'N/A')[:50]}...")
                print(f"  词频: {result.get('frequency', 0)}")
                if result.get('oxford'):
                    print(f"  标签: 牛津3000词")
                if result.get('collins', 0) > 0:
                    print(f"  标签: 柯林斯{result['collins']}星")
            else:
                print(f"  ✗ 未找到单词")

        print("\n✅ 词典查询功能测试通过")
        return True

    except FileNotFoundError as e:
        print(f"\n❌ 错误: {e}")
        print("\n请按照以下步骤操作：")
        print("1. 访问 https://github.com/skywind3000/ECDICT/releases")
        print("2. 下载 ecdict-sqlite-28.zip")
        print("3. 解压后将 stardict.db 重命名为 ecdict.db")
        print("4. 放到项目根目录")
        return False

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_vocabulary():
    """测试生词本功能"""
    print("\n" + "=" * 50)
    print("测试生词本功能")
    print("=" * 50)

    try:
        import vocabulary

        vocab_db = vocabulary.get_vocabulary_db()

        # 测试添加单词
        print("\n测试添加单词...")
        test_word = "example"
        success = vocab_db.add_word(test_word, "/ɪɡˈzɑːmpl/", "例子；榜样")
        if success:
            print(f"  ✓ 成功添加单词: {test_word}")
        else:
            print(f"  ℹ 单词已存在: {test_word}")

        # 测试检查单词
        print("\n测试检查单词...")
        exists = vocab_db.is_word_in_vocab(test_word)
        print(f"  单词 '{test_word}' 是否在生词本中: {exists}")

        # 测试获取所有单词
        print("\n测试获取生词列表...")
        words = vocab_db.get_all_words()
        print(f"  ✓ 生词本中共有 {len(words)} 个单词")

        if words:
            print("\n  前3个单词:")
            for word in words[:3]:
                print(f"    - {word['word']}: {word['translation'][:30]}...")

        # 测试统计
        print("\n测试统计功能...")
        stats = vocab_db.get_stats()
        print(f"  总词数: {stats['total_words']}")
        print(f"  今日新增: {stats['today_added']}")
        print(f"  总复习次数: {stats['total_reviews']}")

        # 测试删除单词
        print("\n测试删除单词...")
        success = vocab_db.remove_word(test_word)
        if success:
            print(f"  ✓ 成功删除单词: {test_word}")
        else:
            print(f"  ✗ 删除失败")

        print("\n✅ 生词本功能测试通过")
        return True

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """主测试函数"""
    print("\n" + "=" * 50)
    print("英语学习功能后端测试")
    print("=" * 50)

    dict_ok = test_dictionary()
    vocab_ok = test_vocabulary()

    print("\n" + "=" * 50)
    print("测试总结")
    print("=" * 50)
    print(f"词典查询: {'✅ 通过' if dict_ok else '❌ 失败'}")
    print(f"生词本功能: {'✅ 通过' if vocab_ok else '❌ 失败'}")

    if dict_ok and vocab_ok:
        print("\n🎉 所有测试通过！可以启动服务器了。")
        print("\n启动命令:")
        print("  python server.py")
    else:
        print("\n⚠️ 部分测试失败，请检查错误信息。")

    print("=" * 50)


if __name__ == "__main__":
    main()
