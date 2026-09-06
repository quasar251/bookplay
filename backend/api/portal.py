"""个人信息 / 认知图谱 / 群组讨论聚合 API（Phase 4 补充业务 API）

- GET /api/bootstrap            一次拉取全部档案（前端首屏初始化）
- GET /api/profile              用户资料页（user + userProfile + achievements + skillTree）
- GET /api/graph                认知星图（nodes + links + categories，ECharts 直接可用）
- GET /api/group-discussions    群组讨论列表（含参与 NPC 摘要，便于卡片渲染）

数据源为 backend/data/seed.json（与前端 mockData 对齐）。
"""

from fastapi import APIRouter, HTTPException

from core.services import get_catalog

router = APIRouter(prefix="/api", tags=["portal"])

_catalog = get_catalog()


@router.get("/bootstrap")
async def get_bootstrap() -> dict:
    """一次拉取全部档案数据（覆盖 /api/books、/api/npcs、/api/profile 等）"""
    return _catalog.bootstrap()


@router.get("/profile")
async def get_profile() -> dict:
    """用户资料页数据：user + userProfile + achievements + skillTree"""
    data = _catalog.bootstrap()
    return {
        "user": data.get("user"),
        "userProfile": data.get("userProfile"),
        "achievements": data.get("achievements"),
        "skillTree": data.get("skillTree"),
    }


@router.get("/graph")
async def get_knowledge_graph() -> dict:
    """认知星图（knowledgeGraph 原样返回，供 ECharts graph 使用）

    Raises:
        404: 种子未配置 knowledgeGraph
    """
    graph = _catalog.bootstrap().get("knowledgeGraph")
    if not graph:
        raise HTTPException(status_code=404, detail="knowledgeGraph not configured")
    return graph


@router.get("/group-discussions")
async def get_group_discussions() -> dict:
    """群组讨论列表，每个讨论附带参与 NPC 的名称/头像（供卡片渲染）"""
    data = _catalog.bootstrap()
    npcs = data.get("npcs", [])
    npc_map = {n["id"]: n for n in npcs}
    discussions = []
    for d in data.get("groupDiscussions", []):
        item = dict(d)
        participants = []
        for npc_id in d.get("npcIds") or []:
            npc = npc_map.get(npc_id)
            if npc:
                participants.append({
                    "id": npc["id"],
                    "name": npc["name"],
                    "avatarEmoji": npc.get("avatarEmoji", "🧙"),
                })
        item["participants"] = participants
        discussions.append(item)
    return {"total": len(discussions), "discussions": discussions}
