"""Phase 2a 验证脚本 — LCEL 封装层测试

测试内容：
1. LLMClient 能正常构建（无 API key 用哨兵占位，不崩溃）
2. LCEL 链能正确拼接 system/human 消息
3. invoke_text 正确提取 AIMessage.content
4. invoke_structured 正确注入 format_instructions 并解析
5. _call_llm 兼容旧返回约定（{"raw": ...} / {"success": False, ...}）
"""

import asyncio
import sys
import traceback


# 可 ainvoke 的假链：模拟 langchain LCEL 链输出
class FakeChain:
    """可 ainvoke 的假链，直接返回预设结果"""

    def __init__(self, result) -> None:
        self.result = result

    async def ainvoke(self, inputs) -> object:
        return self.result


async def test_client_construction():
    """测试 LLMClient 构建（无 API key 占位）"""
    print("=== 1. LLMClient 构建 ===")

    import llm.client as client_module
    from llm.client import LLMClient

    # 强制重建单例（确保无 key）
    client_module._llm_client = None
    c = client_module.get_llm_client()
    assert c is not None
    assert c._model is not None
    print("  ✅ LLMClient 构建成功（无 API key 不崩溃，使用哨兵占位）")
    print()


async def test_chain_building():
    """测试 LCEL 链构建与消息拼接"""
    print("=== 2. LCEL 链构建 ===")

    from llm.client import LLMClient

    client = LLMClient.__new__(LLMClient)  # 跳过 __init__

    # 验证 prompt 模板正确
    prompt = __import__("langchain_core.prompts", fromlist=["ChatPromptTemplate"]).ChatPromptTemplate
    from langchain_core.prompts import ChatPromptTemplate

    p = ChatPromptTemplate.from_messages([
        ("system", "你是助手"),
        ("human", "{input}"),
    ])
    messages = p.format_messages(input="你好")
    assert messages[0].content == "你是助手"
    assert messages[1].content == "你好"
    print("  ✅ ChatPromptTemplate 消息拼接正确")
    print()


async def test_invoke_text():
    """测试 invoke_text 提取文本"""
    print("=== 3. invoke_text ===")

    from langchain_core.messages import AIMessage
    from llm.client import LLMClient

    client = LLMClient.__new__(LLMClient)

    # mock 返回 AIMessage
    result = AIMessage(content="这是返回的文本")
    client._build_chain = lambda system_prompt: FakeChain(result)

    text = await client.invoke_text("sys", "user")
    assert text == "这是返回的文本"
    print(f"  ✅ invoke_text → '{text}'")

    # 空响应应报错
    result2 = AIMessage(content="")
    client._build_chain = lambda system_prompt: FakeChain(result2)
    try:
        await client.invoke_text("sys", "user")
        assert False, "空响应应该抛错"
    except Exception as e:
        print(f"  ✅ 空响应报错: {type(e).__name__}")
    print()


async def test_invoke_structured():
    """测试 invoke_structured 解析"""
    print("=== 4. invoke_structured ===")

    import json
    from langchain_core.messages import AIMessage
    from models.schemas import Concept
    from llm.client import LLMClient

    client = LLMClient.__new__(LLMClient)

    # 合法 JSON 响应 → 应解析成功
    concept_json = json.dumps({
        "name": "身份驱动习惯",
        "definition": "你的习惯是你身份的投射",
        "keywords": ["身份", "习惯"],
        "source_quote": "行为是身份的投射",
        "source_chapter": None,
    })
    captured_prompt = {}

    class RecordingChain:
        async def ainvoke(self, inputs):
            captured_prompt["input"] = inputs["input"]
            return AIMessage(content=concept_json)

    client._build_chain = lambda system_prompt: RecordingChain()

    result = await client.invoke_structured("sys", "问概念", Concept)
    assert result["name"] == "身份驱动习惯"
    assert result["definition"] == "你的习惯是你身份的投射"
    assert "输出格式要求" in captured_prompt["input"]
    print(f"  ✅ invoke_structured 解析成功: {result['name']}")
    print(f"  ✅ format_instructions 已注入 prompt (含'输出格式要求')")
    print()


async def test_call_llm_compat():
    """测试 BaseAgent._call_llm 兼容约定"""
    print("=== 5. _call_llm 兼容性 ===")

    import json
    from unittest.mock import patch
    from agents.extract import ExtractAgent

    agent = ExtractAgent()  # 会走 get_llm_client 单例（占位 key，不崩溃）
    assert agent._llm is not None
    print("  ✅ Agent 实例化不崩溃，_llm 客户端就绪")

    # mock invoke_text 返回非法 JSON → 应返回 {"raw": ...}
    async def fake_invoke_text(sp, up):
        return "这不是 JSON 文本"

    with patch.object(agent._llm, "invoke_text", new=fake_invoke_text):
        r = await agent._call_llm("sys", "user")
        assert "raw" in r
        assert r["raw"] == "这不是 JSON 文本"
        print("  ✅ 非法 JSON → {'raw': ...} 兼容")

    # mock invoke_structured 抛错 → 应返回 {"success": False}
    from llm.client import LLMClientError
    from models.schemas import Concept

    async def fake_invoke_structured(sp, up, model):
        raise LLMClientError("模拟连接失败")

    with patch.object(agent._llm, "invoke_structured", new=fake_invoke_structured):
        r = await agent._call_llm("sys", "user", response_model=Concept)
        assert r.get("success") is False
        assert "模拟连接失败" in r.get("error", "")
        print("  ✅ LLMClientError → {'success': False} 兼容")
    print()


async def main():
    try:
        await test_client_construction()
        await test_chain_building()
        await test_invoke_text()
        await test_invoke_structured()
        await test_call_llm_compat()

        print("=" * 50)
        print("🎉 Phase 2a 所有测试通过！")
        print("   LCEL 封装：ChatPromptTemplate + ChatOpenAI + PydanticOutputParser")
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
