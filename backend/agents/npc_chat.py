"""NpcChatAgent —— 角色化 NPC 对话（对应 PRD4 第三章 3.1 / 3.2）

处理流程（双层路由）：
    玩家输入
      ↓ 第 1 层：意图识别（规则前置 + LLM 兜底）
      ├── OUT_OF_SCOPE → 礼貌拒绝（无检索）
      ├── CHAT         → 寒暄 + 引导回书籍（无检索）
      └── BOOK/REFLECTION
              ↓ 第 2 层：RAG 检索（向量库 Top-K）
              ↓ 第 3 层：Prompt 构建（灵魂档案 + 原文 + 引用规则）
              ↓ 第 4 层：生成 + 后处理校验（validate_response，失败重试一次）

设计要点：
- 复用 BaseAgent 的 _llm（LCEL），但不注册进生成管道 Registry
  （它是运行时对话，不是离线内容生成）。
- VectorStore 依赖注入，便于单测与替换存储实现。
"""

import logging
from typing import Any, Dict, List, Optional

from agents.base import BaseAgent
from agents.npc_intent import IntentCategory, classify_by_rules
from memory.vector_store import RetrievedChunk, VectorStore
from models.schemas import AgentResult
from prompts import npc as npc_prompts

logger = logging.getLogger(__name__)


def validate_response(response: str, chunks: List[RetrievedChunk]) -> bool:
    """校验回复是否至少引用了 1 条检索到的原文（PRD4 3.5）

    实现：把每个 chunk 按中文标点切成短句片段，
    任一 ≥10 字的片段出现在回复中，即视为"引用了该书内容"。

    相比整段/头尾匹配，句子级检测更贴合真实回复
    （通常引用一句话，而非恰好覆盖原文头尾）。

    Args:
        response: NPC 生成的回复
        chunks: 检索到的原文分块

    Returns:
        True 表示命中引用，False 表示无引用（需重新生成）
    """
    if not response or not chunks:
        return False
    for chunk in chunks:
        text = (chunk.text or "").strip()
        if not text:
            continue
        for fragment in _split_sentences(text):
            if len(fragment) >= 10 and fragment in response:
                return True
    return False


def _split_sentences(text: str) -> List[str]:
    """按中文/英文标点切分为短句片段"""
    import re

    # 按句末标点切分，保留足够语义长度
    parts = re.split(r"[。！？!?；;]", text)
    return [p.strip() for p in parts if p.strip()]


