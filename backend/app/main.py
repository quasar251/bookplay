"""BookPlay Agent 系统 — FastAPI 入口

提供 HTTP API，对外暴露：
- GET  /api/health     - 健康检查
- GET  /api/agents     - 查看已注册的 Agent 列表
- POST /api/generate   - 提交生成任务（异步，立即返回 task_id）
- GET  /api/tasks      - 任务列表
- GET  /api/tasks/{id} - 任务详情/进度
"""

from fastapi import FastAPI

from api.tasks import router as tasks_router
from agents.registry import Registry
from core.executor import TaskExecutor
from core.orchestrator import Orchestrator
from core.task_manager import get_task_manager
from models.schemas import (
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
)

# 全局单例
_registry = Registry()
_orchestrator = Orchestrator(_registry)
_task_manager = get_task_manager()
_executor = TaskExecutor(_orchestrator, _task_manager)


app = FastAPI(
    title="BookPlay Agent System",
    description=(
        "沉浸式知识引擎的 Agent 编排系统。\n\n"
        "Phase 1：可插拔框架 + 顺序编排器 + 异步任务。\n"
        "未来演进：LangChain LCEL → LangGraph StateGraph。"
    ),
    version="0.2.0",
)

# 注册路由
app.include_router(tasks_router)


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """健康检查"""
    return HealthResponse(
        status="ok",
        agents_count=len(_registry.list_agents()),
        available_agents=[a["name"] for a in _registry.list_agents()],
    )


@app.get("/api/agents")
async def list_agents() -> dict:
    """列出所有已注册的 Agent"""
    agents = _registry.list_agents()
    return {"count": len(agents), "agents": agents}


@app.post("/api/generate", response_model=GenerateResponse)
async def generate_game_content(body: GenerateRequest) -> GenerateResponse:
    """提交书籍游戏内容生成任务（异步）

    立即返回 task_id，后台执行。通过 GET /api/tasks/{task_id} 查询进度。

    Args:
        body: 生成请求，包含 book_text（书籍文本）、可选的 book_title 和 book_type

    Returns:
        GenerateResponse: data 中包含 task_id
    """
    import time

    task_id = _executor.submit_generate(
        book_text=body.book_text,
        book_title=body.book_title or "",
        book_type=body.book_type,
    )

    return GenerateResponse(
        code=0,
        message="task_submitted",
        data={
            "task_id": task_id,
            "status": "pending",
        },
        metadata={
            "polling_url": f"/api/tasks/{task_id}",
        },
        timestamp=int(time.time()),
    )
