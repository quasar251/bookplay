"""任务执行器 —— 在后台运行 LangGraph 状态机并更新任务进度

负责：
- 接收任务输入，启动 GenerationGraph（Phase 2b）
- 通过节点进度回调实时同步各阶段状态到 TaskManager
- 处理成功/失败结果
"""

import asyncio
import logging
from threading import RLock
from typing import Any, Dict, Optional, Tuple

from core.catalog import (
    Catalog,
    derive_chapters_from_game,
    derive_game_corpus_lines,
    derive_quotes_from_game,
)
from core.orchestrator import Orchestrator, OrchestratorResult
from core.task_manager import TaskManager, get_task_manager
from memory.vector_store import BookChunk, VectorStore
from models.schemas import AgentResult, ExecutionStage


class TaskExecutor:
    """任务执行器 —— 将 Orchestrator 执行绑定到 Task 上

    可选的 Catalog / VectorStore 用于"注册新书"链路：
    - 提交前在 Catalog 登记占位书（in_progress）
    - 生成成功后回写游戏 JSON/章节/摘录，并把游戏语料导入向量库
    - 生成失败把书标记为 failed

    使用方式：
        >>> executor = TaskExecutor(orchestrator, task_manager)
        >>> task_id = executor.submit_generate(book_text="...", book_title="...")
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        task_manager: Optional[TaskManager] = None,
        catalog: Optional[Catalog] = None,
        vector_store: Optional[VectorStore] = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._task_manager = task_manager or get_task_manager()
        self._catalog = catalog
        self._vector_store = vector_store
        # task_id -> book_id（用于生成完成后回写书档案）
        self._book_links: Dict[str, str] = {}
        self._links_lock = RLock()

    # ============================================================
    # 任务创建（通用生成）
    # ============================================================

    def submit_generate(
        self,
        book_text: str,
        book_title: str = "",
        book_type: str = "non_fiction",
        max_scenes: int = 3,
    ) -> str:
        """提交一个生成任务（立即返回 task_id，后台执行）

        Args:
            book_text: 书籍全文或摘要
            book_title: 书籍标题（可选）
            book_type: 书籍类型（non_fiction / fiction）
            max_scenes: 最多生成几个场景（控制成本）

        Returns:
            task_id: 任务 ID
        """
        input_data = {
            "book_text": book_text,
            "book_title": book_title,
            "book_type": book_type,
            "max_scenes": max_scenes,
        }
        task_id = self._create_task(input_data)
        self._start_task(task_id, input_data)
        return task_id

    def submit_generate_book(
        self,
        book_title: str,
        book_text: str,
        book_type: str = "non_fiction",
        max_scenes: int = 3,
    ) -> Tuple[str, str]:
        """提交"注册新书"生成任务：先在书库登记，生成成功后回写

        Args:
            book_title: 书名（必填）
            book_text: 书籍正文/摘要（至少 100 字）
            book_type: 书籍类型（non_fiction / fiction）
            max_scenes: 最多生成几个场景

        Returns:
            (book_id, task_id)

        Raises:
            RuntimeError: Catalog 未注入（不允许注册场景）
        """
        if self._catalog is None:
            raise RuntimeError("TaskExecutor.catalog is not configured")

        input_data = {
            "book_text": book_text,
            "book_title": book_title,
            "book_type": book_type,
            "max_scenes": max_scenes,
        }
        task_id = self._create_task(input_data)
        book_id = self._catalog.register_book(title=book_title, task_id=task_id)
        with self._links_lock:
            self._book_links[task_id] = book_id
        self._start_task(task_id, input_data)
        return book_id, task_id

    def submit_generate_for_existing(
        self,
        book_id: str,
        book_title: str,
        book_text: str,
        book_type: str = "non_fiction",
        max_scenes: int = 3,
    ) -> str:
        """为书库中已有书（种子书或注册书）提交生成任务

        与 submit_generate_book 的区别：不新建记录，完成后把
        产物挂载到原 book_id（种子书保持自身状态字段）。

        Args:
            book_id: 已有书 id
            book_title: 书名
            book_text: 书籍正文/摘要（至少 100 字）
            book_type: 书籍类型
            max_scenes: 最多生成几个场景

        Returns:
            task_id
        """
        input_data = {
            "book_text": book_text,
            "book_title": book_title,
            "book_type": book_type,
            "max_scenes": max_scenes,
        }
        task_id = self._create_task(input_data)
        with self._links_lock:
            self._book_links[task_id] = book_id
        self._start_task(task_id, input_data)
        return task_id

    def _create_task(self, input_data: Dict[str, Any]) -> str:
        """创建 Task（含各 Agent 阶段的进度槽）"""
        agent_names = [a["name"] for a in self._orchestrator._registry.list_agents()]
        task = self._task_manager.create_task(
            task_type="generate",
            input_data=input_data,
            agent_names=agent_names,
        )
        return task.task_id

    def _start_task(self, task_id: str, input_data: Dict[str, Any]) -> None:
        """用 asyncio 后台运行（在 ASGI 事件循环中）"""
        self._run_background(task_id, input_data)

    def _run_background(self, task_id: str, input_data: Dict[str, Any]) -> None:
        """启动后台异步任务（fire-and-forget）

        在 FastAPI 环境下，利用当前事件循环创建 task。
        """
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.create_task(self._execute_task(task_id, input_data))

    async def _execute_task(
        self,
        task_id: str,
        input_data: Dict[str, Any],
    ) -> None:
        """真正执行任务的协程

        运行 Orchestrator，每完成一个阶段就更新 Task 状态；
        若该任务关联了注册书（book_links），完成后回写书档案。
        """
        try:
            self._task_manager.start_task(task_id)

            # 自定义一个带进度回调的执行
            result = await self._run_with_progress(task_id, input_data)

            if result.success:
                final_game = result.final_result
                self._task_manager.complete_task(
                    task_id,
                    result={
                        "stages": [s.model_dump() for s in result.stages],
                        "final_result": final_game,
                        "execution_log": result.execution_log,
                        "total_time_seconds": result.total_time_seconds,
                    },
                )
                if final_game:
                    self._finalize_book(task_id, game=final_game)
            else:
                # 找出失败阶段的错误信息
                error_msg = "Unknown error"
                for stage in result.stages:
                    if stage.status == "failed" and stage.result and stage.result.error:
                        error_msg = stage.result.error
                        break
                self._task_manager.fail_task(task_id, error_msg)
                self._finalize_book(task_id, error=error_msg)

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            self._task_manager.fail_task(task_id, error_msg)
            self._finalize_book(task_id, error=error_msg)

    # ============================================================
    # 注册书回写（成功后章节/摘录/语料入库，失败标记状态）
    # ============================================================

    def _finalize_book(
        self,
        task_id: str,
        game: Optional[Dict[str, Any]] = None,
        error: str = "",
    ) -> None:
        """生成结束后把结果写回 Catalog

        注册书 → 更新状态字段并保存章节/摘录/游戏 JSON；
        种子书 → 挂载到 _generated（保持原状态字段不变）。

        Args:
            task_id: 任务 ID（查 book_links）
            game: 生成成功的完整游戏 JSON
            error: 失败原因（失败时非空）
        """
        with self._links_lock:
            book_id = self._book_links.pop(task_id, None)
        if not book_id or self._catalog is None:
            return

        if self._catalog.is_registered(book_id):
            if game is not None:
                chapters = derive_chapters_from_game(game)
                quotes = derive_quotes_from_game(game)
                self._catalog.update_book_status(
                    book_id,
                    "completed",
                    message="生成完成，沉浸式学习内容已就绪。",
                    game=game,
                    chapters=chapters,
                    quotes=quotes,
                )
            else:
                self._catalog.update_book_status(
                    book_id,
                    "failed",
                    message=error or "生成失败，请稍后重试。",
                )
        else:
            self._catalog.attach_seed_generated(
                book_id,
                status="completed" if game is not None else "failed",
                message=(
                    "生成完成，沉浸式学习内容已就绪。"
                    if game is not None
                    else (error or "生成失败，请稍后重试。")
                ),
                game=game,
            )

        if game is not None:
            self._ingest_game_corpus(book_id, game)

    def _ingest_game_corpus(
        self,
        book_id: str,
        game: Dict[str, Any],
    ) -> None:
        """把生成后的游戏语料写入向量库（NPC 后续对话可 RAG 检索）

        Args:
            book_id: 新书 id
            game: 完整游戏 JSON
        """
        if self._vector_store is None:
            return
        try:
            lines = derive_game_corpus_lines(game)
            chunks = [
                BookChunk(chunk_index=i, text=text)
                for i, text in enumerate(lines)
                if text.strip()
            ]
            if chunks:
                self._vector_store.add_chunks(book_id, chunks)
        except Exception:
            # 语料导入失败不影响主流程（NPC 对话会自动降级）
            logging.getLogger(__name__).exception(
                "ingest game corpus failed for book %s", book_id,
            )

    async def _run_with_progress(
        self,
        task_id: str,
        input_data: Dict[str, Any],
    ) -> OrchestratorResult:
        """通过 LangGraph 状态机执行内容生成，并同步进度到 TaskManager

        每个图节点（extract/scene/narrator）执行时会通过回调
        更新对应 Task 阶段的状态与整体进度。

        Returns:
            OrchestratorResult: 兼容旧接口的封装结果
        """
        from core.state_graph import GenerationGraph

        def on_stage(
            agent: str,
            status: str,
            progress: int,
            message: Optional[str] = None,
        ) -> None:
            self._task_manager.update_stage(
                task_id, agent, status, progress, message,
            )

        graph = GenerationGraph(
            self._orchestrator._registry,
            progress_callback=on_stage,
        )
        state = await graph.arun(input_data)

        final_game = state.get("final_game")
        if final_game:
            return OrchestratorResult(
                success=True,
                stages=[],
                final_result=final_game,
                total_time_seconds=0.0,
                execution_log=[],
            )

        # 失败：把错误信息放进一个 failed 阶段，方便上层提取
        error_msg = state.get("error") or "Unknown generation error"
        failed_stage = ExecutionStage(
            stage=1,
            agent="generation_graph",
            status="failed",
            duration_ms=0.0,
            input_keys=list(input_data.keys()),
            result=AgentResult(
                success=False,
                result=None,
                error=error_msg,
            ),
        )
        return OrchestratorResult(
            success=False,
            stages=[failed_stage],
            final_result=None,
            total_time_seconds=0.0,
            execution_log=[],
        )
