import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { DataProvider } from './api/DataContext';
import MainLayout from './layouts/MainLayout';
import DungeonList from './pages/DungeonList';
import DungeonDetail from './pages/DungeonDetail';
import NpcList from './pages/NpcList';
import NpcChat from './pages/NpcChat';
import GroupDiscussion from './pages/GroupDiscussion';
import KnowledgeGraph from './pages/KnowledgeGraph';
import Profile from './pages/Profile';
import GameEngine from './pages/GameEngine';

export default function App() {
  return (
    <DataProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<MainLayout />}>
            <Route index element={<DungeonList />} />
            <Route path="book/:bookId" element={<DungeonDetail />} />
            <Route path="npc" element={<NpcList />} />
            <Route path="npc/:npcId" element={<NpcChat />} />
            <Route path="group" element={<GroupDiscussion />} />
            <Route path="graph" element={<KnowledgeGraph />} />
            <Route path="profile" element={<Profile />} />
            <Route path="game" element={<GameEngine />} />
            {/* 带书籍 ID 的游戏入口 */}
            <Route path="book/:bookId/game" element={<GameEngine />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </DataProvider>
  );
}
