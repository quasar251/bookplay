"""Phase 4 验证脚本 — 书库 / 档案 / 注册新书链路测试

对应 PRD4 Phase 4（真实 API + 注册新书生成 + 种子业务档案）：
1. Catalog 种子加载（books / npcs / conversations / chapters / quotes）
2. 纯函数：game JSON → 章节 / 摘录 / 语料行
3. 注册书状态机：register → update(completed + game) → 读取生成产物
4. 种子书 overlay：attach_seed_generated → game/chapters/quotes 统一查询
5. API 读接口冒烟（books / npcs / profile / graph / group-discussions / bootstrap）
6. API 注册新书（替换 executor.submit_generate_book，避免依赖真实 LLM）

说明：真实 LLM 端到端生成放在 S10 验收单独跑，本文件不发起网络调用。
"""

import asyncio
import copy
import sys
import traceback

from core.catalog import (
    Catalog,
    derive_chapters_from_game,
    derive_game_corpus_lines,
    derive_quotes_from_game,
)
from core.services import get_catalog
from models.schemas import BookGenerateRequest


# ============================================================
# 最小可用 game JSON（模拟 Narrator 输出）
# ============================================================

FAKE_GAME = {
    "book_title": "测试之书",
    "book_type": "non_fiction",
    "core_theme": "用测试驱动一切。",
    "all_cards": [
        {"name": "先写断言", "source_concept": "红绿循环"},
    ],
    "chapters": [
        {
            "chapter_id": 1,
            "title": "第一章 红绿循环",
            "summary": "先让测试失败，再让它通过。",
            "chapter_hook": "如果你敢，先写一个会失败的测试。",
            "scenes": [
                {
                    "concept_name": "红绿循环",
                    "learning": {
                        "speaker": "作者",
                        "dialogue": "先写一个失败的测试。",
                        "key_idea": "失败是迈向成功的第一个里程碑。",
                    },
                    "scenario": {
                        "title": "深夜改代码",
                        "description": "你面对一个没人敢动的模块。",
                    },
                    "card": {
                        "name": "先写断言",
                        "definition": "让代码先给出一个错误答案。",
                    },
                },
            ],
        },
    ],
}


# ============================================================
# 1. Catalog 种子加载
# ============================================================


async def test_catalog_seed():
    """种子档案加载正确"""
    print("=== 1. Catalog 种子加载 ===")
    c = Catalog()  # 独立实例（不污染 API 全局单例）
    books = c.list_books()
    assert len(books) == 8, f"expect 8 seed books, got {len(books)}"
    assert c.get_book("book1")["title"] == "思考，快与慢"
    assert c.get_book_by_title("影响力")["id"] == "book2"
    assert c.get_book("not-exist") is None
    print("  ✅ books=8, get_book / get_book_by_title / 404 行为正确")

    assert len(c.get_npcs()) == 3
    assert c.get_npc("npc1")["name"] == "卡尼曼的幽灵"
    assert len(c.get_npc_conversations("npc1")) == 3
    assert c.get_npc("bad") is None
    print("  ✅ npcs=3, npcConversations[npc1]=3")

    # 种子章节/quotes 在全局返回
    assert len(c.get_chapters("book4")) > 0
    assert len(c.get_quotes("book4")) > 0
    assert c.get_chapters("book1") == []  # book1 无种子章节
    print("  ✅ 种子 chapters/quotes 读取（book4 有，book1 无）")
    print()


# ============================================================
# 2. 纯函数
# ============================================================


async def test_derive_functions():
    """game JSON → 章节 / 摘录 / 语料行"""
    print("=== 2. derive 纯函数 ===")
    chapters = derive_chapters_from_game(FAKE_GAME)
    assert len(chapters) == 1
    ch = chapters[0]
    assert ch["title"].startswith("第一章")
    assert ch["concepts"] == ["红绿循环"]
    assert "scenes" in ch and len(ch["scenes"]) == 1
    print("  ✅ chapters: 标题/概念标签/scenes 保留")

    quotes = derive_quotes_from_game(FAKE_GAME)
    assert len(quotes) == 2  # key_idea + card.definition
    assert quotes[0]["chapter"] == 1
    print("  ✅ quotes: 从 key_idea + card.definition 提取")

    lines = derive_game_corpus_lines(FAKE_GAME)
    assert len(lines) == 4  # dialogue/key_idea/scenario/card
    assert any("红绿循环" in ln for ln in lines)
    assert any("测试之书" in ln for ln in lines)
    print("  ✅ corpus_lines: 4 行可检索语料（含书标题上下文）")
    print()


