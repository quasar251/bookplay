"""Phase 1a 验证脚本 — 测试 schemas + 更新后的 agent/orchestrator/main"""

import asyncio
import sys
import traceback


def test_imports():
    """测试所有模块能正确导入"""
    print("=== 1. 导入测试 ===")
    
    from models.schemas import (
        Concept, ChapterSkeleton, BookSkeleton,
        LearningStage, ScenarioOption, ScenarioStage,
        ReflectionStage, Card, GameScene,
        AgentMeta, AgentResult, ExecutionStage,
        OrchestratorResult, GenerateRequest, GenerateResponse, HealthResponse,
    )
    from agents.base import BaseAgent
    from agents.extract import ExtractAgent
    from agents.registry import Registry
    from core.orchestrator import Orchestrator, OrchestratorError
    from app.main import app
    
    print("  ✅ 所有模块导入成功")
    print(f"  ✅ Pydantic 模型: {len([Concept, ChapterSkeleton, BookSkeleton, LearningStage, ScenarioOption, ScenarioStage, ReflectionStage, Card, GameScene, AgentMeta, AgentResult, ExecutionStage, OrchestratorResult, GenerateRequest, GenerateResponse, HealthResponse])} 个")
    print(f"  ✅ FastAPI app 路由数: {len(app.routes)}")
    print()


def test_schemas():
    """测试 Pydantic 模型的创建与序列化"""
    print("=== 2. Schema 测试 ===")
    
    from models.schemas import (
        BookSkeleton, ChapterSkeleton, Concept,
        GameScene, LearningStage, ScenarioStage,
        ScenarioOption, ReflectionStage, Card,
        AgentResult, OrchestratorResult,
    )
    
    # 1. BookSkeleton
    skeleton = BookSkeleton(
        core_theme="身份驱动习惯",
        chapters=[
            ChapterSkeleton(
                id=1,
                title="身份驱动",
                summary="行为是身份的投射",
                concepts=[
                    Concept(
                        name="身份驱动习惯",
                        definition="你的习惯是你身份的投射",
                        keywords=["身份", "习惯"],
                        source_quote="行为是身份的投射",
                    )
                ],
            )
        ],
        main_arguments=["小习惯积累成大变化"],
    )
    d = skeleton.model_dump()
    assert "core_theme" in d
    assert "total_concepts" in d  # 字段存在（由 LLM 或 Agent 填充）
    print("  ✅ BookSkeleton 正常")
    
    # 2. GameScene (完整闭环)
    scene = GameScene(
        concept_name="身份驱动习惯",
        chapter_id=1,
        learning=LearningStage(
            speaker="詹姆斯·克利尔",
            dialogue="行为是身份的投射……",
            key_idea="先改身份，再改行为",
        ),
        scenario=ScenarioStage(
            title="养成读书习惯",
            description="你想养成每天读书的习惯……",
            options=[
                ScenarioOption(
                    id="A",
                    label="身份驱动",
                    text="告诉自己'我是读书人'，每天读1页",
                    cost="可能觉得太简单",
                    consequence="身份先建立，行为自然跟上",
                    correct=True,
                    explanation="这就是身份驱动习惯",
                    tags=["身份", "习惯"],
                ),
                ScenarioOption(
                    id="B",
                    label="目标驱动",
                    text="定目标每天读30分钟",
                    cost="可能三天打鱼两天晒网",
                    consequence="靠意志力维持，容易中断",
                    correct=False,
                ),
            ],
        ),
        reflection=ReflectionStage(
            prompt="你生活中哪里可以用身份驱动？",
            type="text",
        ),
        card=Card(
            icon="🪞",
            name="身份驱动习惯",
            definition="你的习惯是你身份的投射",
            example="想跑步？先告诉自己'我是跑者'",
            counter_example="定减肥10斤是结果导向",
            tags=["身份", "习惯", "行为改变"],
        ),
    )
    d = scene.model_dump()
    assert d["concept_name"] == "身份驱动习惯"
    assert len(d["scenario"]["options"]) == 2
    assert d["card"]["tags"] == ["身份", "习惯", "行为改变"]
    print("  ✅ GameScene 正常 (学→练→用→卡牌 完整闭环)")
    
    # 3. AgentResult
    result = AgentResult(success=True, result={"foo": "bar"})
    assert result.success is True
    assert result.result == {"foo": "bar"}
    assert result.error is None
    print("  ✅ AgentResult 正常")
    
    # 4. OrchestratorResult
    orch_result = OrchestratorResult(
        success=True,
        stages=[],
        final_result={"data": "ok"},
        total_time_seconds=1.23,
    )
    assert orch_result.success is True
    assert orch_result.total_time_seconds == 1.23
    print("  ✅ OrchestratorResult 正常")
    print()


