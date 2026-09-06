"""核心编排 —— 基于 LangGraph StateGraph 的内容生成状态机

对应 PRD4 第五章 5.2 的状态机设计：

    extract(骨架+概念)
        │
        ▼
    [条件路由: 是否有概念?] ──否──→ error → END
        │是
        ▼
      scene(场景生成)
        │
        ▼
    [条件路由: 场景数量>0?] ──否──→ error → END
        │是
        ▼
     narrator(聚合编织) → END

本模块是 Phase 2b 的核心交付：
- 用 LangGraph StateGraph 定义节点与条件路由
- 每个节点内部调用对应 Agent（Registry 获取）
- 节点可上报进度到 TaskManager（通过可选回调）
"""

import uuid
from typing import Any, Callable, Dict, List, Literal, Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agents.registry import Registry

# 阶段进度回调签名: (agent_name, status, progress, message)
ProgressCallback = Callable[[str, str, int, Optional[str]], None]


# ============================================================
# 状态定义
# ============================================================


class GenerationState(TypedDict, total=False):
    """生成流程的状态（LangGraph State）"""

    # 输入
    book_text: str
    book_title: str
    book_type: str
    max_scenes: int

    # ExtractAgent 输出
    core_theme: str
    chapters: List[Dict[str, Any]]
    total_concepts: int

    # SceneAgent 输出
    scenes: List[Dict[str, Any]]
    scene_count: int
    processed_concepts: List[str]

    # NarratorAgent 输出
    final_game: Dict[str, Any]

    # 控制/错误
    error: str


# ============================================================
# 图构建器
# ============================================================


class GenerationGraphError(Exception):
    """生成图运行时错误"""


def _count_concepts(state: GenerationState) -> int:
    """从 state.chapters 统计概念总数（用于条件路由）"""
    total = 0
    for ch in state.get("chapters", []):
        total += len(ch.get("concepts", []))
    return total


def _is_scene_success(state: GenerationState) -> bool:
    """判断 scene 阶段是否成功产出场景"""
    return state.get("scene_count", 0) > 0


