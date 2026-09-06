"""Phase 1b 验证脚本 — 测试 SceneAgent + NarratorAgent + 三阶段管道

用 mock LLM 响应模拟成功路径，验证整个管道流程。
"""

import asyncio
import json
import sys
import traceback
from unittest.mock import AsyncMock, patch


MOCK_SKELETON = {
    "core_theme": "身份驱动习惯养成",
    "chapters": [
        {
            "id": 1,
            "title": "身份驱动",
            "summary": "行为是身份的投射",
            "concepts": [
                {
                    "name": "身份驱动习惯",
                    "definition": "你的习惯是你身份的投射",
                    "keywords": ["身份", "习惯"],
                    "source_quote": "行为是身份的投射",
                }
            ],
        }
    ],
    "main_arguments": ["小习惯积累成大变化"],
    "total_concepts": 1,
}


MOCK_SCENE = {
    "concept_name": "身份驱动习惯",
    "chapter_id": 1,
    "learning": {
        "speaker": "詹姆斯·克利尔",
        "dialogue": "行为是身份的投射。如果你想跑步，先告诉自己'我是一个跑者'。",
        "key_idea": "先改身份，再改行为",
    },
    "scenario": {
        "title": "养成读书习惯",
        "description": "你想养成每天读书的习惯，但总是坚持不下来……",
        "options": [
            {
                "id": "A",
                "label": "身份驱动",
                "text": "告诉自己'我是读书人'，每天读1页",
                "cost": "可能觉得太简单",
                "consequence": "身份先建立，行为自然跟上",
                "correct": True,
                "explanation": "这就是身份驱动习惯",
                "tags": ["身份", "习惯"],
            },
            {
                "id": "B",
                "label": "目标驱动",
                "text": "定目标每天读30分钟",
                "cost": "可能三天打鱼两天晒网",
                "consequence": "靠意志力维持，容易中断",
                "correct": False,
                "explanation": "结果导向，容易放弃",
                "tags": [],
            },
            {
                "id": "C",
                "label": "环境驱动",
                "text": "把书放在枕头边",
                "cost": "被动提醒，缺乏内在动力",
                "consequence": "环境有用但不持久",
                "correct": False,
                "explanation": "环境设计是辅助而非核心",
                "tags": [],
            },
        ],
    },
    "reflection": {
        "prompt": "你生活中哪里可以用身份驱动来重新设计一个习惯？",
        "type": "text",
        "choices": [],
    },
    "card": {
        "id": "card_001",
        "icon": "🪞",
        "name": "身份驱动习惯",
        "definition": "你的习惯是你身份的投射",
        "example": "想跑步？先告诉自己'我是跑者'",
        "counter_example": "定减肥10斤是结果导向",
        "tags": ["身份", "习惯", "行为改变"],
        "source_concept": "身份驱动习惯",
    },
}


MOCK_NARRATION = {
    "book_title": "原子习惯",
    "book_type": "non_fiction",
    "core_theme": "身份驱动习惯养成",
    "narrative_hook": "你以为你在培养习惯，其实你在塑造自己是谁。",
    "chapters": [
        {
            "chapter_id": 1,
            "title": "身份驱动",
            "summary": "行为是身份的投射",
            "scenes": [MOCK_SCENE],
            "chapter_hook": "下一章，你会发现——你每天做的 1% 小事，正在悄悄改写你的人生。",
        }
    ],
    "all_cards": [MOCK_SCENE["card"]],
    "identity_labels": ["身份驱动者", "行动派", "长期主义者"],
    "estimated_playtime_minutes": 15,
    "difficulty_level": "beginner",
}


def test_imports():
    """测试新 Agent 能正确导入"""
    print("=== 1. 导入测试 ===")

    from agents.scene import SceneAgent
    from agents.narrator import NarratorAgent
    from agents.registry import Registry

    print("  ✅ SceneAgent 导入成功")
    print("  ✅ NarratorAgent 导入成功")

    reg = Registry()
    names = [a["name"] for a in reg.list_agents()]
    assert "extract" in names
    assert "scene" in names
    assert "narrator" in names
    print(f"  ✅ Registry 有 {len(names)} 个 Agent: {names}")
    print()


