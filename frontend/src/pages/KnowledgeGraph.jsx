import { useState, useEffect, useMemo } from 'react';
import ReactECharts from 'echarts-for-react';
import api from '../api/client';

export default function KnowledgeGraph() {
  const [kg, setKg] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [reloadKey, setReloadKey] = useState(0);
  const [showBooks, setShowBooks] = useState(true);
  const [showConcepts, setShowConcepts] = useState(true);
  const [showNpcs, setShowNpcs] = useState(true);
  const [searchText, setSearchText] = useState('');
  const [selectedNode, setSelectedNode] = useState(null);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      setError('');
      try {
        const graph = await api.graph();
        if (!cancelled) {
          setKg(graph);
          setSelectedNode(null);
        }
      } catch (e) {
        if (!cancelled) setError(e.message || '加载认知星图失败');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [reloadKey]);

  const option = useMemo(() => {
    if (!kg) return null;

    let nodes = kg.nodes;
    let links = kg.links;

    // 根据开关过滤
    if (!showBooks) {
      nodes = nodes.filter(n => n.category !== 0);
      links = links.filter(l => {
        const sourceNode = kg.nodes.find(n => n.id === l.source);
        const targetNode = kg.nodes.find(n => n.id === l.target);
        return sourceNode?.category !== 0 && targetNode?.category !== 0;
      });
    }
    if (!showConcepts) {
      nodes = nodes.filter(n => n.category !== 1);
      links = links.filter(l => {
        const sourceNode = kg.nodes.find(n => n.id === l.source);
        const targetNode = kg.nodes.find(n => n.id === l.target);
        return sourceNode?.category !== 1 && targetNode?.category !== 1;
      });
    }
    if (!showNpcs) {
      nodes = nodes.filter(n => n.category !== 2);
      links = links.filter(l => {
        const sourceNode = kg.nodes.find(n => n.id === l.source);
        const targetNode = kg.nodes.find(n => n.id === l.target);
        return sourceNode?.category !== 2 && targetNode?.category !== 2;
      });
    }

    // 搜索高亮
    if (searchText.trim()) {
      const matchedIds = new Set();
      nodes.forEach(n => {
        if (n.name.toLowerCase().includes(searchText.toLowerCase())) {
          matchedIds.add(n.id);
          // 找到相邻节点
          links.forEach(l => {
            if (l.source === n.id) matchedIds.add(l.target);
            if (l.target === n.id) matchedIds.add(l.source);
          });
        }
      });

      nodes = nodes.map(n => ({
        ...n,
        itemStyle: {
          opacity: matchedIds.size > 0 ? (matchedIds.has(n.id) ? 1 : 0.15) : 1,
        },
        label: {
          show: matchedIds.size === 0 || matchedIds.has(n.id),
        },
      }));

      links = links.map(l => ({
        ...l,
        lineStyle: {
          ...l.lineStyle,
          opacity: matchedIds.size > 0 ? (matchedIds.has(l.source) && matchedIds.has(l.target) ? 1 : 0.1) : 0.5,
        },
      }));
    }

    return {
      tooltip: {
        trigger: 'item',
        formatter: function(params) {
          if (params.dataType === 'node') {
            return `<div style="padding:4px 8px;">
              <div style="font-weight:bold;">${params.name}</div>
              <div style="color:#64748b;font-size:11px;margin-top:2px;">
                ${kg.categories[params.data.category]?.name || ''}
              </div>
            </div>`;
          }
          return '';
        },
      },
      legend: {
        show: false,
        data: kg.categories.map(c => c.name),
      },
      animationDuration: 1500,
      animationEasingUpdate: 'quinticInOut',
      series: [
        {
          type: 'graph',
          layout: 'force',
          data: nodes,
          links: links,
          categories: kg.categories,
          roam: true,
          draggable: true,
          label: {
            show: true,
            position: 'bottom',
            fontSize: 11,
            color: '#475569',
            formatter: '{b}',
          },
          lineStyle: {
            color: 'source',
            curveness: 0.15,
            width: 1.5,
            opacity: 0.5,
          },
          itemStyle: {
            borderColor: '#fff',
            borderWidth: 2,
            shadowBlur: 10,
            shadowColor: 'rgba(0, 0, 0, 0.1)',
          },
          emphasis: {
            focus: 'adjacency',
            lineStyle: {
              width: 3,
            },
            label: {
              fontWeight: 'bold',
            },
          },
          force: {
            repulsion: 350,
            gravity: 0.1,
            edgeLength: [80, 180],
            layoutAnimation: true,
          },
          // 不同分类的颜色
          color: ['#38bdf8', '#a78bfa', '#f472b6'],
          // 节点形状
          symbolSize: (value, params) => params.data.symbolSize || 20,
        },
      ],
    };
  }, [kg, showBooks, showConcepts, showNpcs, searchText]);

  const onEvents = {
    click: function(params) {
      if (params.dataType === 'node') {
        setSelectedNode(params.data);
      }
    },
  };

  const stats = kg
    ? {
        books: kg.nodes.filter(n => n.category === 0).length,
        concepts: kg.nodes.filter(n => n.category === 1).length,
        npcs: kg.nodes.filter(n => n.category === 2).length,
        connections: kg.links.length,
      }
    : { books: 0, concepts: 0, npcs: 0, connections: 0 };

  return (
    <div className="h-full flex flex-col p-6">
      {/* 顶部工具栏 */}
      <div className="flex items-center justify-between mb-4">
        <div>
          <h1 className="text-xl font-bold text-slate-800">✨ 认知星图</h1>
          <p className="text-xs text-slate-500 mt-0.5">
            你读过的每一本书、每一个概念，都是这片星空中的星辰
          </p>
        </div>

        {/* 搜索框 */}
        <div className="flex items-center gap-3">
          <div className="relative">
            <input
              type="text"
              value={searchText}
              onChange={e => setSearchText(e.target.value)}
              placeholder="搜索概念或书籍..."
              className="w-64 pl-9 pr-4 py-2 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-violet-400 focus:border-transparent"
            />
            <span className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 text-sm">
              🔍
            </span>
          </div>
        </div>
      </div>

      {/* 统计 + 图例 */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex gap-4">
          <StatBadge label="书籍" value={stats.books} color="bg-sky-500" />
          <StatBadge label="概念" value={stats.concepts} color="bg-violet-500" />
          <StatBadge label="NPC" value={stats.npcs} color="bg-pink-500" />
          <StatBadge label="连接" value={stats.connections} color="bg-emerald-500" />
        </div>

        <div className="flex items-center gap-2">
          <LegendToggle
            label="书籍"
            color="bg-sky-500"
            active={showBooks}
            onClick={() => setShowBooks(!showBooks)}
          />
          <LegendToggle
            label="概念"
            color="bg-violet-500"
            active={showConcepts}
            onClick={() => setShowConcepts(!showConcepts)}
          />
          <LegendToggle
            label="NPC"
            color="bg-pink-500"
            active={showNpcs}
            onClick={() => setShowNpcs(!showNpcs)}
          />
        </div>
      </div>

      {/* 图谱区域 */}
      <div className="flex-1 flex gap-4 min-h-0">
        <div className="flex-1 bg-white rounded-2xl shadow-sm border border-slate-100 overflow-hidden">
          {loading && (
            <div className="h-full flex flex-col items-center justify-center text-slate-400">
              <div className="inline-block w-8 h-8 border-4 border-slate-200 border-t-violet-500 rounded-full animate-spin mb-3" />
              <div className="text-sm">正在点亮星图...</div>
            </div>
          )}

          {error && !loading && (
            <div className="h-full flex flex-col items-center justify-center text-center px-6">
              <div className="text-4xl mb-3 opacity-30">🛰️</div>
              <p className="text-slate-500 text-sm">认知星图暂时无法加载</p>
              <p className="text-xs text-red-400 mt-1">{error}</p>
              <button
                onClick={() => setReloadKey(k => k + 1)}
                className="mt-4 px-5 py-2 bg-gradient-to-r from-violet-500 to-fuchsia-500 text-white rounded-xl text-sm font-medium hover:shadow-lg transition-all"
              >
                重试
              </button>
            </div>
          )}

          {!loading && !error && kg && (
            <ReactECharts
              option={option}
              style={{ height: '100%', width: '100%' }}
              onEvents={onEvents}
              opts={{ renderer: 'canvas' }}
            />
          )}
        </div>

        {/* 右侧详情面板 */}
        <div className="w-72 bg-white rounded-2xl shadow-sm border border-slate-100 p-5 flex flex-col">
          <h3 className="font-bold text-slate-800 text-sm mb-3">🔍 节点详情</h3>

          {selectedNode && kg ? (
            <div>
              <div className="text-center pb-4 border-b border-slate-100">
                <div className={`inline-flex w-14 h-14 rounded-full items-center justify-center text-xl mb-2 ${
                  selectedNode.category === 0 ? 'bg-sky-100' :
                  selectedNode.category === 1 ? 'bg-violet-100' : 'bg-pink-100'
                }`}>
                  {selectedNode.category === 0 ? '📚' :
                   selectedNode.category === 1 ? '💎' : '🧠'}
                </div>
                <div className="font-bold text-slate-800">{selectedNode.name}</div>
                <div className="text-xs text-slate-400 mt-0.5">
                  {kg.categories[selectedNode.category]?.name}
                </div>
              </div>

              <div className="mt-4 space-y-3">
                <div>
                  <div className="text-xs text-slate-400 mb-1">关联书籍</div>
                  <div className="text-xs text-slate-600 bg-slate-50 px-3 py-2 rounded-lg">
                    {selectedNode.category === 0
                      ? selectedNode.name
                      : '《思考，快与慢》等 2 本'}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-400 mb-1">关联概念</div>
                  <div className="flex flex-wrap gap-1">
                    {['认知偏差', '系统1', '损失厌恶'].map((c, i) => (
                      <span
                        key={i}
                        className="text-[11px] px-2 py-0.5 bg-violet-50 text-violet-600 rounded-full"
                      >
                        {c}
                      </span>
                    ))}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-slate-400 mb-1">定义 / 说明</div>
                  <div className="text-xs text-slate-600 leading-relaxed">
                    这是一个从书籍中提取的核心概念，点击可以查看来源书籍和相关摘录。
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex-1 flex flex-col items-center justify-center text-center">
              <div className="text-4xl mb-3 opacity-30">🌌</div>
              <p className="text-sm text-slate-400">点击星图上的节点</p>
              <p className="text-xs text-slate-300 mt-1">查看详细信息</p>
            </div>
          )}

          <div className="mt-auto pt-4 border-t border-slate-100">
            <button className="w-full py-2 text-xs text-slate-400 hover:text-violet-500 transition-colors">
              📥 导出星图 JSON
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function StatBadge({ label, value, color }) {
  return (
    <div className="flex items-center gap-2 bg-white rounded-xl px-3 py-1.5 border border-slate-100 shadow-sm">
      <div className={`w-2.5 h-2.5 rounded-full ${color}`} />
      <span className="text-xs text-slate-500">{label}</span>
      <span className="text-sm font-bold text-slate-700">{value}</span>
    </div>
  );
}

function LegendToggle({ label, color, active, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
        active
          ? 'bg-white shadow-sm border border-slate-200 text-slate-600'
          : 'bg-slate-50 border border-slate-100 text-slate-300 line-through'
      }`}
    >
      <div className={`w-2.5 h-2.5 rounded-full ${color} ${active ? '' : 'opacity-30'}`} />
      {label}
    </button>
  );
}
