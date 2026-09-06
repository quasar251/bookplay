"""Phase 2b 验证脚本 — LangGraph StateGraph 测试

测试内容：
1. 图能正确编译（含 checkpointer）
2. 正常流：extract → scene → narrator 全链路成功
3. 条件路由：extract 无概念 → 直接 error（拦截 scene）
4. 条件路由：scene 产出为 0 → error（拦截 narrator）
5. 检查点：使用 MemorySaver，执行后能读取到 checkpoint 数据
"""

import asyncio
import sys
import traceback
from unittest.mock import patch

from tests.test_phase1b import MOCK_SKELETON, MOCK_NARRATION, MOCK_SCENE


async def test_graph_build():
    """测试图能编译"""
    print("=== 1. LangGraph 图构建 ===")

    from agents.registry import Registry
    from core.state_graph import GenerationGraph

    reg = Registry()  # 自动注册 extract/scene/narrator
    g = GenerationGraph(reg)
    assert g._graph is not None
    print("  ✅ GenerationGraph 编译成功（含 MemorySaver checkpointer）")

    # 节点齐备
    nodes = [n for n in g._graph.get_graph().nodes]
    for expected in ["extract", "scene", "narrator", "error_handler"]:
        assert expected in nodes, f"缺少节点 {expected}"
    print(f"  ✅ 节点齐备: {sorted(nodes)}")
    print()


async def test_success_path():
    """测试正常流 extract → scene → narrator"""
    print("=== 2. 正常流测试 ===")

    from agents.registry import Registry
    from core.state_graph import GenerationGraph

    call_count = {"n": 0}

    async def mock_call_llm(self, system_prompt, user_prompt, response_model=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return MOCK_SKELETON
        if call_count["n"] == 2:
            return MOCK_SCENE
        return MOCK_NARRATION

    with patch("agents.base.BaseAgent._call_llm", new=mock_call_llm):
        g = GenerationGraph(Registry())
        result = await g.arun({
            "book_text": "身份驱动习惯养成方法论。" * 40,
            "book_title": "原子习惯",
            "book_type": "non_fiction",
            "max_scenes": 3,
        })

    # 应成功产出 final_game
    assert "error" not in result or not result.get("error")
    assert result.get("final_game") is not None
    fg = result["final_game"]
    assert fg.get("book_title") == "原子习惯"
    assert fg.get("core_theme") == "身份驱动习惯养成"
    assert len(fg.get("all_cards", [])) >= 1
    assert len(fg.get("identity_labels", [])) >= 1
    print(f"  ✅ final_game 生成成功: {fg.get('book_title')}")
    print(f"  ✅ 身份标签: {fg.get('identity_labels')}")
    print(f"  ✅ LLM 调用: {call_count['n']} 次 (extract 1 + scene 1 + narrator 1)")
    print()


async def test_route_extract_no_concepts():
    """条件路由 1：extract 后无概念 → 直接 error"""
    print("=== 3. extract 无概念 → error 路由 ===")

    from agents.registry import Registry
    from core.state_graph import GenerationGraph

    empty_skeleton = {
        **MOCK_SKELETON,
        "chapters": [],  # 无章节 → 无概念
        "total_concepts": 0,
    }

    async def mock_call_llm(self, system_prompt, user_prompt, response_model=None):
        return empty_skeleton  # 无论调几次，extract 都返回空概念

    with patch("agents.base.BaseAgent._call_llm", new=mock_call_llm):
        g = GenerationGraph(Registry())
        result = await g.arun({
            "book_text": "这本书记录了足够长的内容，用于触发提取。" * 20,
            "book_title": "空概念书",
        })

    # 不应有 final_game
    assert "final_game" not in result or result.get("final_game") is None
    assert result.get("error"), "应当进入 error 节点"
    assert "extract" in result["error"] or "concept" in result["error"] or "error" in result
    print(f"  ✅ 已拦截: {result.get('error')}")
    print()


async def test_route_scene_empty():
    """条件路由 2：scene 后场景为 0 → error"""
    print("=== 4. scene 无场景 → error 路由 ===")

    from agents.registry import Registry
    from core.state_graph import GenerationGraph

    call_count = {"n": 0}

    async def mock_call_llm(self, system_prompt, user_prompt, response_model=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return MOCK_SKELETON  # extract 成功，有 1 个概念
        # scene 阶段返回空场景（非 JSON / 缺字段 → SceneAgent 处理）
        return {"raw": "no scenes generated"}  # 模拟 scene LLM 解析失败

    with patch("agents.base.BaseAgent._call_llm", new=mock_call_llm):
        g = GenerationGraph(Registry())
        result = await g.arun({
            "book_text": "这本书有足够长内容可提取。" * 20,
            "book_title": "无场景书",
        })

    # SceneAgent 对 {"raw":...} 会抛 ValueError → AgentResult.success=False
    # → scene 节点写入 error → 路由到 error
    assert "final_game" not in result or result.get("final_game") is None
    assert result.get("error"), "应当进入 error 节点"
    print(f"  ✅ 已拦截: {result.get('error')}")
    print()


async def test_checkpoint():
    """测试检查点：执行后可读 checkpoint"""
    print("=== 5. 检查点 (MemorySaver) ===")

    from agents.registry import Registry
    from core.state_graph import GenerationGraph

    call_count = {"n": 0}

    async def mock_call_llm(self, system_prompt, user_prompt, response_model=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return MOCK_SKELETON
        if call_count["n"] == 2:
            return MOCK_SCENE
        return MOCK_NARRATION

    with patch("agents.base.BaseAgent._call_llm", new=mock_call_llm):
        g = GenerationGraph(Registry())

        # 手动用固定 thread_id 执行一次，验证 checkpoint 持久化
        thread_id = "test-checkpoint-thread"
        initial = {
            "book_text": "身份驱动习惯养成方法论。" * 40,
            "book_title": "原子习惯",
            "max_scenes": 3,
        }
        config = {"configurable": {"thread_id": thread_id}}

        # 直接通过 graph 对象执行
        result = await g._graph.ainvoke(
            {
                "book_text": initial["book_text"],
                "book_title": initial["book_title"],
                "book_type": "non_fiction",
                "max_scenes": initial["max_scenes"],
            },
            config=config,
        )
        assert result.get("final_game") is not None

        # 读取 checkpoint 历史
        checkpoints = [
            c async for c in g._graph.aget_state_history(config)
        ]
        assert len(checkpoints) >= 1
        print(f"  ✅ checkpoint 历史: {len(checkpoints)} 条")
        latest = await g._graph.aget_state(config)
        assert latest is not None
        assert latest.values.get("final_game") is not None
        print(f"  ✅ 最新 checkpoint 包含 final_game")
        print()


async def main():
    try:
        await test_graph_build()
        await test_success_path()
        await test_route_extract_no_concepts()
        await test_route_scene_empty()
        await test_checkpoint()

        print("=" * 50)
        print("🎉 Phase 2b 所有测试通过！")
        print("   LangGraph StateGraph: 节点 + 条件路由 + 错误拦截 + 检查点")
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
