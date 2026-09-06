"""LLM 客户端 —— 基于 LangChain LCEL 的封装

本模块是项目中唯一直接依赖 LangChain 的层。
Agent 层通过 `get_llm_client()` 获取实例，调用：
    - invoke_text(system_prompt, user_prompt)          → 自由文本
    - invoke_structured(system, user, pydantic_model)  → Pydantic 结构化输出

实现要点：
    - LCEL 链只负责 `prompt | model`（返回 AIMessage 文本）
    - PydanticOutputParser 负责两件事：
        ① 生成 format_instructions 注入 human prompt（让 LLM 输出合法 JSON）
        ② 对 LLM 返回文本做严格解析 → Pydantic 模型
    - 重试交给 ChatOpenAI 内置 max_retries（OpenAI SDK 层）
"""

from typing import Optional, Type

from langchain_core.messages import AIMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from pydantic import BaseModel, ValidationError

from config.settings import settings


# OpenAI SDK 要求 api_key 非空；无 key 时（纯 mock 开发）用哨兵值占位，
# 真实调用会在运行时因认证失败而报错，不会在导入/构造阶段崩溃。
_PLACEHOLDER_API_KEY = "sk-not-configured"


class LLMClientError(Exception):
    """LLM 调用异常"""


class LLMClient:
    """LLM 客户端 —— LCEL 组合链封装

    使用方式：
        >>> client = get_llm_client()
        >>> text = await client.invoke_text("system", "user")
        >>> data = await client.invoke_structured("system", "user", BookSkeleton)
    """

    def __init__(self) -> None:
        api_key = settings.OPENAI_API_KEY or _PLACEHOLDER_API_KEY
        self._model = ChatOpenAI(
            model=settings.MODEL_NAME,
            api_key=api_key,
            base_url=settings.OPENAI_BASE_URL,
            temperature=0.7,
            max_tokens=settings.MAX_TOKENS,
            timeout=settings.AGENT_TIMEOUT_SECONDS,
            max_retries=settings.AGENT_RETRY_COUNT,
        )

    def _build_chain(self, system_prompt: str):
        """构建 LCEL 链：prompt | model

        Args:
            system_prompt: 系统提示词

        Returns:
            可 ainvoke 的 Runnable，输入 {"input": str}，输出 AIMessage
        """
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{input}"),
        ])
        # 组装成链：输入 dict({"input": ...}) → AIMessage
        return prompt | self._model

    async def invoke_text(
        self,
        system_prompt: str,
        user_prompt: str,
    ) -> str:
        """调用 LLM 返回自由文本

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词

        Returns:
            LLM 返回的文本内容

        Raises:
            LLMClientError: 调用失败或返回空内容
        """
        chain = self._build_chain(system_prompt)
        try:
            result = await chain.ainvoke({"input": user_prompt})
        except Exception as e:
            raise LLMClientError(
                f"LLM text call failed: {type(e).__name__}: {e}"
            ) from e

        text = self._extract_text(result)
        if not text.strip():
            raise LLMClientError("Empty LLM response")
        return text

    async def invoke_structured(
        self,
        system_prompt: str,
        user_prompt: str,
        response_model: Type[BaseModel],
    ) -> dict:
        """调用 LLM 返回结构化数据（解析为 Pydantic 模型 dict）

        Args:
            system_prompt: 系统提示词
            user_prompt: 用户提示词
            response_model: 期望的输出 Pydantic 模型

        Returns:
            解析后的 dict（response_model.model_dump()）

        Raises:
            LLMClientError: 调用失败或解析失败
        """
        parser = PydanticOutputParser(pydantic_object=response_model)

        # 将 format 指令注入 human prompt，让 LLM 严格按结构输出 JSON
        formatted_user = (
            f"{user_prompt}\n\n"
            f"【输出格式要求（必须严格遵守）】\n{parser.get_format_instructions()}"
        )

        chain = self._build_chain(system_prompt)
        try:
            result = await chain.ainvoke({"input": formatted_user})
        except Exception as e:
            raise LLMClientError(
                f"LLM structured call failed: {type(e).__name__}: {e}"
            ) from e

        text = self._extract_text(result)
        try:
            parsed = parser.parse(text)
        except ValidationError as e:
            raise LLMClientError(f"Output validation failed: {e}") from e
        except Exception as e:
            raise LLMClientError(
                f"Output parsing failed: {type(e).__name__}: {e}"
            ) from e

        if isinstance(parsed, BaseModel):
            return parsed.model_dump()
        if isinstance(parsed, dict):
            return parsed
        raise LLMClientError(f"Unexpected parse result type: {type(parsed)}")

    # ============================================================
    # 内部工具
    # ============================================================

    @staticmethod
    def _extract_text(result: object) -> str:
        """从 LCEL 链输出中提取纯文本"""
        if isinstance(result, AIMessage):
            return result.content or ""
        if isinstance(result, str):
            return result
        # 兜底：非预期的输出类型
        return str(result)


# 全局单例
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """获取全局 LLMClient 单例"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
