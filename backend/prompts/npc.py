"""NPC 对话提示词 —— 对应 PRD4 3.2 第 3 层（Prompt 构建 + 强制引用）"""


def build_system_prompt(npc: dict) -> str:
    """基于 NPC 灵魂档案构建系统提示词

    Args:
        npc: 灵魂档案字段：
            - name: NPC 名称
            - core_belief: 核心信念（一句话）
            - tone: 语气风格说明
            - persona_guide: 立场 / 价值观说明

    Returns:
        系统提示词字符串
    """
    name = npc.get("name", "NPC")
    core_belief = npc.get("core_belief", "")
    tone = npc.get("tone", "专业且亲切")
    persona_guide = npc.get("persona_guide", "")

    return (
        f"你正在扮演「{name}」，一位书籍 NPC 导师。\n"
        f"核心信念：{core_belief}\n"
        f"语气风格：{tone}\n"
        f"立场与价值观：{persona_guide}\n"
        f"玩家正在向你请教这本书的内容。\n\n"
        f"【硬性规则】\n"
        f"1. 必须引用下方【检索到的原文】中的内容来支撑回答，\n"
        f"   引用时用「原文：」标注，至少引用 1 条；\n"
        f"2. 引用原句时用自己的话解释，不要逐字复述整段；\n"
        f"3. 保持人设语气，回答简洁（不超过 200 字）。"
    )


def build_book_prompt(message: str, chunks: list, reflection_hint: bool = False) -> str:
    """构建 BOOK / REFLECTION 类请求的用户提示词

    Args:
        message: 玩家输入
        chunks: 检索到的原文分块（RetrievedChunk 或 dict）
        reflection_hint: True 表示玩家在分享个人经历，需先共情再关联书中内容

    Returns:
        用户提示词字符串
    """
    chunk_texts = []
    for c in chunks:
        if hasattr(c, "to_dict"):
            c = c.to_dict()
        chapter = c.get("chapter") or "未知章节"
        text = c.get("text", "")
        chunk_texts.append(f"[{chapter}]\n{text}")

    retrieved_block = "\n\n".join(chunk_texts) if chunk_texts else "(无检索结果)"

    if reflection_hint:
        prompt = (
            f"玩家分享了一段个人经历/感受：\n「{message}」\n\n"
            f"请先表达理解，再把 ta 的经历与书中观点联系起来，"
            f"最后给出 1 个书中可应用的行动建议。"
        )
    else:
        prompt = f"玩家提问：\n「{message}」\n\n请基于书中内容回答。"

    return (
        f"{prompt}\n\n"
        f"【检索到的原文（回答必须引用其中至少 1 条）】\n{retrieved_block}"
    )


# 意图对应的无检索回复模板
OUT_OF_SCOPE_REPLY = (
    "这个问题超出了我的知识范围——我只了解这本书。"
    "要不要换个与本书相关的问题继续聊聊？"
)

CHAT_REPLY = (
    "你好呀！很高兴见到你。无论你想探讨书中的核心概念，"
    "还是分享自己正在面对的困惑，我都愿意陪你聊聊。"
    "想从哪里开始？"
)
