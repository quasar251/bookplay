"""NPC 档案相关 API 路由（Phase 4：NPC 殿堂页真实数据）

- GET /api/npcs                  NPC 档案列表（含关联书信息）
- GET /api/npcs/{npc_id}         单个 NPC 档案
- GET /api/npcs/{npc_id}/conversations  该 NPC 的历史对话种子

数据源为 backend/data/seed.json（npcConversations 存的是"聊过的历史
问答记忆"，NPC 对话页可用来做开场示例问题）。
"""

from fastapi import APIRouter, HTTPException

from core.services import get_catalog

router = APIRouter(prefix="/api/npcs", tags=["npcs"])

_catalog = get_catalog()


def _npc_payload(npc: dict) -> dict:
    """在 NPC 档案字段上附加关联书基本信息（便于卡片渲染）"""
    payload = dict(npc)
    books = []
    for title in npc.get("booksAssociated") or []:
        book = _catalog.get_book_by_title(title)
        if book:
            books.append({
                "id": book.get("id"),
                "title": book.get("title"),
                "cover": book.get("cover"),
                "coverColor": book.get("coverColor"),
            })
    payload["associatedBooks"] = books
    payload["conversationCount"] = len(_catalog.get_npc_conversations(npc["id"]))
    return payload


@router.get("")
async def list_npcs() -> dict:
    """NPC 档案列表"""
    items = [_npc_payload(n) for n in _catalog.get_npcs()]
    return {"total": len(items), "items": items}


@router.get("/{npc_id}")
async def get_npc(npc_id: str) -> dict:
    """单个 NPC 档案

    Raises:
        404: NPC 不存在
    """
    npc = _catalog.get_npc(npc_id)
    if not npc:
        raise HTTPException(status_code=404, detail=f"NPC {npc_id} not found")
    return {"npc": _npc_payload(npc)}


@router.get("/{npc_id}/conversations")
async def get_npc_conversations(npc_id: str) -> dict:
    """该 NPC 的历史对话种子（Q&A 记忆，可作为示例问题）

    Raises:
        404: NPC 不存在
    """
    if not _catalog.get_npc(npc_id):
        raise HTTPException(status_code=404, detail=f"NPC {npc_id} not found")
    items = _catalog.get_npc_conversations(npc_id)
    return {"total": len(items), "items": items}
