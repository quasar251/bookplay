// 全局数据 Provider —— 首屏并行加载 bootstrap + 书库，
// 供侧栏 / 大厅 / NPC 等页面共享；注册新书后调用 refresh() 刷新书库。
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import api from './client';

const DataContext = createContext(null);

export function DataProvider({ children }) {
  const [bootstrap, setBootstrap] = useState(null);
  const [books, setBooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reloadKey, setReloadKey] = useState(0);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const [b, bookItems] = await Promise.all([api.bootstrap(), api.listBooks()]);
      setBootstrap(b);
      setBooks(bookItems);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load, reloadKey]);

  const refresh = useCallback(() => {
    setReloadKey((k) => k + 1);
  }, []);

  const value = useMemo(() => {
    const user = bootstrap?.user ?? null;
    return {
      bootstrap,
      user,
      books,
      loading,
      error,
      refresh,
      // 便捷查询
      getBook: (bookId) => books.find((b) => b.id === bookId) ?? null,
    };
  }, [bootstrap, books, loading, error, refresh]);

  return <DataContext.Provider value={value}>{children}</DataContext.Provider>;
}

export function useData() {
  const ctx = useContext(DataContext);
  if (!ctx) throw new Error('useData must be used within <DataProvider>');
  return ctx;
}