async def test_scene_agent_validation():
    """测试 SceneAgent 的输入校验（不调用 LLM）"""
    print("=== 2. SceneAgent 输入校验 ===")

    from agents.scene import SceneAgent

    agent = SceneAgent()

    # 空 chapters 应该失败
    result = await agent.run({"chapters": []})
    assert result.success is False
    assert "chapters is empty" in (result.error or "")
    print(f"  ✅ 空 chapters 失败: {result.error}")

    # 无概念应该失败
    result = await agent.run({"chapters": [{"id": 1, "title": "test", "concepts": []}]})
    assert result.success is False
    assert "No concepts" in (result.error or "")
    print(f"  ✅ 无概念失败: {result.error}")
    print()


async def test_narrator_agent_validation():
    """测试 NarratorAgent 的输入校验"""
    print("=== 3. NarratorAgent 输入校验 ===")

    from agents.narrator import NarratorAgent

    agent = NarratorAgent()

    # 空 scenes 应该失败
    result = await agent.run({"scenes": [], "core_theme": "test"})
    assert result.success is False
    assert "scenes is empty" in (result.error or "")
    print(f"  ✅ 空 scenes 失败: {result.error}")

    # 无 core_theme 应该失败
    result = await agent.run({"scenes": [{"concept_name": "x"}], "core_theme": ""})
    assert result.success is False
    assert "core_theme" in (result.error or "")
    print(f"  ✅ 无 core_theme 失败: {result.error}")
    print()


async def test_full_pipeline_with_mock():
    """用 mock LLM 跑通三阶段完整管道"""
    print("=== 4. 三阶段管道 mock 测试 ===")

    from agents.registry import Registry
    from core.orchestrator import Orchestrator

    call_count = {"n": 0}

    async def mock_call_llm(self, system_prompt, user_prompt, response_model=None):
        call_count["n"] += 1
        # 第 1 次调用：ExtractAgent → 返回骨架
        if call_count["n"] == 1:
            return MOCK_SKELETON
        # 第 2 次调用：SceneAgent 第一个概念 → 返回场景
        if call_count["n"] == 2:
            return MOCK_SCENE
        # 第 3 次调用：NarratorAgent → 返回完整游戏
        if call_count["n"] == 3:
            return MOCK_NARRATION
        return MOCK_SCENE

    with patch("agents.base.BaseAgent._call_llm", new=mock_call_llm):
        reg = Registry()
        orch = Orchestrator(reg)

        result = await orch.run({
            "book_text": "原子习惯测试内容" * 20,
            "book_title": "原子习惯",
            "max_scenes": 1,  # 只处理 1 个概念，减少 mock
        })

        print(f"  ✅ 管道执行成功: success={result.success}")
        print(f"  ✅ 阶段数: {len(result.stages)}")
        print(f"  ✅ 总耗时: {result.total_time_seconds}s")

        # 验证有 3 个阶段
        assert len(result.stages) == 3, f"预期 3 个阶段，实际 {len(result.stages)}"

        # 验证阶段顺序
        stage_names = [s.agent for s in result.stages]
        assert stage_names == ["extract", "scene", "narrator"], f"顺序错误: {stage_names}"
        print(f"  ✅ 执行顺序: {' → '.join(stage_names)}")

        # 验证每个阶段都成功
        for stage in result.stages:
            assert stage.status == "completed", f"{stage.agent} 状态: {stage.status}"
            assert stage.result is not None
            assert stage.result.success is True
            print(f"    - {stage.agent}: completed ({stage.duration_ms}ms)")

        # 验证最终结果有完整游戏结构
        final = result.final_result
        assert final is not None
        assert "book_title" in final
        assert "chapters" in final
        assert "all_cards" in final
        assert "identity_labels" in final
        print(f"  ✅ 最终结果: book_title={final['book_title']}, "
              f"cards={len(final['all_cards'])}, "
              f"labels={len(final['identity_labels'])}")

        print(f"  ✅ LLM 调用次数: {call_count['n']}")
    print()


async def main():
    try:
        test_imports()
        await test_scene_agent_validation()
        await test_narrator_agent_validation()
        await test_full_pipeline_with_mock()

        print("=" * 50)
        print("🎉 Phase 1b 所有测试通过！")
        print("   ExtractAgent → SceneAgent → NarratorAgent 三阶段管道跑通")
        print("=" * 50)
        return 0
    except AssertionError as e:
        print(f"\n❌ 断言失败: {e}")
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ 异常: {e}")
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
