"""Phase 3 验证脚本 — NPC 对话 + RAG 测试

对应 PRD4 第三章：
1. 意图识别（规则前置 + LLM 兜底）
2. RAG 检索（chromadb 封装 + 阈值过滤）
3. NpcChatAgent 双层路由 + 引用校验
4. API 端点（/api/npc/chunks + /api/npc/chat）
"""

import asyncio
import sys
import traceback
from unittest.mock import patch

from agents.npc_intent import IntentCategory, classify_intent
from memory.vector_store import BookChunk, RetrievedChunk, VectorStore


# 示例书籍分块（模拟一本讲行为决策的书）
SAMPLE_CHUNKS = [
    BookChunk(
        chunk_index=0,
        text="系统一快思考自动运行，系统二慢思考才是理性分析。"
             "本书第一核心观点是两种系统共同决定判断。",
        chapter="第一章 快思考与慢思考",
    ),
    BookChunk(
        chunk_index=1,
        text="锚定效应让人先入为主，第一眼看到的价格会影响后续判断。",
        chapter="第二章 启发与偏差",
    ),
    BookChunk(
        chunk_index=2,
        text="损失厌恶：失去一百元的痛苦远大于得到一百元的快乐。",
        chapter="第三章 过度自信",
    ),
]


def make_fake_llm(classify_result: str = "BOOK"):
    """构造一个可复用 FakeLLM（替换 get_llm_client）

    - 意图分类请求（system 含“意图分类器”）→ 返回指定类别
    - 其他对话请求 → 返回带引用的固定回复
    """

    class FakeLLM:
        def __init__(self) -> None:
            self.classify_result = classify_result

        async def invoke_text(self, system_prompt: str, user_prompt: str) -> str:
            if "意图分类器" in system_prompt:
                return self.classify_result
            # 固定回复：引用第 0 块原文开头，保证引用校验通过
            return (
                "这是个好问题。就像书里说的："
                "「系统一快思考自动运行，系统二慢思考才是理性分析。」"
                "在做重大判断时，我们应当放慢节奏，启动系统二。"
            )

        async def invoke_structured(self, *a, **kw):  # 本轮未用到
            raise NotImplementedError

    return FakeLLM()


# ============================================================
# 1. 意图识别
# ============================================================


async def test_intent_rules():
    """规则前置拦截 OUT_OF_SCOPE / CHAT"""
    print("=== 1. 意图识别 ===")

    assert classify_intent("今天天气如何") == IntentCategory.OUT_OF_SCOPE
    assert classify_intent("帮我写代码") == IntentCategory.OUT_OF_SCOPE
    assert classify_intent("你好呀") == IntentCategory.CHAT
    assert classify_intent("嗨，在吗") == IntentCategory.CHAT
    print("  ✅ 规则拦截: OUT_OF_SCOPE（天气/写代码）+ CHAT（你好/嗨）")

    # LLM 兜底
    result = classify_intent("锚定效应是什么意思", llm_fallback=lambda m: "BOOK")
    assert result == IntentCategory.BOOK
    result = classify_intent("我最近总是犹豫不决", llm_fallback=lambda m: "REFLECTION")
    assert result == IntentCategory.REFLECTION
    print("  ✅ LLM 兜底: BOOK / REFLECTION")

    # 非法类别 → ValueError
    try:
        classify_intent("xxx", llm_fallback=lambda m: "UNKNOWN")
        assert False, "非法类别应抛 ValueError"
    except ValueError:
        print("  ✅ 非法类别 → ValueError")
    print()


# ============================================================
# 2. RAG 检索
# ============================================================


async def test_vector_store():
    """向量库写入 + 检索 + 阈值过滤"""
    print("=== 2. RAG 向量检索 ===")

    # 独立 collection，避免 chroma 进程内共享数据干扰
    store = VectorStore(collection_name="ut-vec")
    n = store.add_chunks("book-atomic", SAMPLE_CHUNKS)
    assert n == 3
    assert store.count() == 3
    print("  ✅ 写入 3 个分块, count=3")

    # 检索与 chunk-0 相关的查询
    hits = store.search("系统一和系统二怎么区分", book_id="book-atomic", top_k=3, min_score=0.0)
    assert len(hits) > 0
    assert hits[0].chunk_index == 0, "应优先命中 chunk-0"
    print(f"  ✅ 命中 {len(hits)} 条，Top-1 = chunk-{hits[0].chunk_index}, score={hits[0].score:.2f}")

    # 限定 book_id：另一本书查不到
    other_hits = store.search("系统一", book_id="book-other", min_score=0.0)
    assert other_hits == []
    print("  ✅ book_id 过滤生效（别的书查不到）")

    # 阈值过滤：高分阈值下无关查询为空
    strict = store.search(
        "今天天气真不错适合郊游", book_id="book-atomic", min_score=0.999,
    )
    assert strict == []
    print("  ✅ min_score 阈值过滤生效")

    # 空文本安全
    assert store.search("", book_id="book-atomic") == []
    print("  ✅ 空查询安全返回")
    print()


# ============================================================
# 3. 引用校验函数
# ============================================================


async def test_validate_response():
    """引用校验：命中任一句子片段 → True"""
    print("=== 3. 引用校验 validate_response ===")

    from agents.npc_chat import validate_response

    chunk = SAMPLE_CHUNKS[0]

    # 回复完整引用第一句
    ok_reply = "正如书中所说「系统一快思考自动运行，系统二慢思考才是理性分析」。"
    assert validate_response(ok_reply, [chunk]) is True
    print("  ✅ 命中完整句子 → True")

    # 回复引用第二句
    mid_reply = "这本书最重要的主张是：本书第一核心观点是两种系统共同决定判断。"
    assert validate_response(mid_reply, [chunk]) is True
    print("  ✅ 命中句子片段 → True")

    # 完全无关回复
    assert validate_response("今天天气真好", [chunk]) is False
    print("  ✅ 无关回复 → False")

    # 空参数
    assert validate_response("", [chunk]) is False
    assert validate_response("abc", []) is False
    print("  ✅ 空参数安全")
    print()