# ============================================================
# 3. 注册书状态机（catalog 直测）
# ============================================================


async def test_register_flow():
    """register → update(completed+game) → 读取生成产物"""
    print("=== 3. 注册书状态机 ===")
    c = Catalog()
    book_id = c.register_book(title="状态机之书", task_id="t1")
    assert c.is_registered(book_id)
    book = c.get_book(book_id)
    assert book["status"] == "in_progress"
    assert c.get_game(book_id) is None
    assert c.get_chapters(book_id) == []
    print(f"  ✅ 注册占位: {book_id} in_progress, 无 game")

    ok = c.update_book_status(
        book_id, "completed", game=FAKE_GAME,
    )
    assert ok
    book = c.get_book(book_id)
    assert book["status"] == "completed"
    assert book["totalChapters"] == 1
    assert book["conceptCount"] == 1
    assert c.get_game(book_id) == FAKE_GAME
    ch = c.get_chapters(book_id)
    assert len(ch) == 1 and ch[0]["title"].startswith("第一章")
    assert len(c.get_quotes(book_id)) == 2
    print("  ✅ 回写完成: status=completed, chapters/quotes 可读取")

    # 失败路径
    book_id2 = c.register_book(title="失败之书", task_id="t2")
    c.update_book_status(book_id2, "failed", message="LLM timeout")
    st = c.get_generated_state(book_id2)
    assert st["status"] == "failed"
    assert "timeout" in st["message"]
    print("  ✅ 失败标记: failed + message 回读")
    print()


# ============================================================
# 4. 种子书 overlay
# ============================================================


async def test_seed_overlay():
    """种子书"用本书内容生成"挂载后统一查询"""
    print("=== 4. 种子书 overlay ===")
    c = Catalog()
    assert c.get_game("book1") is None

    ok = c.attach_seed_generated(
        "book1", status="completed", game=copy.deepcopy(FAKE_GAME),
    )
    assert ok
    assert c.get_game("book1") is not None
    st = c.get_generated_state("book1")
    assert st["status"] == "completed"
    assert len(c.get_chapters("book1")) == 1
    assert len(c.get_quotes("book1")) == 2
    print("  ✅ 挂载后 get_game / get_chapters / get_quotes 读到生成产物")

    # 原始种子书状态字段不受影响（list 仍返回 seed 原样 status）
    book = c.get_book("book1")
    assert book["status"] == "completed"  # 原 seed status（阅读进度）
    assert "generation" not in book  # overlay 不写回 seed 字段
    print("  ✅ seed 原始字段保持，overlay 独立存储")
    print()


# ============================================================
# 5. API 读接口冒烟
# ============================================================


async def test_api_reads():
    """books / npcs / profile / graph / group-discussions / bootstrap"""
    print("=== 5. API 读接口 ===")
    from fastapi.testclient import TestClient

    from app.main import app

    client = TestClient(app)

    # books
    r = client.get("/api/books")
    assert r.status_code == 200, r.text
    items = r.json()["items"]
    assert len(items) == 8
    assert all("generation" in b for b in items)
    print("  ✅ GET /api/books → 200, items=8, 均带 generation")

    r = client.get("/api/books/book1")
    body = r.json()
    assert body["book"]["id"] == "book1"
    assert body["has_game"] is False
    print("  ✅ GET /api/books/book1 → 200, has_game=False")

    assert client.get("/api/books/nope").status_code == 404
    assert client.get("/api/books/nope/game").status_code == 404
    print("  ✅ 不存在书 → 404")

    # npcs
    r = client.get("/api/npcs")
    body = r.json()
    assert body["total"] == 3
    npc1 = next(n for n in body["items"] if n["id"] == "npc1")
    assert len(npc1["associatedBooks"]) == 1
    assert npc1["associatedBooks"][0]["title"] == "思考，快与慢"
    print("  ✅ GET /api/npcs → 200, 关联书信息附加")

    r = client.get("/api/npcs/npc1")
    assert r.json()["npc"]["name"] == "卡尼曼的幽灵"
    assert client.get("/api/npcs/nope").status_code == 404
    conv = client.get("/api/npcs/npc1/conversations").json()
    assert conv["total"] == 3
    print("  ✅ GET /api/npcs/{id} + conversations → 200")

    # profile
    r = client.get("/api/profile")
    body = r.json()
    assert set(body) == {"user", "userProfile", "achievements", "skillTree"}
    assert body["user"]["username"] == "知识探索者"
    assert len(body["achievements"]) == 8
    print("  ✅ GET /api/profile → user/userProfile/achievements/skillTree")

    # graph
    r = client.get("/api/graph")
    body = r.json()
    assert "nodes" in body and "links" in body and "categories" in body
    assert len(body["nodes"]) > 5
    print(f"  ✅ GET /api/graph → nodes={len(body['nodes'])}")

    # group discussions
    r = client.get("/api/group-discussions")
    body = r.json()
    assert body["total"] == 2
    assert all("participants" in d for d in body["discussions"])
    print("  ✅ GET /api/group-discussions → participants 已附加")

    # bootstrap
    r = client.get("/api/bootstrap")
    body = r.json()
    for key in (
        "books", "chapters", "quotes", "npcs", "npcConversations",
        "user", "achievements", "skillTree", "userProfile",
        "groupDiscussions", "knowledgeGraph",
    ):
        assert key in body, f"bootstrap missing {key}"
    print("  ✅ GET /api/bootstrap → 11 个档案键齐全")
    print()


