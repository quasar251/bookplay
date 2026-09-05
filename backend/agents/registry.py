"""Agent 注册中心

统一管理所有 Agent 的注册、注销与获取。
支持动态扩展 —— 新增 Agent 只需在此处注册。
"""

from typing import Any, Dict, List, Type

from agents.base import BaseAgent


class Registry:
    """Agent 注册中心 —— Phase 0 核心组件之一

    职责：
        - 管理所有已注册的 Agent（name → instance）
        - 提供类型安全的 Agent 查找
        - 导出当前可用 Agent 列表（用于 API 文档 / 监控）

    使用方式：
        >>> reg = Registry()
        >>> reg.register(ExtractAgent())
        >>> reg.register(SceneAgent())
        >>> agent = reg.get("extract")
        >>> print(agent.name)   # "extract"
    """

    def __init__(self) -> None:
        self._agents: Dict[str, BaseAgent] = {}
        self._auto_register()

    def _auto_register(self) -> None:
        """自动注册内置 Agent（Phase 0）"""
        # 延迟导入避免循环依赖
        from agents.extract import ExtractAgent  # noqa: F811
        
        instances: List[BaseAgent] = [ExtractAgent()]
        for instance in instances:
            self.register(instance)

    def register(self, agent: BaseAgent) -> None:
        """注册一个 Agent

        Args:
            agent: 实现了 BaseAgent 接口的实例

        Raises:
            ValueError: 如果已有同名 Agent
        """
        if agent.name in self._agents:
            raise ValueError(f"Agent '{agent.name}' already registered")
        self._agents[agent.name] = agent

    def unregister(self, name: str) -> bool:
        """注销一个 Agent

        Args:
            name: Agent 名称

        Returns:
            True 如果成功注销，False 如果不存在
        """
        return self._agents.pop(name, None) is not None

    def get(self, name: str) -> BaseAgent:
        """获取已注册的 Agent

        Args:
            name: Agent 名称

        Returns:
            BaseAgent 实例

        Raises:
            KeyError: 如果 Agent 不存在
        """
        agent = self._agents.get(name)
        if agent is None:
            raise KeyError(f"Agent '{name}' not found. Available: {list(self._agents.keys())}")
        return agent

    def list_agents(self) -> List[Dict[str, Any]]:
        """列出所有已注册的 Agent（序列化）

        Returns:
            Agent 元信息列表
        """
        return [a.to_dict() for a in self._agents.values()]

    def has(self, name: str) -> bool:
        """检查 Agent 是否已注册"""
        return name in self._agents
