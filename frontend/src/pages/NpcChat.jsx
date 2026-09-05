import { useState, useRef, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { npcs, npcConversations } from '../data/mockData';
import NpcAvatar from '../components/NpcAvatar';
import npcAvatarConfig from '../data/npcAvatars';

export default function NpcChat() {
  const { npcId } = useParams();
  const navigate = useNavigate();
  const npc = npcs.find(n => n.id === npcId);
  const [messages, setMessages] = useState(() => {
    const history = npcConversations[npcId] || [];
    // 把历史记录展平
    const msgs = [];
    history.forEach(h => {
      msgs.push({ role: 'user', content: h.userMessage });
      msgs.push({ role: 'npc', content: h.npcResponse });
    });
    // 加上开场白
    if (msgs.length === 0 && npc) {
      msgs.push({ role: 'npc', content: npc.greeting });
    }
    return msgs.length > 0 ? msgs : (npc ? [{ role: 'npc', content: npc.greeting }] : []);
  });
  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const chatEndRef = useRef(null);

  const scrollToBottom = () => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isTyping]);

  if (!npc) {
    return <div className="p-8 text-center text-slate-500">未找到该 NPC</div>;
  }

  const icebreakers = [
    '你最核心的观点是什么？',
    '给我举个日常的例子吧',
    '你和其他 NPC 有什么不同？',
  ];

  const handleSend = (text) => {
    const msg = text || input;
    if (!msg.trim()) return;

    setMessages(prev => [...prev, { role: 'user', content: msg }]);
    setInput('');
    setIsTyping(true);

    // 模拟 AI 回复
    setTimeout(() => {
      const responses = [
        `这是个很有意思的问题！从${npc.personalityTags[0]}的角度来看，${msg.slice(0, 10)}... 嗯，让我想想。其实核心在于，我们常常高估自己的理性，低估环境对决策的影响。你有没有遇到过类似的情况？`,
        `好问题！让我用一个例子来说明吧。想象你在超市里，看到"第二件半价"的标签——虽然你根本不需要第二件，但还是忍不住放进了购物车。这就是认知偏差在悄悄起作用。`,
        `你问到点子上了。我可以给你三个建议：第一，慢下来，给系统2一点时间；第二，逆向思考，反过来想；第三，建立多元思维模型，不要只用一把锤子看世界。`,
      ];
      const randomReply = responses[Math.floor(Math.random() * responses.length)];
      setMessages(prev => [...prev, { role: 'npc', content: randomReply }]);
      setIsTyping(false);
    }, 1200);
  };

  const familiarityPercent = npc.familiarity * 100;
  const avatarConfig = npcAvatarConfig[npc.id] || npcAvatarConfig.npc1;

  return (
    <div className="h-full flex">
      {/* 左侧 NPC 信息面板 */}
      <div className="w-72 bg-white border-r border-slate-200 p-6 flex flex-col">
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
          <p className="text-xs text-slate-400 mt-0.5">来自《{npc.booksAssociated[0]}》</p>
        </div>

        {/* 性格标签 */}
        <div className="flex flex-wrap justify-center gap-1.5 mt-4">
          {npc.personalityTags.map((tag, i) => (
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
            <span>{Math.round(familiarityPercent)}%</span>
          </div>
          <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className={`h-full bg-gradient-to-r ${avatarConfig.gradient} rounded-full xp-bar-fill`}
              style={{ width: `${familiarityPercent}%` }}
            />
          </div>
        </div>

        {/* 核心信念 */}
        <div className="mt-6">
          <h4 className="text-xs font-semibold text-slate-500 mb-2">💡 核心信念</h4>
          <ul className="space-y-1.5">
            {npc.coreBeliefs.map((belief, i) => (
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
            {npc.topicsDiscussed.map((topic, i) => (
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
            <ChatBubble key={i} role={msg.role} content={msg.content} npc={npc} />
          ))}
          {isTyping && (
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

        {/* 破冰问题 */}
        {messages.length <= 1 && (
          <div className="px-6 pb-3">
            <p className="text-xs text-slate-400 mb-2">💡 试试问这些：</p>
            <div className="flex gap-2 flex-wrap">
              {icebreakers.map((q, i) => (
                <button
                  key={i}
                  onClick={() => handleSend(q)}
                  className="px-3 py-1.5 bg-white border border-slate-200 rounded-full text-xs text-slate-600 hover:border-violet-300 hover:text-violet-600 hover:bg-violet-50 transition-all"
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
              onKeyDown={e => e.key === 'Enter' && handleSend()}
              placeholder="和这位智者聊聊吧..."
              className="flex-1 px-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-purple-400 focus:border-transparent"
            />
            <button
              onClick={() => handleSend()}
              className={`px-5 py-2.5 bg-gradient-to-r ${avatarConfig.gradient} text-white rounded-xl text-sm font-medium hover:shadow-lg transition-all`}
            >
              发送
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function ChatBubble({ role, content, npc }) {
  if (role === 'user') {
    return (
      <div className="flex gap-3 justify-end">
        <div className="max-w-[70%] bg-gradient-to-r from-sky-500 to-violet-500 text-white rounded-2xl rounded-tr-sm px-4 py-3 text-sm leading-relaxed shadow-md">
          {content}
        </div>
        <div className="w-8 h-8 rounded-full bg-gradient-to-br from-amber-300 to-orange-400 flex items-center justify-center text-sm shrink-0">
          🧙
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3">
      <NpcAvatar npcId={npc.id} size="sm" showGlow={false} />
      <div className="max-w-[70%] bg-white rounded-2xl rounded-tl-sm px-4 py-3 text-sm leading-relaxed shadow-sm border border-slate-100 text-slate-700">
        {content}
      </div>
    </div>
  );
}
