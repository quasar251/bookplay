"""BookPlay Agent 系统 — FastAPI 入口

对外暴露：
- GET  /api/health            - 健康检查
- GET  /api/agents            - 已注册 Agent 列表
- POST /api/generate          - 提交生成任务（异步，立即返回 task_id）
- GET  /api/tasks[/{id}]      - 任务列表 / 详情（注册书生成进度轮询）
- POST /api/books             - 注册新书并启动生成（Phase 4）
- GET/POST /api/books[...]    - 书库查询 / 详情 / 对已有书生成 / 游戏 JSON
- GET  /api/npcs[...]         - NPC 档案 / 历史对话（Phase 4 NPC 殿堂）
- POST /api/npc/chunks|chat   - 书籍分块导入 / NPC 对话（意图 + RAG + 引用）
- GET  /api/profile|graph|group-discussions|bootstrap - 个人/图谱/群组/全量档案

启动时（lifespan）会把 data/seed.json 中的书籍语料导入向量库，
作为 NPC 对话的 RAG 数据源。
"""

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.books import router as books_router
from api.npc import router as npc_router
from api.npcs import router as npcs_router
from api.portal import router as portal_router
from api.tasks import router as tasks_router
from core.services import (
    get_executor,
    get_registry,
    ingest_seed_corpus,
)
from models.schemas import (
    GenerateRequest,
    GenerateResponse,
    HealthResponse,
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    """应用启动：把 seed 语料导入向量库（NPC 对话 RAG 数据源）

    进程内 ChromaDB 随进程重启即清空，因此每次启动导入不会重复累积。
    导入失败不阻塞服务启动（NPC 对话会自动降级为自由态 / 报错提示）。
    """
    try:
        counts = ingest_seed_corpus()
        logger.info("seed corpus ingested at startup: %s", counts)
    except Exception:
        logger.exception("seed corpus ingest failed (NPC RAG 数据源缺失)")
    yield


app = FastAPI(
    title="BookPlay Agent System",
    description=(
        "沉浸式知识引擎的 Agent 编排系统。\n\n"
        "Phase 1：可插拔框架 + 顺序编排器 + 异步任务。\n"
        "Phase 2：LangChain LCEL + LangGraph StateGraph。\n"
        "Phase 3：NPC 对话（意图识别 + RAG + 引用校验）。\n"
        "Phase 4：注册新书真实生成 + 种子业务档案 API + 前端全页面真实接入。"
    ),
    version="0.4.0",
    lifespan=lifespan,
)

# 业务 / 任务路由
app.include_router(tasks_router)
app.include_router(books_router)
app.include_router(npcs_router)
app.include_router(npc_router)
app.include_router(portal_router)

# 跨域（前端独立部署 / Vite 直连后端时使用；开发默认走 Vite 代理）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """健康检查"""
    registry = get_registry()
    return HealthResponse(
        status="ok",
        agents_count=len(registry.list_agents()),
        available_agents=[a["name"] for a in registry.list_agents()],
    )


@app.get("/api/agents")
async def list_agents() -> dict:
    """列出所有已注册的 Agent"""
    agents = get_registry().list_agents()
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

    task_id = get_executor().submit_generate(
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
