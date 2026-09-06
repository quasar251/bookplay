"""书库相关 API 路由（Phase 4：真实数据 + 注册新书生成链路）

- GET    /api/books            书库列表（种子书 + 运行注册书，含生成状态）
- GET    /api/books/{book_id}  单本详情（书档案 + 章节 + 摘录 + 生成状态）
- GET    /api/books/{book_id}/game      该书已生成的游戏 JSON（GameEngine 数据源）
- POST   /api/books            注册新书并启动生成（返回 book_id + task_id）
- POST   /api/books/{book_id}/generate  对已有书（含种子书）启动内容生成

数据源为 backend/data/seed.json（与前端 mockData 对齐），注册书由
TaskExecutor 在生成完成/失败后回写。
"""

import logging
import time

from fastapi import APIRouter, HTTPException

from core.services import get_catalog, get_executor
from models.schemas import BookGenerateRequest, GenerateResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/books", tags=["books"])

_catalog = get_catalog()
_executor = get_executor()


# ============================================================
# 视图组装（把 Catalog 原始记录 + 生成状态合并为前端友好对象）
# ============================================================


def _generation_info(book_id: str) -> dict:
    """生成状态元信息（供列表/详情展示生成进度）

    Returns:
        {
          kind: seed_generated | registered | none,
          status: 生成/任务状态（completed/failed/in_progress/none）,
          has_game: 是否已有可体验的游戏 JSON,
        }
    """
    state = _catalog.get_generated_state(book_id)
    if _catalog.is_registered(book_id):
        book = _catalog.get_book(book_id) or {}
        return {
            "kind": "registered",
            "status": book.get("status", "unknown"),
            "has_game": bool(_catalog.get_game(book_id)),
            "message": state.get("message", "") if state else "",
        }
    if state:
        return {
            "kind": "seed_generated",
            "status": state.get("status", "unknown"),
            "has_game": bool(_catalog.get_game(book_id)),
            "message": state.get("message", ""),
        }
    return {"kind": "none", "status": "none", "has_game": False, "message": ""}


def _book_payload(book: dict) -> dict:
    """在书档案字段上附加 generation 状态（不污染 Catalog 原始数据）"""
    book_id = book["id"]
    payload = dict(book)
    payload["generation"] = _generation_info(book_id)
    return payload


# ============================================================
# 查询接口
# ============================================================


@router.get("")
async def list_books() -> dict:
    """书库列表（种子书在前，注册书在后）"""
    books = [_book_payload(b) for b in _catalog.list_books()]
    return {"total": len(books), "items": books}


@router.get("/{book_id}")
async def get_book_detail(book_id: str) -> dict:
    """单本详情（书档案 + 章节 + 摘录 + 生成状态）

    Raises:
        404: 书不存在
    """
    book = _catalog.get_book(book_id)
    if not book:
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    return {
        "book": _book_payload(book),
        "chapters": _catalog.get_chapters(book_id),
        "quotes": _catalog.get_quotes(book_id),
        "has_game": bool(_catalog.get_game(book_id)),
    }


@router.get("/{book_id}/game")
async def get_book_game(book_id: str) -> dict:
    """获取该书已生成的游戏 JSON（GameEngine 进入沉浸体验的数据源）

    Raises:
        404: 书不存在或尚未生成完成
    """
    if not _catalog.get_book(book_id):
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")
    game = _catalog.get_game(book_id)
    if not game:
        raise HTTPException(
            status_code=404,
            detail="game not generated yet",
        )
    return {"game": game}


# ============================================================
# 注册 / 生成接口
# ============================================================


@router.post("", response_model=GenerateResponse)
async def register_and_generate(body: BookGenerateRequest) -> GenerateResponse:
    """注册新书并启动生成任务

    若书名与书库中已有书完全一致，则不重复注册，改为对已有书
    启动生成（返回其 book_id，语义仍为"把这本书做成游戏"）。

    Args:
        body: 书名 + 书籍正文/摘要 + 类型 + 场景数

    Returns:
        data: {book_id, task_id, created(bool), polling_url}
    """
    # 重名书 → 直接对已有书生成，避免书库出现重复条目
    existing = _catalog.get_book_by_title(body.book_title)
    if existing:
        task_id = _executor.submit_generate_for_existing(
            book_id=existing["id"],
            book_title=body.book_title,
            book_text=body.book_text,
            book_type=body.book_type,
            max_scenes=body.max_scenes,
        )
        logger.info(
            "books: title matches existing book %s, started generate task %s",
            existing["id"], task_id,
        )
        return GenerateResponse(
            code=0,
            message="generate_submitted_for_existing",
            data={
                "book_id": existing["id"],
                "task_id": task_id,
                "created": False,
                "polling_url": f"/api/tasks/{task_id}",
            },
            timestamp=int(time.time()),
        )

    book_id, task_id = _executor.submit_generate_book(
        book_title=body.book_title,
        book_text=body.book_text,
        book_type=body.book_type,
        max_scenes=body.max_scenes,
    )
    return GenerateResponse(
        code=0,
        message="generate_submitted",
        data={
            "book_id": book_id,
            "task_id": task_id,
            "created": True,
            "polling_url": f"/api/tasks/{task_id}",
        },
        timestamp=int(time.time()),
    )


@router.post("/{book_id}/generate", response_model=GenerateResponse)
async def generate_for_existing(book_id: str, body: BookGenerateRequest) -> GenerateResponse:
    """为书库已有书启动内容生成（种子书 / 已注册书均可）

    Raises:
        404: 书不存在
        409: 该书已有生成任务在运行
    """
    if not _catalog.get_book(book_id):
        raise HTTPException(status_code=404, detail=f"Book {book_id} not found")

    state = _catalog.get_generated_state(book_id)
    if state and state.get("status") == "in_progress":
        raise HTTPException(
            status_code=409,
            detail="该书的生成任务正在进行中，请等待完成后再试",
        )

    task_id = _executor.submit_generate_for_existing(
        book_id=book_id,
        book_title=body.book_title,
        book_text=body.book_text,
        book_type=body.book_type,
        max_scenes=body.max_scenes,
    )
    return GenerateResponse(
        code=0,
        message="generate_submitted",
        data={
            "book_id": book_id,
            "task_id": task_id,
            "created": False,
            "polling_url": f"/api/tasks/{task_id}",
        },
        timestamp=int(time.time()),
    )
