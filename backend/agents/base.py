"""BaseAgent — Agent 抽象基类

定义所有 Agent 的统一接口，支持：
- 注册/注销机制（通过 Registry）
- 输入输出数据模型校验（Pydantic）
- 重试与超时控制
- 结构化输出解析
"""

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from config.settings import settings
from models.schemas import AgentMeta, AgentResult


class BaseAgent(ABC):
    """Agent 基类 —— 所有具体 Agent 必须继承此类

    子类只需实现 `execute()` 方法（业务逻辑），
    而 `run()` 负责统一的错误处理与结果封装。
    """

    # Agent 元信息（子类可覆盖）
    name: str = "base_agent"
    description: str = "基础 Agent 模板"

    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

    # ============================================================
    # 对外接口
    # ============================================================

    async def run(self, input_data: Dict[str, Any]) -> AgentResult:
        """执行 Agent（对外统一入口）

        负责统一错误处理与结果封装，子类不应覆盖此方法，
        而应实现 `execute()`。

        Args:
            input_data: 输入参数字典

        Returns:
            AgentResult: 统一格式的执行结果
        """
        try:
            result = await self.execute(input_data)
            # 如果子类返回的是 dict，包装成 AgentResult
            if isinstance(result, AgentResult):
                return result
            if isinstance(result, dict):
                # 兼容旧写法：直接返回 result dict
                if "success" in result:
                    return AgentResult(**result)
                return AgentResult(success=True, result=result)
            # 其他类型当作成功数据
            return AgentResult(success=True, result={"value": result})
        except Exception as e:
            return AgentResult(
                success=False,
                result=None,
                error=f"{type(e).__name__}: {e}",
            )

    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Any:
        """Agent 核心业务逻辑 —— 子类必须实现

        可以返回：
        - AgentResult（推荐，完全控制结果）
        - dict（自动包装为 success=True 的 result）
        - 其他类型（自动包装为 {"value": ...}）

        抛出的异常会被 run() 捕获并封装为失败结果。
        """
        ...

    # ============================================================
    # 工具方法
    # ============================================================

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Dict[str, Any]:
        """调用 LLM API（统一入口，含重试）

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            response_model: Pydantic 模型，用于结构化输出解析

        Returns:
            解析后的结果字典。如果指定了 response_model 且解析成功，
            返回该模型的 dict 形式；解析失败或未指定时，
            返回 {"raw": content} 或直接解析出的 JSON dict。
        """
        last_error: Optional[str] = None

        for attempt in range(1, settings.AGENT_RETRY_COUNT + 1):
            try:
                kwargs: Dict[str, Any] = {
                    "model": settings.MODEL_NAME,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": settings.MAX_TOKENS,
                    "temperature": 0.7,
                }

                if response_model:
                    kwargs["response_format"] = {"type": "json_object"}

                response = await self._client.chat.completions.create(**kwargs)

                content = response.choices[0].message.content
                if not content:
                    raise ValueError("Empty LLM response")

                # 如果指定了 Pydantic 模型，尝试结构化解析
                if response_model:
                    try:
                        data = json.loads(content)
                        parsed = response_model(**data)
                        return parsed.model_dump()
                    except (json.JSONDecodeError, ValidationError):
                        # 解析失败则返回原始文本供上层处理
                        return {"raw": content}

                # 非结构化输出，尝试 JSON 解析
                try:
                    return json.loads(content)
                except json.JSONDecodeError:
                    return {"raw": content}

            except Exception as e:
                last_error = str(e)
                print(f"[{self.name}] Attempt {attempt}/{settings.AGENT_RETRY_COUNT} failed: {e}")
                if attempt < settings.AGENT_RETRY_COUNT:
                    continue  # 简单指数退避可后续扩展

        # 所有重试耗尽
        return {
            "success": False,
            "result": None,
            "error": f"All {settings.AGENT_RETRY_COUNT} attempts failed. Last error: {last_error}",
        }

    def to_dict(self) -> Dict[str, Any]:
        """Agent 元信息序列化（用于 Registry 注册）"""
        meta = AgentMeta(
            name=self.name,
            description=self.description,
            type=type(self).__name__,
        )
        return meta.model_dump()
