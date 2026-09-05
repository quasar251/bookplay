// 《原子习惯》完整章节数据 —— 基于 game-design.md 非虚构模板

export const chapterData = [
  // ===== 阶段 1：学习身份驱动 =====
  {
    id: 'ch1_teach',
    type: 'teach',
    title: '身份驱动习惯',
    teachPhase: {
      speaker: '詹姆斯·克利尔',
      avatar: '📖',
      gradient: 'from-sky-400 to-indigo-500',
      dialogue: `大多数人在改变习惯时搞反了方向。他们认为，如果你想要更好的结果，就要改变你的行为。
  
  但真正的改变是从内到外的，而不是从外到内。
  
  最深层的改变是身份的改变。你不需要说"我想戒烟"，你要相信"我不是一个吸烟者"。`,
      keyIdea: '习惯是身份的投射。每一次行动都是一张选票，证明你想成为什么样的人。',
      hook: '下一章你会遇到一个真实的选择：是继续为目标奋斗，还是重新定义自己？'
    }
  },

  // ===== 阶段 2：情境决策 =====
  {
    id: 'ch1_scenario',
    type: 'scenario',
    title: '养成读书习惯的困境',
    scenario: {
      description: `你已经想养成每天读书的习惯三个月了，但每次都坚持不到一周。明天就是周一，你站在书桌前思考策略。`,
      options: [
        {
          id: 'A',
          text: '"从今天起，我每天只读一页。然后告诉自己：我是一个读书的人。"',
          cost: '⚠️ 你可能觉得太简单，缺乏挑战性',
          consequence: `你翻开书读了第一页就合上——但你已经完成了目标。
          
更重要的是，你在重塑自己的身份：**我是一个会每天读书的人**。
          
连续两周后，你会发现读1页不再需要意志力。因为现在你不是"想读书的人"，而是"读书的人"。`,
          correct: true,
          label: '身份驱动'
        },
        {
          id: 'B',
          text: '"我要下定决心！每天至少读30分钟，设个闹钟强制自己。"',
          cost: '⚠️ 靠意志力硬撑，失败时会自我否定',
          consequence: `第一天你很兴奋，第二天闹钟响了但你困了。第三天一觉睡过头。
          
第五天你对自己说"我就是做不到"。不是因为目标太大（其实也不算大），而是因为**你还在等"变好"的那一天才认同自己是读书人**。`,
          correct: false,
          label: '结果导向'
        },
        {
          id: 'C',
          text: '"等我找到更适合的时间段和方法再开始。先做计划，列一份必读书单。"',
          cost: '⚠️ 永远在准备，从未真正开始',
          consequence: `你花了一周整理书单、研究阅读方法、甚至买了阅读器。
          
但你依然没有读完任何一本书。完美计划成了不行动的借口。**准备本身变成了拖延的新面具**。`,
          correct: false,
          label: '准备陷阱'
        }
      ]
    }
  },

  // ===== 阶段 3：反思 =====
  {
    id: 'ch1_reflect',
    type: 'reflection',
    title: '你的生活实验',
    reflection: {
      prompt: '你生活中有没有哪个习惯一直想养成却失败了？试着用"身份驱动"重新设计它。',
      type: 'text',
      followUp: '完成这个练习，你的习惯就会变成"我是谁"的投票。',
      examples: [
        '想健身 → "我是运动的人，每天动一下"',
        '想写作 → "我是创作者，今天写50个字"',
        '想存钱 → "我是节俭的人，每天少喝一杯咖啡"'
      ]
    }
  },

  // ===== 卡牌 1 =====
  {
    id: 'card_identity',
    type: 'card',
    card: {
      icon: '🪞',
      name: '身份驱动习惯',
      definition: '习惯不是目标的产物，而是身份的投射。你不需要"想减肥"，你要相信"我是个健康的人"。',
      example: '"我是一个读书的人" → 每天读几页是自然的事\n"我是一个创业者" → 面对困难是常态',
      counterExample: '"我要减10斤"（结果导向）→ 依赖意志力\n"我要赚100万"（结果导向）→ 容易半途而废',
      tags: ['身份', '习惯', '行为改变'],
      gradient: 'from-violet-500 to-purple-600',
      acquired: false
    }
  },

  // ===== 阶段 4：两难选择 =====
  {
    id: 'ch2_scenario',
    type: 'scenario',
    title: '改变的岔路口',
    scenario: {
      description: `你用"身份驱动"的方法坚持了一个月读书习惯。现在朋友邀请你参加一个社交活动，你知道去了可能就无法在图书馆安静看书了。`,
      options: [
        {
          id: 'D',
          text: '"我的身份是读书的人。今晚我在图书馆，这是最重要的事。"',
          cost: '⚠️ 你可能会错过一些社交机会和人脉建立',
          consequence: `你拒绝了邀请，坐在图书馆。那一晚你读到了卡尼曼《思考，快与慢》里让你眼睛一亮的一段。
          
两个星期后，这段知识恰好帮你在工作中解决了一个困扰已久的决策问题。`
        },
        {
          id: 'E',
          text: '"偶尔一次没关系。今天是特殊场合，我明天补回来。"',
          cost: '⚠️ "偶尔一次"会积累成惯性',
          consequence: `那天晚上你玩得很开心。第二天你本来要补读的……但因为多了一天休息的理由，你就没去。
          
第三天你说"这周都放松了吧"。第四周……你的"读书的人"身份开始模糊了。`
        },
        {
          id: 'F',
          text: '"带上Kindle去！社交间隙看10分钟也行。两全其美。"',
          cost: '⚠️ 环境切换成本极高，很可能两头都没做好',
          consequence: `你到了现场才发现，嘈杂的环境完全无法阅读。翻了两页就放下了 Kindle。
          
社交的时候你也心不在焉，总觉得自己在"浪费时间"而非享受。`
        }
      ]
    }
  },

  // ===== 阶段 5：最终反思 =====
  {
    id: 'ch2_reflect',
    type: 'reflection',
    title: '你是谁？',
    reflection: {
      prompt: `回顾你在 BookPlay 中的所有选择：你是一个什么样的人？哪些原则对你最重要？`,
      type: 'choice',
      choices: [
        '行动派——我先做了再说',
        '深思者——我会选最优路径',
        '平衡者——我试图兼顾所有'
      ],
      summary: `无论你选择了什么，记住：**每一个选择都是你身份的投票**。
      
 habit 不是一次决定，而是一百次微小的选择累积起来的自我认知。
      
 下一本书，我们会探讨如何让你的环境自动支持你想要的身份。`
    }
  }
];

