import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/client';
import { chapterData, calculateIdentity } from '../data/gameData';

const TEACH_GRADIENT = 'from-sky-400 to-indigo-500';
const CARD_GRADIENTS = [
  'from-violet-500 to-purple-600',
  'from-sky-500 to-blue-600',
  'from-emerald-500 to-teal-600',
  'from-rose-500 to-pink-600',
  'from-amber-500 to-orange-600',
];

// 把后端 game JSON 转成 GameEngine 所需的 chapterData 步骤数组：
// 每章每个 scene 展开为 teach → scenario → reflection → card 四个 step。
// 字段对齐 gameData.js 中 mock chapterData 的既有 schema。
function buildStepsFromGame(game) {
  if (!game || !Array.isArray(game.chapters)) return [];
  const steps = [];
  let cardIdx = 0;

  game.chapters.forEach(chapter => {
    const chapterId = chapter.chapter_id ?? '';
    const chapterHook = chapter.chapter_hook || '';
    const scenes = Array.isArray(chapter.scenes) ? chapter.scenes : [];

    scenes.forEach((scene, si) => {
      const concept =
        scene.concept_name || scene.card?.source_concept || `概念 ${chapterId}-${si + 1}`;
      const prefix = `${chapterId}-${si}`;
      const learning = scene.learning || {};
      const scenario = scene.scenario || {};
      const reflection = scene.reflection || {};
      const card = scene.card || {};

      // teach：学习阶段
      if (learning.dialogue || learning.key_idea) {
        steps.push({
          id: `${prefix}-teach`,
          type: 'teach',
          title: concept,
          teachPhase: {
            speaker: learning.speaker || '讲解者',
            avatar: '📖',
            gradient: TEACH_GRADIENT,
            dialogue: learning.dialogue || '',
            keyIdea: learning.key_idea || '',
            // hook：优先场景钩子，否则取本章 chapter_hook（每章只展示一次）
            hook: si === 0 ? scene.hook || chapterHook : scene.hook || '',
          },
        });
      }

      // scenario：情境决策
      const options = (Array.isArray(scenario.options) ? scenario.options : [])
        .filter(o => o && typeof o === 'object')
        .map((o, i) => ({
          id: o.id ?? String.fromCharCode(65 + i),
          label: o.label ?? '',
          text: o.text ?? '',
          cost: o.cost ?? '',
          consequence: o.consequence ?? '',
          correct: Boolean(o.correct),
        }));
      if (options.length > 0) {
        steps.push({
          id: `${prefix}-scenario`,
          type: 'scenario',
          title: scenario.title || concept,
          scenario: {
            description: scenario.description || '',
            options,
          },
        });
      }

      // reflection：反思内化
      if (reflection.prompt) {
        steps.push({
          id: `${prefix}-reflection`,
          type: 'reflection',
          title: concept,
          reflection: {
            prompt: reflection.prompt,
            type: reflection.type || 'text',
            followUp: reflection.followUp || '',
            examples: Array.isArray(reflection.examples) ? reflection.examples : undefined,
          },
        });
      }

      // card：收获卡牌
      if (card.name || card.definition) {
        steps.push({
          id: `${prefix}-card`,
          type: 'card',
          card: {
            icon: card.icon || '🃏',
            name: card.name || concept,
            definition: card.definition || card.name || '',
            example: card.example || '',
            counterExample: card.counter_example || card.counterExample || '',
            tags: Array.isArray(card.tags) ? card.tags : [],
            gradient: card.gradient || CARD_GRADIENTS[cardIdx % CARD_GRADIENTS.length],
          },
        });
        cardIdx += 1;
      }
    });
  });

  return steps;
}