# ============================================================
# 6. API 注册新书（mock executor，不调 LLM）
# ============================================================


async def test_api_register_book():
    """POST /api/books 注册占位 + mock executor"""
    print("=== 6. API 注册新书 ===")
    from fastapi.testclient import TestClient

    from api import books as books_api
    from app.main import app

    client = TestClient(app)
    catalog = get_catalog()

    def fake_submit(book_title, book_text, book_type, max_scenes):
        bid = catalog.register_book(title=book_title, task_id="t-fake-1")
        return bid, "t-fake-1"

    original = books_api._executor.submit_generate_book
    books_api._executor.submit_generate_book = fake_submit

    try:
        title = "运行时注册测试书（唯一标题）"
        long_text = (
            "这是一段超过一百字的中文书籍正文，专门用于测试注册新书接口能正确接收"
            "入参并启动生成任务流程。它讲述了如何在复杂系统中保持简单与清晰，强调"
            "任何优秀的设计都应该从真实问题出发，逐步迭代而不是一蹴而就，同时还要"
            "兼顾可维护性、可测试性与团队协作效率，让每个决策都有据可循。"
        )
        resp = client.post("/api/books", json=BookGenerateRequest(
            book_title=title,
            book_text=long_text,
            book_type="non_fiction",
            max_scenes=1,
        ).model_dump())
        assert resp.status_code == 200, resp.text
        data = resp.json()["data"]
        assert data["created"] is True
        assert data["book_id"].startswith("bk")
        assert data["task_id"] == "t-fake-1"
        assert data["polling_url"].startswith("/api/tasks/")
        print(f"  ✅ POST /api/books → book_id={data['book_id']}")

        # 列表可见 + 详情 in_progress + 重复标题走 generate_for_existing
        listing = client.get("/api/books").json()["items"]
        assert any(b["id"] == data["book_id"] for b in listing)
        detail = client.get(f"/api/books/{data['book_id']}").json()
        assert detail["book"]["status"] == "in_progress"
        assert detail["book"]["generation"]["status"] == "in_progress"
        assert detail["has_game"] is False
        print("  ✅ 列表可见 / 详情 in_progress / has_game=False")

        # 相同标题 → 不重复注册，返回 created=False（已有书走生成）
        long_text2 = (
            "同一本书名第二次提交时应当复用已有记录，而不是在书库中新增一条重复"
            "条目。这个判断发生在路由层：先按书名精确匹配现有书籍，如果命中就直接"
            "对原书记录发起内容生成任务，从而保证用户反复提交相同书名时不会污染"
            "书架列表，也不浪费占位与清理逻辑。"
        )
        resp2 = client.post("/api/books", json=BookGenerateRequest(
            book_title=title,
            book_text=long_text2,
            max_scenes=1,
        ).model_dump())
        data2 = resp2.json()["data"]
        assert data2["created"] is False
        assert data2["book_id"] == data["book_id"]
        print("  ✅ 同名书 → created=False, 复用原 book_id")
    finally:
        books_api._executor.submit_generate_book = original
        for b in catalog.list_books():
            if b.get("registered"):
                catalog.remove_book(b["id"])
    print()


# ============================================================


async def main():
    try:
        await test_catalog_seed()
        await test_derive_functions()
        await test_register_flow()
        await test_seed_overlay()
        await test_api_reads()
        await test_api_register_book()

        print("=" * 50)
        print("🎉 Phase 4 前端接入数据层测试全部通过！")
        print("   Catalog + derive + 注册回写 + overlay + API 全链路")
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
