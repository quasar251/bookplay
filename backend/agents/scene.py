"""SceneAgent — 场景生成 Agent

基于 BookSkeleton 中的概念列表，逐个生成"学→练→用→卡牌"完整游戏场景。
是分层提取策略的第 3 层（概念 → 场景）。

输入: chapters (来自 BookSkeleton) + core_theme
输出: { "scenes": [GameScene, ...], "scene_count": N }
"""

from typing import Any, Dict, List

from agents.base import BaseAgent
from models.schemas import GameScene
from prompts.scene import SYSTEM_PROMPT


class SceneAgent(BaseAgent):
    """场景生成 Agent —— 将概念转化为沉浸式游戏场景

    职责：
        - 接收上游提取的章节与概念
        - 为每个核心概念生成一个完整 GameScene
        - 返回场景列表供 NarratorAgent 聚合

    使用方式：
        >>> agent = SceneAgent()
        >>> result = await agent.run({
        ...     "chapters": [...],
        ...     "core_theme": "习惯养成",
        ... })
        >>> len(result.result["scenes"])
    """

    name: str = "scene"
    description: str = "将核心概念转化为学→练→用→卡牌游戏场景"

    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行场景生成

        从 input_data 中获取 chapters（来自 BookSkeleton），
        遍历每个章节的每个概念，生成对应的 GameScene。

        为了控制成本，默认只处理前 3 个概念（可配置）。

        Args:
            input_data: 包含以下键：
                - chapters (list): 章节列表，每章含 concepts
                - core_theme (str): 全书核心主题（可选，用于上下文）
                - max_scenes (int, 可选): 最多生成几个场景，默认 3

        Returns:
            { "scenes": [...], "scene_count": N, "processed_concepts": [...] }
        """
        chapters: List[Dict[str, Any]] = input_data.get("chapters", [])
        core_theme: str = input_data.get("core_theme", "")
        max_scenes: int = int(input_data.get("max_scenes", 3))

        if not chapters:
            raise ValueError("chapters is empty — SceneAgent 需要上游提供章节与概念数据")

        # 收集所有概念（带上章节信息）
        all_concepts: List[Dict[str, Any]] = []
        for ch in chapters:
            chapter_id = ch.get("id", 0)
            chapter_title = ch.get("title", "")
            for concept in ch.get("concepts", []):
                all_concepts.append({
                    **concept,
                    "chapter_id": chapter_id,
                    "chapter_title": chapter_title,
                })

        if not all_concepts:
            raise ValueError("No concepts found in chapters")

        # 限制处理数量（控制 LLM 成本）
        concepts_to_process = all_concepts[:max_scenes]

        scenes: List[Dict[str, Any]] = []
        processed_names: List[str] = []

        for concept_info in concepts_to_process:
            scene = await self._generate_single_scene(concept_info, core_theme)
            scenes.append(scene)
            processed_names.append(concept_info.get("name", ""))

        return {
            "scenes": scenes,
            "scene_count": len(scenes),
            "processed_concepts": processed_names,
        }

    async def _generate_single_scene(
        self,
        concept_info: Dict[str, Any],
        core_theme: str,
    ) -> Dict[str, Any]:
        """为单个概念生成一个 GameScene

        Args:
            concept_info: 概念数据（name, definition, keywords, source_quote, chapter_id...）
            core_theme: 全书核心主题

        Returns:
            GameScene 的 dict 形式
        """
        concept_name = concept_info.get("name", "未知概念")
        concept_def = concept_info.get("definition", "")
        concept_quote = concept_info.get("source_quote", "")
        chapter_id = concept_info.get("chapter_id", 0)
        chapter_title = concept_info.get("chapter_title", "")

        user_prompt = (
            f"请为以下核心概念生成一个完整的游戏场景：\n\n"
            f"【概念名称】{concept_name}\n"
            f"【核心定义】{concept_def}\n"
        )
        if concept_quote:
            user_prompt += f"【原文引用】{concept_quote}\n"
        if chapter_title:
            user_prompt += f"【来源章节】{chapter_title}\n"
        if core_theme:
            user_prompt += f"【全书主题】{core_theme}\n"

        user_prompt += (
            "\n请基于这个概念，设计一个让玩家能亲身经历的情境。"
            "情境要贴近真实生活，让玩家通过做选择来理解这个概念。"
        )

        raw_result = await self._call_llm(
            SYSTEM_PROMPT,
            user_prompt,
            response_model=GameScene,
        )

        # 解析失败则抛出异常
        if isinstance(raw_result, dict) and "raw" in raw_result and len(raw_result) == 1:
            raise ValueError(
                f"SceneAgent LLM JSON parse failed for concept '{concept_name}': "
                f"{str(raw_result['raw'])[:200]}"
            )

        if isinstance(raw_result, dict) and raw_result.get("success") is False:
            raise ValueError(raw_result.get("error", "Unknown LLM error"))

        # 确保 chapter_id 正确
        if isinstance(raw_result, dict) and not raw_result.get("chapter_id"):
            raw_result["chapter_id"] = chapter_id

        return raw_result
