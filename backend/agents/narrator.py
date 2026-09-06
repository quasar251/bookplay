"""NarratorAgent — 聚合编织 Agent

把书籍骨架（BookSkeleton）和场景列表（scenes）编织成一个
有叙事节奏、有钩子机制的完整游戏内容。

是分层提取策略的第 4 层（聚合 → 完整游戏 JSON）。

输入: core_theme + chapters + scenes + book_title
输出: 完整游戏内容 dict（含叙事钩子、章节编排、全部卡牌、身份标签）
"""

from typing import Any, Dict, List

from agents.base import BaseAgent
from prompts.narrator import SYSTEM_PROMPT


class NarratorAgent(BaseAgent):
    """叙事编排 Agent —— 将分散的场景编织成完整游戏体验

    职责：
        - 接收上游的骨架 + 场景
        - 重新编排章节与场景顺序
        - 添加章节钩子（悬念）
        - 汇总所有卡牌与身份标签
        - 输出完整的游戏内容 JSON

    使用方式：
        >>> agent = NarratorAgent()
        >>> result = await agent.run({
        ...     "core_theme": "习惯养成",
        ...     "chapters": [...],
        ...     "scenes": [...],
        ...     "book_title": "原子习惯",
        ... })
    """

    name: str = "narrator"
    description: str = "将概念与场景编织成有叙事节奏的完整游戏"

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行聚合编织

        Args:
            input_data: 包含以下键：
                - core_theme (str): 全书核心主题
                - chapters (list): 章节列表（BookSkeleton.chapters）
                - scenes (list): 场景列表（SceneAgent 输出）
                - book_title (str, 可选): 书籍标题
                - book_type (str, 可选): non_fiction / fiction

        Returns:
            完整游戏内容 dict，结构参见 prompts/narrator.py
        """
        core_theme: str = input_data.get("core_theme", "")
        chapters: List[Dict[str, Any]] = input_data.get("chapters", [])
        scenes: List[Dict[str, Any]] = input_data.get("scenes", [])
        book_title: str = input_data.get("book_title", "")
        book_type: str = input_data.get("book_type", "non_fiction")

        if not scenes:
            raise ValueError("scenes is empty — NarratorAgent 需要上游提供场景数据")

        if not core_theme:
            raise ValueError("core_theme is required")

        # 组装提示词
        user_prompt = (
            f"请将以下书籍骨架与场景编织成一个完整的游戏体验：\n\n"
            f"【书籍标题】{book_title or '未命名书籍'}\n"
            f"【书籍类型】{book_type}\n"
            f"【核心主题】{core_theme}\n\n"
            f"【章节骨架】\n"
        )

        for ch in chapters:
            user_prompt += (
                f"- 第{ch.get('id', '?')}章 {ch.get('title', '')}: "
                f"{ch.get('summary', '')}\n"
            )
            for concept in ch.get("concepts", []):
                user_prompt += f"  · 概念: {concept.get('name', '')}\n"

        user_prompt += f"\n【已生成的场景】（共 {len(scenes)} 个）\n"
        for i, scene in enumerate(scenes):
            user_prompt += (
                f"\n场景 {i + 1}：{scene.get('concept_name', '未知概念')}\n"
                f"  - 认知卡：{scene.get('learning', {}).get('key_idea', '')}\n"
                f"  - 情境：{scene.get('scenario', {}).get('title', '')}\n"
                f"  - 卡牌：{scene.get('card', {}).get('name', '')}\n"
            )

        user_prompt += (
            "\n请把这些素材编排成一个有节奏、有钩子的完整游戏。"
            "你可以重新排列章节与场景顺序（如果需要），"
            "为每章添加结尾钩子，汇总所有卡牌，提炼身份标签。"
        )

        raw_result = await self._call_llm(SYSTEM_PROMPT, user_prompt)

        # 解析失败则抛出
        if isinstance(raw_result, dict) and "raw" in raw_result and len(raw_result) == 1:
            raise ValueError(
                f"NarratorAgent LLM JSON parse failed: {str(raw_result['raw'])[:200]}"
            )

        if isinstance(raw_result, dict) and raw_result.get("success") is False:
            raise ValueError(raw_result.get("error", "Unknown LLM error"))

        # 补充一些统计字段
        if isinstance(raw_result, dict):
            raw_result.setdefault("book_type", book_type)
            if book_title and not raw_result.get("book_title"):
                raw_result["book_title"] = book_title
            if not raw_result.get("core_theme"):
                raw_result["core_theme"] = core_theme

        return raw_result