export default function GameEngine() {
  const { bookId } = useParams();
  const navigate = useNavigate();
  const [steps, setSteps] = useState(() => (bookId ? null : chapterData));
  const [gameLoading, setGameLoading] = useState(() => Boolean(bookId));
  const [loadFailed, setLoadFailed] = useState(false);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [choices, setChoices] = useState([]);
  const [showResult, setShowResult] = useState(false);
  const [collectedCards, setCollectedCards] = useState(new Set());
  const [cardRevealed, setCardRevealed] = useState(false);
  const [exitConfirm, setExitConfirm] = useState(false);

  const resetProgress = () => {
    setCurrentIndex(0);
    setChoices([]);
    setShowResult(false);
    setCollectedCards(new Set());
    setCardRevealed(false);
    setExitConfirm(false);
  };

  // 有 bookId：优先加载真实 game 数据；无 bookId / 加载失败 → mock 兜底
  useEffect(() => {
    if (!bookId) return undefined;
    let cancelled = false;
    api.getBookGame(bookId)
      .then(res => {
        if (cancelled) return;
        const built = buildStepsFromGame(res?.game);
        if (built.length > 0) {
          setSteps(built);
          setLoadFailed(false);
        } else {
          setSteps(chapterData);
          setLoadFailed(true);
        }
        resetProgress();
      })
      .catch(() => {
        if (cancelled) return;
        setSteps(chapterData);
        setLoadFailed(true);
        resetProgress();
      })
      .finally(() => {
        if (!cancelled) setGameLoading(false);
      });
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [bookId]);

  const activeSteps = steps ?? [];
  const currentChapter = activeSteps[currentIndex];
  const isLast = currentIndex >= activeSteps.length - 1;
  const identity = calculateIdentity(choices);

  // 自动收集卡牌
  useEffect(() => {
    if (currentChapter?.type === 'card') {
      setCollectedCards(prev => new Set([...prev, currentChapter.id]));
      setTimeout(() => setCardRevealed(true), 500);
    }
  }, [currentChapter]);

  // 进入反思阶段
  const handleScenarioComplete = (choiceId) => {
    setChoices([...choices, choiceId]);
    nextPhase();
  };

  const nextPhase = () => {
    setCardRevealed(false);
    setTimeout(() => setCurrentIndex(prev => prev + 1), 300);
  };

  // 退出游戏
  const handleExit = () => {
    setExitConfirm(true);
  };

  const confirmExit = () => {
    // 如果从书籍详情页进入，返回该书；否则返回大厅
    const returnPath = bookId ? `/book/${bookId}` : '/';
    navigate(returnPath);
  };

  const cancelExit = () => {
    setExitConfirm(false);
  };

  if (gameLoading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-slate-400">
          <div className="text-4xl mb-3 animate-pulse">📖</div>
          <div className="text-sm">正在加载沉浸式副本…</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* 顶部进度条 + 退出按钮 */}
      <GameProgressBar
        total={activeSteps.length}
        current={currentIndex + 1}
        collectedCards={collectedCards.size}
        onExit={handleExit}
      />

      {/* 主内容区 */}
      <div className="flex-1 overflow-y-auto p-6 md:p-8">
        <div className="max-w-3xl mx-auto">
          {loadFailed && (
            <div className="mb-4 px-4 py-2 bg-amber-50 border border-amber-200 rounded-xl text-xs text-amber-600">
              ⚠️ 真实副本内容暂不可用，已切换到示例内容演示。
            </div>
          )}

          {/* 阶段指示器 */}
          <PhaseIndicator type={currentChapter?.type} />

          {/* 根据类型渲染不同阶段 */}
          {currentChapter?.type === 'teach' && (
            <LearnPhase
              data={currentChapter.teachPhase}
              onNext={nextPhase}
              hook={currentChapter.teachPhase.hook}
            />
          )}

          {currentChapter?.type === 'scenario' && (
            <PracticePhase
              scenario={currentChapter.scenario}
              title={currentChapter.title}
              onChoose={handleScenarioComplete}
            />
          )}

          {currentChapter?.type === 'reflection' && (
            <UsePhase
              reflection={currentChapter.reflection}
              title={currentChapter.title}
              onSubmit={() => nextPhase()}
            />
          )}

          {currentChapter?.type === 'card' && (
            <CardPhase
              card={currentChapter.card}
              revealed={cardRevealed}
              onNext={() => {
                if (isLast) {
                  setShowResult(true);
                } else {
                  nextPhase();
                }
              }}
            />
          )}
        </div>
      </div>

      {/* 身份结果页 */}
      {showResult && (
        <IdentityResult
          identity={identity}
          choices={choices}
          collectedCards={collectedCards.size}
          onClose={() => navigate(bookId ? `/book/${bookId}` : '/')}
        />
      )}

      {/* 退出确认弹窗 */}
      {exitConfirm && (
        <ExitConfirmModal
          progress={`${Math.round((currentIndex / activeSteps.length) * 100)}%`}
          onConfirm={confirmExit}
          onCancel={cancelExit}
        />
      )}
    </div>
  );
}

