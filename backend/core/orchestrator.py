"""Orchestrator — 顺序编排器

按注册顺序依次执行 Agent，将输出作为输入传递给下一个 Agent。
支持：
- 自动发现并排序内置 Agent
- 错误中断（某个 Agent 失败则停止）
- 结果汇总
"""

import asyncio
import time
from typing import Any, Dict, List, Optional, Tuple

from agents.base import BaseAgent
from agents.registry import Registry


class OrchestratorError(Exception):
    """编排器运行时错误"""


class Orchestrator:
    """顺序编排器 —— Phase 0 核心组件之一

    职责：
        - 从 Registry 获取所有已注册的 Agent
        - 按顺序执行每个 Agent
        - 将上一个 Agent 的输出注入到下一个 Agent 的输入
        - 返回完整执行链路的结果

    使用方式：
        >>> reg = Registry()
        >>> orch = Orchestrator(reg)
        >>> result = await orch.run(book_text="...")
    """

    def __init__(self, registry: Registry) -> None:
        self._registry = registry
        self._exec_log: List[Dict[str, Any]] = []

    @property
    def log(self) -> List[Dict[str, Any]]:
        """获取执行日志"""
        return self._exec_log.copy()

    def _prepare_input(
        self,
        initial_input: Dict[str, Any],
        previous_output: Optional[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """为 Agent 准备输入数据
        
        Args:
            initial_input: 用户提供的初始输入
            previous_output: 前一个 Agent 的输出
        
        Returns:
            合并后的输入字典
        """
        if previous_output is None:
            return initial_input.copy()
        
        # 如果上一个 Agent 成功且返回了 result，将其合并到输入中
        merged = initial_input.copy()
        if previous_output.get("success"):
            result = previous_output.get("result")
            if isinstance(result, dict):
                merged.update(result)
            elif isinstance(result, str):
                merged["_last_raw"] = result
        else:
            # 上一个失败，传递错误信息给下一个 Agent
            merged["previous_error"] = previous_output.get("error", "Unknown error")
        
        return merged

    async def run(
        self,
        input_data: Dict[str, Any],
        agent_order: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """按序执行所有 Agent

        Args:
            input_data: 初始输入数据
            agent_order: 指定执行的 Agent 名称序列（可选，None 则使用默认注册顺序）
        
        Returns:
            {
                "success": bool,
                "stages": [各阶段结果],
                "final_result": 最后一个 Agent 的输出,
                "total_time_seconds": float,
            }
        
        Raises:
            OrchestratorError: 当没有可执行的 Agent 时
        """
        start_time = time.time()
        self._exec_log.clear()

        # 获取待执行的 Agent 列表
        if agent_order:
            agents: List[Tuple[str, BaseAgent]] = []
            for name in agent_order:
                try:
                    agent = self._registry.get(name)
                    agents.append((name, agent))
                except KeyError:
                    raise OrchestratorError(f"Requested Agent '{name}' not found in Registry")
        else:
            agents = [(name, agent) for name, agent in self._registry._agents.items()]

        if not agents:
            raise OrchestratorError("No agents registered")

        current_input = input_data
        stages: List[Dict[str, Any]] = []
        final_result: Optional[Dict[str, Any]] = None

        for stage_idx, (agent_name, agent) in enumerate(agents):
            stage_result = await self._execute_stage(
                agent_name, agent, current_input, stage_idx,
            )
            stages.append(stage_result)
            
            # 记录日志
            self._exec_log.append({
                "stage": stage_idx + 1,
                "agent": agent_name,
                "status": stage_result["status"],
                "duration_ms": round(stage_result["duration_ms"], 1),
            })

            # 如果当前 Agent 失败，停止执行
            if not stage_result["result"].get("success"):
                break

            # 将当前 Agent 输出作为下一阶段的输入
            current_input = self._prepare_input(input_data, stage_result["result"])
            final_result = stage_result["result"]

        total_time = time.time() - start_time

        return {
            "success": final_result is not None and final_result.get("success"),
            "stages": stages,
            "final_result": final_result,
            "total_time_seconds": round(total_time, 2),
        }

    async def _execute_stage(
        self,
        agent_name: str,
        agent: BaseAgent,
        input_data: Dict[str, Any],
        stage_number: int,
    ) -> Dict[str, Any]:
        """执行单个 Agent 阶段"""
        stage_start = time.time()

        try:
            result = await agent.run(input_data)
            duration = time.time() - stage_start

            return {
                "stage": stage_number + 1,
                "agent": agent_name,
                "input_keys": list(input_data.keys()),
                "result": result,
                "status": "completed",
                "duration_ms": round(duration * 1000, 1),
            }

        except Exception as e:
            duration = time.time() - stage_start
            return {
                "stage": stage_number + 1,
                "agent": agent_name,
                "input_keys": list(input_data.keys()),
                "result": {
                    "success": False,
                    "result": None,
                    "error": f"Agent runtime error: {e}",
                },
                "status": "failed",
                "duration_ms": round(duration * 1000, 1),
            }

    def get_execution_summary(self) -> Dict[str, Any]:
        """获取本次编排的执行摘要"""
        return {
            "total_stages": len(self._exec_log),
            "stages": self._exec_log,
        }
