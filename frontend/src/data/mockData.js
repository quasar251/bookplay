// Mock 数据层 - 所有数据均为模拟

// ===== 用户数据 =====
export const user = {
  id: "u001",
  username: "知识探索者",
  avatar: "🧙",
  level: 7,
  totalXp: 680,
  xpToNextLevel: 1000,
  currentLevelXp: 680 - 600, // 6级需要600XP
  nextLevelXp: 700 - 600, // 升到7级需要100XP
  streak: 12, // 连续打卡天数
  totalBooks: 8,
  completedBooks: 3,
  totalConcepts: 42,
  totalNpcs: 3,
  joinDate: "2026-06-15",
};

// ===== 成就数据 =====
export const achievements = [
  { id: "a1", name: "初出茅庐", description: "通关第一本书", icon: "🎯", unlocked: true, unlockedAt: "2026-07-02" },
  { id: "a2", name: "概念猎手", description: "提取 20 个概念", icon: "💎", unlocked: true, unlockedAt: "2026-07-20" },
  { id: "a3", name: "织网者", description: "建立 10 条跨书连接", icon: "🕸️", unlocked: true, unlockedAt: "2026-08-10" },
  { id: "a4", name: "思想策展人", description: "组织 3 次群组讨论", icon: "🎪", unlocked: true, unlockedAt: "2026-08-25" },
  { id: "a5", name: "坚持不懈", description: "连续打卡 7 天", icon: "🔥", unlocked: true, unlockedAt: "2026-08-01" },
  { id: "a6", name: "书虫", description: "通关 5 本书", icon: "📚", unlocked: false, progress: 3, target: 5 },
  { id: "a7", name: "星图大师", description: "拥有 100 个概念节点", icon: "🌌", unlocked: false, progress: 42, target: 100 },
  { id: "a8", name: "社交蝴蝶", description: "与 5 个 NPC 对话超过 10 轮", icon: "🦋", unlocked: false, progress: 1, target: 5 },
];

// ===== 技能树数据 =====
export const skillTree = {
  branches: [
    {
      id: "b1",
      name: "行为科学",
      level: 3,
      color: "#f59e0b",
      concepts: ["认知偏差", "系统1", "损失厌恶", "锚定效应", "从众心理", "双曲贴现"],
    },
    {
      id: "b2",
      name: "决策科学",
      level: 2,
      color: "#8b5cf6",
      concepts: ["期望值理论", "前景理论", "决策树", "贝叶斯思维"],
    },
    {
      id: "b3",
      name: "技术思维",
      level: 2,
      color: "#0ea5e9",
      concepts: ["递归", "抽象", "分层架构", "模块化"],
    },
    {
      id: "b4",
      name: "产品思维",
      level: 1,
      color: "#ec4899",
      concepts: ["用户旅程", "MVP法则"],
    },
  ],
};

// ===== 用户画像 =====
export const userProfile = {
  learningStyle: "归纳型",
  preferredTopics: ["行为经济学", "决策科学", "人工智能"],
  readingPatterns: {
    avgDailyMinutes: 35,
    mostActiveHour: "22:00-23:00",
    completionRate: 0.73,
  },
};

