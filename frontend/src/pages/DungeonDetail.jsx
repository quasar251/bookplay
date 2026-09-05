import { useParams, useNavigate } from 'react-router-dom';
import { books, chapters, quotes, npcs } from '../data/mockData';
import { useState } from 'react';

export default function DungeonDetail() {
  const { bookId } = useParams();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('chapters');

  const book = books.find(b => b.id === bookId);
  const chapterList = chapters[bookId] || [];
  const quoteList = quotes[bookId] || [];
  const npc = book?.npcId ? npcs.find(n => n.id === book.npcId) : null;

  if (!book) {
    return (
      <div className="p-8 text-center text-slate-500">
        未找到该副本
      </div>
    );
  }

  const progress = (book.completedChapters / book.totalChapters) * 100;
  const isCompleted = book.status === 'completed';
  const isInProgress = book.status === 'in_progress';
  const isNotStarted = book.status === 'not_started';

  // 从章节中提取概念
  const allConcepts = chapterList
    .filter(c => c.concepts?.length)
    .flatMap(c => c.concepts);

  // 获取游戏进度（模拟）
  const getGameStatus = () => {
    if (isCompleted) return 'done';
    if (isInProgress && chapterList.length > 0) {
      const completedChapters = chapterList.filter(c => c.completed).length;
      if (completedChapters === 0) return 'not-started';
      if (completedChapters < chapterList.length) return 'in-progress';
      return 'done';
    }
    return 'not-started';
  };

  const gameStatus = getGameStatus();

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* 返回按钮 */}
      <button
        onClick={() => navigate('/')}
        className="text-sm text-slate-500 hover:text-slate-700 mb-4 flex items-center gap-1"
      >
        ← 返回副本大厅
      </button>

      {/* 顶部书籍信息 + 游戏入口 */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 mb-6">
        <div className="flex gap-6">
          {/* 封面 */}
          <div className={`w-32 h-44 rounded-xl bg-gradient-to-br ${book.coverColor} flex items-center justify-center text-6xl shadow-lg shrink-0 relative overflow-hidden`}>
            {book.cover}
            
            {/* 游戏状态标记 */}
            {gameStatus !== 'done' && (
              <div className="absolute top-2 right-2 bg-black/50 backdrop-blur-sm px-2 py-1 rounded-lg text-xs text-white">
                {gameStatus === 'in-progress' ? '🎮 进行中' : ' 待解锁'}
              </div>
            )}
            {gameStatus === 'done' && (
              <div className="absolute top-2 right-2 bg-emerald-500/90 px-2 py-1 rounded-lg text-xs text-white">
                ✓ 已完成
              </div>
            )}
          </div>

          {/* 信息 */}
          <div className="flex-1">
            <div className="flex items-start justify-between">
              <div>
                <h1 className="text-2xl font-bold text-slate-800">{book.title}</h1>
                <p className="text-slate-500 mt-1">{book.author}</p>
              </div>

              {/* NPC 对话按钮（仅已完成） */}
              {isCompleted && npc && (
                <button
                  onClick={() => navigate(`/npc/${npc.id}`)}
                  className="px-4 py-2 bg-gradient-to-r from-violet-500 to-pink-500 text-white rounded-xl text-sm font-medium hover:shadow-lg transition-all flex items-center gap-1.5"
                >
                  <span>{npc.avatarEmoji}</span> 与 NPC 对话
                </button>
              )}
            </div>

            <p className="text-sm text-slate-500 mt-3 leading-relaxed">{book.description}</p>

            {/* 进度条 */}
            <div className="mt-5">
              <div className="flex justify-between text-sm mb-2">
                <span className="text-slate-600 font-medium">副本进度</span>
                <span className="text-emerald-600 font-semibold">+{book.xpEarned} XP</span>
              </div>
              <div className="h-3 bg-slate-100 rounded-full overflow-hidden">
                <div
                  className={`h-full rounded-full xp-bar-fill ${
                    isCompleted
                      ? 'bg-gradient-to-r from-emerald-400 to-teal-500'
                      : 'bg-gradient-to-r from-sky-400 to-violet-500'
                  }`}
                  style={{ width: `${progress}%` }}
                />
              </div>
              <div className="text-xs text-slate-400 mt-1.5">
                {book.completedChapters} / {book.totalChapters} 章 · {Math.round(progress)}%
              </div>
            </div>

            {/* 数据统计 */}
            <div className="flex gap-6 mt-5 text-sm">
              <div>
                <span className="text-slate-400">💎 概念</span>
                <span className="ml-1.5 font-semibold text-slate-700">{book.conceptCount}</span>
              </div>
              <div>
                <span className="text-slate-400">📝 摘录</span>
                <span className="ml-1.5 font-semibold text-slate-700">{quoteList.length}</span>
              </div>
              <div>
                <span className="text-slate-400">⚔️ 难度</span>
                <span className="ml-1.5 font-semibold text-rose-500">
                  {book.difficulty === 'hard' ? '硬核' : book.difficulty === 'medium' ? '中等' : '简单'}
                </span>
              </div>
            </div>

            {/* 🎮 游戏入口按钮 */}
            {gameStatus === 'done' ? (
              <div className="mt-6 flex items-center gap-2 text-emerald-600 font-medium text-sm">
                <span className="text-xl">🏆</span>
                <span>沉浸体验已完成 — 你可以回顾知识或与 NPC 对话</span>
              </div>
            ) : (
              <button
                onClick={() => navigate(`/book/${bookId}/game`)}
                className={`mt-6 w-full py-3 rounded-xl font-bold text-base flex items-center justify-center gap-2 transition-all ${
                  isInProgress
                    ? 'bg-gradient-to-r from-violet-500 to-purple-600 text-white hover:shadow-lg hover:shadow-violet-200'
                    : 'bg-gradient-to-r from-sky-500 to-blue-600 text-white hover:shadow-lg hover:shadow-sky-200 animate-pulse'
                }`}
              >
                <span className="text-2xl">🎮</span>
                <span>{isInProgress ? '继续沉浸冒险 →' : '开始沉浸式学习 →'}</span>
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Tab 切换 */}
      <div className="flex gap-1 mb-4 bg-white rounded-xl p-1 border border-slate-100 shadow-sm inline-flex">
        {[
          { key: 'chapters', label: '📖 章节列表' },
          { key: 'concepts', label: '💎 概念提取' },
          { key: 'quotes', label: '📝 我的摘录' },
        ].map(tab => (
          <button
            key={tab.key}
            onClick={() => setActiveTab(tab.key)}
            className={`px-5 py-2 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.key
                ? 'bg-gradient-to-r from-sky-500 to-violet-500 text-white shadow'
                : 'text-slate-500 hover:text-slate-700 hover:bg-slate-50'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab 内容 */}
      <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
        {activeTab === 'chapters' && (
          <div className="space-y-2">
            {chapterList.map(ch => (
              <ChapterItem key={ch.index} chapter={ch} isCompleted={isCompleted} />
            ))}
          </div>
        )}

        {activeTab === 'concepts' && (
          <div>
            {allConcepts.length > 0 ? (
              <div className="flex flex-wrap gap-2">
                {allConcepts.map((concept, i) => (
                  <span
                    key={i}
                    className="px-4 py-2 bg-gradient-to-r from-sky-50 to-violet-50 border border-sky-100 text-sky-700 rounded-xl text-sm font-medium"
                  >
                    💎 {concept}
                  </span>
                ))}
              </div>
            ) : (
              <div className="text-center py-10 text-slate-400">
                还没有提取概念，完成章节后自动解锁
              </div>
            )}
          </div>
        )}

        {activeTab === 'quotes' && (
          <div className="space-y-3">
            {quoteList.length > 0 ? (
              quoteList.map(q => (
                <div key={q.id} className="p-4 bg-slate-50 rounded-xl border-l-4 border-violet-400">
                  <p className="text-slate-700 text-sm leading-relaxed italic">"{q.text}"</p>
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-xs text-slate-400">第 {q.chapter} 章</span>
                    <span className="text-xs px-2 py-0.5 bg-violet-100 text-violet-600 rounded-full font-medium">
                      💎 {q.concept}
                    </span>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center py-10 text-slate-400">
                还没有摘录，开始阅读添加你的第一条吧
              </div>
            )}
            <button className="w-full mt-4 py-3 border-2 border-dashed border-slate-200 rounded-xl text-slate-400 text-sm hover:border-sky-400 hover:text-sky-500 transition-all">
              ➕ 添加新摘录
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

function ChapterItem({ chapter, isCompleted: bookCompleted }) {
  const isDone = chapter.completed;

  return (
    <div
      className={`flex items-center gap-4 p-4 rounded-xl transition-all cursor-pointer ${
        isDone ? 'bg-emerald-50/50' : 'bg-slate-50/50 hover:bg-slate-50'
      }`}
    >
      {/* 状态图标 */}
      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm shrink-0 ${
        isDone
          ? 'bg-emerald-500 text-white'
          : 'bg-slate-200 text-slate-400'
      }`}>
        {isDone ? '✓' : chapter.index}
      </div>

      {/* 标题 */}
      <div className="flex-1">
        <h4 className={`text-sm font-medium ${
          isDone ? 'text-slate-700' : 'text-slate-800'
        }`}>
          {chapter.title}
        </h4>
        {chapter.concepts?.length > 0 && (
          <div className="flex gap-1.5 mt-1">
            {chapter.concepts.map((c, i) => (
              <span key={i} className="text-[11px] text-violet-600 bg-violet-50 px-1.5 py-0.5 rounded">
                💎 {c}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* XP */}
      {chapter.xpGained > 0 && (
        <span className="text-xs font-medium text-emerald-600">+{chapter.xpGained} XP</span>
      )}

      {/* 状态标签 */}
      {!isDone && !bookCompleted && (
        <span className="text-xs text-slate-400">未完成 →</span>
      )}
    </div>
  );
}
