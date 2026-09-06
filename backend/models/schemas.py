"""BookPlay 核心数据模型

所有 Agent 的输入输出、API 请求响应、内部数据结构都在此定义。
遵循 Pydantic v2 规范，所有字段都有类型注解与默认值。
"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ============================================================
# 一、概念与书籍结构（对应 PRD4 第 4 章：分层提取策略）
# ============================================================


class Concept(BaseModel):
    """核心概念 —— 书籍知识的最小单元

    由 ExtractAgent 从章节中抽取，是场景生成的原材料。
    """

    name: str = Field(..., description="概念名称，如'身份驱动习惯'")
    definition: str = Field(..., description="核心定义，不超过 50 字")
    keywords: List[str] = Field(default_factory=list, description="关键词，用于 RAG 检索")
    source_quote: Optional[str] = Field(None, description="原文中最有力的一句话引用")
    source_chapter: Optional[str] = Field(None, description="来源章节")


class ChapterSkeleton(BaseModel):
    """章节骨架 —— 单章的结构信息"""

    id: int = Field(..., description="章节序号")
    title: str = Field(..., description="章节标题")
    summary: str = Field(..., description="本章一句话概述")
    concepts: List[Concept] = Field(default_factory=list, description="本章提取的核心概念")


class BookSkeleton(BaseModel):
    """书籍骨架 —— 第 1 层提取的最终产物

    由 ExtractAgent 输出，作为后续 SceneAgent 的输入。
    """

    core_theme: str = Field(..., description="全书核心主题，一句话概括")
    chapters: List[ChapterSkeleton] = Field(default_factory=list, description="章节列表")
    main_arguments: List[str] = Field(default_factory=list, description="全书主要论点")
    total_concepts: int = Field(0, description="提取到的概念总数")


# ============================================================
# 二、游戏场景结构（对应 PRD4 第 2 章：学→练→用 闭环）
# ============================================================


class LearningStage(BaseModel):
    """学·认知阶段

    NPC 以作者口吻传授核心原理。
    """

    speaker: str = Field(..., description="讲解者身份，如'詹姆斯·克利尔'")
    dialogue: str = Field(..., description="核心传授内容（NPC 说的话）")
    key_idea: str = Field(..., description="一句话总结，即'关键认知卡'")


class ScenarioOption(BaseModel):
    """情境选项 —— 三选一的单个选项"""

    id: str = Field(..., description="选项标识，如'A'、'B'、'C'")
    label: str = Field(..., description="选项简短标题")
    text: str = Field(..., description="选项详细描述")
    cost: str = Field(..., description="代价描述（必填，无完美答案）")
    consequence: str = Field(..., description="选择后的后果描述")
    # 非虚构类专用
    correct: Optional[bool] = Field(None, description="是否为最优解（非虚构类有）")
    explanation: Optional[str] = Field(None, description="为什么这个是最优解")
    # 虚构类专用
    trait: Optional[str] = Field(None, description="对应的读者侧写，如'共谋者型读者'")
    trait_desc: Optional[str] = Field(None, description="侧写说明")
    tags: List[str] = Field(default_factory=list, description="身份标签")


class ScenarioStage(BaseModel):
    """练·情境决策阶段"""

    title: str = Field(..., description="情境标题")
    description: str = Field(..., description="情境背景描述")
    options: List[ScenarioOption] = Field(..., description="3 个选项")


class ReflectionStage(BaseModel):
    """用·反思内化阶段"""

    prompt: str = Field(..., description="引导问题")
    type: str = Field("text", description="反思类型：text（开放式）/ choice（选择式）")
    choices: List[str] = Field(default_factory=list, description="选择式的选项（type=choice 时使用）")


class Card(BaseModel):
    """卡牌 —— 可携带的学习成果

    对应 PRD4 中的“🃏 卡牌”阶段。
    """

    id: Optional[str] = Field(None, description="卡牌唯一 ID")
    icon: str = Field("🃏", description="卡牌图标 emoji")
    name: str = Field(..., description="卡牌名称")
    definition: str = Field(..., description="核心定义")
    example: Optional[str] = Field(None, description="正面示例")
    counter_example: Optional[str] = Field(None, description="反面示例/角色对照")
    tags: List[str] = Field(default_factory=list, description="身份标签")
    source_concept: Optional[str] = Field(None, description="来源概念名称")


class GameScene(BaseModel):
    """完整游戏场景 —— 学→练→用→卡牌 闭环

    由 SceneAgent 基于单个 Concept 生成。
    """

    concept_name: str = Field(..., description="对应的核心概念名称")
    chapter_id: Optional[int] = Field(None, description="所属章节 ID")
    learning: LearningStage = Field(..., description="学·认知阶段")
    scenario: ScenarioStage = Field(..., description="练·情境决策阶段")
    reflection: ReflectionStage = Field(..., description="用·反思内化阶段")
    card: Card = Field(..., description="通关后获得的卡牌")


# ============================================================
# 三、Agent 通用结构
# ============================================================


class AgentMeta(BaseModel):
    """Agent 元信息"""

    name: str = Field(..., description="Agent 唯一标识")
    description: str = Field("", description="Agent 功能描述")
    type: str = Field("", description="类名")


class AgentResult(BaseModel):
    """Agent 执行结果 —— 所有 Agent 的统一返回格式"""

    success: bool = Field(..., description="是否成功")
    result: Optional[Dict[str, Any]] = Field(None, description="实际结果数据（结构化）")
    error: Optional[str] = Field(None, description="错误信息（失败时）")
    raw_text: Optional[str] = Field(None, description="LLM 原始文本（调试用）")


class ExecutionStage(BaseModel):
    """编排器单个执行阶段记录"""

    stage: int = Field(..., description="阶段序号")
    agent: str = Field(..., description="Agent 名称")
    status: str = Field(..., description="状态：completed / failed / skipped")
    duration_ms: float = Field(0.0, description="耗时（毫秒）")
    input_keys: List[str] = Field(default_factory=list, description="输入字段列表")
    result: Optional[AgentResult] = Field(None, description="该阶段的详细结果")


class OrchestratorResult(BaseModel):
    """编排器最终执行结果"""

    success: bool = Field(..., description="整体是否成功")
    stages: List[ExecutionStage] = Field(default_factory=list, description="各阶段执行详情")
    final_result: Optional[Dict[str, Any]] = Field(None, description="最后一个 Agent 的输出数据")
    total_time_seconds: float = Field(0.0, description="总耗时（秒）")
    execution_log: List[Dict[str, Any]] = Field(default_factory=list, description="简化版执行日志")


# ============================================================
# 四、API 请求 / 响应模型
# ============================================================


class GenerateRequest(BaseModel):
    """生成游戏内容请求体"""

    book_text: str = Field(..., min_length=100, description="书籍全文或摘要（至少 100 字）")
    book_title: Optional[str] = Field(None, description="书籍标题（可选，用于提升生成质量）")
    book_type: str = Field("non_fiction", description="书籍类型：non_fiction / fiction")


class GenerateResponse(BaseModel):
    """生成游戏内容响应体"""

    code: int = Field(0, description="状态码：0 成功，非 0 失败")
    message: str = Field("success", description="状态描述")
    data: Dict[str, Any] = Field(default_factory=dict, description="业务数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据（耗时、日志等）")
    timestamp: int = Field(0, description="时间戳")


class HealthResponse(BaseModel):
    """健康检查响应"""

    status: str = Field("ok", description="服务状态")
    agents_count: int = Field(0, description="已注册 Agent 数量")
    available_agents: List[str] = Field(default_factory=list, description="可用 Agent 名称列表")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
