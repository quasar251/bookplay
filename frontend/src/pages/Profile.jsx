import { useEffect, useState } from 'react';
import api from '../api/client';

export default function Profile() {
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const data = await api.profile();
        if (!cancelled) setProfile(data);
      } catch (e) {
        if (!cancelled) setError(e.message || '加载个人资料失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  if (loading) {
    return (
      <div className="p-8 max-w-5xl mx-auto">
        <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-16 flex flex-col items-center justify-center text-slate-400">
          <div className="inline-block w-8 h-8 border-4 border-slate-200 border-t-violet-500 rounded-full animate-spin mb-3" />
          <div className="text-sm">正在读取个人档案...</div>
        </div>
      </div>
    );
  }

  if (error || !profile) {
    return (
      <div className="p-8 max-w-5xl mx-auto">
        <div className="bg-white rounded-3xl border border-slate-100 shadow-sm p-12 text-center">
          <div className="text-4xl mb-3 opacity-30">🛰️</div>
          <p className="text-slate-500 text-sm">个人资料暂时无法访问</p>
          <p className="text-xs text-red-400 mt-1">{error}</p>
          <button
            onClick={() => setReloadKey(k => k + 1)}
            className="mt-4 px-5 py-2 bg-gradient-to-r from-violet-500 to-pink-500 text-white rounded-xl text-sm font-medium hover:shadow-lg transition-all"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  const { user, userProfile, achievements, skillTree } = profile;
  const xpPercent = (user.currentLevelXp / 100) * 100;

  return (
    <div className="p-8 max-w-5xl mx-auto">
      {/* 顶部个人信息卡片 */}
      <div className="bg-gradient-to-r from-sky-500 via-violet-500 to-pink-500 rounded-3xl p-8 mb-8 text-white relative overflow-hidden">
        {/* 装饰 */}
        <div className="absolute top-0 right-0 w-64 h-64 bg-white/10 rounded-full -translate-y-1/2 translate-x-1/2" />
        <div className="absolute bottom-0 left-0 w-48 h-48 bg-white/5 rounded-full translate-y-1/2 -translate-x-1/2" />

        <div className="relative flex items-center gap-6">
          <div className="w-24 h-24 rounded-2xl bg-white/20 backdrop-blur flex items-center justify-center text-5xl shadow-lg">
            {user.avatar}
          </div>
          <div className="flex-1">
            <h1 className="text-2xl font-bold">{user.username}</h1>
            <div className="flex items-center gap-3 mt-2">
              <span className="px-3 py-1 bg-white/20 rounded-full text-sm font-medium backdrop-blur">
                ⭐ Lv.{user.level}
              </span>
              <span className="text-white/80 text-sm">
                累计 {user.totalXp} XP
              </span>
              <span className="text-white/80 text-sm">
                🔥 {user.streak} 天连续打卡
              </span>
            </div>

            {/* XP 进度条 */}
            <div className="mt-4 max-w-md">
              <div className="flex justify-between text-xs text-white/70 mb-1.5">
                <span>Lv.{user.level}</span>
                <span>{user.currentLevelXp} / 100 XP</span>
                <span>Lv.{user.level + 1}</span>
              </div>
              <div className="h-2.5 bg-white/20 rounded-full overflow-hidden backdrop-blur">
                <div
                  className="h-full bg-white rounded-full xp-bar-fill"
                  style={{ width: `${xpPercent}%` }}
                />
              </div>
            </div>
          </div>

          {/* 快速数据 */}
          <div className="grid grid-cols-2 gap-4">
            <QuickStat label="书籍" value={user.totalBooks} icon="📚" />
            <QuickStat label="已通关" value={user.completedBooks} icon="🏆" />
            <QuickStat label="概念" value={user.totalConcepts} icon="💎" />
            <QuickStat label="NPC" value={user.totalNpcs} icon="🧠" />
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* 左侧：成就 */}
        <div className="col-span-2">
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-bold text-slate-800 text-lg">🏅 成就墙</h2>
              <span className="text-sm text-slate-400">
                已解锁 {achievements.filter(a => a.unlocked).length} / {achievements.length}
              </span>
            </div>

            <div className="grid grid-cols-4 gap-4">
              {achievements.map(achievement => (
                <AchievementCard key={achievement.id} achievement={achievement} />
              ))}
            </div>
          </div>

          {/* 技能树 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-6 mt-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="font-bold text-slate-800 text-lg">🌳 技能树</h2>
              <span className="text-sm text-slate-400">
                共 {skillTree.branches.length} 个分支
              </span>
            </div>

            <div className="space-y-5">
              {skillTree.branches.map(branch => (
                <div key={branch.id}>
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      <div
                        className="w-3 h-3 rounded-full"
                        style={{ backgroundColor: branch.color }}
                      />
                      <span className="text-sm font-semibold text-slate-700">
                        {branch.name}
                      </span>
                      <span className="text-xs px-2 py-0.5 bg-slate-100 text-slate-500 rounded-full">
                        Lv.{branch.level}
                      </span>
                    </div>
                    <span className="text-xs text-slate-400">
                      {branch.concepts.length} 个概念
                    </span>
                  </div>
                  <div className="h-2 bg-slate-100 rounded-full overflow-hidden mb-2.5">
                    <div
                      className="h-full rounded-full xp-bar-fill"
                      style={{
                        width: `${Math.min(branch.concepts.length * 10, 100)}%`,
                        backgroundColor: branch.color,
                      }}
                    />
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {branch.concepts.map((concept, i) => (
                      <span
                        key={i}
                        className="text-[11px] px-2 py-0.5 rounded-full bg-slate-50 text-slate-500 border border-slate-100"
                      >
                        {concept}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 右侧：用户画像 */}
        <div className="space-y-6">
          {/* 学习风格 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
            <h3 className="font-bold text-slate-800 text-sm mb-4">🧠 学习风格</h3>
            <div className="text-center py-3">
              <div className="text-3xl mb-1">🔍</div>
              <div className="text-lg font-bold text-slate-800">
                {userProfile.learningStyle}
              </div>
              <div className="text-xs text-slate-400 mt-1">
                擅长通过案例和归纳理解概念
              </div>
            </div>
            <button className="w-full mt-3 py-2 text-xs text-slate-400 hover:text-violet-500 border border-dashed border-slate-200 rounded-xl hover:border-violet-300 transition-all">
              ✏️ 手动修正
            </button>
          </div>

          {/* 偏好主题 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
            <h3 className="font-bold text-slate-800 text-sm mb-3">❤️ 偏好主题</h3>
            <div className="flex flex-wrap gap-1.5">
              {(userProfile.preferredTopics || []).map((topic, i) => (
                <span
                  key={i}
                  className="text-xs px-2.5 py-1 bg-gradient-to-r from-pink-50 to-violet-50 text-violet-600 rounded-full font-medium border border-violet-100"
                >
                  {topic}
                </span>
              ))}
            </div>
          </div>

          {/* 阅读模式 */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-100 p-5">
            <h3 className="font-bold text-slate-800 text-sm mb-4">📊 阅读数据</h3>
            <div className="space-y-3">
              <DataRow label="日均阅读" value={`${userProfile.readingPatterns.avgDailyMinutes} 分钟`} />
              <DataRow label="最活跃时段" value={userProfile.readingPatterns.mostActiveHour} />
              <DataRow
                label="完成率"
                value={`${Math.round(userProfile.readingPatterns.completionRate * 100)}%`}
              />
            </div>
          </div>

          {/* 加入时间 */}
          <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-2xl p-5 text-center">
            <div className="text-xs text-slate-400">加入 BookPlay</div>
            <div className="text-lg font-bold text-slate-700 mt-1">{user.joinDate}</div>
            <div className="text-xs text-slate-400 mt-0.5">已经探索了 82 天</div>
          </div>
        </div>
      </div>
    </div>
  );
}

function QuickStat({ label, value, icon }) {
  return (
    <div className="bg-white/15 backdrop-blur rounded-xl px-4 py-3 text-center">
      <div className="text-2xl mb-0.5">{icon}</div>
      <div className="text-lg font-bold">{value}</div>
      <div className="text-[11px] text-white/70">{label}</div>
    </div>
  );
}

function AchievementCard({ achievement }) {
  const unlocked = achievement.unlocked;

  return (
    <div
      className={`rounded-xl p-4 text-center border transition-all ${
        unlocked
          ? 'bg-gradient-to-br from-amber-50 to-orange-50 border-amber-100'
          : 'bg-slate-50 border-slate-100 opacity-60'
      }`}
    >
      <div className={`text-3xl mb-2 ${unlocked ? '' : 'grayscale'}`}>
        {achievement.icon}
      </div>
      <div className={`text-sm font-semibold ${unlocked ? 'text-slate-700' : 'text-slate-400'}`}>
        {achievement.name}
      </div>
      <div className="text-[11px] text-slate-400 mt-1">
        {achievement.description}
      </div>
      {!unlocked && achievement.progress !== undefined && (
        <div className="mt-2">
          <div className="h-1 bg-slate-200 rounded-full overflow-hidden">
            <div
              className="h-full bg-slate-400 rounded-full"
              style={{ width: `${(achievement.progress / achievement.target) * 100}%` }}
            />
          </div>
          <div className="text-[10px] text-slate-400 mt-1">
            {achievement.progress} / {achievement.target}
          </div>
        </div>
      )}
      {unlocked && (
        <div className="text-[10px] text-amber-500 mt-2 font-medium">
          ✓ {achievement.unlockedAt}
        </div>
      )}
    </div>
  );
}

function DataRow({ label, value }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-xs text-slate-400">{label}</span>
      <span className="text-sm font-semibold text-slate-700">{value}</span>
    </div>
  );
}
