"""测试 Orchestrator — 验证编排器是否正确执行 Agent"""

import asyncio
from agents import Registry
from core.orchestrator import Orchestrator


async def test_single_agent():
    """测试单 Agent 编排（ExtractAgent）"""
    reg = Registry()
    orch = Orchestrator(reg)

    # 1. 没有输入时应该失败
    result = await orch.run({"book_text": "ab"})
    print("=== Test: short input ===")
    print(f"Success: {result['success']}")
    assert not result["success"], "Short text should fail"
    assert len(result["stages"]) == 1
    print("PASS\n")

    # 2. 正常输入（虽然没 API Key，但能走到 _call_llm 报错）
    sample_book = (
        "这本书讲的是习惯的力量。詹姆斯·克利尔提出，"
        "行为是身份的投射。如果你想改变习惯，先改变身份。\n" * 50
    )
    result = await orch.run({"book_text": sample_book})
    print("=== Test: normal input ===")
    print(f"Success: {result['success']}")
    print(f"Stages: {len(result['stages'])}")
    print(f"Total time: {result['total_time_seconds']}s")
    assert len(result["stages"]) == 1
    assert result["stages"][0]["agent"] == "extract"
    print("PASS\n")

    # 3. 获取日志
    summary = orch.get_execution_summary()
    print("=== Test: execution log ===")
    print(f"Log entries: {summary['total_stages']}")
    print(f"First stage: {summary['stages'][0]}")
    print("PASS\n")

    print("\nAll orchestrator tests passed!")


if __name__ == "__main__":
    asyncio.run(test_single_agent())