def test_registry():
    """测试 Registry 仍然正常工作"""
    print("=== 3. Registry 测试 ===")
    
    from agents.registry import Registry
    
    reg = Registry()
    agents = reg.list_agents()
    assert len(agents) >= 1, "至少有一个内置 Agent"
    assert agents[0]["name"] == "extract"
    assert "description" in agents[0]
    assert "type" in agents[0]
    print(f"  ✅ 已注册 {len(agents)} 个 Agent: {[a['name'] for a in agents]}")
    print()


async def test_extract_agent_validation():
    """测试 ExtractAgent 的输入校验（不调用 LLM）"""
    print("=== 4. ExtractAgent 输入校验测试 ===")
    
    from agents.extract import ExtractAgent
    
    agent = ExtractAgent()
    
    # 短文本应该失败
    result = await agent.run({"book_text": "short"})
    assert result.success is False
    assert result.error is not None
    assert "too short" in result.error
    print(f"  ✅ 短文本失败: {result.error}")
    
    # 空文本也失败
    result2 = await agent.run({"book_text": ""})
    assert result2.success is False
    print(f"  ✅ 空文本失败: {result2.error}")
    print()


async def test_orchestrator():
    """测试 Orchestrator 基本执行（ExtractAgent 因无 API Key 会失败，验证流程）"""
    print("=== 5. Orchestrator 流程测试 ===")
    
    from agents.registry import Registry
    from core.orchestrator import Orchestrator
    
    reg = Registry()
    orch = Orchestrator(reg)
    
    # 用短文本快速走完流程（ExtractAgent 会因输入太短失败）
    result = await orch.run({"book_text": "测试短文本不够长" * 1})  # 不够 100 字
    
    # 因为输入太短，extract agent 会失败
    assert result.success is False
    assert len(result.stages) == 1
    assert result.stages[0].status == "failed"
    assert result.stages[0].result is not None
    assert result.stages[0].result.success is False
    assert len(result.execution_log) == 1
    assert result.total_time_seconds >= 0
    
    print(f"  ✅ Orchestrator 执行: stages={len(result.stages)}, success={result.success}")
    print(f"  ✅ 执行日志: {result.execution_log}")
    print(f"  ✅ 耗时: {result.total_time_seconds}s")
    print()


def test_fastapi_routes():
    """测试 FastAPI 路由存在且 schema 正确"""
    print("=== 6. FastAPI 路由测试 ===")
    
    from app.main import app
    from fastapi.testclient import TestClient
    
    client = TestClient(app)
    
    # health
    resp = client.get("/api/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert data["agents_count"] >= 1
    print(f"  ✅ GET /api/health → 200, agents={data['agents_count']}")
    
    # agents
    resp = client.get("/api/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert data["count"] >= 1
    print(f"  ✅ GET /api/agents → 200, count={data['count']}")
    
    # generate (短文本应返回 422 验证错误)
    resp = client.post("/api/generate", json={"book_text": "abc"})
    assert resp.status_code == 422  # Pydantic 校验失败
    print(f"  ✅ POST /api/generate (短文本) → 422 (Pydantic 校验)")
    
    # generate (正常文本，但无 API Key → 500)
    long_text = "测试内容" * 50
    resp = client.post("/api/generate", json={"book_text": long_text})
    # 可能因无 API Key 而失败，但应该有响应
    print(f"  ✅ POST /api/generate (长文本) → {resp.status_code}")
    print()


async def main():
    try:
        test_imports()
        test_schemas()
        test_registry()
        await test_extract_agent_validation()
        await test_orchestrator()
        test_fastapi_routes()
        
        print("=" * 50)
        print("🎉 所有测试通过！Phase 1a 完成。")
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
