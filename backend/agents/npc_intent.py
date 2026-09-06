"""NPC 意图识别模块 —— 对应 PRD4 第三章 3.3 / 3.4

双层识别：
    第 1 层（规则前置，零成本）：关键词命中 OUT_OF_SCOPE / CHAT
    第 2 层（LLM 兜底）：其余输入交给分类函数 → BOOK / REFLECTION / OUT_OF_SCOPE

设计要点：
- 纯函数、无 IO，便于单测
- classify_intent 的 llm_fallback 可注入，测试时无需真实 LLM
"""

import enum
from typing import Callable, Optional

# ============================================================
# 意图类别（PRD4 3.3）
# ============================================================


class IntentCategory(str, enum.Enum):
    BOOK = "BOOK"
    REFLECTION = "REFLECTION"
    CHAT = "CHAT"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"

    def __str__(self) -> str:
        return self.value


# ============================================================
# 规则关键词（PRD4 3.4 示例）
# ============================================================

# 与书籍内容无关的话题 → 直接礼貌拒绝
OUT_OF_SCOPE_KEYWORDS = [
    "天气", "写代码", "帮我做", "生成", "新闻", "今天吃什么",
    "股票", "游戏推荐", "讲个笑话",
]

# 日常寒暄 → 简短回应后引导回书籍
CHAT_KEYWORDS = ["你好", "嗨", "hello", "hi", "在吗", "早上好", "晚上好"]


# ============================================================
# 识别函数
# ============================================================


def classify_by_rules(message: str) -> Optional[IntentCategory]:
    """仅用规则前置判断（零成本，不发 LLM）

    Returns:
        命中规则 → IntentCategory；未命中 → None（需 LLM 兜底）
    """
    text = (message or "").strip().lower()
    if not text:
        return None

    # 规则 1：OUT_OF_SCOPE 优先（最保守，避免误答跑题）
    if any(kw in text for kw in OUT_OF_SCOPE_KEYWORDS):
        return IntentCategory.OUT_OF_SCOPE

    # 规则 2：短问候
    if any(kw in text for kw in CHAT_KEYWORDS):
        return IntentCategory.CHAT

    return None


def classify_intent(
    message: str,
    llm_fallback: Optional[Callable[[str], str]] = None,
) -> IntentCategory:
    """意图识别：规则前置，未命中时走 LLM 兜底

    Args:
        message: 玩家输入
        llm_fallback: 可选的**同步** LLM 三分类函数，返回字符串类别；
            注入后规则未命中时会调用它。测试时可不传（返回未命中默认）。

    Returns:
        IntentCategory 枚举

    Raises:
        ValueError: llm_fallback 返回了未知类别
    """
    rule_hit = classify_by_rules(message)
    if rule_hit is not None:
        return rule_hit

    # 规则未命中：LLM 兜底分类（BOOK / REFLECTION / OUT_OF_SCOPE）
    if llm_fallback is not None:
        raw = (llm_fallback(message) or "").strip().upper()
        try:
            return IntentCategory(raw)
        except ValueError:
            raise ValueError(
                f"LLM 分类返回未知类别: {raw!r}，"
                f"可选: {[c.value for c in IntentCategory]}",
            )

    # 无兜底时的保守默认：当作 BOOK 处理（宁可信是书内问题）
    return IntentCategory.BOOK