class GenerationGraph:
    """LangGraph 状态机 —— 三阶段内容生成

    用法：
        >>> reg = Registry()
        >>> g = GenerationGraph(reg)
        >>> result = await g.arun({
        ...     "book_text": "...", "book_title": "...",
        ... })
        >>> result["final_game"]["book_title"]
    """

    def __init__(
        self,
        registry: Registry,
        progress_callback: Optional[ProgressCallback] = None,
    ) -> None:
        self._registry = registry
        self._progress_callback = progress_callback
        self._graph = self._build_graph()

    # ============================================================
    # 进度上报
    # ============================================================

    def _emit(
        self,
        agent: str,
        status: str,
        progress: int,
        message: Optional[str] = None,
    ) -> None:
        """上报单个阶段的进度（若有回调）"""
        if self._progress_callback is not None:
            self._progress_callback(agent, status, progress, message)

    # ============================================================
    # 节点定义（对应 PRD4 的 extract/scene/narrator）
    # ============================================================

    async def _extract_node(self, state: GenerationState) -> Dict[str, Any]:
        """节点 1：ExtractAgent 骨架提取"""
        self._emit("extract", "running", 5, "提取书籍骨架…")
        try:
            agent = self._registry.get("extract")
        except KeyError as e:
            self._emit("extract", "failed", 0, str(e))
            return {"error": f"extract agent not registered: {e}"}

        # Agent.run 自带异常兜底，返回 AgentResult
        from agents.base import AgentResult

        result = await agent.run(state)
        if not isinstance(result, AgentResult) or not result.success:
            err = getattr(result, "error", "extract failed")
            self._emit("extract", "failed", 0, err)
            return {"error": f"extract agent failed: {err}"}
        if not result.result:
            self._emit("extract", "failed", 0, "empty result")
            return {"error": "extract returned empty result"}

        data = result.result  # BookSkeleton dict
        self._emit("extract", "completed", 100, "骨架提取完成")
        return {
            "core_theme": data.get("core_theme", ""),
            "chapters": data.get("chapters", []),
            "total_concepts": data.get("total_concepts", 0),
        }

    async def _scene_node(self, state: GenerationState) -> Dict[str, Any]:
        """节点 2：SceneAgent 场景生成"""
        self._emit("scene", "running", 5, "生成决策场景…")
        try:
            agent = self._registry.get("scene")
        except KeyError as e:
            self._emit("scene", "failed", 0, str(e))
            return {"error": f"scene agent not registered: {e}"}

        # 校验上游
        if not _count_concepts(state):
            self._emit("scene", "failed", 0, "no concepts from extract")
            return {"error": "scene skipped: no concepts from extract"}

        from agents.base import AgentResult

        result = await agent.run(state)
        if not isinstance(result, AgentResult) or not result.success:
            err = getattr(result, "error", "scene failed")
            self._emit("scene", "failed", 0, err)
            return {"error": f"scene agent failed: {err}"}
        if not result.result:
            self._emit("scene", "failed", 0, "empty result")
            return {"error": "scene returned empty result"}

        data = result.result
        self._emit("scene", "completed", 100, "场景生成完成")
        return {
            "scenes": data.get("scenes", []),
            "scene_count": data.get("scene_count", 0),
            "processed_concepts": data.get("processed_concepts", []),
        }

    async def _narrator_node(self, state: GenerationState) -> Dict[str, Any]:
        """节点 3：NarratorAgent 聚合编织"""
        self._emit("narrator", "running", 5, "编织叙事…")
        try:
            agent = self._registry.get("narrator")
        except KeyError as e:
            self._emit("narrator", "failed", 0, str(e))
            return {"error": f"narrator agent not registered: {e}"}

        # 校验上游
        if not state.get("scenes"):
            self._emit("narrator", "failed", 0, "no scenes from scene stage")
            return {"error": "narrator skipped: no scenes from scene stage"}

        from agents.base import AgentResult

        result = await agent.run(state)
        if not isinstance(result, AgentResult) or not result.success:
            err = getattr(result, "error", "narrator failed")
            self._emit("narrator", "failed", 0, err)
            return {"error": f"narrator agent failed: {err}"}

        self._emit("narrator", "completed", 100, "叙事编排完成")
        return {"final_game": result.result}

    # ============================================================
    # 条件路由（PRD4 图上的分支）
    # ============================================================

    def _route_after_extract(
        self, state: GenerationState,
    ) -> Literal["scene", "error_handler"]:
        """extract 后：有概念 → scene；否则 → error_handler"""
        if state.get("error"):
            return "error_handler"
        return "scene" if _count_concepts(state) > 0 else "error_handler"

    def _route_after_scene(
        self, state: GenerationState,
    ) -> Literal["narrator", "error_handler"]:
        """scene 后：场景数量>0 → narrator；否则 → error_handler"""
        if state.get("error"):
            return "error_handler"
        return "narrator" if _is_scene_success(state) else "error_handler"

    # ============================================================
    # 图构建
    # ============================================================

    def _build_graph(self):
        """组装 LangGraph StateGraph"""
        builder = StateGraph(GenerationState)

        builder.add_node("extract", self._extract_node)
        builder.add_node("scene", self._scene_node)
        builder.add_node("narrator", self._narrator_node)
        builder.add_node("error_handler", self._error_node)

        # START → extract
        builder.add_edge(START, "extract")

        # extract → 条件路由
        builder.add_conditional_edges(
            "extract",
            self._route_after_extract,
            {
                "scene": "scene",
                "error_handler": "error_handler",
            },
        )

        # scene → 条件路由
        builder.add_conditional_edges(
            "scene",
            self._route_after_scene,
            {
                "narrator": "narrator",
                "error_handler": "error_handler",
            },
        )

        # narrator / error_handler → END
        builder.add_edge("narrator", END)
        builder.add_edge("error_handler", END)

        # MemorySaver 提供检查点持久化（进程内存），
        # 生产环境可替换为 SqliteSaver/PostgresSaver（PRD4 5.3）。
        return builder.compile(checkpointer=MemorySaver())

    def _error_node(self, state: GenerationState) -> Dict[str, Any]:
        """错误终止节点：仅保留 error 状态，终止流程"""
        return {"error": state.get("error", "unknown error")}

    # ============================================================
    # 对外接口
    # ============================================================

    async def arun(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """异步执行完整生成流程

        Args:
            input_data: 初始输入（book_text / book_title / book_type / max_scenes）

        Returns:
            最终 state dict，含 final_game（成功）或 error（失败）
        """
        # 每次执行使用唯一 thread_id，避免检查点累积旧状态导致串扰
        thread_id = f"{input_data.get('book_title', 'book')}-{uuid.uuid4().hex[:8]}"

        # 准备初始状态
        initial: GenerationState = {
            "book_text": input_data.get("book_text", ""),
            "book_title": input_data.get("book_title", ""),
            "book_type": input_data.get("book_type", "non_fiction"),
            "max_scenes": int(input_data.get("max_scenes", 3)),
        }

        config = {
            "configurable": {"thread_id": thread_id},
        }

        result = await self._graph.ainvoke(initial, config=config)
        return result
