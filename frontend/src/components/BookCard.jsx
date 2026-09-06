import { useNavigate } from 'react-router-dom';

export default function BookCard({ book }) {
  const navigate = useNavigate();
  const totalChapters = book.totalChapters || 0;
  const progress = totalChapters ? (book.completedChapters / totalChapters) * 100 : 0;
  const isCompleted = book.status === 'completed';
  const isNotStarted = book.status === 'not_started';
  const genStatus = book.generation?.status;
  const isGenerating = genStatus === 'in_progress';
  const genFailed = genStatus === 'failed';

  const difficultyLabel = {
    easy: '简单',
    medium: '中等',
    hard: '硬核',
  };

  const difficultyColor = {
    easy: 'bg-green-100 text-green-700',
    medium: 'bg-amber-100 text-amber-700',
    hard: 'bg-rose-100 text-rose-700',
  };

  return (
    <div
      onClick={() => navigate(`/book/${book.id}`)}
      className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden card-hover cursor-pointer"
    >
      {/* 封面区 */}
      <div className={`h-32 bg-gradient-to-br ${book.coverColor} flex items-center justify-center relative`}>
        <span className="text-5xl">{book.cover}</span>
        {isGenerating && (
          <div className="absolute top-2 right-2 bg-white/90 backdrop-blur px-2 py-0.5 rounded-full text-xs font-medium text-sky-600">
            ⚙️ 生成中…
          </div>
        )}
        {!isGenerating && genFailed && (
          <div className="absolute top-2 right-2 bg-white/90 backdrop-blur px-2 py-0.5 rounded-full text-xs font-medium text-rose-600">
            生成失败
          </div>
        )}
        {!isGenerating && !genFailed && isCompleted && (
          <div className="absolute top-2 right-2 bg-white/90 backdrop-blur px-2 py-0.5 rounded-full text-xs font-medium text-emerald-600">
            ✓ 已通关
          </div>
        )}
        {!isGenerating && !genFailed && isNotStarted && (
          <div className="absolute top-2 right-2 bg-white/90 backdrop-blur px-2 py-0.5 rounded-full text-xs font-medium text-slate-500">
            待开始
          </div>
        )}
        <div className="absolute bottom-2 left-2">
          <span className={`text-[10px] px-2 py-0.5 rounded-full font-medium ${difficultyColor[book.difficulty]}`}>
            {difficultyLabel[book.difficulty]}
          </span>
        </div>
      </div>

      {/* 信息区 */}
      <div className="p-4">
        <h3 className="font-bold text-slate-800 text-base truncate">{book.title}</h3>
        <p className="text-xs text-slate-500 mt-0.5">{book.author}</p>

        <p className="text-xs text-slate-400 mt-2 line-clamp-2 h-8">{book.description}</p>

        {/* 进度条 */}
        {!isNotStarted && totalChapters > 0 && (
          <div className="mt-3">
            <div className="flex justify-between text-[11px] text-slate-500 mb-1">
              <span>{book.completedChapters} / {book.totalChapters} 章</span>
              <span className="font-medium text-emerald-600">+{book.xpEarned} XP</span>
            </div>
            <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
              <div
                className={`h-full rounded-full xp-bar-fill ${
                  isCompleted
                    ? 'bg-gradient-to-r from-emerald-400 to-teal-500'
                    : 'bg-gradient-to-r from-sky-400 to-violet-500'
                }`}
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* 底部数据 */}
        <div className="mt-3 pt-3 border-t border-slate-50 flex justify-between text-[11px] text-slate-400">
          <span>💎 {book.conceptCount} 概念</span>
          {isCompleted && book.npcId && (
            <span className="text-violet-500 font-medium">✨ 已生成 NPC</span>
          )}
        </div>
      </div>
    </div>
  );
}
