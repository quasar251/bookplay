import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';
import NpcAvatar from '../components/NpcAvatar';
import npcAvatarConfig from '../data/npcAvatars';

export default function NpcList() {
  const navigate = useNavigate();
  const [npcs, setNpcs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const items = await api.listNpcs();
        if (!cancelled) setNpcs(items || []);
      } catch (e) {
        if (!cancelled) setError(e.message || '加载 NPC 列表失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* 标题 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">🏛️ NPC 殿堂</h1>
        <p className="text-slate-500 mt-1 text-sm">
          每本通关的书都会在这里留下它的灵魂，与你对话
        </p>
      </div>

      {loading && (
        <div className="grid grid-cols-3 gap-6">
          {[0, 1, 2].map(i => (
            <div key={i} className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden animate-pulse">
              <div className="h-32 bg-slate-100" />
              <div className="p-5 space-y-3">
                <div className="h-4 bg-slate-100 rounded mx-auto w-1/2" />
                <div className="h-3 bg-slate-100 rounded mx-auto w-2/3" />
                <div className="h-2 bg-slate-100 rounded" />
                <div className="h-2 bg-slate-100 rounded w-3/4 mx-auto" />
              </div>
            </div>
          ))}
        </div>
      )}

      {error && !loading && (
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-10 text-center">
          <div className="text-4xl mb-3 opacity-30">🛰️</div>
          <p className="text-slate-500 text-sm">NPC 殿堂暂时无法访问</p>
          <p className="text-xs text-red-400 mt-1">{error}</p>
          <button
            onClick={() => setReloadKey(k => k + 1)}
            className="mt-4 px-5 py-2 bg-gradient-to-r from-indigo-500 to-purple-500 text-white rounded-xl text-sm font-medium hover:shadow-lg transition-all"
          >
            重试
          </button>
        </div>
      )}

      {/* NPC 网格 */}
      {!loading && !error && (
        <div className="grid grid-cols-3 gap-6">
          {npcs.map(npc => {
            const avatarConfig = npcAvatarConfig[npc.id] || npcAvatarConfig.npc1;
            const familiarity = npc.familiarity ?? 0;
            const bookTitle =
              npc.associatedBooks?.[0]?.title || npc.booksAssociated?.[0] || '未知';
            const topicCount = npc.topicsDiscussed?.length ?? 0;
            const conversationCount = npc.conversationCount ?? 0;
            return (
              <div
                key={npc.id}
                onClick={() => navigate(`/npc/${npc.id}`)}
                className="bg-white rounded-2xl shadow-sm border border-slate-100 overflow-visible card-hover cursor-pointer group"
              >
                {/* 头部装饰区 */}
                <div className={`h-26 bg-gradient-to-br ${avatarConfig.gradient} relative flex items-end justify-center pb-7`}>
                  {/* 光斑装饰 */}
                  <div className="absolute top-3 left-4 text-lg opacity-30">{avatarConfig.particleEmoji}</div>
                  <div className="absolute -bottom-6 right-6 text-xl opacity-25">{avatarConfig.particleEmoji}</div>

                  {/* 半悬浮头像 — 上半部在渐变背景里，下半部露出到卡片区域 */}
                  <NpcAvatar npcId={npc.id} size="lg" showGlow={true} animated={true} />
                </div>

                {/* 内容区 */}
                <div className="pt-1 pb-5 px-5 text-center">
                  <h3 className="font-bold text-slate-800 text-lg">{npc.name}</h3>
                  <p className="text-xs text-slate-400 mt-0.5">
                    来自《{bookTitle}》
                  </p>

                  {/* 性格标签 */}
                  <div className="flex flex-wrap justify-center gap-1.5 mt-3">
                    {(npc.personalityTags || []).map((tag, i) => (
                      <span
                        key={i}
                        className="text-[11px] px-2 py-0.5 bg-slate-50 text-slate-500 rounded-full border border-slate-100"
                      >
                        {tag}
                      </span>
                    ))}
                  </div>

                  {/* 熟悉度 */}
                  <div className="mt-4">
                    <div className="flex justify-between text-[11px] text-slate-400 mb-1">
                      <span>💕 熟悉度</span>
                      <span>{Math.round(familiarity * 100)}%</span>
                    </div>
                    <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full bg-gradient-to-r ${avatarConfig.gradient} rounded-full xp-bar-fill`}
                        style={{ width: `${familiarity * 100}%` }}
                      />
                    </div>
                  </div>

                  {/* 讨论话题 / 会话数 */}
                  <div className="mt-4 text-[11px] text-slate-400">
                    聊过 <span className="text-slate-600 font-medium">{topicCount}</span> 个话题
                    <span className="mx-1 text-slate-200">·</span>
                    <span className="text-slate-600 font-medium">{conversationCount}</span> 次对话
                  </div>

                  {/* 关联书 */}
                  {(npc.associatedBooks?.length > 1 || (npc.booksAssociated?.length || 0) > 1) && (
                    <div className="mt-2 text-[11px] text-slate-400">
                      关联 {(npc.associatedBooks?.length || npc.booksAssociated?.length || 0)} 本书
                    </div>
                  )}

                  {/* 对话按钮 */}
                  <button
                    className={`mt-4 w-full py-2 rounded-xl text-sm font-medium bg-gradient-to-r ${avatarConfig.gradient} text-white opacity-0 group-hover:opacity-100 transition-all transform translate-y-1 group-hover:translate-y-0`}
                  >
                    开始对话 →
                  </button>
                </div>
              </div>
            );
          })}

          {/* 空列表占位 */}
          {npcs.length === 0 && (
            <div className="col-span-3 bg-white/50 rounded-2xl border-2 border-dashed border-slate-200 flex flex-col items-center justify-center p-8 min-h-[320px] text-center">
              <div className="text-5xl mb-3 opacity-20">🔮</div>
              <div className="text-slate-400 text-sm font-medium">暂无 NPC 灵魂</div>
              <div className="text-slate-300 text-xs mt-1">通关更多书籍来召唤新的灵魂</div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