// 玩家身份标签系统
export function calculateIdentity(choices) {
  const labels = new Set();
  const identityScores = {
    actionOriented: 0,      // 行动型
    deepThinker: 0,         // 深思型
    balanceSeeker: 0,       // 平衡型
    identityFocused: 0,     // 身份驱动型
  };

  choices.forEach(choice => {
    if (choice === 'A') {
      identityScores.identityFocused += 2;
      identityScores.actionOriented += 1;
      labels.add(' 身份驱动者');
      labels.add('🔥 微小行动派');
    } else if (choice === 'B') {
      identityScores.deepThinker += 1;
      labels.add('💪 意志力强人');
    } else if (choice === 'C') {
      identityScores.deepThinker += 2;
      labels.add('📋 完美策划者');
    } else if (choice === 'D') {
      identityScores.identityFocused += 1;
      identityScores.actionOriented += 1;
      labels.add('📚 专注学习者');
    } else if (choice === 'E') {
      identityScores.balanceSeeker += 2;
      labels.add('🌊 灵活适应者');
    } else if (choice === 'F') {
      identityScores.balanceSeeker += 1;
      identityScores.deepThinker += 1;
      labels.add('🔄 两全追求者');
    }
  });

  return {
    labels: Array.from(labels),
    scores: identityScores
  };
}
