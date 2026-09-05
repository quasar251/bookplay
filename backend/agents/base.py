"""BaseAgent — Agent 抽象基类

定义所有 Agent 的统一接口，支持：
- 注册/注销机制（通过 Registry）
- 输入输出数据模型校验（Pydantic）
- 重试与超时控制
- 结构化输出解析
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Type
import json

from openai import AsyncOpenAI
from pydantic import BaseModel, ValidationError

from config.settings import settings


class BaseAgent(ABC):
    """Agent 基类 —— 所有具体 Agent 必须继承此类"""

    # Agent 元信息（子类可覆盖）
    name: str = "base_agent"
    description: str = "基础 Agent 模板"
    
    def __init__(self) -> None:
        self._client = AsyncOpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )

    @abstractmethod
    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行 Agent 核心逻辑 —— 子类必须实现
        
        Args:
            input_data: 输入参数字典，由 Registry 或调用方提供
        
        Returns:
            输出结果字典，包含 keys:
              - success: bool
              - result: 实际结果数据
              - error: 错误信息（失败时）
        """
        ...

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Optional[Type[BaseModel]] = None,
    ) -> Any:
        """调用 LLM API（统一入口，含重试）
        
        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            response_model: Pydantic 模型，用于结构化输出解析
        
        Returns:
            解析后的结果（Dict 或 BaseModel 实例）
        """
        last_error = None
        
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
        return {
            "name": self.name,
            "description": self.description,
            "type": type(self).__name__,
        }