// ========== 各阶段组件 ==========

function LearnPhase({ data, onNext, hook }) {
  return (
    <div className="space-y-6 animate-fadeIn">
      {/* NPC 头像和名称 */}
      <div className="flex items-center gap-4 mb-6">
        <div className={`w-16 h-16 rounded-2xl bg-gradient-to-br ${data.gradient} flex items-center justify-center text-2xl shadow-lg`}>
          {data.avatar}
        </div>
        <div>
          <div className="text-sm text-slate-500">讲解者</div>
          <div className="font-bold text-slate-800">{data.speaker}</div>
        </div>
      </div>

      {/* 核心内容 */}
      <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-6 space-y-4">
        <p className="text-slate-700 leading-relaxed whitespace-pre-line">{data.dialogue}</p>

        {/* 一句话总结 */}
        <div className="bg-gradient-to-r from-violet-50 to-purple-50 border-l-4 border-violet-400 p-4 rounded-r-xl">
          <div className="text-xs font-semibold text-violet-600 mb-1">💡 核心认知</div>
          <div className="text-slate-800 font-medium">{data.keyIdea}</div>
        </div>
      </div>

      {/* 下一步按钮 */}
      <button
        onClick={onNext}
        className="w-full py-3 bg-gradient-to-r from-sky-500 to-violet-500 text-white rounded-xl font-medium hover:shadow-lg hover:shadow-sky-200 transition-all"
      >
        进入情境 →
      </button>

      {/* 钩子提示 */}
      {hook && (
        <div className="text-center text-sm text-slate-400 italic">
          ⚠️ {hook}
        </div>
      )}
    </div>
  );
}

function PracticePhase({ scenario, title, onChoose }) {
  const [selected, setSelected] = useState(null);
  const [revealed, setRevealed] = useState(false);

  const handleSelect = (id) => {
    setSelected(id);
    setRevealed(true);
  };

  const handleConfirm = () => {
    if (selected) {
      onChoose(selected);
    }
  };

  const selectedOption = scenario.options.find(o => o.id === selected);

  return (
    <div className="space-y-6 animate-fadeIn">
      {/* 情境描述 */}
      <div className="bg-slate-900 rounded-2xl p-6 text-white">
        <div className="text-xs text-slate-400 mb-2">🎯 {title}</div>
        <p className="leading-relaxed">{scenario.description}</p>
      </div>

      {/* 三选一 */}
      <div className="space-y-3">
        {scenario.options.map(option => (
          <ScenarioOption
            key={option.id}
            option={option}
            isSelected={selected === option.id}
            isRevealed={revealed}
            onClick={() => handleSelect(option.id)}
          />
        ))}
      </div>

      {/* 选择后的反馈区 */}
      {revealed && selectedOption && (
        <div className={`rounded-2xl p-6 border-2 ${
          selectedOption.correct
            ? 'border-emerald-300 bg-emerald-50'
            : selectedOption.label === '身份驱动'
              ? 'border-sky-300 bg-sky-50'
              : 'border-amber-300 bg-amber-50'
        }`}>
          <div className="flex items-center gap-2 mb-3">
            <span className={`px-2 py-1 rounded-lg text-xs font-semibold ${
              selectedOption.correct
                ? 'bg-emerald-200 text-emerald-700'
                : 'bg-amber-200 text-amber-700'
            }`}>
              {selectedOption.correct ? '✅ 最优解' : `← ${selectedOption.label}`}
            </span>
          </div>
          <p className="text-slate-700 leading-relaxed whitespace-pre-line">{selectedOption.consequence}</p>
        </div>
      )}

      {/* 确认按钮 */}
      {revealed && (
        <button
          onClick={handleConfirm}
          disabled={!selected}
          className="w-full py-3 bg-gradient-to-r from-violet-500 to-pink-500 text-white rounded-xl font-medium hover:shadow-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all"
        >
          继续 →
        </button>
      )}
    </div>
  );
}

