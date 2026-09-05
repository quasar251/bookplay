import npcAvatarConfig from '../data/npcAvatars';

export default function NpcAvatar({ npcId, size = 'md', showGlow = true, showParticles = false }) {
  const config = npcAvatarConfig[npcId] || npcAvatarConfig.npc1;

  const sizeClasses = {
    sm: 'w-8 h-8 text-sm',
    md: 'w-12 h-12 text-xl',
    lg: 'w-20 h-20 text-4xl',
    xl: 'w-24 h-24 text-5xl',
  };

  const particleSize = {
    sm: 'text-[7px]',
    md: 'text-[9px]',
    lg: 'text-lg',
    xl: 'text-xl',
  };

  return (
    <div className="relative inline-flex items-center justify-center">
      {/* 外层光晕 */}
      {showGlow && (
        <div
          className={`absolute inset-0 rounded-full blur-2xl opacity-50 ${config.bgGradient}`}
          style={{ transform: 'scale(1.25)' }}
        />
      )}

      {/* 白色底圈 */}
      <div className={`${sizeClasses[size]} rounded-full shadow-md`} style={{ backgroundColor: '#fff' }} />

      {/* 主头像圆 */}
      <div
        className={`absolute inset-0 ${sizeClasses[size]} flex items-center justify-center rounded-full ${config.bgGradient} shadow-lg ring-1 ring-white/60`}
      >
        <span className="drop-shadow-sm">{config.emoji}</span>
        {showParticles && (
          <span
            className={`absolute -top-0.5 -right-0.5 ${particleSize[size]} opacity-90`}
            style={{ filter: 'drop-shadow(0 1px 2px rgba(0,0,0,0.2))' }}
          >
            {config.particleEmoji}
          </span>
        )}
      </div>
    </div>
  );
}
