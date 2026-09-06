"""services —— 全局服务单例（依赖注入）

统一提供：Registry / Orchestrator / TaskExecutor / Catalog / VectorStore
避免在 main.py 与各 router 中重复构建相同实例（尤其 chromadb 与
任务状态需进程内共享）。

使用方式：
    >>> from core.services import get_executor, get_catalog
    >>> executor = get_executor()
    >>> catalog = get_catalog()
"""

from typing import Dict, Optional

from agents.registry import Registry
from core.catalog import Catalog
from core.executor import TaskExecutor
from core.orchestrator import Orchestrator
from core.task_manager import TaskManager, get_task_manager as _task_manager_factory
from memory.vector_store import BookChunk, VectorStore

_registry: Optional[Registry] = None
_orchestrator: Optional[Orchestrator] = None
_executor: Optional[TaskExecutor] = None
_catalog: Optional[Catalog] = None
_vector_store: Optional[VectorStore] = None
_task_manager: Optional[TaskManager] = None


def get_registry() -> Registry:
    """获取全局 Agent 注册表单例"""
    global _registry
    if _registry is None:
        _registry = Registry()
    return _registry


def get_orchestrator() -> Orchestrator:
    """获取全局编排器单例"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(get_registry())
    return _orchestrator


def get_executor() -> TaskExecutor:
    """获取全局任务执行器单例（绑定 Catalog + VectorStore 用于注册书回写）"""
    global _executor
    if _executor is None:
        _executor = TaskExecutor(
            get_orchestrator(),
            get_task_manager(),
            catalog=get_catalog(),
            vector_store=get_vector_store(),
        )
    return _executor


def get_catalog() -> Catalog:
    """获取全局业务档案单例"""
    global _catalog
    if _catalog is None:
        _catalog = Catalog()
    return _catalog


def get_vector_store() -> VectorStore:
    """获取全局向量库单例（NPC 对话与注册书导入共用）"""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store


def get_task_manager() -> TaskManager:
    """获取全局任务管理器单例（透传 core.task_manager 全局单例）"""
    global _task_manager
    if _task_manager is None:
        _task_manager = _task_manager_factory()
    return _task_manager


# ============================================================
# 种子语料启动导入（NPC 对话 RAG 的数据源）
# ============================================================


def ingest_seed_corpus() -> Dict[str, int]:
    """把 seed 中已有的书籍语料导入向量库（应用启动时调用一次）

    导入范围：
    1. 有 chapters/quotes 的书：章节标题行 + 摘录原文行
    2. 带历史对话种子的 NPC：把对话种子并入其关联书（Q&A 记忆行）

    进程内 ChromaDB 随进程重启即清空，因此启动导入不会重复累积。

    Returns:
        {book_id: 导入分块数}（用于日志/测试断言）
    """
    catalog = get_catalog()
    vector_store = get_vector_store()

    # 1) 先收集每本书的正文语料
    per_book_lines: Dict[str, list] = {}
    for book in catalog.list_books():
        book_id = book["id"]
        chapters = catalog.get_chapters(book_id)
        quotes = catalog.get_quotes(book_id)
        if not chapters and not quotes:
            continue
        lines: list = []
        for ch in chapters:
            title = ch.get("title", "")
            if title:
                lines.append(f"《{book['title']}》第{ch.get('index', '?')}章：{title}")
        for q in quotes:
            text = q.get("text", "")
            if text:
                lines.append(f"《{book['title']}》第{q.get('chapter', '?')}章摘录：{text}")
        per_book_lines[book_id] = lines

    # 2) NPC 关联书对话种子（聊过的 Q&A 作为可检索记忆）
    for npc in catalog.get_npcs():
        conversations = catalog.get_npc_conversations(npc["id"])
        if not conversations:
            continue
        titles = npc.get("booksAssociated") or []
        if not titles:
            continue
        linked_book = catalog.get_book_by_title(titles[0])
        if not linked_book:
            continue
        lines = per_book_lines.setdefault(linked_book["id"], [])
        lines.append(f"【NPC {npc['name']} 与你聊过的内容】")
        for conv in conversations:
            user_msg = conv.get("userMessage", "")
            npc_reply = conv.get("npcResponse", "")
            if user_msg:
                lines.append(f"玩家问：{user_msg}")
            if npc_reply:
                lines.append(f"{npc['name']}答：{npc_reply}")

    # 3) 写入向量库
    added: Dict[str, int] = {}
    for book_id, lines in per_book_lines.items():
        clean = [line for line in lines if line.strip()]
        if not clean:
            continue
        chunks = [
            BookChunk(chunk_index=i, text=line)
            for i, line in enumerate(clean)
        ]
        count = vector_store.add_chunks(book_id, chunks)
        added[book_id] = count
    return added
