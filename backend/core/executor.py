"""任务执行器 —— 在后台运行 LangGraph 状态机并更新任务进度

负责：
- 接收任务输入，启动 GenerationGraph（Phase 2b）
- 通过节点进度回调实时同步各阶段状态到 TaskManager
- 处理成功/失败结果
"""

import asyncio
from typing import Any, Dict, Optional

from core.orchestrator import Orchestrator, OrchestratorResult
from core.task_manager import TaskManager, get_task_manager
from models.schemas import AgentResult, ExecutionStage


class TaskExecutor:
    """任务执行器 —— 将 Orchestrator 执行绑定到 Task 上

    使用方式：
        >>> executor = TaskExecutor(orchestrator, task_manager)
        >>> task_id = executor.submit_generate(book_text="...", book_title="...")
    """

    def __init__(
        self,
        orchestrator: Orchestrator,
        task_manager: Optional[TaskManager] = None,
    ) -> None:
        self._orchestrator = orchestrator
        self._task_manager = task_manager or get_task_manager()

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
        agent_names = [a["name"] for a in self._orchestrator._registry.list_agents()]

        task = self._task_manager.create_task(
            task_type="generate",
            input_data={"book_text": book_text, "book_title": book_title},
            agent_names=agent_names,
        )

        input_data = {
            "book_text": book_text,
            "book_title": book_title,
            "book_type": book_type,
            "max_scenes": max_scenes,
        }

        # 用 asyncio 后台运行（在 ASGI 事件循环中）
        self._run_background(task.task_id, input_data)

        return task.task_id

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

        运行 Orchestrator，每完成一个阶段就更新 Task 状态。
        """
        try:
            self._task_manager.start_task(task_id)

            # 自定义一个带进度回调的执行
            result = await self._run_with_progress(task_id, input_data)

            if result.success:
                self._task_manager.complete_task(
                    task_id,
                    result={
                        "stages": [s.model_dump() for s in result.stages],
                        "final_result": result.final_result,
                        "execution_log": result.execution_log,
                        "total_time_seconds": result.total_time_seconds,
                    },
                )
            else:
                # 找出失败阶段的错误信息
                error_msg = "Unknown error"
                for stage in result.stages:
                    if stage.status == "failed" and stage.result and stage.result.error:
                        error_msg = stage.result.error
                        break
                self._task_manager.fail_task(task_id, error_msg)

        except Exception as e:
            self._task_manager.fail_task(task_id, f"{type(e).__name__}: {e}")

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
