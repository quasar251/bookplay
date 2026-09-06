// 统一 API 客户端 —— 所有页面请求经由此层
// - baseURL: 开发走 Vite 代理（/api → 后端），生产可配置 VITE_API_BASE_URL
// - 统一错误处理：网络异常 / 非 2xx → 抛出 ApiError（含可读 message）
// - GenerateResponse 包装：POST /api/books、/api/npc/chat 等返回
//   { code, message, data, metadata, timestamp }，本层自动解包返回 data

const BASE_URL = (import.meta.env?.VITE_API_BASE_URL ?? '').replace(/\/$/, '');

export class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request(path, { method = 'GET', body } = {}) {
  const url = `${BASE_URL}${path}`;
  let res;
  try {
    res = await fetch(url, {
      method,
      headers: body !== undefined ? { 'Content-Type': 'application/json' } : undefined,
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, '无法连接后端服务，请确认服务已启动');
  }

  const text = await res.text();
  let data = null;
  try {
    data = text ? JSON.parse(text) : null;
  } catch {
    data = null;
  }

  if (!res.ok) {
    const detail = data && (data.detail ?? data.message);
    throw new ApiError(res.status, detail || `请求失败（${res.status}）`);
  }
  return data;
}

// 兼容旧返回：GET 类接口直接返回业务对象；POST 业务接口统一包一层
function unwrap(payload) {
  if (payload && typeof payload === 'object' && 'code' in payload && 'data' in payload) {
    return payload.data;
  }
  return payload;
}

export const api = {
  // ---- bootstrap / 档案 ----
  bootstrap: () => request('/api/bootstrap'),
  profile: () => request('/api/profile'),
  graph: () => request('/api/graph'),
  groupDiscussions: () => request('/api/group-discussions'),

  // ---- 书库 ----
  listBooks: async () => {
    const data = await request('/api/books');
    return data.items ?? [];
  },
  getBook: (bookId) => request(`/api/books/${bookId}`),
  getBookGame: (bookId) => request(`/api/books/${bookId}/game`),
  registerBook: async (payload) =>
    unwrap(await request('/api/books', { method: 'POST', body: payload })),
  generateExisting: async (bookId, payload) =>
    unwrap(await request(`/api/books/${bookId}/generate`, { method: 'POST', body: payload })),

  // ---- NPC ----
  listNpcs: async () => {
    const data = await request('/api/npcs');
    return data.items ?? [];
  },
  getNpc: (npcId) => request(`/api/npcs/${npcId}`),
  getNpcConversations: async (npcId) => {
    const data = await request(`/api/npcs/${npcId}/conversations`);
    return data.items ?? [];
  },
  npcChat: async (payload) => unwrap(await request('/api/npc/chat', { method: 'POST', body: payload })),

  // ---- 任务 ----
  getTask: (taskId) => request(`/api/tasks/${taskId}`),
};

export default api;
