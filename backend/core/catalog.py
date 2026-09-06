"""Catalog —— BookPlay 业务数据层（内存版）

Phase 4 新增：把原前端 mock 的"书库 / 章节 / 摘录 / NPC / 图谱 /
群组 / 用户"等数据收拢到后端，作为种子业务数据（seed），并支持
注册新书（真实生成，完成后回写书籍档案）。

数据来源：
- data/seed.json：前端 mockData 导出的静态档案（结构保持一致，
  便于前端最小化改动）。
- 运行时注册：register_book() 追加用户生成的书，状态由对应
  生成 Task 驱动（in_progress → completed / failed）。

设计要点：
- 线程安全：内部使用 RLock。
- 单一数据源：前端不再 import mockData.js，而是统一访问本层。
"""

import copy
import json
import logging
import uuid
from datetime import datetime
from pathlib import Path
from threading import RLock
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_SEED_PATH = Path(__file__).resolve().parent.parent / "data" / "seed.json"

# 注册书生成前的默认展示字段（可被 register_book 覆盖）
_BOOK_COVERS: List[str] = ["📕", "📗", "📘", "📙"]
_BOOK_COVER_COLORS: List[str] = [
    "from-cyan-400 to-blue-600",
    "from-emerald-400 to-teal-600",
    "from-violet-400 to-purple-600",
    "from-rose-400 to-pink-600",
]


