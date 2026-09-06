"""Orchestrator — 顺序编排器

按注册顺序依次执行 Agent，将输出作为输入传递给下一个 Agent。
支持：
- 自动发现并排序内置 Agent
- 错误中断（某个 Agent 失败则停止）
- 结果汇总（返回 OrchestratorResult）
"""

import time
from typing import Any, Dict, List, Optional, Tuple

from agents.base import BaseAgent
from agents.registry import Registry
from models.schemas import AgentResult, ExecutionStage, OrchestratorResult


class OrchestratorError(Exception):
    """编排器运行时错误"""


class Orchestrator:
    """顺序编排器 —— Phase 0 核心组件之一

    职责：
        - 从 Registry 获取所有已注册的 Agent
        - 按顺序执行每个 Agent
        - 将上一个 Agent 的输出注入到下一个 Agent 的输入
        - 返回完整执行链路的结果（OrchestratorResult）

    使用方式：
        >>> reg = Registry()
        >>> orch = Orchestrator(reg)
        >>> result = await orch.run({"book_text": "..."})
        >>> result.success
        True
    """

    def __init__(self, registry: Registry) -> None:
        self._registry = registry
        self._exec_log: List[Dict[str, Any]] = []

    @property
    def log(self) -> List[Dict[str, Any]]:
        """获取执行日志（简化版，用于 API 元数据）"""
        return self._exec_log.copy()

    # ============================================================
    # 输入准备
    # ============================================================

    def _prepare_input(
        self,
        initial_input: Dict[str, Any],
        previous_result: Optional[AgentResult],
    ) -> Dict[str, Any]:
        """为 Agent 准备输入数据

        将上一个 Agent 的成功结果合并到初始输入中，
        让下一个 Agent 能拿到上游的数据。

        Args:
            initial_input: 用户提供的初始输入
            previous_result: 前一个 Agent 的执行结果

        Returns:
            合并后的输入字典
        """
        if previous_result is None:
            return initial_input.copy()

        merged = initial_input.copy()

        if previous_result.success and previous_result.result is not None:
            result = previous_result.result
            if isinstance(result, dict):
                merged.update(result)
            elif isinstance(result, str):
                merged["_last_raw"] = result
        else:
            # 上一个失败，传递错误信息给下一个 Agent
            merged["previous_error"] = previous_result.error or "Unknown error"

        return merged

    # ============================================================
    # 主流程
    # ============================================================

    async def run(
        self,
        input_data: Dict[str, Any],
        agent_order: Optional[List[str]] = None,
    ) -> OrchestratorResult:
        """按序执行所有 Agent

        数据在各 Agent 间累积传递：
        第 N 个 Agent 的输入 = 初始输入 + 前 N-1 个 Agent 的所有输出（后者覆盖前者）

        Args:
            input_data: 初始输入数据
            agent_order: 指定执行的 Agent 名称序列（None 则使用默认注册顺序）

        Returns:
            OrchestratorResult: 完整的执行结果，包含各阶段详情

        Raises:
            OrchestratorError: 当没有可执行的 Agent 时
        """
        start_time = time.time()
        self._exec_log.clear()

        # 获取待执行的 Agent 列表
        agents: List[Tuple[str, BaseAgent]] = self._resolve_agents(agent_order)
        if not agents:
            raise OrchestratorError("No agents registered")

        # 累积上下文：初始输入 + 各 Agent 输出逐步合并
        context: Dict[str, Any] = input_data.copy()
        stages: List[ExecutionStage] = []
        last_result: Optional[AgentResult] = None

        for stage_idx, (agent_name, agent) in enumerate(agents):
            stage = await self._execute_stage(
                agent_name, agent, context, stage_idx,
            )
            stages.append(stage)

            # 记录简化日志
            self._exec_log.append({
                "stage": stage.stage,
                "agent": stage.agent,
                "status": stage.status,
                "duration_ms": stage.duration_ms,
            })

            # 如果当前 Agent 失败，停止执行
            if stage.result is None or not stage.result.success:
                break

            # 将当前 Agent 输出合并到上下文（供下游使用）
            if stage.result.result and isinstance(stage.result.result, dict):
                context.update(stage.result.result)

            last_result = stage.result

        total_time = time.time() - start_time

        return OrchestratorResult(
            success=last_result is not None and last_result.success if last_result else False,
            stages=stages,
            final_result=last_result.result if last_result and last_result.success else None,
            total_time_seconds=round(total_time, 2),
            execution_log=self._exec_log.copy(),
        )

    # ============================================================
    # 内部辅助
    # ============================================================

    def _resolve_agents(
        self, agent_order: Optional[List[str]]
    ) -> List[Tuple[str, BaseAgent]]:
        """解析要执行的 Agent 列表"""
        if agent_order:
            result: List[Tuple[str, BaseAgent]] = []
            for name in agent_order:
                try:
                    agent = self._registry.get(name)
                    result.append((name, agent))
                except KeyError as e:
                    raise OrchestratorError(
                        f"Requested Agent '{name}' not found in Registry"
                    ) from e
            return result

        # 默认按注册顺序
        return list(self._registry._agents.items())

    async def _execute_stage(
        self,
        agent_name: str,
        agent: BaseAgent,
        input_data: Dict[str, Any],
        stage_index: int,
    ) -> ExecutionStage:
        """执行单个 Agent 阶段"""
        stage_start = time.time()

        try:
            result: AgentResult = await agent.run(input_data)
            duration = time.time() - stage_start

            return ExecutionStage(
                stage=stage_index + 1,
                agent=agent_name,
                status="completed" if result.success else "failed",
                duration_ms=round(duration * 1000, 1),
                input_keys=list(input_data.keys()),
                result=result,
            )

        except Exception as e:
            duration = time.time() - stage_start
            return ExecutionStage(
                stage=stage_index + 1,
                agent=agent_name,
                status="failed",
                duration_ms=round(duration * 1000, 1),
                input_keys=list(input_data.keys()),
                result=AgentResult(
                    success=False,
                    result=None,
                    error=f"Agent runtime error: {e}",
                ),
            )

    def get_execution_summary(self) -> Dict[str, Any]:
        """获取本次编排的执行摘要（简化版）"""
        return {
            "total_stages": len(self._exec_log),
            "stages": self._exec_log,
        }
