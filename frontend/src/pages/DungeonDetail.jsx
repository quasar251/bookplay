import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useData } from '../api/DataContext';
import api from '../api/client';

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

export default function DungeonDetail() {
  const { bookId } = useParams();
  const navigate = useNavigate();
  const { bootstrap, refresh } = useData();
  const npcs = bootstrap?.npcs ?? [];
  const [activeTab, setActiveTab] = useState('chapters');

  // 详情数据（api.getBook）
  const [detail, setDetail] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // "用本书内容生成"弹窗
  const [showGenModal, setShowGenModal] = useState(false);
  const [genTitle, setGenTitle] = useState('');
  const [genType, setGenType] = useState('non_fiction');
  const [genText, setGenText] = useState('');
  const [genFormError, setGenFormError] = useState('');
  const [genSubmitting, setGenSubmitting] = useState(false);
  const [genTask, setGenTask] = useState(null); // { taskId }
  const [genTaskState, setGenTaskState] = useState(null);
  const [genTaskError, setGenTaskError] = useState('');

  // 进入时拉取书籍详情
  useEffect(() => {
    let cancelled = false;
    api.getBook(bookId)
      .then(data => {
        if (cancelled) return;
        setDetail(data);
        setLoading(false);
      })
      .catch(e => {
        if (cancelled) return;
        setError(e?.message || '加载书籍失败');
        setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [bookId]);

  const book = detail?.book ?? null;
  const chapterList = detail?.chapters ?? [];
  const quoteList = detail?.quotes ?? [];
  const hasGame = !!detail?.has_game;
  const generation = book?.generation;
  const genInProgress = !!generation && generation.status === 'in_progress' && !hasGame;

  // 生成中：每 2 秒轮询详情，直到 has_game
  useEffect(() => {
    if (!genInProgress || !bookId) return undefined;
    const timer = setInterval(() => {
      api.getBook(bookId)
        .then(data => setDetail(data))
        .catch(() => {
          // 瞬时错误忽略，继续轮询
        });
    }, 2000);
    return () => clearInterval(timer);
  }, [bookId, genInProgress]);

  // 生成任务轮询（"用本书内容生成"提交后）
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
        setGenTaskError(e?.message || '查询生成进度失败，正在重试…');
        timer = setTimeout(poll, 2000);
        return;
      }
      if (cancelled) return;

      setGenTaskState(snapshot);
      if (snapshot.status === 'success') {
        setGenTaskError('');
        refresh();
        // 刷新详情，让"进入副本"入口出现
        api.getBook(bookId)
          .then(data => setDetail(data))
          .catch(() => {});
        setShowGenModal(false);
      } else if (snapshot.status === 'failed') {
        setGenTaskError(snapshot.message || snapshot.error || '生成失败，请稍后重试');
      } else {
        timer = setTimeout(poll, 2000);
      }
    };

    poll();
    return () => {
      cancelled = true;
      if (timer) clearTimeout(timer);
    };
  }, [bookId, genTask, refresh]);

  // ---------- 渲染 ----------

  if (loading) {
    return (
      <div className="p-8 max-w-5xl mx-auto">
        <div className="flex flex-col items-center justify-center py-40 text-slate-400">
          <div className="text-4xl mb-3 animate-pulse">📚</div>
          <div className="text-sm">副本加载中…</div>
        </div>
      </div>
    );
  }

  if (!book) {
    return (
      <div className="p-8 max-w-5xl mx-auto">
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-10 text-center">
          <div className="text-4xl mb-3">🧭</div>
          <p className="text-slate-600 font-medium">未找到该副本</p>
          <p className="text-sm text-slate-400 mt-1 mb-5">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="px-6 py-2.5 bg-gradient-to-r from-sky-500 to-violet-500 text-white rounded-xl text-sm font-medium hover:shadow-lg transition-all"
          >
            ← 返回副本大厅
          </button>
        </div>
      </div>
    );
  }

  const totalChapters = book.totalChapters || 0;
  const progress = totalChapters ? (book.completedChapters / totalChapters) * 100 : 0;
  const isCompleted = book.status === 'completed';
  const npc = book.npcId ? npcs.find(n => n.id === book.npcId) : null;

  // 从章节中提取概念
  const allConcepts = chapterList
    .filter(c => c.concepts?.length)
    .flatMap(c => c.concepts);

  const openGenModal = () => {
    setGenTitle(book?.title || '');
    setGenType('non_fiction');
    setGenText('');
    setGenFormError('');
    setGenSubmitting(false);
    setGenTask(null);
    setGenTaskState(null);
    setGenTaskError('');
    setShowGenModal(true);
  };

  const closeGenModal = () => {
    setShowGenModal(false);
    setGenTitle('');
    setGenText('');
    setGenType('non_fiction');
    setGenFormError('');
    setGenSubmitting(false);
    setGenTask(null);
    setGenTaskState(null);
    setGenTaskError('');
  };

  const handleStartGenerate = async () => {
    if (genSubmitting) return;
    const trimmedTitle = genTitle.trim();
    const trimmedText = genText.trim();
    if (!trimmedTitle) {
      setGenFormError('请填写书名');
      return;
    }
    if (trimmedText.length < 100) {
      setGenFormError(`正文至少需要 100 字，当前已输入 ${trimmedText.length} 字`);
      return;
    }
    setGenFormError('');
    setGenSubmitting(true);
    setGenTaskError('');
    try {
      const data = await api.generateExisting(bookId, {
        book_title: trimmedTitle,
        book_text: trimmedText,
        book_type: genType,
        max_scenes: 3,
      });
      setGenTask({ taskId: data.task_id });
    } catch (e) {
      setGenFormError(e?.message || '提交失败，请稍后重试');
      setGenSubmitting(false);
    }
  };

  const isGenTaskRunning = !!genTask && (!genTaskState || (genTaskState.status !== 'failed' && genTaskState.status !== 'success'));

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

            {/* 生成 / 可玩状态标记 */}
            {hasGame && (
              <div className="absolute top-2 right-2 bg-emerald-500/90 px-2 py-1 rounded-lg text-xs text-white">
                ✓ 可进入副本
              </div>
            )}
            {!hasGame && genInProgress && (
              <div className="absolute top-2 right-2 bg-sky-500/90 px-2 py-1 rounded-lg text-xs text-white">
                ⚙️ 生成中
              </div>
            )}
            {!hasGame && !genInProgress && (
              <div className="absolute top-2 right-2 bg-black/50 backdrop-blur-sm px-2 py-1 rounded-lg text-xs text-white">
                待解锁
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

              {/* NPC 对话按钮（仅已完成且有 NPC） */}
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

            {/* 🎮 游戏入口 / 生成进度 / 生成入口 */}
            {hasGame ? (
              <button
                onClick={() => navigate(`/book/${bookId}/game`)}
                className="mt-6 w-full py-3 rounded-xl font-bold text-base flex items-center justify-center gap-2 transition-all bg-gradient-to-r from-emerald-500 to-teal-600 text-white hover:shadow-lg hover:shadow-emerald-200"
              >
                <span className="text-2xl">🎮</span>
                <span>进入副本</span>
              </button>
            ) : genInProgress ? (
              <div className="mt-6 bg-sky-50 border border-sky-200 rounded-xl p-4">
                <div className="flex items-center gap-2 text-sky-700 font-medium text-sm">
                  <span className="inline-block w-4 h-4 border-2 border-sky-500 border-t-transparent rounded-full animate-spin" />
                  ⚙️ AI 正在生成沉浸式内容…
                </div>
                {generation?.message && (
                  <p className="text-xs text-sky-600/80 mt-1.5">{generation.message}</p>
                )}
                <div className="h-1.5 bg-sky-100 rounded-full overflow-hidden mt-3">
                  <div className="h-full w-2/3 bg-gradient-to-r from-sky-400 to-violet-500 rounded-full animate-pulse" />
                </div>
                <p className="text-[11px] text-sky-400 mt-1.5">
                  生成完成后会自动出现"进入副本"入口
                </p>
              </div>
            ) : (
              <button
                onClick={openGenModal}
                className="mt-6 w-full py-3 rounded-xl font-bold text-base flex items-center justify-center gap-2 transition-all bg-gradient-to-r from-sky-500 to-blue-600 text-white hover:shadow-lg hover:shadow-sky-200"
              >
                <span className="text-2xl">📜</span>
                <span>用本书内容生成</span>
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
            {chapterList.length > 0 ? (
              chapterList.map(ch => (
                <ChapterItem key={ch.index ?? ch.title} chapter={ch} isCompleted={isCompleted} />
              ))
            ) : (
              <div className="text-center py-10 text-slate-400">
                还没有章节内容，生成后自动解锁
              </div>
            )}
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

      {/* 用本书内容生成弹窗 */}
      {showGenModal && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50"
          onClick={() => {
            if (!isGenTaskRunning) closeGenModal();
          }}
        >
          <div
            className="bg-white rounded-2xl p-6 w-[520px] shadow-2xl max-h-[90vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            {!genTask ? (
              /* ---------- 表单视图 ---------- */
              <>
                <h3 className="text-lg font-bold text-slate-800 mb-4">📜 用本书内容生成副本</h3>
                <div className="space-y-4">
                  <div>
                    <label className="text-sm text-slate-600 mb-1.5 block">书名</label>
                    <input
                      type="text"
                      value={genTitle}
                      onChange={e => setGenTitle(e.target.value)}
                      placeholder="输入书名，如《思考，快与慢》"
                      className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-transparent"
                    />
                  </div>

                  <div>
                    <label className="text-sm text-slate-600 mb-1.5 block">书籍类型</label>
                    <select
                      value={genType}
                      onChange={e => setGenType(e.target.value)}
                      className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-transparent bg-white"
                    >
                      <option value="non_fiction">非虚构（认知 / 方法 / 社科）</option>
                      <option value="fiction">虚构（小说 / 故事）</option>
                    </select>
                  </div>

                  <div>
                    <label className="text-sm text-slate-600 mb-1.5 block">书籍正文 / 摘要</label>
                    <textarea
                      value={genText}
                      onChange={e => setGenText(e.target.value)}
                      placeholder="粘贴本书正文或摘要（至少 100 字）…"
                      rows={6}
                      className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-transparent resize-none"
                    />
                    <p className={`text-[11px] mt-1.5 ${genText.trim().length >= 100 ? 'text-emerald-500' : 'text-slate-400'}`}>
                      已输入 {genText.trim().length} 字（至少 100 字）
                    </p>
                  </div>

                  {genFormError && (
                    <div className="bg-rose-50 border border-rose-200 text-rose-600 rounded-xl px-4 py-2.5 text-sm">
                      {genFormError}
                    </div>
                  )}

                  <div className="flex gap-2 pt-1">
                    <button
                      onClick={closeGenModal}
                      disabled={genSubmitting}
                      className="flex-1 py-2.5 border border-slate-200 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-50 disabled:opacity-40"
                    >
                      取消
                    </button>
                    <button
                      onClick={handleStartGenerate}
                      disabled={genSubmitting}
                      className="flex-1 py-2.5 bg-gradient-to-r from-sky-500 to-violet-500 text-white rounded-xl text-sm font-medium hover:shadow-lg disabled:opacity-60 disabled:cursor-not-allowed transition-all"
                    >
                      {genSubmitting ? '提交中…' : '开始生成'}
                    </button>
                  </div>
                </div>
              </>
            ) : (
              /* ---------- 生成进度视图 ---------- */
              <>
                <h3 className="text-lg font-bold text-slate-800 mb-1">⚙️ 副本生成中</h3>
                <p className="text-sm text-slate-400 mb-5">
                  AI 正在把《{genTitle.trim() || '本书'}》拆解为章节概念并编织沉浸式场景
                </p>

                {!genTaskState && !genTaskError && (
                  <div className="text-center py-6 text-slate-400 text-sm">
                    <div className="text-3xl mb-2 animate-pulse">🧙</div>
                    任务已提交，等待开始…
                  </div>
                )}

                {genTaskState && genTaskState.status !== 'failed' && (
                  <>
                    {/* 总进度 */}
                    <div className="mb-5">
                      <div className="flex justify-between text-xs text-slate-500 mb-1.5">
                        <span className="font-medium">
                          {genTaskState.status === 'success'
                            ? '✅ 全部完成'
                            : genTaskState.status === 'running'
                              ? '🏃 生成进行中'
                              : '⏳ 排队中'}
                        </span>
                        <span>{genTaskState.progress ?? 0}%</span>
                      </div>
                      <div className="h-2.5 bg-slate-100 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-gradient-to-r from-sky-400 to-violet-500 transition-all duration-500"
                          style={{ width: `${genTaskState.progress ?? 0}%` }}
                        />
                      </div>
                      {genTaskState.message && (
                        <p className="text-xs text-slate-400 mt-1.5">{genTaskState.message}</p>
                      )}
                    </div>

                    {/* 各 Agent 阶段 */}
                    {Array.isArray(genTaskState.stages) && genTaskState.stages.length > 0 && (
                      <div className="space-y-2.5">
                        {genTaskState.stages.map((stage, i) => (
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
                                <p className="text-[11px] text-slate-400 leading-relaxed">
                                  {stage.message}
                                </p>
                              )}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                )}

                {genTaskError && (
                  <div className="bg-rose-50 border border-rose-200 text-rose-600 rounded-xl px-4 py-3 text-sm mb-4">
                    <div className="font-medium mb-1">生成失败</div>
                    <p className="text-rose-500">{genTaskError}</p>
                  </div>
                )}

                {!isGenTaskRunning && (
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={closeGenModal}
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