// ===== 书籍副本数据 =====
export const books = [
  {
    id: "book1",
    title: "思考，快与慢",
    author: "丹尼尔·卡尼曼",
    cover: "🧠",
    coverColor: "from-amber-400 to-orange-500",
    status: "completed",
    totalChapters: 12,
    completedChapters: 12,
    xpEarned: 280,
    difficulty: "hard",
    conceptCount: 18,
    npcId: "npc1",
    description: "诺贝尔经济学奖得主的经典之作，揭示人类思维的两套系统。",
    createdAt: "2026-06-20",
    completedAt: "2026-07-02",
  },
  {
    id: "book2",
    title: "影响力",
    author: "罗伯特·西奥迪尼",
    cover: "🎭",
    coverColor: "from-rose-400 to-pink-600",
    status: "completed",
    totalChapters: 8,
    completedChapters: 8,
    xpEarned: 180,
    difficulty: "medium",
    conceptCount: 12,
    npcId: "npc2",
    description: "社会心理学经典，剖析让人顺从的六大心理学原理。",
    createdAt: "2026-07-05",
    completedAt: "2026-07-18",
  },
  {
    id: "book3",
    title: "穷查理宝典",
    author: "彼得·考夫曼",
    cover: "📖",
    coverColor: "from-emerald-400 to-teal-600",
    status: "completed",
    totalChapters: 10,
    completedChapters: 10,
    xpEarned: 220,
    difficulty: "hard",
    conceptCount: 15,
    npcId: "npc3",
    description: "查理·芒格的智慧箴言录，多元思维模型的集合。",
    createdAt: "2026-07-20",
    completedAt: "2026-08-15",
  },
  {
    id: "book4",
    title: "深入理解计算机系统",
    author: "Randal E. Bryant",
    cover: "💻",
    coverColor: "from-sky-400 to-blue-600",
    status: "in_progress",
    totalChapters: 13,
    completedChapters: 5,
    xpEarned: 120,
    difficulty: "hard",
    conceptCount: 8,
    npcId: null,
    description: "从程序员视角深入剖析计算机系统的经典教材。",
    createdAt: "2026-08-20",
  },
  {
    id: "book5",
    title: "原则",
    author: "瑞·达利欧",
    cover: "📐",
    coverColor: "from-slate-400 to-slate-700",
    status: "in_progress",
    totalChapters: 9,
    completedChapters: 3,
    xpEarned: 60,
    difficulty: "medium",
    conceptCount: 5,
    npcId: null,
    description: "桥水基金创始人分享的生活与工作原则。",
    createdAt: "2026-08-28",
  },
  {
    id: "book6",
    title: "置身事内",
    author: "兰小欢",
    cover: "🏛️",
    coverColor: "from-red-400 to-rose-600",
    status: "in_progress",
    totalChapters: 8,
    completedChapters: 2,
    xpEarned: 30,
    difficulty: "medium",
    conceptCount: 3,
    npcId: null,
    description: "理解中国政府与经济关系的入门佳作。",
    createdAt: "2026-09-01",
  },
  {
    id: "book7",
    title: "设计模式",
    author: "GoF",
    cover: "🎨",
    coverColor: "from-purple-400 to-indigo-600",
    status: "not_started",
    totalChapters: 23,
    completedChapters: 0,
    xpEarned: 0,
    difficulty: "hard",
    conceptCount: 0,
    npcId: null,
    description: "四人组经典，面向对象软件设计的基础。",
    createdAt: "2026-09-03",
  },
  {
    id: "book8",
    title: "乌合之众",
    author: "古斯塔夫·勒庞",
    cover: "👥",
    coverColor: "from-yellow-400 to-amber-600",
    status: "not_started",
    totalChapters: 5,
    completedChapters: 0,
    xpEarned: 0,
    difficulty: "easy",
    conceptCount: 0,
    npcId: null,
    description: "群体心理学的开山之作。",
    createdAt: "2026-09-04",
  },
];

