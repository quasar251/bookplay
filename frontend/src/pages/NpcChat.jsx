import { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../api/client';
import NpcAvatar from '../components/NpcAvatar';
import npcAvatarConfig from '../data/npcAvatars';

const FALLBACK_ICEBREAKERS = [
  '你最核心的观点是什么？',
  '给我举个日常的例子吧',
  '你和其他 NPC 有什么不同？',
];

export default function NpcChat() {
  const { npcId } = useParams();
  const navigate = useNavigate();

  // 档案与可用数据
  const [npc, setNpc] = useState(null);
  const [books, setBooks] = useState([]);
  const [selectedBookId, setSelectedBookId] = useState('');
  const [seedQuestions, setSeedQuestions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);

  // 当前会话
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [chatError, setChatError] = useState('');
  const chatEndRef = useRef(null);

  // 拉取 NPC 档案 + 可用书 + 历史对话种子
  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      setChatError('');
      try {
        const [npcRes, bookItems, convItems] = await Promise.all([
          api.getNpc(npcId),
          api.listBooks(),
          api.getNpcConversations(npcId),
        ]);
        if (cancelled) return;
        const npcData = npcRes.npc;
        const bookList = bookItems || [];
        setNpc(npcData);
        setBooks(bookList);
        setSeedQuestions(convItems || []);
        // 默认书：档案关联书第一本 → 该 NPC 名下的书 → 书库第一本
        const preferredId =
          npcData?.associatedBooks?.[0]?.id ||
          bookList.find(b => b.npcId === npcData?.id)?.id ||
          bookList[0]?.id ||
          '';
        setSelectedBookId(preferredId);
        setMessages(npcData?.greeting ? [{ role: 'npc', content: npcData.greeting }] : []);
      } catch (e) {
        if (!cancelled) setError(e.message || '加载 NPC 档案失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [npcId, reloadKey]);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isSending]);

  const handleSend = async (text) => {
    const msg = (text ?? input).trim();
    if (!msg || isSending || !selectedBookId) return;

    setChatError('');
    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    setInput('');
    setIsSending(true);
    try {
      const data = await api.npcChat({
        message: msg,
        book_id: selectedBookId,
        npc_id: npcId,
        npc_name: npc?.name || '',
        top_k: 3,
        min_score: 0.0,
        allow_free_talk: true,
      });
      setMessages(prev => [
        ...prev,
        {
          role: 'npc',
          content: data.reply || '（未收到回复）',
          intent: data.intent,
          citations: data.citations || [],
          hasReference: Boolean(data.has_reference),
          freeTalk: Boolean(data.free_talk),
        },
      ]);
    } catch (e) {
      // 回滚用户消息并把输入还原，方便重试
      setMessages(prev => prev.slice(0, -1));
      setInput(msg);
      setChatError(e.message || '发送失败，请稍后再试');
    } finally {
      setIsSending(false);
    }
  };

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center text-slate-400">
          <div className="inline-block w-8 h-8 border-4 border-slate-200 border-t-violet-500 rounded-full animate-spin mb-3" />
          <div className="text-sm">正在召唤 NPC 的灵魂...</div>
        </div>
      </div>
    );
  }

  if (error || !npc) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="bg-white rounded-2xl border border-slate-100 shadow-sm p-10 text-center max-w-md mx-auto">
          <div className="text-4xl mb-3 opacity-30">👻</div>
          <p className="text-slate-500 text-sm">{error || '未找到该 NPC'}</p>
          <div className="flex gap-2 justify-center mt-4">
            <button
              onClick={() => navigate('/npc')}
              className="px-4 py-2 border border-slate-200 text-slate-600 rounded-xl text-sm font-medium hover:bg-slate-50"
            >
              ← 返回 NPC 列表
            </button>
            <button
              onClick={() => setReloadKey(k => k + 1)}
              className="px-4 py-2 bg-gradient-to-r from-violet-500 to-purple-500 text-white rounded-xl text-sm font-medium hover:shadow-lg transition-all"
            >
              重试
            </button>
          </div>
        </div>
      </div>
    );
  }

  const familiarityPercent = Math.round((npc.familiarity ?? 0) * 100);
  const avatarConfig = npcAvatarConfig[npc.id] || npcAvatarConfig.npc1;
  const icebreakers =
    seedQuestions.length > 0
      ? seedQuestions.map(c => c.userMessage)
      : FALLBACK_ICEBREAKERS;
  const noBookAvailable = books.length === 0 && !selectedBookId;

  return (
    <div className="h-full flex">
      {/* 左侧 NPC 信息面板 */}
      <div className="w-72 bg-white border-r border-slate-200 p-6 flex flex-col overflow-y-auto">
        <button
          onClick={() => navigate('/npc')}
          className="text-sm text-slate-400 hover:text-slate-600 mb-4 flex items-center gap-1"
        >
          ← 返回 NPC 列表
        </button>

        {/* NPC 头像 */}
        <div className="text-center">
          <div className="mx-auto w-fit">
            <NpcAvatar npcId={npc.id} size="xl" showGlow={true} animated={true} />
          </div>
          <h2 className="mt-4 text-lg font-bold text-slate-800">{npc.name}</h2>
          <p className="text-xs text-slate-400 mt-0.5">
            来自《{npc.associatedBooks?.[0]?.title || npc.booksAssociated?.[0] || '未知'}》
          </p>
        </div>

        {/* 性格标签 */}
        <div className="flex flex-wrap justify-center gap-1.5 mt-4">
          {(npc.personalityTags || []).map((tag, i) => (
            <span
              key={i}
              className="text-[11px] px-2.5 py-0.5 bg-slate-50 text-slate-600 rounded-full font-medium border border-slate-100"
            >
              {tag}
            </span>
          ))}
        </div>

        {/* 熟悉度 */}
        <div className="mt-6">
          <div className="flex justify-between text-xs text-slate-500 mb-1.5">
            <span>💕 熟悉度</span>
            <span>{familiarityPercent}%</span>
          </div>
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r ${avatarConfig.gradient} rounded-full xp-bar-fill`}
              style={{ width: `${familiarityPercent}%` }}
            />
          </div>
        </div>

        {/* 正在聊的书 */}
        <div className="mt-6">
          <h4 className="text-xs font-semibold text-slate-500 mb-2">📚 正在聊的书</h4>
          {noBookAvailable ? (
            <p className="text-xs text-slate-400 leading-relaxed">
              暂无可用书籍，请先在书库中创建/生成一本书再回来聊聊。
            </p>
          ) : (
            <select
              value={selectedBookId}
              onChange={e => setSelectedBookId(e.target.value)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent"
            >
              {books.map(b => (
                <option key={b.id} value={b.id}>
                  {b.title}
                </option>
              ))}
            </select>
          )}
        </div>

        {/* 核心信念 */}
        <div className="mt-6">
          <h4 className="text-xs font-semibold text-slate-500 mb-2">💡 核心信念</h4>
          <ul className="space-y-1.5">
            {(npc.coreBeliefs || []).map((belief, i) => (
              <li key={i} className="text-xs text-slate-600 leading-relaxed flex gap-1.5">
                <span className="text-slate-400 shrink-0">◆</span>
                {belief}
              </li>
            ))}
          </ul>
        </div>

        {/* 聊过的话题 */}
        <div className="mt-6">
          <h4 className="text-xs font-semibold text-slate-500 mb-2">🗣️ 聊过的话题</h4>
          <div className="flex flex-wrap gap-1.5">
            {(npc.topicsDiscussed || []).map((topic, i) => (
              <span
                key={i}
                className="text-[11px] px-2 py-0.5 bg-slate-100 text-slate-600 rounded-full"
              >
                {topic}
              </span>
            ))}
          </div>
        </div>

        <div className="mt-auto pt-4 text-[10px] text-slate-300 text-center">
          语气：{npc.tone}
        </div>
      </div>

      {/* 右侧聊天区 */}
      <div className="flex-1 flex flex-col bg-slate-50">
        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.map((msg, i) => (
            <ChatBubble key={i} msg={msg} npc={npc} />
          ))}
          {isSending && (
            <div className="flex gap-3">
              <NpcAvatar npcId={npc.id} size="sm" showGlow={false} />
              <div className="bg-white rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border border-slate-100">
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-slate-300 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          )}
          <div ref={chatEndRef} />
        </div>

        {chatError && (
          <div className="px-6 pb-3">
            <div className="text-xs text-red-500 bg-red-50 border border-red-100 rounded-xl px-4 py-2.5">
              ⚠️ {chatError}
            </div>
          </div>
        )}

        {/* 开场示例问题（历史对话种子，点击即发送） */}
        {messages.length <= 1 && !isSending && (
          <div className="px-6 pb-3">
            <p className="text-xs text-slate-400 mb-2">💡 试试问这些：</p>
            <div className="flex gap-2 flex-wrap">
              {icebreakers.map((q, i) => (
                <button
                  key={`${q}-${i}`}
                  onClick={() => handleSend(q)}
                  disabled={isSending || noBookAvailable}
                  className="px-3 py-1.5 bg-white border border-slate-200 rounded-full text-xs text-slate-600 hover:border-violet-300 hover:text-violet-600 hover:bg-violet-50 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* 输入框 */}
        <div className="p-4 border-t border-slate-200 bg-white">
          <div className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && !isSending && handleSend()}
              placeholder={noBookAvailable ? '暂无可聊的书，先去书库创建一本吧' : '和这位智者聊聊吧...'}
              disabled={isSending || noBookAvailable}
              className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent disabled:opacity-60 disabled:cursor-not-allowed"
            />
            <button
              onClick={() => handleSend()}
              disabled={isSending || !input.trim() || noBookAvailable}
              className={`px-5 py-2.5 bg-gradient-to-r ${avatarConfig.gradient} text-white rounded-xl text-sm font-medium hover:shadow-lg transition-all disabled:opacity-40 disabled:cursor-not-allowed`}
            >
              {isSending ? '思考中...' : '发送'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatBubble({ msg, npc }) {
  if (msg.role === 'user') {
    return (
      <div className="flex gap-3 justify-end">
        <div className="max-w-[70%] bg-gradient-to-r from-sky-500 to-violet-500 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed shadow-md">
          {msg.content}
        </div>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-300 to-orange-400 flex items-center justify-center text-sm shrink-0">
          🧙
        </div>
      </div>
    );
  }

  const showIntentTag = msg.intent && msg.intent !== 'BOOK' && msg.intent !== 'REFLECTION';
  const showFreeTalkNote = msg.freeTalk && !msg.hasReference;
  const citations = msg.citations || [];

  return (
    <div className="flex gap-3">
      <NpcAvatar npcId={npc.id} size="sm" showGlow={false} />
      <div className="max-w-[70%] bg-white rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed shadow-sm border border-slate-100 text-slate-700">
        <div className="whitespace-pre-wrap">{msg.content}</div>

        {showIntentTag && (
          <div className={`mt-2 inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full border font-medium ${msg.intent === 'OUT_OF_SCOPE' ? 'border-amber-200 text-amber-600 bg-amber-50' : 'border-slate-200 text-slate-500 bg-slate-50'}`}>
            {msg.intent === 'CHAT' ? '💬 自由畅谈' : '🚧 超出书内范围'}
          </div>
        )}

        {showFreeTalkNote && (
          <div className="mt-2 text-[10px] text-slate-400">
            * 此回复为 NPC 自由作答，未引用书中原文
          </div>
        )}

        {citations.length > 0 && (
          <details className="mt-2">
            <summary className="text-[11px] text-violet-500 cursor-pointer select-none">
              📖 引用原文（{citations.length}）
            </summary>
            <div className="mt-2 space-y-2">
              {citations.map((c, i) => (
                <div key={i} className="bg-slate-50 border border-slate-100 rounded-lg px-3 py-2">
                  <div className="text-xs text-slate-600 leading-relaxed">“{c.text}”</div>
                  <div className="mt-1 text-[10px] text-slate-400">
                    — 第 {c.chapter ?? '?'} 章
                    {c.score != null && (
                      <span className="ml-1">· 相关度 {(c.score * 100).toFixed(0)}%</span>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}
