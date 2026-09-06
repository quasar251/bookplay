"""BookPlay Agent 系统 — FastAPI 入口

提供 HTTP API，对外暴露：
- GET  /api/health     - 健康检查
- GET  /api/agents     - 查看已注册的 Agent 列表
- POST /api/generate   - 为书籍生成游戏内容骨架（调用 Orchestrator）
"""

from fastapi import FastAPI, HTTPException

from agents.registry import Registry
from core.orchestrator import Orchestrator, OrchestratorError
from models.schemas import (
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
)

# 全局单例：注册中心 + 编排器
_registry = Registry()
_orchestrator = Orchestrator(_registry)


app = FastAPI(
    title="BookPlay Agent System",
    description=(
        "沉浸式知识引擎的 Agent 编排系统。\n\n"
        "Phase 0：可插拔框架 + 顺序编排器。\n"
        "未来演进：LangChain LCEL → LangGraph StateGraph。"
    ),
    version="0.1.0",
)


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
    """为指定书籍生成游戏内容骨架

    Args:
        body: 生成请求，包含 book_text（书籍文本）、可选的 book_title 和 book_type

    Returns:
        GenerateResponse: 统一响应格式，data 中包含 stages 和 final_result
    """
    try:
        result = await _orchestrator.run({
            "book_text": body.book_text,
            "book_title": body.book_title or "",
            "book_type": body.book_type,
        })

        return GenerateResponse(
            code=0,
            message="success",
            data={
                "success": result.success,
                "stages": [s.model_dump() for s in result.stages],
                "final_result": result.final_result,
            },
            metadata={
                "execution_log": result.execution_log,
                "total_time_seconds": result.total_time_seconds,
            },
        )

    except OrchestratorError as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
