"""Phase 1c 验证脚本 — 异步任务系统测试

测试内容：
1. TaskManager 基本 CRUD + 状态机
2. /api/tasks 路由
3. 端到端：POST /api/generate → 轮询 → 获取结果
"""

import asyncio
import sys
import time
import traceback
from unittest.mock import patch

from tests.test_phase1b import MOCK_SKELETON, MOCK_SCENE, MOCK_NARRATION


def test_task_manager_basic():
    """测试 TaskManager 基本操作"""
    print("=== 1. TaskManager 基本操作 ===")

    from core.task_manager import TaskManager

    mgr = TaskManager()

    # 创建任务
    task = mgr.create_task(
        task_type="generate",
        input_data={"book_text": "test"},
        agent_names=["extract", "scene", "narrator"],
    )

    assert task.task_id
    assert task.status == "pending"
    assert task.progress == 0
    assert len(task.stages) == 3
    assert task.stages[0].agent == "extract"
    assert task.stages[0].status == "pending"
    print(f"  ✅ 创建任务: id={task.task_id[:8]}..., stages={len(task.stages)}")

    # 获取任务
    got = mgr.get_task(task.task_id)
    assert got is not None
    assert got.task_id == task.task_id
    print("  ✅ get_task 正常")

    # 任务列表
    task2 = mgr.create_task("generate", {"x": 1})
    tasks = mgr.list_tasks()
    assert len(tasks) == 2
    assert tasks[0].task_id == task2.task_id  # 倒序，最新的在前
    print(f"  ✅ list_tasks 正常，共 {len(tasks)} 个（倒序）")
    print()


def test_task_manager_state_machine():
    """测试任务状态流转"""
    print("=== 2. 任务状态机测试 ===")

    from core.task_manager import TaskManager

    mgr = TaskManager()
    task = mgr.create_task(
        "generate",
        {},
        agent_names=["extract", "scene", "narrator"],
    )

    # start
    mgr.start_task(task.task_id)
    t = mgr.get_task(task.task_id)
    assert t.status == "running"
    assert t.started_at is not None
    print(f"  ✅ start_task → status={t.status}")

    # 阶段1 运行中
    mgr.update_stage(task.task_id, "extract", "running", 50)
    t = mgr.get_task(task.task_id)
    assert t.stages[0].status == "running"
    assert t.stages[0].progress == 50
    # 3 个阶段，第一个跑了 50% → 总进度 ≈ 16.6%
    assert 10 <= t.progress <= 20
    print(f"  ✅ update_stage(running, 50) → progress={t.progress}%")

    # 阶段1 完成
    mgr.update_stage(task.task_id, "extract", "completed", 100)
    t = mgr.get_task(task.task_id)
    assert t.stages[0].status == "completed"
    assert t.progress >= 30  # 第一个阶段完成 = 33%
    print(f"  ✅ update_stage(completed) → progress={t.progress}%")

    # 阶段2 完成
    mgr.update_stage(task.task_id, "scene", "completed", 100)
    t = mgr.get_task(task.task_id)
    assert t.progress >= 60  # 两个阶段完成 = 66%
    print(f"  ✅ 两阶段完成 → progress={t.progress}%")

    # 全部完成
    mgr.complete_task(task.task_id, {"result": "ok"})
    t = mgr.get_task(task.task_id)
    assert t.status == "success"
    assert t.progress == 100
    assert t.result == {"result": "ok"}
    assert t.finished_at is not None
    assert t.total_time_seconds >= 0
    print(f"  ✅ complete_task → status={t.status}, progress=100%")
    print()


def test_task_manager_fail():
    """测试任务失败场景"""
    print("=== 3. 任务失败场景 ===")

    from core.task_manager import TaskManager

    mgr = TaskManager()
    task = mgr.create_task("generate", {}, agent_names=["extract", "scene"])

    mgr.start_task(task.task_id)
    mgr.update_stage(task.task_id, "extract", "failed", 0, "LLM 连接失败")
    mgr.fail_task(task.task_id, "LLM 连接失败")

    t = mgr.get_task(task.task_id)
    assert t.status == "failed"
    assert t.error == "LLM 连接失败"
    assert t.finished_at is not None
    assert t.stages[0].status == "failed"
    print(f"  ✅ fail_task → status={t.status}, error={t.error}")
    print()