class Catalog:
    """业务档案与运行时书库（内存单例可多次构建，进程重启即重置）

    使用方式：
        >>> catalog = Catalog()
        >>> catalog.list_books()          # 种子书 + 注册书
        >>> catalog.get_book("book1")     # 单本详情
        >>> catalog.register_book(title="...", task_id="...")  # 注册占位
    """

    def __init__(self, seed_path: Path = _SEED_PATH) -> None:
        self._lock = RLock()
        self._seed_path = seed_path
        seed = self._load_seed(seed_path)

        # 静态档案（deep copy 防外部修改）
        self._books: List[Dict[str, Any]] = copy.deepcopy(seed.get("books", []))
        self._chapters: Dict[str, List[Dict[str, Any]]] = copy.deepcopy(
            seed.get("chapters", {}),
        )
        self._quotes: Dict[str, List[Dict[str, Any]]] = copy.deepcopy(
            seed.get("quotes", {}),
        )
        self._npcs: List[Dict[str, Any]] = copy.deepcopy(seed.get("npcs", []))
        self._npc_conversations: Dict[str, List[Dict[str, Any]]] = copy.deepcopy(
            seed.get("npcConversations", {}),
        )
        self._static = {
            key: copy.deepcopy(seed.get(key))
            for key in (
                "user",
                "achievements",
                "skillTree",
                "userProfile",
                "groupDiscussions",
                "knowledgeGraph",
            )
        }
        # 后续运行时插入的注册书记录 book_id -> dict
        self._registered: Dict[str, Dict[str, Any]] = {}
        # 运行时生成的游戏内容（对已有书 id 的挂载，含种子书）book_id -> dict
        self._generated: Dict[str, Dict[str, Any]] = {}

    # ============================================================
    # 种子加载
    # ============================================================

    @staticmethod
    def _load_seed(seed_path: Path) -> Dict[str, Any]:
        """读取 seed.json

        Args:
            seed_path: 种子文件路径

        Returns:
            解析后的 dict

        Raises:
            FileNotFoundError: 文件不存在
            json.JSONDecodeError: JSON 非法
        """
        if not seed_path.exists():
            raise FileNotFoundError(f"seed file not found: {seed_path}")
        with seed_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    # ============================================================
    # 档案查询（只读）
    # ============================================================

    def bootstrap(self) -> Dict[str, Any]:
        """返回前端需要的全部档案数据（一次拉取）

        Returns:
            {books, chapters, quotes, npcs, npcConversations, user,
             achievements, skillTree, userProfile, groupDiscussions,
             knowledgeGraph}
        """
        with self._lock:
            return {
                "books": self.list_books(),
                "chapters": copy.deepcopy(self._chapters),
                "quotes": copy.deepcopy(self._quotes),
                "npcs": copy.deepcopy(self._npcs),
                "npcConversations": copy.deepcopy(self._npc_conversations),
                "user": copy.deepcopy(self._static["user"]),
                "achievements": copy.deepcopy(self._static["achievements"]),
                "skillTree": copy.deepcopy(self._static["skillTree"]),
                "userProfile": copy.deepcopy(self._static["userProfile"]),
                "groupDiscussions": copy.deepcopy(self._static["groupDiscussions"]),
                "knowledgeGraph": copy.deepcopy(self._static["knowledgeGraph"]),
            }

    def list_books(self) -> List[Dict[str, Any]]:
        """返回全部书籍（种子书在前，注册书在后）"""
        with self._lock:
            books = copy.deepcopy(self._books)
            for book in sorted(
                self._registered.values(), key=lambda b: b.get("createdAt", ""),
            ):
                books.append(copy.deepcopy(book))
            return books

    def get_book(self, book_id: str) -> Optional[Dict[str, Any]]:
        """按 id 获取单本书（种子书或注册书）"""
        with self._lock:
            for book in self._books:
                if book.get("id") == book_id:
                    return copy.deepcopy(book)
            registered = self._registered.get(book_id)
            return copy.deepcopy(registered) if registered else None

    def get_book_by_title(self, title: str) -> Optional[Dict[str, Any]]:
        """按书名精确匹配书籍（种子书或注册书）

        Args:
            title: 书名

        Returns:
            匹配的书籍 dict；无匹配返回 None
        """
        with self._lock:
            for book in self.list_books():
                if book.get("title") == title:
                    return book
            return None

    def get_chapters(self, book_id: str) -> List[Dict[str, Any]]:
        """获取某本书的章节列表

        优先级：种子章节 → 注册书（生成后填充）→ 种子书挂载的游戏产物。
        注册书在生成完成前为空，种子书在"用本书内容生成"完成前为空。

        Args:
            book_id: 书 id

        Returns:
            章节列表；无内容返回 []
        """
        with self._lock:
            if book_id in self._chapters:
                return copy.deepcopy(self._chapters[book_id])
            registered = self._registered.get(book_id)
            if registered:
                if registered.get("chapters"):
                    return copy.deepcopy(registered["chapters"])
                game = registered.get("game")
                if game:
                    return derive_chapters_from_game(game)
                return []
            generated = self._generated.get(book_id)
            if generated and generated.get("game"):
                return derive_chapters_from_game(generated["game"])
            return []

    def get_quotes(self, book_id: str) -> List[Dict[str, Any]]:
        """获取某本书的摘录列表

        优先级：种子摘录 → 注册书（生成后填充）→ 种子书挂载的游戏产物。
        注册书在生成完成前为空，种子书在"用本书内容生成"完成前为空。

        Args:
            book_id: 书 id

        Returns:
            摘录列表；无内容返回 []
        """
        with self._lock:
            if book_id in self._quotes:
                return copy.deepcopy(self._quotes[book_id])
            registered = self._registered.get(book_id)
            if registered:
                if registered.get("quotes"):
                    return copy.deepcopy(registered["quotes"])
                game = registered.get("game")
                if game:
                    return derive_quotes_from_game(game)
                return []
            generated = self._generated.get(book_id)
            if generated and generated.get("game"):
                return derive_quotes_from_game(generated["game"])
            return []

    def get_npc_conversations(self, npc_id: str) -> List[Dict[str, Any]]:
        """按 NPC id 获取历史对话种子"""
        with self._lock:
            return copy.deepcopy(self._npc_conversations.get(npc_id, []))

    def get_npcs(self) -> List[Dict[str, Any]]:
        """获取 NPC 档案列表"""
        with self._lock:
            return copy.deepcopy(self._npcs)

    def get_npc(self, npc_id: str) -> Optional[Dict[str, Any]]:
        """按 id 获取单个 NPC 档案"""
        with self._lock:
            for npc in self._npcs:
                if npc.get("id") == npc_id:
                    return copy.deepcopy(npc)
            return None

    # ============================================================
    # 注册书管理（写操作）
    # ============================================================

    def register_book(self, title: str, task_id: str) -> str:
        """登记一本正在生成的书（占位记录）

        Args:
            title: 书名
            task_id: 生成任务 ID（驱动状态）

        Returns:
            新书 book_id

        Raises:
            ValueError: title 为空
        """
        if not title or not title.strip():
            raise ValueError("title is required")

        book_id = f"bk{uuid.uuid4().hex[:8]}"
        idx = len(self._registered) % len(_BOOK_COVERS)
        book: Dict[str, Any] = {
            "id": book_id,
            "title": title,
            "author": "BookPlay 生成",
            "cover": _BOOK_COVERS[idx],
            "coverColor": _BOOK_COVER_COLORS[idx],
            "status": "in_progress",
            "totalChapters": 0,
            "completedChapters": 0,
            "xpEarned": 0,
            "difficulty": "medium",
            "conceptCount": 0,
            "npcId": None,
            "description": "正在由 Agent 生成沉浸式学习内容…",
            "createdAt": datetime.now().isoformat(timespec="seconds"),
            "registered": True,
            "task_id": task_id,
        }
        with self._lock:
            self._registered[book_id] = book
        logger.info("catalog: registered book %s (title=%s)", book_id, title)
        return book_id

    def update_book_status(
        self,
        book_id: str,
        status: str,
        *,
        message: str = "",
        game: Optional[Dict[str, Any]] = None,
        chapters: Optional[List[Dict[str, Any]]] = None,
        quotes: Optional[List[Dict[str, Any]]] = None,
    ) -> bool:
        """更新注册书状态（由任务执行器回写）

        Args:
            book_id: 书 id
            status: 新状态（in_progress / completed / failed）
            message: 状态描述（失败原因等）
            game: 生成完成后的完整游戏 JSON（可选）
            chapters: 生成完成后的章节列表（可选）
            quotes: 生成完成后的摘录列表（可选）

        Returns:
            是否找到并更新
        """
        with self._lock:
            book = self._registered.get(book_id)
            if not book:
                return False
            book["status"] = status
            if message:
                book["description"] = message
            if game:
                book["game"] = game
                book["conceptCount"] = len(game.get("all_cards", []))
                chapters_in_game = game.get("chapters", [])
                if chapters_in_game:
                    book["totalChapters"] = len(chapters_in_game)
            if chapters is not None:
                book["chapters"] = chapters
            if quotes is not None:
                book["quotes"] = quotes
            return True

    def remove_book(self, book_id: str) -> bool:
        """从注册书集合中移除（失败任务清理等）

        Args:
            book_id: 书 id

        Returns:
            是否存在
        """
        with self._lock:
            removed = self._registered.pop(book_id, None) is not None
            self._generated.pop(book_id, None)
            return removed

    # ============================================================
    # 生成内容挂载（种子书/注册书统一查询入口）
    # ============================================================

    def is_registered(self, book_id: str) -> bool:
        """book_id 是否为运行时注册的书"""
        with self._lock:
            return book_id in self._registered

    def get_game(self, book_id: str) -> Optional[Dict[str, Any]]:
        """获取某本书的完整游戏 JSON（注册书优先，种子书看挂载）

        Args:
            book_id: 书 id

        Returns:
            游戏 JSON；尚未生成时返回 None
        """
        with self._lock:
            registered = self._registered.get(book_id)
            if registered and registered.get("game"):
                return copy.deepcopy(registered["game"])
            generated = self._generated.get(book_id)
            if generated and generated.get("game"):
                return copy.deepcopy(generated["game"])
            return None

    def get_generated_state(self, book_id: str) -> Optional[Dict[str, Any]]:
        """获取某本书的生成状态元信息（status / message）

        Args:
            book_id: 书 id

        Returns:
            注册书返回 {status, message,...}（含失败原因）；无记录返回 None
        """
        with self._lock:
            registered = self._registered.get(book_id)
            if registered:
                return copy.deepcopy({
                    "status": registered.get("status"),
                    "message": registered.get("description", ""),
                })
            generated = self._generated.get(book_id)
            if generated:
                return copy.deepcopy({
                    "status": generated.get("status", "unknown"),
                    "message": generated.get("message", ""),
                })
            return None

    def attach_seed_generated(
        self,
        book_id: str,
        *,
        status: str,
        message: str = "",
        game: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """把生成结果挂载到已有种子书上（种子书保持自身状态字段）

        种子书原本不带生成游戏；用户点击"用本书内容生成"后，
        把产物挂载到原书 id 上，前端即可进入真实生成的沉浸体验。

        Args:
            book_id: 种子书 id
            status: 生成状态（completed / failed / in_progress）
            message: 描述信息（失败原因等）
            game: 完整游戏 JSON（成功时提供）

        Returns:
            是否挂载成功（仅当是种子书且未注册时）
        """
        with self._lock:
            is_seed = any(b.get("id") == book_id for b in self._books)
            if not is_seed or book_id in self._registered:
                return False
            overlay: Dict[str, Any] = {
                "status": status,
                "message": message,
                "book_id": book_id,
            }
            if game:
                overlay["game"] = game
                overlay["conceptCount"] = len(game.get("all_cards", []))
                overlay["totalChapters"] = len(game.get("chapters", []))
            self._generated[book_id] = overlay
            logger.info("catalog: attached generated content to seed book %s", book_id)
            return True


# ============================================================
# 纯函数：把 Agent 生成的 game JSON 转换为档案内容
# （与数据库/向量库解耦，便于单测）
# ============================================================


def derive_chapters_from_game(game: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从完整游戏 JSON 提取章节列表（BookPlay 详情页结构）

    每章聚合其 scenes 下的概念名称作为"概念标签"，
    scene 原始数据保留在 scenes 字段供 GameEngine 使用。

    Args:
        game: Narrator 输出的完整游戏 JSON

    Returns:
        章节列表；无章节时返回 []
    """
    result: List[Dict[str, Any]] = []
    for ch in game.get("chapters", []):
        concepts: List[str] = []
        for scene in ch.get("scenes", []):
            name = scene.get("concept_name") or (scene.get("card") or {}).get("source_concept")
            if name and name not in concepts:
                concepts.append(name)
        result.append({
            "index": int(ch.get("chapter_id", len(result) + 1)),
            "title": ch.get("title", "未命名章节"),
            "summary": ch.get("summary", ""),
            "chapter_hook": ch.get("chapter_hook", ""),
            "concepts": concepts,
            "completed": False,
            "xpGained": 0,
            "scenes": ch.get("scenes", []),
        })
    return result


def derive_quotes_from_game(game: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从完整游戏 JSON 提取摘录（来自各场景的核心认知/卡牌定义）

    注：生成阶段的"原文摘录"随本书生成时的上下文存在；这里
    用场景的关键认知与卡牌定义作为可展示的精华句，供详情页回看。

    Args:
        game: Narrator 输出的完整游戏 JSON

    Returns:
        摘录列表
    """
    quotes: List[Dict[str, Any]] = []
    for ch in game.get("chapters", []):
        chapter_no = int(ch.get("chapter_id", 0))
        for scene in ch.get("scenes", []):
            learning = scene.get("learning") or {}
            card = scene.get("card") or {}
            concept = scene.get("concept_name") or card.get("source_concept") or ""
            texts = []
            if learning.get("key_idea"):
                texts.append(learning["key_idea"])
            if card.get("definition"):
                texts.append(card["definition"])
            for text in texts:
                if not text:
                    continue
                quotes.append({
                    "id": f"gq{chapter_no}-{len(quotes) + 1}",
                    "chapter": chapter_no,
                    "text": text,
                    "concept": concept,
                })
    return quotes


def derive_game_corpus_lines(game: Dict[str, Any]) -> List[str]:
    """把生成的游戏 JSON 转成可写入向量库的原文行（供 NPC 后续 RAG）

    每行 = 一条可检索的"书中知识"，带章节上下文。

    Args:
        game: Narrator 输出的完整游戏 JSON

    Returns:
        纯文本行列表
    """
    lines: List[str] = []
    book_title = game.get("book_title", "")
    for ch in game.get("chapters", []):
        chapter_no = int(ch.get("chapter_id", 0))
        title = ch.get("title", "")
        for scene in ch.get("scenes", []):
            concept = scene.get("concept_name", "")
            learning = scene.get("learning") or {}
            scenario = scene.get("scenario") or {}
            card = scene.get("card") or {}
            head = f"《{book_title}》第{chapter_no}章「{title}」关于「{concept}」："
            if learning.get("key_idea"):
                lines.append(f"{head}核心认知：{learning['key_idea']}")
            if learning.get("dialogue"):
                lines.append(f"{head}{learning['dialogue']}")
            if scenario.get("title") and scenario.get("description"):
                lines.append(
                    f"{head}情境「{scenario['title']}」：{scenario['description']}",
                )
            if card.get("definition"):
                lines.append(f"{head}卡牌「{card.get('name', '')}」：{card['definition']}")
    return lines
