"""ExtractAgent — 书籍骨架提取 Agent

从书籍原文中提取：核心主题、章节列表、核心概念、主要论点

输入: book_text（全书文本或摘要）
输出: BookSkeleton（core_theme + chapters + main_arguments）
"""

from typing import Any, Dict

from agents.base import BaseAgent
from models.schemas import BookSkeleton
from prompts.extract import SYSTEM_PROMPT


class ExtractAgent(BaseAgent):
    """书籍骨架提取 Agent —— Phase 0 第一个可插拔 Agent

    职责：
        - 接收书籍全文或摘要
        - 调用 LLM 提取核心概念骨架
        - 返回结构化的 BookSkeleton 数据

    使用方式：
        >>> agent = ExtractAgent()
        >>> result = await agent.run({"book_text": "全书内容..."})
        >>> result.result["core_theme"]
    """

    name: str = "extract"
    description: str = "从书籍原文中提取核心概念骨架"

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行骨架提取

        Args:
            input_data: 包含以下键：
                - book_text (str): 书籍全文或摘要
                - book_title (str, 可选): 书籍标题

        Returns:
            BookSkeleton 的 dict 形式（core_theme / chapters / main_arguments / total_concepts）
            失败时抛出异常（由 BaseAgent.run 捕获）
        """
        book_text: str = input_data.get("book_text", "")

        if not book_text or len(book_text.strip()) < 100:
            raise ValueError("book_text is too short (minimum 100 chars)")

        # 超长文本截断（避免超出上下文窗口）
        truncated: bool = False
        max_length: int = 8000
        display_text = book_text
        if len(display_text) > max_length:
            display_text = display_text[:max_length]
            truncated = True

        book_title = input_data.get("book_title", "")
        user_prompt: str = f"请为以下书籍提取概念骨架"
        if book_title:
            user_prompt += f"（《{book_title}》）"
        user_prompt += f"：\n\n{display_text}"
        if truncated:
            user_prompt += "\n\n[注意：此为截断版本，请基于可用内容推断完整框架]"

        raw_result = await self._call_llm(
            SYSTEM_PROMPT,
            user_prompt,
            response_model=BookSkeleton,
        )

        # 如果返回了 raw（说明解析失败），抛出异常让上层处理
        if isinstance(raw_result, dict) and "raw" in raw_result and len(raw_result) == 1:
            raise ValueError(f"LLM returned non-JSON text: {raw_result['raw'][:200]}")

        # 如果 LLM 重试耗尽（带 success=False 的错误结构）
        if isinstance(raw_result, dict) and raw_result.get("success") is False:
            raise ValueError(raw_result.get("error", "Unknown LLM error"))

        # 补充 total_concepts 计算
        if isinstance(raw_result, dict) and "chapters" in raw_result:
            total = sum(
                len(ch.get("concepts", [])) for ch in raw_result["chapters"]
            )
            raw_result["total_concepts"] = total

        return raw_result