// ===== 章节数据（按书存储）=====
export const chapters = {
  book4: [
    { index: 1, title: "计算机系统漫游", completed: true, xpGained: 20, concepts: ["抽象", "分层架构"] },
    { index: 2, title: "信息的表示和处理", completed: true, xpGained: 25, concepts: ["补码", "浮点数"] },
    { index: 3, title: "程序的机器级表示", completed: true, xpGained: 30, concepts: ["汇编", "栈帧"] },
    { index: 4, title: "处理器体系结构", completed: true, xpGained: 25, concepts: ["流水线", "ISA"] },
    { index: 5, title: "优化程序性能", completed: true, xpGained: 20, concepts: ["循环展开", "分支预测"] },
    { index: 6, title: "存储器层次结构", completed: false, xpGained: 0, concepts: [] },
    { index: 7, title: "链接", completed: false, xpGained: 0, concepts: [] },
    { index: 8, title: "异常控制流", completed: false, xpGained: 0, concepts: [] },
    { index: 9, title: "虚拟内存", completed: false, xpGained: 0, concepts: [] },
    { index: 10, title: "系统级I/O", completed: false, xpGained: 0, concepts: [] },
    { index: 11, title: "网络编程", completed: false, xpGained: 0, concepts: [] },
    { index: 12, title: "并发编程", completed: false, xpGained: 0, concepts: [] },
    { index: 13, title: "附录", completed: false, xpGained: 0, concepts: [] },
  ],
  book5: [
    { index: 1, title: "我的探险历程", completed: true, xpGained: 20, concepts: ["极度求真"] },
    { index: 2, title: "生活原则", completed: true, xpGained: 25, concepts: ["拥抱现实", "痛苦+反思=进步"] },
    { index: 3, title: "工作原则（上）", completed: true, xpGained: 15, concepts: ["创意择优"] },
    { index: 4, title: "工作原则（下）", completed: false, xpGained: 0, concepts: [] },
    { index: 5, title: "打造允许犯错的文化", completed: false, xpGained: 0, concepts: [] },
    { index: 6, title: "求取共识并坚持", completed: false, xpGained: 0, concepts: [] },
    { index: 7, title: "做决策时要从观点的可信度出发", completed: false, xpGained: 0, concepts: [] },
    { index: 8, title: "知道如何超越分歧", completed: false, xpGained: 0, concepts: [] },
    { index: 9, title: "结束语", completed: false, xpGained: 0, concepts: [] },
  ],
  book6: [
    { index: 1, title: "地方政府的权力与事务", completed: true, xpGained: 15, concepts: ["事权划分"] },
    { index: 2, title: "财税与政府行为", completed: true, xpGained: 15, concepts: ["土地财政"] },
    { index: 3, title: "政府投融资与债务", completed: false, xpGained: 0, concepts: [] },
    { index: 4, title: "工业化中的政府角色", completed: false, xpGained: 0, concepts: [] },
    { index: 5, title: "城市化与不平衡", completed: false, xpGained: 0, concepts: [] },
    { index: 6, title: "债务与风险", completed: false, xpGained: 0, concepts: [] },
    { index: 7, title: "国内国际失衡", completed: false, xpGained: 0, concepts: [] },
    { index: 8, title: "总结：政府与经济发展", completed: false, xpGained: 0, concepts: [] },
  ],
};

// ===== 摘录/笔记数据 =====
export const quotes = {
  book4: [
    { id: "q1", chapter: 1, text: "计算机系统中的抽象是管理复杂性的主要工具。", concept: "抽象" },
    { id: "q2", chapter: 3, text: "栈帧是函数调用的基础，理解栈帧有助于理解递归。", concept: "栈帧" },
    { id: "q3", chapter: 5, text: "循环展开可以通过减少循环控制指令的开销来提升性能。", concept: "循环展开" },
  ],
  book5: [
    { id: "q4", chapter: 1, text: "痛苦 + 反思 = 进步。", concept: "痛苦+反思=进步" },
    { id: "q5", chapter: 2, text: "拥抱现实，应对现实。", concept: "拥抱现实" },
  ],
  book6: [
    { id: "q6", chapter: 1, text: "事权划分的核心原则是外部性和信息复杂性。", concept: "事权划分" },
  ],
};

