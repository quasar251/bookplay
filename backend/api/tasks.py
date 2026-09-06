"""任务相关 API 路由

提供异步任务的查询与管理接口：
- GET  /api/tasks          - 任务列表
- GET  /api/tasks/{task_id} - 任务详情（含进度、结果）
"""

from fastapi import APIRouter, HTTPException

from core.task_manager import get_task_manager
from models.schemas import Task, TaskListResponse


router = APIRouter(prefix="/api/tasks", tags=["tasks"])

_task_manager = get_task_manager()


@router.get("", response_model=TaskListResponse)
async def list_tasks(limit: int = 20) -> TaskListResponse:
    """获取任务列表（按创建时间倒序）

    Args:
        limit: 返回数量限制，默认 20

    Returns:
        任务列表
    """
    tasks = _task_manager.list_tasks(limit=limit)
    return TaskListResponse(total=len(tasks), tasks=tasks)


@router.get("/{task_id}", response_model=Task)
async def get_task(task_id: str) -> Task:
    """获取单个任务详情

    Args:
        task_id: 任务 ID

    Returns:
        任务详情（含状态、进度、各阶段、结果等）

    Raises:
        404: 任务不存在
    """
    task = _task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task
