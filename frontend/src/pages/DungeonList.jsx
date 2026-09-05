import { books, user } from '../data/mockData';
import BookCard from '../components/BookCard';
import { useState } from 'react';

export default function DungeonList() {
  const [showRegister, setShowRegister] = useState(false);
  const inProgressBooks = books.filter(b => b.status === 'in_progress');
  const completedBooks = books.filter(b => b.status === 'completed');
  const notStartedBooks = books.filter(b => b.status === 'not_started');

  return (
    <div className="p-8 max-w-6xl mx-auto">
      {/* 顶部欢迎区 */}
      <div className="mb-8">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">
              📚 副本大厅
            </h1>
            <p className="text-slate-500 mt-1 text-sm">
              每本书都是一个副本，通关后召唤它的灵魂 NPC
            </p>
          </div>
          <button
            onClick={() => setShowRegister(true)}
            className="px-5 py-2.5 bg-gradient-to-r from-sky-500 to-violet-500 text-white rounded-xl font-medium text-sm hover:shadow-lg hover:shadow-sky-200 transition-all flex items-center gap-2"
          >
            <span>➕</span> 注册新书
          </button>
        </div>
      </div>

      {/* 快速统计 */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        <StatCard label="进行中" value={inProgressBooks.length} icon="⚔️" color="from-sky-400 to-blue-500" />
        <StatCard label="已通关" value={completedBooks.length} icon="🏆" color="from-emerald-400 to-teal-500" />
        <StatCard label="总 XP" value={user.totalXp} icon="⚡" color="from-amber-400 to-orange-500" />
        <StatCard label="连续打卡" value={`${user.streak} 天`} icon="🔥" color="from-rose-400 to-pink-500" />
      </div>

      {/* 进行中的副本 */}
      {inProgressBooks.length > 0 && (
        <section className="mb-10">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-lg">⚔️</span>
            <h2 className="text-lg font-bold text-slate-800">进行中的副本</h2>
            <span className="text-xs text-slate-400">（继续阅读）</span>
          </div>
          <div className="grid grid-cols-3 gap-5">
            {inProgressBooks.map(book => (
              <BookCard key={book.id} book={book} />
            ))}
          </div>
        </section>
      )}

      {/* 已通关副本 */}
      {completedBooks.length > 0 && (
        <section className="mb-10">
          <div className="flex items-center gap-2 mb-4">
            <span className="text-lg">🏆</span>
            <h2 className="text-lg font-bold text-slate-800">已通关副本</h2>
            <span className="text-xs text-slate-400">（已生成 NPC）</span>
          </div>
          <div className="grid grid-cols-3 gap-5">
            {completedBooks.map(book => (
              <BookCard key={book.id} book={book} />
            ))}
          </div>
        </section>
      )}

      {/* 待开始副本 */}
      {notStartedBooks.length > 0 && (
        <section>
          <div className="flex items-center gap-2 mb-4">
            <span className="text-lg">📦</span>
            <h2 className="text-lg font-bold text-slate-800">待开始副本</h2>
            <span className="text-xs text-slate-400">（准备冒险）</span>
          </div>
          <div className="grid grid-cols-3 gap-5">
            {notStartedBooks.map(book => (
              <BookCard key={book.id} book={book} />
            ))}
          </div>
        </section>
      )}

      {/* 注册新书弹窗 */}
      {showRegister && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50"
          onClick={() => setShowRegister(false)}
        >
          <div
            className="bg-white rounded-2xl p-6 w-[480px] shadow-2xl"
            onClick={e => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold text-slate-800 mb-4">📖 注册新书副本</h3>
            <div className="space-y-4">
              <div>
                <label className="text-sm text-slate-600 mb-1.5 block">书名 / URL</label>
                <input
                  type="text"
                  placeholder="输入书名或粘贴文章链接..."
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-transparent"
                />
              </div>
              <div>
                <label className="text-sm text-slate-600 mb-1.5 block">通关目标</label>
                <div className="grid grid-cols-3 gap-2">
                  {['轻量模式', '标准模式', '硬核模式'].map((mode, i) => (
                    <button
                      key={mode}
                      className={`py-2 rounded-xl text-xs font-medium border transition-all ${
                        i === 1
                          ? 'bg-sky-50 border-sky-400 text-sky-600'
                          : 'bg-white border-slate-200 text-slate-500 hover:border-slate-300'
                      }`}
                    >
                      {mode}
                    </button>
                  ))}
                </div>
                <p className="text-[11px] text-slate-400 mt-1.5">
                  标准模式：每章 1 条摘录 + 1 条感想
                </p>
              </div>
              <div className="flex gap-2 pt-2">
                <button
                  onClick={() => setShowRegister(false)}
                  className="flex-1 py-2.5 border border-slate-200 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-50"
                >
                  取消
                </button>
                <button
                  onClick={() => setShowRegister(false)}
                  className="flex-1 py-2.5 bg-gradient-to-r from-sky-500 to-violet-500 text-white rounded-xl text-sm font-medium hover:shadow-lg"
                >
                  生成副本
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon, color }) {
  return (
    <div className="bg-white rounded-2xl p-4 border border-slate-100 shadow-sm">
      <div className="flex items-center gap-3">
        <div className={`w-11 h-11 rounded-xl bg-gradient-to-br ${color} flex items-center justify-center text-xl`}>
          {icon}
        </div>
        <div>
          <div className="text-xl font-bold text-slate-800">{value}</div>
          <div className="text-xs text-slate-400">{label}</div>
        </div>
      </div>
    </div>
  );
}
