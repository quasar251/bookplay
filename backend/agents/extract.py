"""ExtractAgent — 书籍骨架提取 Agent

从书籍原文中提取：核心主题、章节列表、核心概念、主要论点

输入: book_text（全书文本或摘要）
输出: core_theme + chapters + main_arguments（JSON）
"""

from typing import Any, Dict

from agents.base import BaseAgent

from prompts.extract import SYSTEM_PROMPT


class ExtractAgent(BaseAgent):
    """书籍骨架提取 Agent —— Phase 0 第一个可插拔 Agent

    职责：
        - 接收书籍全文或摘要
        - 调用 LLM 提取核心概念骨架
        - 返回结构化的章节/概念/论点数据

    使用方式：
        >>> agent = ExtractAgent()
        >>> result = await agent.run({"book_text": "全书内容..."})
    """

    name: str = "extract"
    description: str = "从书籍原文中提取核心概念骨架"

    async def run(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行骨架提取

        Args:
            input_data: 包含以下键：
                - book_text (str): 书籍全文或摘要

        Returns:
            Dict[str, Any]: 骨架数据（core_theme / chapters / main_arguments）
                           如果失败则包含 error 键
        """
        book_text: str = input_data.get("book_text", "")
        
        if not book_text or len(book_text.strip()) < 100:
            return {
                "success": False,
                "result": None,
                "error": "book_text is too short (minimum 100 chars)",
            }

        # 超长文本截断提示（避免超出上下文窗口）
        truncated: bool = False
        max_length: int = 8000
        if len(book_text) > max_length:
            book_text = book_text[:max_length]
            truncated = True

        user_prompt: str = f"请为以下书籍提取概念骨架：\n\n{book_text}"
        if truncated:
            user_prompt += "\n\n[注意：此为截断版本，请基于可用内容推断完整框架]"

        raw_result = await self._call_llm(SYSTEM_PROMPT, user_prompt)

        # 结构化结果
        if isinstance(raw_result, dict) and "raw" in raw_result:
            return {
                "success": False,
                "result": raw_result.get("raw"),
                "error": "LLM returned non-JSON text",
            }

        return {
            "success": True,
            "result": raw_result,
        }