// ===== NPC 数据 =====
export const npcs = [
  {
    id: "npc1",
    name: "卡尼曼的幽灵",
    avatarEmoji: "🧠",
    personalityTags: ["理性", "循循善诱", "喜欢出思维实验题"],
    coreBeliefs: [
      "系统1是直觉，系统2是理性",
      "认知偏差无处不在",
      "慢思考比快思考更可靠",
    ],
    greeting: "我注意到你对'系统1的直觉陷阱'很感兴趣，要不要来做一个思维实验？",
    tone: "学术但亲切，喜欢用日常例子",
    familiarity: 0.65,
    booksAssociated: ["思考，快与慢"],
    topicsDiscussed: ["锚定效应", "损失厌恶", "框架效应"],
  },
  {
    id: "npc2",
    name: "西奥迪尼的影子",
    avatarEmoji: "🎭",
    personalityTags: ["敏锐", "善于观察", "幽默"],
    coreBeliefs: [
      "人类的顺从有固定模式",
      "社会认同原理力量强大",
      "承诺和一致是强大的心理武器",
    ],
    greeting: "嘿，年轻人！今天我们来聊聊，为什么你总是忍不住买第二件半价的东西？",
    tone: "轻松幽默，案例丰富",
    familiarity: 0.45,
    booksAssociated: ["影响力"],
    topicsDiscussed: ["社会认同", "稀缺原理"],
  },
  {
    id: "npc3",
    name: "芒格的多面镜",
    avatarEmoji: "📖",
    personalityTags: ["博学", "务实", "逆向思维"],
    coreBeliefs: [
      "多元思维模型是智慧的钥匙",
      "反过来想，总是反过来想",
      "避免愚蠢比追求聪明更重要",
    ],
    greeting: "年轻人，如果你想获得某样东西，首先得配得上它。今天想聊聊哪个领域的思维模型？",
    tone: "老派智者，言简意赅，金句频出",
    familiarity: 0.52,
    booksAssociated: ["穷查理宝典"],
    topicsDiscussed: ["多元思维模型", "误判心理学", "lollapalooza效应"],
  },
];

// ===== NPC 对话历史 =====
export const npcConversations = {
  npc1: [
    {
      id: "c1",
      userMessage: "系统1和系统2真的是两套独立的系统吗？",
      npcResponse: "好问题！其实更准确的说法是，它们是大脑运作的两种模式——系统1像自动巡航，系统2像手动驾驶。大部分时候我们用系统1节能，只有遇到难题才唤醒系统2。你有没有过那种'脱口而出然后后悔'的经历？那就是系统1抢答了。",
      topics: ["系统1", "系统2"],
    },
    {
      id: "c2",
      userMessage: "锚定效应在谈判中怎么用？",
      npcResponse: "哦，这可是个实用的问题。想象你去买东西，卖家先报一个高价——那就是在给你'锚定'。我的建议是：在谈判中，如果你有足够信息，先出价；如果信息不足，别急着回应对方的开价，先在心里重置锚点。对了，你最近有没有遇到被锚定的场景？",
      topics: ["锚定效应", "谈判"],
    },
    {
      id: "c3",
      userMessage: "损失厌恶和禀赋效应有什么关系？",
      npcResponse: "敏锐！禀赋效应其实是损失厌恶的一种表现——你一旦拥有了某样东西，放弃它就成了'损失'，而损失的痛苦是获得快乐的2.5倍。这就是为什么免费试用那么有效——你用着用着就觉得它是你的了，退订就像在损失什么。",
      topics: ["损失厌恶", "禀赋效应"],
    },
  ],
};

// ===== 群组讨论数据 =====
export const groupDiscussions = [
  {
    id: "gd1",
    topic: "为什么聪明人也会做蠢事？",
    npcIds: ["npc1", "npc2", "npc3"],
    date: "2026-08-25",
    summary: "三位智者从不同角度探讨了这个问题：卡尼曼强调认知偏差的普遍性，西奥迪尼关注社会情境的影响，芒格则提出多元思维模型是解药。",
    keyDisagreements: [
      "卡尼曼认为偏差主要来自个体认知局限",
      "西奥迪尼更强调社会情境的诱导作用",
      "芒格认为可以通过训练系统性地减少错误",
    ],
  },
  {
    id: "gd2",
    topic: "如何提升决策质量？",
    npcIds: ["npc1", "npc3"],
    date: "2026-08-30",
    summary: "卡尼曼和芒格一致认为：慢思考 + 多模型 + 逆向思维是提升决策质量的三驾马车。",
    keyDisagreements: [
      "卡尼曼侧重避免认知偏差",
      "芒格侧重积累多元思维模型",
    ],
  },
];

