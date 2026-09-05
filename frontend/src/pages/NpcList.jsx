import { useNavigate } from 'react-router-dom';
import { npcs } from '../data/mockData';
import NpcAvatar from '../components/NpcAvatar';
import npcAvatarConfig from '../data/npcAvatars';

export default function NpcList() {
  const navigate = useNavigate();

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* 标题 */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-800">🏛️ NPC 殿堂</h1>
        <p className="text-slate-500 mt-1 text-sm">
          每本通关的书都会在这里留下它的灵魂，与你对话
        </p>
      </div>

      {/* NPC 网格 */}
      <div className="grid grid-cols-3 gap-6">
        {npcs.map(npc => {
          const avatarConfig = npcAvatarConfig[npc.id] || npcAvatarConfig.npc1;
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
                  来自《{npc.booksAssociated[0]}》
                </p>

                {/* 性格标签 */}
                <div className="flex flex-wrap justify-center gap-1.5 mt-3">
                  {npc.personalityTags.map((tag, i) => (
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
                    <span>{Math.round(npc.familiarity * 100)}%</span>
                  </div>
                  <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full bg-gradient-to-r ${avatarConfig.gradient} rounded-full xp-bar-fill`}
                      style={{ width: `${npc.familiarity * 100}%` }}
                    />
                  </div>
                </div>

                {/* 讨论话题 */}
                <div className="mt-4 text-[11px] text-slate-400">
                  聊过 <span className="text-slate-600 font-medium">{npc.topicsDiscussed.length}</span> 个话题
                </div>

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

        {/* 未解锁占位 */}
        <div className="bg-white/50 rounded-2xl border-2 border-dashed border-slate-200 flex flex-col items-center justify-center p-8 min-h-[320px] text-center">
          <div className="text-5xl mb-3 opacity-20">🔮</div>
          <div className="text-slate-400 text-sm font-medium">更多 NPC 待解锁</div>
          <div className="text-slate-300 text-xs mt-1">通关更多书籍来召唤新的灵魂</div>
        </div>
      </div>
    </div>
  );
}
