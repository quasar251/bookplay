"""NPC 对话 + RAG + 档案 API 路由（对应 PRD4 第三章）

- POST /api/npc/chunks  导入书籍分块到向量库
- POST /api/npc/chat    与 NPC 对话（意图识别 + RAG + 引用校验）
- GET  /api/npcs        展示 NPC 档案列表（Phase 4 新增，供 NPC 殿堂页）
- GET  /api/npcs/{id}   展示单个 NPC 档案
- GET  /api/npcs/{id}/conversations  该 NPC 的历史对话种子

档案数据源为 backend/data/seed.json（与前端 mockData 对齐），
灵魂档案字段：name / core_beliefs / tone / personalityTags 等。
"""

import logging
import time
from typing import Dict

from fastapi import APIRouter, HTTPException

from agents.npc_chat import NpcChatAgent
from core.services import get_catalog, get_vector_store
from memory.vector_store import BookChunk
from models.schemas import (
    GenerateResponse,
    IngestChunksRequest,
    NpcChatRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/npc", tags=["npc"])

# 全局向量库单例（进程内共享，启动时已导入种子语料）
_vector_store = get_vector_store()

# 内置 NPC 灵魂档案（示例，生产可入库管理；无 npc_id 时的降级）
NPC_PROFILES: Dict[str, Dict[str, str]] = {
    "行为经济学导师": {
        "name": "卡尼曼导师",
        "core_belief": "人类决策充满系统性偏差，看见偏差是理性的起点。",
        "tone": "温和、爱用生活例子打比方，偶尔自嘲。",
        "persona_guide": "以《思考，快与慢》的立场回应：尊重直觉的价值，"
                         "但提醒玩家警惕快思考的陷阱。",
    },
    "习惯教练": {
        "name": "克利尔教练",
        "core_belief": "你无法'坚持'一个习惯，你只会成为那个身份的人。",
        "tone": "行动导向、鼓励式、善于把目标拆成 2 分钟小行动。",
        "persona_guide": "以《掌控习惯》的立场回应：先改变身份，再设计系统，"
                         "不靠意志力。",
    },
    "默认导师": {
        "name": "书境向导",
        "core_belief": "把书读进生活里，才算是真正读过。",
        "tone": "温和、好奇、引导式提问。",
        "persona_guide": "以中立立场帮助玩家连接书中概念与自己的生活，"
                         "不做价值评判。",
    },
}


# ============================================================
# NPC 档案（Phase 4：由 Catalog/seed 提供真实数据）
# ============================================================


def _resolve_npc_profile(npc_id: str = "", npc_name: str = "") -> Dict[str, Dict[str, str]]:
    """解析 NPC 灵魂档案（供 NpcChatAgent 使用的 4 个字段）

    优先级：
    1. npc_id → Catalog 中该 NPC 档案（真实种子数据）
    2. npc_name → 内置 NPC_PROFILES（旧接口兼容）
    3. 默认导师

    Args:
        npc_id: NPC id（如 npc1）
        npc_name: NPC 名称/内置档案名

    Returns:
        {name, core_belief, tone, persona_guide}
    """
    catalog = get_catalog()
    if npc_id:
        npc = catalog.get_npc(npc_id)
        if npc:
            core_beliefs = npc.get("coreBeliefs") or []
            tags = npc.get("personalityTags") or []
            return {
                "name": npc.get("name", npc_name or "书境向导"),
                "core_belief": "；".join(core_beliefs) or "陪伴读者把书读进生活。",
                "tone": npc.get("tone", "温和、好奇、引导式提问。"),
                "persona_guide": "来自《"
                                 + str((npc.get("booksAssociated") or ["这本书"])[0])
                                 + "》的化身，性格："
                                 + "、".join(tags)
                                 + "。以书中立场陪伴玩家思考，不做价值评判。",
            }
    return dict(NPC_PROFILES.get(npc_name, NPC_PROFILES["默认导师"]))


@router.post("/chunks", response_model=GenerateResponse)
async def ingest_chunks(body: IngestChunksRequest) -> GenerateResponse:
    """导入书籍分块到向量库（RAG 数据源）

    Args:
        body: book_id + 分块列表（text / chapter / chunk_index）

    Returns:
        code=0 + data.ingested=导入数量
    """
    chunks = [
        BookChunk(chunk_index=c.chunk_index, text=c.text, chapter=c.chapter)
        for c in body.chunks
    ]
    try:
        ingested = _vector_store.add_chunks(body.book_id, chunks)
    except Exception as e:
        logger.exception("ingest failed")
        raise HTTPException(status_code=500, detail=f"Ingest failed: {e}")

    return GenerateResponse(
        code=0,
        message="chunks_ingested",
        data={"book_id": body.book_id, "ingested": ingested},
        metadata={"collection_total": _vector_store.count()},
        timestamp=int(time.time()),
    )


@router.post("/chat", response_model=GenerateResponse)
async def npc_chat(body: NpcChatRequest) -> GenerateResponse:
    """与 NPC 对话

    流程：意图识别 →（BOOK/REFLECTION）RAG 检索 → 生成 → 引用校验；
    检索不到原文时若 allow_free_talk=True，NPC 以人设知识自由作答。

    Args:
        body: message / book_id / npc_id|npc_name / top_k / min_score / allow_free_talk

    Returns:
        data: { intent, reply, citations, has_reference, free_talk }

    Raises:
        404: 没有导入过该书分块
    """
    profile = _resolve_npc_profile(body.npc_id or "", body.npc_name)

    # 空库时友好提示（正常启动已导入种子语料，此处作为兜底）
    if _vector_store.count() == 0:
        raise HTTPException(
            status_code=404,
            detail="向量库为空，请先通过 POST /api/npc/chunks 导入书籍分块",
        )

    agent = NpcChatAgent(npc=profile, vector_store=_vector_store)
    result = await agent.run({
        "message": body.message,
        "book_id": body.book_id,
        "top_k": body.top_k,
        "min_score": body.min_score,
        "allow_free_talk": body.allow_free_talk,
    })

    if not result.success:
        logger.error("npc chat failed: %s", result.error)
        raise HTTPException(status_code=500, detail=result.error or "NPC chat failed")

    return GenerateResponse(
        code=0,
        message="npc_reply",
        data=result.result or {},
        metadata={
            "npc_id": body.npc_id,
            "npc_name": body.npc_name,
            "book_id": body.book_id,
        },
        timestamp=int(time.time()),
    )