def test_tasks_api():
    """测试 /api/tasks 路由"""
    print("=== 4. /api/tasks API 测试 ===")

    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)

    # 列表
    resp = client.get("/api/tasks")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "tasks" in data
    print(f"  ✅ GET /api/tasks → 200, total={data['total']}")

    # 404
    resp = client.get("/api/tasks/non-existent-id")
    assert resp.status_code == 404
    print(f"  ✅ GET /api/tasks/not-found → 404")
    print()


async def test_generate_async_executor():
    """测试异步生成（直接调 TaskExecutor + mock LLM）"""
    print("=== 5. 异步生成端到端测试（TaskExecutor） ===")

    from core.executor import TaskExecutor
    from core.orchestrator import Orchestrator
    from core.task_manager import TaskManager
    from agents.registry import Registry

    call_count = {"n": 0}

    async def mock_call_llm(self, system_prompt, user_prompt, response_model=None):
        call_count["n"] += 1
        if call_count["n"] == 1:
            return MOCK_SKELETON
        if call_count["n"] == 2:
            return MOCK_SCENE
        return MOCK_NARRATION

    with patch("agents.base.BaseAgent._call_llm", new=mock_call_llm):
        reg = Registry()
        orch = Orchestrator(reg)
        task_mgr = TaskManager()
        executor = TaskExecutor(orch, task_mgr)

        # 1. 提交任务
        long_text = "身份驱动习惯测试内容。" * 30
        task_id = executor.submit_generate(
            book_text=long_text,
            book_title="原子习惯",
            max_scenes=1,
        )
        assert task_id
        print(f"  ✅ 提交任务 → task_id={task_id[:8]}...")

        # 2. 立即查询
        task = task_mgr.get_task(task_id)
        assert task is not None
        assert task.status in ("pending", "running")
        print(f"  ✅ 立即查询 → status={task.status}")

        # 3. 等待完成（最多 3 秒）
        max_wait = 3.0
        waited = 0.0
        interval = 0.1
        final_status = None

        while waited < max_wait:
            await asyncio.sleep(interval)
            waited += interval
            task = task_mgr.get_task(task_id)
            final_status = task.status
            if final_status in ("success", "failed"):
                break

        print(f"  ✅ 等待 {waited:.1f}s 后 → status={final_status}")
        assert final_status == "success", f"任务未成功: {final_status}, error={task.error}"
        assert task.progress == 100

        # 4. 验证结果
        assert task.result is not None
        result = task.result
        assert "final_result" in result
        assert result["final_result"]["book_title"] == "原子习惯"
        assert len(result["final_result"]["all_cards"]) >= 1
        print(f"  ✅ 最终结果: book_title={result['final_result']['book_title']}")
        print(f"  ✅ 卡牌数: {len(result['final_result']['all_cards'])}")
        print(f"  ✅ 身份标签: {result['final_result'].get('identity_labels', [])}")

        # 5. 验证 3 个阶段都完成
        assert len(task.stages) == 3
        for stage in task.stages:
            assert stage.status == "completed"
            print(f"    - {stage.agent}: completed (progress={stage.progress}%)")

        print(f"  ✅ LLM 调用次数: {call_count['n']}")
        print(f"  ✅ 总耗时: {task.total_time_seconds}s")
    print()


async def main():
    try:
        test_task_manager_basic()
        test_task_manager_state_machine()
        test_task_manager_fail()
        test_tasks_api()
        await test_generate_async_executor()

        print("=" * 50)
        print("🎉 Phase 1c 所有测试通过！")
        print("   异步任务系统跑通：提交 → 后台执行 → 轮询 → 结果")
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
