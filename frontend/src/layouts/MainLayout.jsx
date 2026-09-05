import { NavLink, Outlet } from 'react-router-dom';
import { user } from '../data/mockData';

const navItems = [
  { path: '/', label: '副本大厅', icon: '📚', end: true },
  { path: '/npc', label: 'NPC 列表', icon: '👨‍💻' },
  { path: '/group', label: '群组讨论', icon: '💬' },
  { path: '/graph', label: '认知星图', icon: '✨' },
  { path: '/profile', label: '我的', icon: '👤' },
];

export default function MainLayout() {
  const xpPercent = (user.currentLevelXp / 100) * 100; // 每级100XP

  return (
    <div className="flex h-screen bg-slate-50">
      {/* 侧边栏 */}
      <aside className="w-60 bg-white border-r border-slate-200 flex flex-col">
        {/* Logo */}
        <div className="p-5 border-b border-slate-100">
          <h1 className="text-xl font-bold gradient-text">BookPlay</h1>
          <p className="text-xs text-slate-400 mt-1">游戏化阅读 · 知识冒险</p>
        </div>

        {/* 导航 */}
        <nav className="flex-1 p-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.end}
              className={({ isActive }) =>
                `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all ${
                  isActive
                    ? 'bg-gradient-to-r from-sky-500 to-violet-500 text-white shadow-md shadow-sky-200'
                    : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
                }`
              }
            >
              <span className="text-lg">{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>

        {/* 底部用户信息 */}
        <div className="p-3 border-t border-slate-100">
          <div className="bg-gradient-to-br from-slate-50 to-slate-100 rounded-xl p-3">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-amber-300 to-orange-400 flex items-center justify-center text-xl">
                {user.avatar}
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-sm font-semibold text-slate-800 truncate">
                  {user.username}
                </div>
                <div className="text-xs text-slate-500">
                  Lv.{user.level} · {user.totalXp} XP
                </div>
              </div>
            </div>
            {/* XP 进度条 */}
            <div className="mt-2.5">
              <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-emerald-400 to-teal-500 rounded-full xp-bar-fill"
                  style={{ width: `${xpPercent}%` }}
                />
              </div>
              <div className="text-[10px] text-slate-400 mt-1 text-right">
                {user.currentLevelXp} / 100 XP
              </div>
            </div>
          </div>
        </div>
      </aside>

      {/* 主内容区 */}
      <main className="flex-1 overflow-auto">
        <Outlet />
      </main>
    </div>
  );
}
