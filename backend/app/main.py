"""BookPlay Agent 系统 — FastAPI 入口

提供 HTTP API，对外暴露：
- GET /api/agents       - 查看已注册的 Agent 列表
- POST /api/generate   - 为书籍生成游戏内容骨架（调用 Orchestrator）
"""

from typing import Any, Dict

from fastapi import FastAPI, HTTPException

from agents.registry import Registry
from core.orchestrator import Orchestrator, OrchestratorError

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


@app.get("/api/health")
async def health_check() -> Dict[str, Any]:
    """健康检查"""
    return {
        "status": "ok",
        "agents_count": len(_registry.list_agents()),
        "available_agents": [a["name"] for a in _registry.list_agents()],
    }


@app.get("/api/agents")
async def list_agents() -> Dict[str, Any]:
    """列出所有已注册的 Agent"""
    agents = _registry.list_agents()
    return {"count": len(agents), "agents": agents}


@app.post("/api/generate")
async def generate_game_content(body: Dict[str, Any]) -> Dict[str, Any]:
    """为指定书籍生成游戏内容骨架

    请求体：
        book_text (str): 书籍全文或摘要（建议至少 100 字）

    返回：
        { code, message, data: {...}, timestamp }
    """
    book_text = body.get("book_text", "")
    
    if not book_text or len(book_text.strip()) < 100:
        raise HTTPException(
            status_code=400,
            detail="book_text is required and must be at least 100 characters",
        )

    try:
        result = await _orchestrator.run({"book_text": book_text})
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "success": result["success"],
                "stages": result["stages"],
                "final_result": result["final_result"],
            },
            "metadata": {
                "execution_log": _orchestrator.log,
                "total_time_seconds": result["total_time_seconds"],
            },
            "timestamp": 0,
        }

    except OrchestratorError as e:
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {e}")