class NpcChatAgent(BaseAgent):
    """NPC 对话 Agent —— 双层路由 + RAG + 引用校验"""

    name = "npc_chat"
    description = "角色化 NPC 对话（意图识别 + RAG 检索 + 引用校验）"

    def __init__(
        self,
        npc: Dict[str, Any],
        vector_store: Optional[VectorStore] = None,
    ) -> None:
        super().__init__()
        self._npc = npc
        self._vector_store = vector_store

    # ============================================================
    # 意图识别（第 1 层）
    # ============================================================

    async def _llm_classify(self, message: str) -> str:
        """LLM 三分类兜底：返回 BOOK / REFLECTION / OUT_OF_SCOPE

        分类 prompt 携带 NPC 角色与其关联书籍上下文，避免模型把
        "把书中概念用到现实（谈判/习惯/决策…）"的提问误判为越界。
        """
        npc = self._npc
        core_belief = npc.get("core_belief", "")
        persona = npc.get("persona_guide", "")
        sys_prompt = (
            "你是意图分类器。一位 NPC 导师正在陪伴玩家读书，设定如下：\n"
            f"核心信念：{core_belief}\n"
            f"身份与所读之书：{persona}\n\n"
            "把玩家的输入分类为以下三种之一：\n"
            "BOOK: 询问书中概念/内容/观点，或想借用书中知识应对现实场景"
            "（如谈判、习惯养成、决策等）\n"
            "REFLECTION: 分享个人经历、感受，希望被倾听、被共情\n"
            "OUT_OF_SCOPE: 与这本书及其领域完全无关的话题"
            "（如天气、写代码、点外卖、时事新闻）\n\n"
            "只输出一个单词（BOOK / REFLECTION / OUT_OF_SCOPE），不要解释。"
        )
        try:
            text = await self._llm.invoke_text(sys_prompt, message)
            raw = text.strip().upper()
            # 容错：可能输出多余内容，取第一个合法词
            for token in raw.replace("\n", " ").split():
                if token in ("BOOK", "REFLECTION", "OUT_OF_SCOPE"):
                    return token
            return IntentCategory.BOOK.value
        except Exception as e:  # LLM 不可用时保守回退
            logger.warning("LLM classify failed, fallback BOOK: %s", e)
            return IntentCategory.BOOK.value

    async def _classify(self, message: str) -> IntentCategory:
        """规则前置（async 组合）+ LLM 兜底"""
        rule_hit = classify_by_rules(message)
        if rule_hit is not None:
            return rule_hit
        # 规则未命中 → LLM 三分类兜底
        raw = await self._llm_classify(message)
        try:
            return IntentCategory(raw)
        except ValueError:
            logger.warning("unknown intent %r, fallback BOOK", raw)
            return IntentCategory.BOOK

    # ============================================================
    # 主流程
    # ============================================================

    async def execute(self, input_data: Dict[str, Any]) -> Any:
        """执行一轮 NPC 对话

        Args:
            input_data:
                - message: 玩家输入
                - book_id: 书籍标识（RAG 检索范围）
                - npc: NPC 灵魂档案（dict，含 name/core_belief/tone/persona_guide）
                - top_k: 检索数量（默认 3）
                - min_score: 检索阈值（默认 0.75，可下调以便演示）
                - allow_free_talk: 无原文时是否允许人设自由作答

        Returns:
            AgentResult.result 为 dict：
                - intent: 识别出的意图
                - reply: NPC 回复
                - citations: 引用到的原文分块列表
                - has_reference: 是否通过引用校验
        """
        message = (input_data.get("message") or "").strip()
        book_id = input_data.get("book_id", "")
        top_k = int(input_data.get("top_k", 3))
        # 演示环境常设较低阈值（哈希向量相似度偏低）
        min_score = float(input_data.get("min_score", 0.0))
        allow_free_talk = bool(input_data.get("allow_free_talk", False))

        if not message:
            raise ValueError("message is required")
        if self._vector_store is None:
            raise ValueError("vector_store is not initialized")

        intent = await self._classify(message)
        reply, citations, has_reference = await self._route(
            message=message,
            intent=intent,
            book_id=book_id,
            top_k=top_k,
            min_score=min_score,
            allow_free_talk=allow_free_talk,
        )

        return {
            "intent": intent.value,
            "reply": reply,
            "citations": [c.to_dict() for c in citations],
            "has_reference": has_reference,
            "free_talk": has_reference is False
            and intent in (IntentCategory.BOOK, IntentCategory.REFLECTION)
            and not citations
            and allow_free_talk,
        }

    # ============================================================
    # 路由（第 2 层）
    # ============================================================

    async def _route(
        self,
        message: str,
        intent: IntentCategory,
        book_id: str,
        top_k: int,
        min_score: float,
        allow_free_talk: bool = False,
    ) -> tuple[str, List[RetrievedChunk], bool]:
        """按意图路由：无检索模板 vs RAG + LLM + 引用校验"""
        # OUT_OF_SCOPE / CHAT：不检索，直接模板回复
        if intent == IntentCategory.OUT_OF_SCOPE:
            return npc_prompts.OUT_OF_SCOPE_REPLY, [], False

        if intent == IntentCategory.CHAT:
            return npc_prompts.CHAT_REPLY, [], False

        # BOOK / REFLECTION：RAG 检索
        try:
            chunks = self._vector_store.search(
                message, book_id=book_id, top_k=top_k, min_score=min_score,
            )
        except Exception as e:
            logger.error("RAG search failed: %s", e)
            if allow_free_talk:
                return await self._generate_free_talk(message, intent), [], False
            return "检索出错了，请稍后再试。", [], False

        if not chunks:
            if allow_free_talk:
                return await self._generate_free_talk(message, intent), [], False
            return (
                "抱歉，我目前还没有这本书的相关原文记录，"
                "暂时无法回答这个问题。", [], False,
            )

        reply = await self._generate_with_citation(
            message=message,
            intent=intent,
            chunks=chunks,
        )
        has_reference = validate_response(reply, chunks)
        return reply, chunks, has_reference

    async def _generate_free_talk(
        self,
        message: str,
        intent: IntentCategory,
    ) -> str:
        """无检索原文时，以 NPC 人设知识自由作答（不编造引用）

        适合书库尚未收录原文、但 NPC 对相关领域有真实积累的场景。

        Args:
            message: 玩家输入
            intent: 意图类别（BOOK / REFLECTION）

        Returns:
            回复文本
        """
        npc = self._npc
        core_belief = npc.get("core_belief", "")
        tone = npc.get("tone", "专业且亲切")
        persona = npc.get("persona_guide", "")
        system_prompt = (
            f"你正在扮演「{npc.get('name', 'NPC')}」，一位书籍 NPC 导师。\n"
            f"核心信念：{core_belief}\n"
            f"语气风格：{tone}\n"
            f"立场与价值观：{persona}\n\n"
            f"【本次限制】当前没有可引用的原文片段。"
            f"请你基于自己对这个领域/这本书的真实了解，用自己的话作答；\n"
            f"不得编造具体的原文引语。回答简洁（不超过 180 字）。"
        )
        if intent == IntentCategory.REFLECTION:
            user_prompt = (
                f"玩家分享了一段个人经历/感受：\n「{message}」\n"
                f"请先表达理解，再把 ta 的经历与你的观点联系起来，给出 1 个可行动建议。"
            )
        else:
            user_prompt = f"玩家提问：\n「{message}」\n请结合你对这个领域的了解作答。"
        return await self._call_text(system_prompt, user_prompt)

    # ============================================================
    # 生成 + 引用校验（第 3/4 层）
    # ============================================================

    async def _generate_with_citation(
        self,
        message: str,
        intent: IntentCategory,
        chunks: List[RetrievedChunk],
    ) -> str:
        """构建 prompt → LLM 生成 → 校验引用；失败则强化约束重试一次"""
        system_prompt = npc_prompts.build_system_prompt(self._npc)
        user_prompt = npc_prompts.build_book_prompt(
            message,
            chunks=[c.to_dict() for c in chunks],
            reflection_hint=(intent == IntentCategory.REFLECTION),
        )

        reply = await self._call_text(system_prompt, user_prompt)

        # 引用校验
        if validate_response(reply, chunks):
            return reply

        # 重试一次：强化"必须引用"约束
        retry_prompt = (
            f"{user_prompt}\n\n"
            f"你上一轮的回答没有引用任何原文。"
            f"请务必引用【检索到的原文】中的至少一句话（用「原文：」标注），"
            f"再围绕它展开解释。"
        )
        logger.info("NPC reply failed citation check, retrying once…")
        return await self._call_text(system_prompt, retry_prompt)

    async def _call_text(self, system_prompt: str, user_prompt: str) -> str:
        """调用 LLM 返回纯文本（不经过 JSON 解析）"""
        return await self._llm.invoke_text(system_prompt, user_prompt)
