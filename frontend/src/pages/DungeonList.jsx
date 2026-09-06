import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useData } from '../api/DataContext';
import api from '../api/client';
import BookCard from '../components/BookCard';

const STAGE_LABEL = {
  pending: '等待中',
  running: '生成中',
  completed: '已完成',
  failed: '失败',
};

const STAGE_COLOR = {
  pending: 'bg-slate-200',
  running: 'bg-sky-500',
  completed: 'bg-emerald-500',
  failed: 'bg-rose-500',
};

export default function DungeonList() {
  const navigate = useNavigate();
  const { books, user, loading, error, refresh } = useData();
  const [showRegister, setShowRegister] = useState(false);
  // 注册表单
  const [title, setTitle] = useState('');
  const [bookType, setBookType] = useState('non_fiction');
  const [bookText, setBookText] = useState('');
  const [formError, setFormError] = useState('');
  const [submitting, setSubmitting] = useState(false);
  // 生成任务进度
  const [genTask, setGenTask] = useState(null); // { bookId, taskId }
  const [task, setTask] = useState(null);
  const [taskError, setTaskError] = useState('');

  // 轮询生成任务，直至 success / failed
  useEffect(() => {
    if (!genTask) return undefined;
    let cancelled = false;
    let timer = null;

    const poll = async () => {
      let snapshot;
      try {
        snapshot = await api.getTask(genTask.taskId);
      } catch (e) {
        if (cancelled) return;
        setTaskError(e?.message || '查询生成进度失败，正在重试…');
        timer = setTimeout(poll, 2000);
        return;
      }
      if (cancelled) return;

      setTask(snapshot);
      if (snapshot.status === 'success') {
        refresh();
        navigate(`/book/${genTask.bookId}`);
      } else if (snapshot.status === 'failed') {
        setTaskError(snapshot.message || snapshot.error || '生成失败，请稍后重试');
      } else {
        timer = setTimeout(poll, 2000);
      }
    };

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [genTask, navigate, refresh]);

  // 重置注册弹窗状态
  const closeRegister = () => {
    setShowRegister(false);
    setTitle('');
    setBookText('');
    setBookType('non_fiction');
    setFormError('');
    setSubmitting(false);
    setGenTask(null);
    setTask(null);
    setTaskError('');
  };

  const handleStartGenerate = async () => {
    if (submitting) return;
    const trimmedTitle = title.trim();
    const trimmedText = bookText.trim();
    if (!trimmedTitle) {
      setFormError('请填写书名');
      return;
    }
    if (trimmedText.length < 100) {
      setFormError(`正文至少需要 100 字，当前已输入 ${trimmedText.length} 字`);
      return;
    }
    setFormError('');
    setSubmitting(true);
    setTaskError('');
    try {
      const data = await api.registerBook({
        book_title: trimmedTitle,
        book_text: trimmedText,
        book_type: bookType,
      });
      setGenTask({ bookId: data.book_id, taskId: data.task_id });
    } catch (e) {
      setFormError(e?.message || '提交失败，请稍后重试');
      setSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div className="p-8 max-w-6xl mx-auto">
        <div className="flex flex-col items-center justify-center py-40 text-slate-400">
          <div className="text-4xl mb-3 animate-pulse">📚</div>
          <div className="text-sm">书库加载中…</div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-8 max-w-6xl mx-auto">
        <div className="bg-rose-50 border border-rose-200 rounded-2xl p-8 text-center">
          <div className="text-4xl mb-2">😵</div>
          <p className="text-rose-600 font-medium">书库加载失败</p>
          <p className="text-sm text-rose-400 mt-1 mb-5">{error}</p>
          <button
            onClick={refresh}
            className="px-6 py-2.5 bg-rose-500 text-white rounded-xl text-sm font-medium hover:bg-rose-600 transition-all"
          >
            重新加载
          </button>
        </div>
      </div>
    );
  }

  const inProgressBooks = books.filter(b => b.status === 'in_progress');
  const completedBooks = books.filter(b => b.status === 'completed');
  const notStartedBooks = books.filter(b => b.status === 'not_started');

  const isTaskRunning = !!genTask && (!task || (task.status !== 'failed' && task.status !== 'success'));

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
        <StatCard label="总 XP" value={user?.totalXp ?? 0} icon="⚡" color="from-amber-400 to-orange-500" />
        <StatCard label="连续打卡" value={`${user?.streak ?? 0} 天`} icon="🔥" color="from-rose-400 to-pink-500" />
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
          onClick={() => {
            if (!isTaskRunning) closeRegister();
          }}
        >
          <div
            className="bg-white rounded-2xl p-6 w-[520px] shadow-2xl max-h-[90vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            {!genTask ? (
              /* ---------- 表单视图 ---------- */
              <>
                <h3 className="text-lg font-bold text-slate-800 mb-4">📖 注册新书副本</h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-slate-600 mb-1.5 block">书名</label>
                    <input
                      type="text"
                      value={title}
                      onChange={e => setTitle(e.target.value)}
                      placeholder="输入书名，如《思考，快与慢》"
                      className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="text-sm text-slate-600 mb-1.5 block">书籍类型</label>
                    <select
                      value={bookType}
                      onChange={e => setBookType(e.target.value)}
                      className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-transparent bg-white"
                    >
                      <option value="non_fiction">非虚构（认知 / 方法 / 社科）</option>
                      <option value="fiction">虚构（小说 / 故事）</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-sm text-slate-600 mb-1.5 block">书籍正文 / 摘要</label>
                    <textarea
                      value={bookText}
                      onChange={e => setBookText(e.target.value)}
                      placeholder="粘贴书籍正文或你撰写的内容摘要（至少 100 字）…"
                      rows={6}
                      className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-transparent resize-none"
                    />
                    <p className={`text-[11px] mt-1.5 ${bookText.trim().length >= 100 ? 'text-emerald-500' : 'text-slate-400'}`}>
                      已输入 {bookText.trim().length} 字（至少 100 字）
                    </p>
                  </div>

                  {formError && (
                    <div className="bg-rose-50 border border-rose-200 text-rose-600 rounded-xl px-4 py-2.5 text-sm">
                      {formError}
                    </div>
                  )}

                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={closeRegister}
                      disabled={submitting}
                      className="flex-1 py-2.5 border border-slate-200 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-50 disabled:opacity-40"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleStartGenerate}
                      disabled={submitting}
                      className="flex-1 py-2.5 bg-gradient-to-r from-sky-500 to-violet-500 text-white rounded-xl text-sm font-medium hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed transition-all"
                    >
                      {submitting ? '提交中…' : '开始生成'}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              /* ---------- 生成进度视图 ---------- */
              <>
                <h3 className="text-lg font-bold text-slate-800 mb-1">⚙️ 副本生成中</h3>
                <p className="text-sm text-slate-400 mb-5">
                  AI 正在把《{title.trim() || '本书'}》拆解为章节概念并编织沉浸式场景
                </p>

                {!task && !taskError && (
                  <div className="text-center py-6 text-slate-400 text-sm">
                    <div className="text-3xl mb-2 animate-pulse">🧙</div>
                    任务已提交，等待开始…
                  </div>
                )}

                {task && task.status !== 'failed' && (
                  <>
                    {/* 总进度 */}
                    <div className="mb-5">
                      <div className="flex justify-between text-xs text-slate-500 mb-1.5">
                        <span className="font-medium">
                          {task.status === 'success' ? '✅ 全部完成' : task.status === 'running' ? '🏃 生成进行中' : '⏳ 排队中'}
                        </span>
                        <span>{task.progress ?? 0}%</span>
                      </div>
                      <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-sky-400 to-violet-500 transition-all duration-500"
                          style={{ width: `${task.progress ?? 0}%` }}
                        />
                      </div>
                      {task.message && <p className="text-xs text-slate-400 mt-1.5">{task.message}</p>}
                    </div>

                    {/* 各 Agent 阶段 */}
                    {Array.isArray(task.stages) && task.stages.length > 0 && (
                      <div className="space-y-2.5">
                        {task.stages.map((stage, i) => (
                          <div
                            key={stage.agent ?? i}
                            className="flex items-start gap-3 bg-slate-50 rounded-xl p-3"
                          >
                            <span
                              className={`mt-0.5 w-2.5 h-2.5 rounded-full shrink-0 ${STAGE_COLOR[stage.status] || 'bg-slate-200'}`}
                            />
                            <div className="flex-1 min-w-0">
                              <div className="flex justify-between text-xs mb-1">
                                <span className="font-semibold text-slate-700 capitalize">
                                  {stage.agent}
                                </span>
                                <span className="text-slate-400">
                                  {STAGE_LABEL[stage.status] || stage.status} · {stage.progress ?? 0}%
                                </span>
                              </div>
                              {stage.progress > 0 && (
                                <div className="h-1 bg-slate-200 rounded-full overflow-hidden mb-1">
                                  <div
                                    className="h-full bg-sky-500 rounded-full transition-all duration-500"
                                    style={{ width: `${stage.progress ?? 0}%` }}
                                  />
                                </div>
                              )}
                              {stage.message && (
                                <p className="text-[11px] text-slate-400 leading-relaxed">{stage.message}</p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}

                {taskError && (
                  <div className="bg-rose-50 border border-rose-200 text-rose-600 rounded-xl px-4 py-3 text-sm mb-4">
                    <div className="font-medium mb-1">生成失败</div>
                    <p className="text-rose-500">{taskError}</p>
                  </div>
                )}

                {!isTaskRunning && (
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={closeRegister}
                      className="flex-1 py-2.5 border border-slate-200 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-50"
                    >
                      关闭
                    </button>
                  </div>
                )}
              </>
            )}
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