// ===== 认知星图数据 =====
export const knowledgeGraph = {
  nodes: [
    // 书籍节点（圆形，category 0）
    { id: "book1", name: "思考快与慢", category: 0, symbolSize: 40 },
    { id: "book2", name: "影响力", category: 0, symbolSize: 35 },
    { id: "book3", name: "穷查理宝典", category: 0, symbolSize: 38 },
    { id: "book4", name: "深入理解计算机系统", category: 0, symbolSize: 30 },
    { id: "book5", name: "原则", category: 0, symbolSize: 28 },
    // 概念节点（菱形，category 1）
    { id: "c1", name: "认知偏差", category: 1, symbolSize: 25 },
    { id: "c2", name: "系统1", category: 1, symbolSize: 22 },
    { id: "c3", name: "系统2", category: 1, symbolSize: 22 },
    { id: "c4", name: "损失厌恶", category: 1, symbolSize: 24 },
    { id: "c5", name: "锚定效应", category: 1, symbolSize: 22 },
    { id: "c6", name: "社会认同", category: 1, symbolSize: 22 },
    { id: "c7", name: "稀缺原理", category: 1, symbolSize: 20 },
    { id: "c8", name: "多元思维模型", category: 1, symbolSize: 28 },
    { id: "c9", name: "逆向思维", category: 1, symbolSize: 20 },
    { id: "c10", name: "前景理论", category: 1, symbolSize: 22 },
    { id: "c11", name: "从众心理", category: 1, symbolSize: 20 },
    { id: "c12", name: "双曲贴现", category: 1, symbolSize: 18 },
    { id: "c13", name: "抽象", category: 1, symbolSize: 20 },
    { id: "c14", name: "分层架构", category: 1, symbolSize: 20 },
    { id: "c15", name: "极度求真", category: 1, symbolSize: 20 },
    { id: "c16", name: "创意择优", category: 1, symbolSize: 18 },
    // NPC 节点（星形，category 2）
    { id: "npc1", name: "卡尼曼的幽灵", category: 2, symbolSize: 32 },
    { id: "npc2", name: "西奥迪尼的影子", category: 2, symbolSize: 30 },
    { id: "npc3", name: "芒格的多面镜", category: 2, symbolSize: 30 },
  ],
  links: [
    // 书籍-概念关系
    { source: "book1", target: "c1" },
    { source: "book1", target: "c2" },
    { source: "book1", target: "c3" },
    { source: "book1", target: "c4" },
    { source: "book1", target: "c5" },
    { source: "book1", target: "c10" },
    { source: "book2", target: "c6" },
    { source: "book2", target: "c7" },
    { source: "book2", target: "c11" },
    { source: "book3", target: "c8" },
    { source: "book3", target: "c9" },
    { source: "book4", target: "c13" },
    { source: "book4", target: "c14" },
    { source: "book5", target: "c15" },
    { source: "book5", target: "c16" },
    // 跨书概念连接
    { source: "c1", target: "c8", lineStyle: { type: "dashed" } }, // 认知偏差 → 多元思维模型
    { source: "c4", target: "c10", lineStyle: { type: "dashed" } }, // 损失厌恶 → 前景理论
    { source: "c5", target: "c7", lineStyle: { type: "dashed" } }, // 锚定 → 稀缺
    { source: "c6", target: "c11", lineStyle: { type: "dashed" } }, // 社会认同 → 从众
    { source: "c9", target: "c16", lineStyle: { type: "dashed" } }, // 逆向思维 → 创意择优
    { source: "c8", target: "c13", lineStyle: { type: "dashed" } }, // 多元思维 → 抽象
    // 书籍-NPC 关系
    { source: "book1", target: "npc1" },
    { source: "book2", target: "npc2" },
    { source: "book3", target: "npc3" },
  ],
  categories: [
    { name: "书籍" },
    { name: "概念" },
    { name: "NPC" },
  ],
};