function ScenarioOption({ option, isSelected, isRevealed, onClick }) {
  return (
    <div
      onClick={onClick}
      className={`relative p-4 rounded-xl border-2 cursor-pointer transition-all ${
        !isRevealed
          ? isSelected
            ? 'border-violet-400 bg-violet-50'
            : 'border-slate-200 bg-white hover:border-slate-300'
          : isSelected
            ? option.correct
              ? 'border-emerald-400 bg-emerald-50'
              : 'border-amber-400 bg-amber-50'
            : 'border-slate-100 bg-slate-50 opacity-50'
      }`}
    >
      {/* 选项标识 */}
      <div className="flex items-start gap-3">
        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-sm font-bold ${
          !isRevealed
            ? 'bg-slate-200 text-slate-600'
            : isSelected
              ? option.correct
                ? 'bg-emerald-500 text-white'
                : 'bg-amber-500 text-white'
              : 'bg-slate-200 text-slate-400'
        }`}>
          {option.id}
        </div>

        <div className="flex-1">
          <p className="text-sm text-slate-800 mb-2 leading-relaxed">{option.text}</p>

          {isRevealed && isSelected && (
            <div className="text-xs text-slate-500">
              📝 {option.cost}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function UsePhase({ reflection, title, onSubmit }) {
  const [submitted, setSubmitted] = useState(false);

  return (
    <div className="space-y-6 animate-fadeIn">
      <div className="text-center mb-6">
        <h2 className="text-2xl font-bold text-slate-800 mb-2">✨ {title}</h2>
        <p className="text-slate-500">现在是你的回合——把知识变成行动。</p>
      </div>

      {/* 引导问题 */}
      <div className="bg-white rounded-2xl border border-slate-100 p-6 shadow-sm">
        <label className="block text-sm font-semibold text-slate-700 mb-3">
          {reflection.prompt}
        </label>

        <textarea
          value=""
          readOnly
          placeholder="在这里写下你的思考..."
          rows={4}
          className="w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-xl resize-none focus:outline-none"
        />

        {/* 示例 */}
        {reflection.examples && (
          <details className="mt-4">
            <summary className="cursor-pointer text-xs text-slate-400 hover:text-slate-600">
              💡 参考示例
            </summary>
            <ul className="mt-2 space-y-2">
              {reflection.examples.map((ex, i) => (
                <li key={i} className="text-xs text-slate-600 bg-slate-50 px-3 py-2 rounded-lg">
                  {ex}
                </li>
              ))}
            </ul>
          </details>
        )}
      </div>

      {/* 提交按钮 */}
      {!submitted ? (
        <button
          onClick={() => {
            setSubmitted(true);
            onSubmit();
          }}
          className="w-full py-3 bg-gradient-to-r from-emerald-500 to-teal-500 text-white rounded-xl font-medium hover:shadow-lg transition-all"
        >
          提交我的答案 ✓
        </button>
      ) : (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4 text-center">
          <div className="text-2xl mb-2">✓</div>
          <p className="text-emerald-700 font-medium">{reflection.followUp || '太棒了！继续下一段旅程。'}</p>
        </div>
      )}
    </div>
  );
}

function CardPhase({ card, revealed, onNext }) {
  return (
    <div className={`space-y-6 animate-fadeIn ${revealed ? '' : 'blur-sm'}`}>
      {/* 获取卡牌动画 */}
      <div className="text-center mb-8">
        <div className={`inline-block ${revealed ? 'animate-bounce' : ''}`}>
          <div className="text-6xl mb-4">🃏</div>
          <div className="text-sm text-slate-500">新卡牌解锁</div>
        </div>
      </div>

      {/* 卡牌本体 */}
      <div className={`transform transition-all duration-500 ${
        revealed ? 'scale-100 rotate-0' : 'scale-90 -rotate-6'
      }`}>
        <div className={`bg-gradient-to-br ${card.gradient} rounded-3xl p-8 text-white shadow-2xl`}>
          <div className="text-center mb-6">
            <div className="text-5xl mb-3">{card.icon}</div>
            <h3 className="text-2xl font-bold">{card.name}</h3>
          </div>

          <div className="bg-white/20 backdrop-blur rounded-2xl p-5 mb-4">
            <div className="text-xs text-white/70 mb-1">核心定义</div>
            <p className="leading-relaxed">{card.definition}</p>
          </div>

          <div className="grid grid-cols-2 gap-3 mb-4">
            <div className="bg-white/10 rounded-xl p-3">
              <div className="text-xs text-white/70 mb-1">✅ 正面例子</div>
              <p className="text-xs leading-relaxed">{card.example?.split('\n')[0]}</p>
            </div>
            <div className="bg-white/10 rounded-xl p-3">
              <div className="text-xs text-white/70 mb-1">❌ 反面例子</div>
              <p className="text-xs leading-relaxed">{card.counterExample?.split('\n')[0]}</p>
            </div>
          </div>

          {/* 标签 */}
          <div className="flex flex-wrap gap-2 justify-center">
            {card.tags.map((tag, i) => (
              <span key={i} className="px-3 py-1 bg-white/20 rounded-full text-xs font-medium">
                #{tag}
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* 获得确认 */}
      <button
        onClick={onNext}
        className="w-full py-3 bg-white/20 backdrop-blur text-white rounded-xl font-medium hover:bg-white/30 transition-all"
      >
        收入囊中 →
      </button>
    </div>
  );
}

function IdentityResult({ identity, choices, collectedCards, onClose }) {
  const topTrait = Object.entries(identity.scores).sort((a, b) => b[1] - a[1])[0];

  const traitLabels = {
    actionOriented: '⚡ 行动派',
    deepThinker: '🧠 深思者',
    balanceSeeker: '⚖️ 平衡者',
    identityFocused: '🪞 身份驱动者',
  };

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fadeIn">
      <div className="bg-white rounded-3xl max-w-lg w-full p-8 shadow-2xl relative">
        {/* 关闭按钮 */}
        <button
          onClick={onClose}
          className="absolute top-4 right-4 w-8 h-8 rounded-full bg-slate-100 flex items-center justify-center text-slate-400 hover:text-slate-600"
        >
          ✕
        </button>

        {/* 标题 */}
        <div className="text-center mb-8">
          <div className="text-4xl mb-2">🎭</div>
          <h2 className="text-2xl font-bold text-slate-800 mb-1">你的身份画像</h2>
          <p className="text-sm text-slate-500">基于你在游戏中的所有选择</p>
        </div>

        {/* 主要特质 */}
        <div className="bg-gradient-to-br from-violet-50 to-purple-50 rounded-2xl p-6 text-center mb-6">
          <div className="text-3xl mb-3">{traitLabels[topTrait[0]]}</div>
          <p className="text-sm text-slate-600">
            你是一个{topTrait[0] === 'identityFocused' ? '善于从内在重塑自我' :
                     topTrait[0] === 'actionOriented' ? '相信先做了再说' :
                     topTrait[0] === 'deepThinker' ? '倾向于深入分析再决定' :
                     '在复杂中寻找平衡'}的人。
          </p>
        </div>

        {/* 身份标签 */}
        {identity.labels.length > 0 && (
          <div className="mb-6">
            <div className="text-sm font-semibold text-slate-700 mb-3">你的身份标签</div>
            <div className="flex flex-wrap gap-2">
              {identity.labels.map((label, i) => (
                <span key={i} className="px-4 py-2 bg-slate-100 text-slate-700 rounded-xl text-sm font-medium">
                  {label}
                </span>
              ))}
            </div>
          </div>
        )}

        {/* 统计 */}
        <div className="grid grid-cols-3 gap-3 mb-6">
          <StatItem label="选择数" value={choices.length} icon="↗" />
          <StatItem label="卡牌" value={collectedCards} icon="🃏" />
          <StatItem label="深度" value={`${Math.round((choices.length / 5) * 100)}%`} icon="" />
        </div>

        {/* 开始新篇章 */}
        <button
          onClick={onClose}
          className="w-full py-3 bg-gradient-to-r from-violet-500 to-pink-500 text-white rounded-xl font-medium hover:shadow-lg transition-all"
        >
          开始新的冒险 →
        </button>
      </div>
    </div>
  );
}

function StatItem({ label, value, icon }) {
  return (
    <div className="bg-slate-50 rounded-xl p-4 text-center">
      <div className="text-xl mb-1">{icon}</div>
      <div className="text-xl font-bold text-slate-800">{value}</div>
      <div className="text-xs text-slate-400">{label}</div>
    </div>
  );
}

function GameProgressBar({ total, current, collectedCards, onExit }) {
  const percent = Math.round(((current - 1) / total) * 100);

  return (
    <div className="bg-white border-b border-slate-100 px-6 py-3">
      <div className="flex items-center gap-4">
        {/* 左上角退出按钮 */}
        <button
          onClick={onExit}
          className="px-4 py-1.5 bg-red-50 text-red-600 rounded-lg text-sm font-medium hover:bg-red-100 transition-all border border-red-200 shrink-0"
        >
          ✕ 退出游戏
        </button>

        {/* 书名信息 */}
        <div className="text-sm font-semibold text-slate-700 shrink-0">
          《原子习惯》 · 第一章
        </div>

        {/* 卡牌收集数 */}
        <span className="text-xs text-slate-500 shrink-0">
          🃏 {collectedCards} 张卡牌已收集
        </span>

        {/* 进度条（弹性占满剩余空间） */}
        <div className="flex-1 flex items-center gap-3 ml-4">
          <div className="text-xs text-slate-500 min-w-[40px]">
            {Math.min(current, total)}/{total}
          </div>
          <div className="flex-1">
            <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className="h-full bg-gradient-to-r from-sky-400 to-violet-500 rounded-full transition-all duration-300"
                style={{ width: `${Math.max(0, Math.min(percent, 100))}%` }}
              />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

function ExitConfirmModal({ progress, onConfirm, onCancel }) {
  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4 animate-fadeIn">
      <div className="bg-white rounded-2xl max-w-md w-full p-6 shadow-2xl">
        <div className="text-center mb-4">
          <div className="text-4xl mb-2">🚪</div>
          <h3 className="text-lg font-bold text-slate-800">确定要退出吗？</h3>
          <p className="text-sm text-slate-500 mt-1">
            当前进度：<strong>{progress}</strong> 已完成
          </p>
        </div>

        <div className="bg-slate-50 rounded-xl p-4 mb-6 text-center">
          <p className="text-xs text-slate-600">
            退出后进度会保存，下次可以从这里继续
          </p>
        </div>

        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-2.5 border border-slate-200 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-50 transition-all"
          >
            继续冒险
          </button>
          <button
            onClick={onConfirm}
            className="flex-1 py-2.5 bg-red-500 text-white rounded-xl text-sm font-medium hover:bg-red-600 transition-all"
          >
            确认退出
          </button>
        </div>
      </div>
    </div>
  );
}

function PhaseIndicator({ type }) {
  const phases = {
    teach: { label: '学·认知', icon: '📖', color: 'from-sky-400 to-blue-500' },
    scenario: { label: '练·决策', icon: '🎯', color: 'from-violet-400 to-purple-500' },
    reflection: { label: '用·反思', icon: '💭', color: 'from-emerald-400 to-teal-500' },
    card: { label: '收获·卡牌', icon: '🃏', color: 'from-amber-400 to-orange-500' },
  };

  const phase = phases[type] || phases.teach;

  return (
    <div className="mb-8">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-10 h-10 rounded-xl bg-gradient-to-br ${phase.color} flex items-center justify-center text-lg`}>
          {phase.icon}
        </div>
        <div>
          <div className="font-bold text-slate-800">{phase.label}</div>
        </div>
      </div>
    </div>
  );
}
