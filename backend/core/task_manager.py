"""TaskManager — 异步任务管理器

基于 PRD4 第七章的设计：BackgroundTasks + 任务表。
当前为内存实现（MVP 阶段），后续可平滑迁移到 PostgreSQL。

状态机: pending → running → success
                  ↘ failed
"""

import asyncio
import time
import uuid
from datetime import datetime
from threading import RLock
from typing import Any, Callable, Dict, List, Optional

from models.schemas import Task, TaskStage


class TaskManagerError(Exception):
    """任务管理器异常"""


class TaskManager:
    """异步任务管理器（内存版）

    职责：
        - 创建任务并分配唯一 task_id
        - 跟踪任务状态与进度
        - 在后台执行长耗时操作
        - 提供查询接口（列表 / 详情）

    线程安全：使用 RLock 保护内部状态字典。

    使用方式：
        >>> manager = TaskManager()
        >>> task_id = manager.create_task("generate", {"book_text": "..."})
        >>> task = manager.get_task(task_id)
        >>> task.status
        'pending'
    """

    def __init__(self) -> None:
        self._tasks: Dict[str, Task] = {}
        self._lock = RLock()

    # ============================================================
    # 任务创建与查询
    # ============================================================

    def create_task(
        self,
        task_type: str,
        input_data: Dict[str, Any],
        agent_names: Optional[List[str]] = None,
    ) -> Task:
        """创建一个新任务

        Args:
            task_type: 任务类型（generate / npc_chat 等）
            input_data: 任务输入数据
            agent_names: 涉及的 Agent 名称列表（用于初始化 stages）

        Returns:
            新创建的 Task 对象
        """
        task_id = str(uuid.uuid4())

        stages: List[TaskStage] = []
        if agent_names:
            for idx, name in enumerate(agent_names):
                stages.append(TaskStage(
                    stage=idx + 1,
                    agent=name,
                    status="pending",
                    progress=0,
                ))

        task = Task(
            task_id=task_id,
            task_type=task_type,
            status="pending",
            progress=0,
            message=f"任务已创建，等待执行",
            stages=stages,
        )

        with self._lock:
            self._tasks[task_id] = task

        return task

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务详情"""
        with self._lock:
            return self._tasks.get(task_id)

    def list_tasks(self, limit: int = 20) -> List[Task]:
        """获取任务列表（按创建时间倒序）"""
        with self._lock:
            tasks = sorted(
                self._tasks.values(),
                key=lambda t: t.created_at,
                reverse=True,
            )
            return tasks[:limit]

    # ============================================================
    # 状态更新（供执行器调用）
    # ============================================================

    def start_task(self, task_id: str) -> None:
        """标记任务开始执行"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                raise TaskManagerError(f"Task {task_id} not found")
            task.status = "running"
            task.started_at = datetime.utcnow()
            task.message = "任务执行中..."

    def update_stage(
        self,
        task_id: str,
        agent_name: str,
        status: str,
        progress: int = 0,
        message: Optional[str] = None,
    ) -> None:
        """更新某个阶段的状态，并刷新整体进度

        Args:
            task_id: 任务 ID
            agent_name: 阶段 Agent 名称
            status: 新状态（pending / running / completed / failed）
            progress: 阶段进度 0-100
            message: 阶段描述
        """
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            # 找到对应阶段
            for stage in task.stages:
                if stage.agent == agent_name:
                    stage.status = status
                    stage.progress = max(0, min(100, progress))
                    if message:
                        stage.message = message
                    break

            # 计算整体进度
            self._recalc_progress(task)

            # 更新 message
            running_stage = next(
                (s for s in task.stages if s.status == "running"),
                None,
            )
            if running_stage:
                task.message = f"正在执行：{running_stage.agent} 阶段"

    def complete_task(
        self,
        task_id: str,
        result: Dict[str, Any],
    ) -> None:
        """标记任务成功完成"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            task.status = "success"
            task.progress = 100
            task.result = result
            task.finished_at = datetime.utcnow()
            task.message = "任务完成"
            if task.started_at:
                task.total_time_seconds = round(
                    (task.finished_at - task.started_at).total_seconds(), 2,
                )

            # 所有未完成阶段标记为 completed
            for stage in task.stages:
                if stage.status in ("pending", "running"):
                    stage.status = "completed"
                    stage.progress = 100

    def fail_task(self, task_id: str, error: str) -> None:
        """标记任务失败"""
        with self._lock:
            task = self._tasks.get(task_id)
            if not task:
                return

            task.status = "failed"
            task.error = error
            task.finished_at = datetime.utcnow()
            task.message = f"任务失败：{error}"
            if task.started_at:
                task.total_time_seconds = round(
                    (task.finished_at - task.started_at).total_seconds(), 2,
                )

    # ============================================================
    # 内部工具
    # ============================================================

    def _recalc_progress(self, task: Task) -> None:
        """根据各阶段状态重新计算整体进度"""
        if not task.stages:
            return

        # 每个阶段权重相等
        stage_weight = 100.0 / len(task.stages)
        total = 0.0

        for stage in task.stages:
            if stage.status == "completed":
                total += stage_weight * 100 / 100
            elif stage.status == "running":
                total += stage_weight * (stage.progress / 100.0)
            elif stage.status == "failed":
                total += 0
            # pending 不计入

        task.progress = int(min(100, max(0, total)))


# 全局单例
_task_manager = TaskManager()


def get_task_manager() -> TaskManager:
    """获取全局 TaskManager 单例"""
    return _task_manager
