import { useState } from 'react';
import { npcs, groupDiscussions } from '../data/mockData';
import NpcAvatar from '../components/NpcAvatar';

export default function GroupDiscussion() {
  const [showCreate, setShowCreate] = useState(false);
  const [selectedNpcs, setSelectedNpcs] = useState([]);
  const [topic, setTopic] = useState('');

  const toggleNpc = (id) => {
    setSelectedNpcs(prev =>
      prev.includes(id) ? prev.filter(n => n !== id) : [...prev, id]
    );
  };

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* 标题 */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-800">💬 圆桌会议</h1>
          <p className="text-slate-500 mt-1 text-sm">
            拉上几个 NPC 智者，来一场思想的碰撞
          </p>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-5 py-2.5 bg-gradient-to-r from-violet-500 to-pink-500 text-white rounded-xl font-medium text-sm hover:shadow-lg hover:shadow-violet-200 transition-all flex items-center gap-2"
        >
          <span>✨</span> 发起讨论
        </button>
      </div>

      {/* 历史讨论列表 */}
      <div className="space-y-4">
        {groupDiscussions.map(discussion => (
          <div
            key={discussion.id}
            className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 card-hover"
          >
            <div className="flex items-start justify-between">
              <div className="flex-1">
                <h3 className="font-bold text-slate-800 text-lg">
                  🎯 {discussion.topic}
                </h3>
                <div className="flex items-center gap-2 mt-2">
                  <div className="flex -space-x-2">
                    {discussion.npcIds.map(npcId => {
                      const npc = npcs.find(n => n.id === npcId);
                      return npc ? (
                        <div key={npcId} className="relative" title={npc.name}>
                          <div className="absolute inset-0 bg-white rounded-full scale-110" />
                          <NpcAvatar npcId={npcId} size="sm" showGlow={false} />
                        </div>
                      ) : null;
                    })}
                  </div>
                  <span className="text-xs text-slate-400">
                    {discussion.npcIds.length} 位参与者
                  </span>
                  <span className="text-xs text-slate-300">·</span>
                  <span className="text-xs text-slate-400">{discussion.date}</span>
                </div>

                <p className="text-sm text-slate-600 mt-4 leading-relaxed">
                  📝 <span className="font-medium">讨论摘要：</span>{discussion.summary}
                </p>

                {discussion.keyDisagreements && (
                  <div className="mt-4">
                    <p className="text-xs font-medium text-slate-500 mb-2">⚡ 分歧点：</p>
                    <ul className="space-y-1">
                      {discussion.keyDisagreements.map((d, i) => (
                        <li key={i} className="text-xs text-slate-500 flex gap-2">
                          <span className="text-amber-400">◆</span>
                          {d}
                        </li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* 发起讨论弹窗 */}
      {showCreate && (
        <div
          className="fixed inset-0 bg-black/40 backdrop-blur-sm flex items-center justify-center z-50"
          onClick={() => setShowCreate(false)}
        >
          <div
            className="bg-white rounded-2xl p-6 w-[520px] shadow-2xl max-h-[90vh] overflow-y-auto"
            onClick={e => e.stopPropagation()}
          >
            <h3 className="text-lg font-bold text-slate-800 mb-4">✨ 发起圆桌讨论</h3>

            {/* 选择 NPC */}
            <div className="mb-5">
              <label className="text-sm text-slate-600 mb-2 block font-medium">
                选择参与者（至少 2 位）
              </label>
              <div className="grid grid-cols-3 gap-2">
                {npcs.map(npc => (
                  <button
                    key={npc.id}
                    onClick={() => toggleNpc(npc.id)}
                    className={`p-3 rounded-xl border-2 transition-all text-center ${
                      selectedNpcs.includes(npc.id)
                        ? 'border-purple-400 bg-purple-50'
                        : 'border-slate-200 bg-white hover:border-slate-300'
                    }`}
                  >
                    <div className="flex justify-center mb-2">
                      <NpcAvatar npcId={npc.id} size="md" showGlow={selectedNpcs.includes(npc.id)} />
                    </div>
                    <div className="text-xs font-medium text-slate-700 truncate">
                      {npc.name}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* 输入主题 */}
            <div className="mb-5">
              <label className="text-sm text-slate-600 mb-2 block font-medium">
                讨论主题
              </label>
              <textarea
                value={topic}
                onChange={e => setTopic(e.target.value)}
                placeholder="例如：AI 是否拥有真正的创造力？"
                rows={3}
                className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent resize-none"
              />
              <div className="flex gap-1.5 mt-2">
                {['如何提升决策质量？', '为什么聪明人也会做蠢事？', '未来的学习方式'].map(suggestion => (
                  <button
                    key={suggestion}
                    onClick={() => setTopic(suggestion)}
                    className="text-[11px] px-2 py-1 bg-slate-100 text-slate-500 rounded-full hover:bg-violet-50 hover:text-violet-600 transition-colors"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>

            {/* 按钮 */}
            <div className="flex gap-2">
              <button
                onClick={() => setShowCreate(false)}
                className="flex-1 py-2.5 border border-slate-200 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-50"
              >
                取消
              </button>
              <button
                disabled={selectedNpcs.length < 2 || !topic.trim()}
                onClick={() => {
                  alert('🎉 讨论已发起！(MVP 版本仅展示历史记录)');
                  setShowCreate(false);
                }}
                className="flex-1 py-2.5 bg-gradient-to-r from-violet-500 to-pink-500 text-white rounded-xl text-sm font-medium hover:shadow-lg disabled:opacity-40 disabled:cursor-not-allowed transition-all"
              >
                开始讨论
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