# ============================================================
# 4. NpcChatAgent
# ============================================================


async def test_npc_agent_book():
    """BOOK 意图：走 RAG → LLM → 引用校验通过"""
    print("=== 4. NpcChatAgent ===")

    from agents.base import AgentResult
    from agents.npc_chat import NpcChatAgent

    store = VectorStore(collection_name="ut-agent")
    store.add_chunks("book-atomic", SAMPLE_CHUNKS)

    profile = {
        "name": "卡尼曼导师",
        "core_belief": "人类决策充满系统性偏差。",
        "tone": "温和、爱打比方",
        "persona_guide": "以《思考，快与慢》的立场回应",
    }

    fake = make_fake_llm(classify_result="BOOK")
    with patch("agents.base.get_llm_client", return_value=fake):
        agent = NpcChatAgent(npc=profile, vector_store=store)
        res = await agent.run({
            "message": "快思考和慢思考有什么区别",
            "book_id": "book-atomic",
            "min_score": 0.0,
        })

    assert isinstance(res, AgentResult)
    assert res.success, res.error
    data = res.result
    assert data["intent"] == "BOOK"
    assert len(data["citations"]) > 0
    assert data["has_reference"] is True
    print(f"  ✅ intent=BOOK, citations={len(data['citations'])}")
    print(f"  ✅ 引用校验通过 (has_reference=True)")
    print(f"  ✅ 回复: {data['reply'][:50]}…")
    print()


async def test_npc_agent_no_chunks():
    """BOOK 意图但库内无该书分块 → 礼貌提示"""
    print("=== 5. NPC 无检索结果 ===")

    from agents.npc_chat import NpcChatAgent

    store = VectorStore(collection_name="ut-empty")  # 独立空库
    fake = make_fake_llm(classify_result="BOOK")

    with patch("agents.base.get_llm_client", return_value=fake):
        agent = NpcChatAgent(npc={"name": "n", "core_belief": "x"}, vector_store=store)
        res = await agent.run({
            "message": "锚定效应是什么", "book_id": "book-atomic",
            "min_score": 0.0,
        })

    assert res.success
    assert res.result["citations"] == []
    assert "还没有这本书" in res.result["reply"]
    print(f"  ✅ 无结果礼貌提示: {res.result['reply'][:40]}…")
    print()


async def test_npc_agent_out_of_scope():
    """OUT_OF_SCOPE 意图：不检索，直接模板拒绝"""
    print("=== 6. NPC 越界拦截 ===")

    from agents.npc_chat import NpcChatAgent

    store = VectorStore(collection_name="ut-scope")
    store.add_chunks("book-atomic", SAMPLE_CHUNKS)
    fake = make_fake_llm(classify_result="OUT_OF_SCOPE")

    with patch("agents.base.get_llm_client", return_value=fake):
        agent = NpcChatAgent(npc={"name": "n", "core_belief": "x"}, vector_store=store)
        res = await agent.run({
            "message": "帮我写代码", "book_id": "book-atomic",
            "min_score": 0.0,
        })

    assert res.success
    assert res.result["intent"] == "OUT_OF_SCOPE"
    assert res.result["citations"] == []
    assert "超出了我的知识范围" in res.result["reply"]
    print("  ✅ 规则命中 OUT_OF_SCOPE，未触发检索与 LLM 生成")
    print()


# ============================================================
# 5. API 端点
# ============================================================


async def test_api_endpoints():
    """FastAPI: ingest + chat"""
    print("=== 7. API 端点 ===")

    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    # --- ingest ---
    resp = client.post("/api/npc/chunks", json={
        "book_id": "book-api",
        "chunks": [
            {"chunk_index": i, "text": c.text, "chapter": c.chapter}
            for i, c in enumerate(SAMPLE_CHUNKS)
        ],
    })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["ingested"] == 3
    print("  ✅ POST /api/npc/chunks → 200, ingested=3")

    # --- chat (BOOK, FakeLLM) ---
    fake = make_fake_llm(classify_result="BOOK")
    with patch("agents.base.get_llm_client", return_value=fake):
        resp = client.post("/api/npc/chat", json={
            "message": "什么是锚定效应",
            "book_id": "book-api",
            "npc_name": "默认导师",
            "min_score": 0.0,
        })
    assert resp.status_code == 200
    body = resp.json()
    assert body["code"] == 0
    assert body["data"]["intent"] == "BOOK"
    assert body["data"]["has_reference"] is True
    print("  ✅ POST /api/npc/chat → 200, intent=BOOK, 引用校验通过")

    # --- chat 参数校验 (空 message → 422) ---
    resp = client.post("/api/npc/chat", json={
        "message": "", "book_id": "book-api",
    })
    assert resp.status_code == 422
    print("  ✅ 空 message → 422 校验拦截")
    print()


# ============================================================


async def main():
    try:
        await test_intent_rules()
        await test_vector_store()
        await test_validate_response()
        await test_npc_agent_book()
        await test_npc_agent_no_chunks()
        await test_npc_agent_out_of_scope()
        await test_api_endpoints()

        print("=" * 50)
        print("🎉 Phase 3 所有测试通过！")
        print("   意图识别 + RAG 检索 + 引用校验 + API 全链路")
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
