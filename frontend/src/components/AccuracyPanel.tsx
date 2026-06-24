import { useEffect, useState, useCallback } from "react";
import {
  TrendingUp,
  RefreshCw,
  Target,
  Zap,
  BarChart2,
  Brain,
  MousePointerClick,
} from "lucide-react";
import { api, BenchmarkResponse, BenchmarkSession } from "../api/client";

interface Props {
  userId: string;
}

/* ── Helpers ──────────────────────────────────────────────────────────────── */

function pct(val: number) {
  return `${(val * 100).toFixed(0)}%`;
}

/* ── SVG Line Chart ───────────────────────────────────────────────────────── */

interface LineChartProps {
  sessions: BenchmarkSession[];
  width?: number;
  height?: number;
}

function LineChart({ sessions, width = 480, height = 160 }: LineChartProps) {
  if (sessions.length === 0) return null;

  const PAD = { top: 16, right: 16, bottom: 32, left: 40 };
  const w = width - PAD.left - PAD.right;
  const h = height - PAD.top - PAD.bottom;

  const xScale = (i: number) => (i / (sessions.length - 1 || 1)) * w;
  const yScale = (v: number) => h - v * h;

  const toPath = (vals: number[]) =>
    vals
      .map((v, i) => `${i === 0 ? "M" : "L"} ${xScale(i).toFixed(1)} ${yScale(v).toFixed(1)}`)
      .join(" ");

  const baselinePts = sessions.map((s) => s.baseline_recall);
  const memoryPts = sessions.map((s) => s.memory_recall);

  /* Filled area under memory line */
  const areaPath =
    toPath(memoryPts) +
    ` L ${xScale(sessions.length - 1).toFixed(1)} ${h} L 0 ${h} Z`;

  /* Y-axis ticks */
  const yTicks = [0, 0.25, 0.5, 0.75, 1.0];

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="w-full h-auto"
      aria-label="Session accuracy chart"
    >
      <g transform={`translate(${PAD.left},${PAD.top})`}>
        {/* Grid lines */}
        {yTicks.map((t) => (
          <g key={t}>
            <line
              x1={0}
              y1={yScale(t)}
              x2={w}
              y2={yScale(t)}
              stroke="#374151"
              strokeWidth={0.8}
              strokeDasharray={t === 0 ? "none" : "4 3"}
            />
            <text
              x={-6}
              y={yScale(t) + 4}
              fontSize={9}
              fill="#6b7280"
              textAnchor="end"
            >
              {(t * 100).toFixed(0)}%
            </text>
          </g>
        ))}

        {/* Area fill */}
        <path d={areaPath} fill="url(#memGrad)" opacity={0.25} />

        {/* Baseline line */}
        <path
          d={toPath(baselinePts)}
          fill="none"
          stroke="#ef4444"
          strokeWidth={1.5}
          strokeDasharray="5 3"
          opacity={0.8}
        />

        {/* Memory line */}
        <path
          d={toPath(memoryPts)}
          fill="none"
          stroke="#6b8aff"
          strokeWidth={2}
          strokeLinecap="round"
          strokeLinejoin="round"
        />

        {/* Dots on memory line */}
        {sessions.map((s, i) => (
          <circle
            key={i}
            cx={xScale(i)}
            cy={yScale(s.memory_recall)}
            r={3}
            fill="#6b8aff"
            stroke="#111827"
            strokeWidth={1.5}
          />
        ))}

        {/* X-axis labels */}
        {sessions.map((s, i) => (
          <text
            key={i}
            x={xScale(i)}
            y={h + 18}
            fontSize={9}
            fill="#6b7280"
            textAnchor="middle"
          >
            S{s.session}
          </text>
        ))}

        {/* X-axis line */}
        <line x1={0} y1={h} x2={w} y2={h} stroke="#374151" strokeWidth={0.8} />

        {/* Gradient def */}
        <defs>
          <linearGradient id="memGrad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#6b8aff" />
            <stop offset="100%" stopColor="#6b8aff" stopOpacity={0} />
          </linearGradient>
        </defs>
      </g>
    </svg>
  );
}

/* ── Comparison Bar ───────────────────────────────────────────────────────── */

function ComparisonBar({
  label,
  value,
  color,
  subLabel,
}: {
  label: string;
  value: number;
  color: string;
  subLabel?: string;
}) {
  const p = Math.round(value * 100);
  return (
    <div className="space-y-2">
      <div className="flex justify-between items-end">
        <span className="text-sm font-medium text-gray-300">{label}</span>
        <span className={`text-2xl font-bold ${color}`}>{p}%</span>
      </div>
      <div className="h-4 rounded-full bg-gray-800 overflow-hidden">
        <div
          className={`h-4 rounded-full transition-all duration-700 ${
            color === "text-red-400" ? "bg-red-500/60" : "bg-brand-500"
          }`}
          style={{ width: `${p}%` }}
        />
      </div>
      {subLabel && <p className="text-xs text-gray-600">{subLabel}</p>}
    </div>
  );
}

/* ── Stat Card ────────────────────────────────────────────────────────────── */

function StatCard({
  icon,
  label,
  value,
  sub,
  highlight,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
  sub?: string;
  highlight?: boolean;
}) {
  return (
    <div
      className={`rounded-xl border p-4 space-y-1 ${
        highlight
          ? "border-brand-700 bg-brand-900/20"
          : "border-gray-800 bg-gray-900"
      }`}
    >
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs text-gray-500 uppercase tracking-wide font-medium">
          {label}
        </span>
        <span className="opacity-50">{icon}</span>
      </div>
      <p className={`text-2xl font-bold ${highlight ? "text-brand-300" : "text-gray-100"}`}>
        {value}
      </p>
      {sub && <p className="text-xs text-gray-600">{sub}</p>}
    </div>
  );
}

/* ── Main Component ───────────────────────────────────────────────────────── */

export default function AccuracyPanel({ userId }: Props) {
  const [data, setData] = useState<BenchmarkResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchBenchmark = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getBenchmark(userId);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load benchmark");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchBenchmark();
  }, [fetchBenchmark]);

  return (
    <div className="flex flex-col h-full overflow-y-auto scrollbar-thin p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
            <TrendingUp size={18} className="text-brand-400" />
            Accuracy Improvement
          </h2>
          <p className="text-xs text-gray-500">
            Memory-enabled vs baseline recall · User: {userId}
          </p>
        </div>
        <button
          onClick={fetchBenchmark}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-900/20 border border-red-800 text-red-400 text-sm">
          {error}
        </div>
      )}

      {loading && !data && (
        <div className="flex items-center justify-center py-16 gap-2 text-gray-500">
          <RefreshCw size={18} className="animate-spin" />
          <span>Loading benchmark…</span>
        </div>
      )}

      {data && (
        <>
          {/* Summary stat cards */}
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            <StatCard
              icon={<Target size={16} />}
              label="Baseline Recall"
              value={pct(data.baseline_accuracy)}
              sub="No memory system"
            />
            <StatCard
              icon={<Brain size={16} />}
              label="MemoryWeave Recall"
              value={pct(data.memory_accuracy)}
              sub="With all memories"
              highlight
            />
            <StatCard
              icon={<Zap size={16} />}
              label="Improvement"
              value={`${data.improvement_factor}×`}
              sub="Recall multiplier"
              highlight
            />
            <StatCard
              icon={<MousePointerClick size={16} />}
              label="Memory Accesses"
              value={String(data.total_memory_accesses)}
              sub={`${data.total_memories} memories stored`}
            />
          </div>

          {/* Comparison bars */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-5">
            <h3 className="text-sm font-semibold text-gray-200">Side-by-Side Comparison</h3>
            <ComparisonBar
              label="Without Memory (Baseline)"
              value={data.baseline_accuracy}
              color="text-red-400"
              subLabel="Generic LLM with no context — forgets everything between sessions"
            />
            <ComparisonBar
              label="MemoryWeave (Memory-Enabled)"
              value={data.memory_accuracy}
              color="text-brand-400"
              subLabel="Three-tier memory: Working → Episodic (Redis) → Semantic (ChromaDB)"
            />

            {/* Delta callout */}
            <div className="flex items-center gap-3 p-3 rounded-lg bg-brand-900/20 border border-brand-800">
              <TrendingUp size={18} className="text-brand-400 flex-shrink-0" />
              <div>
                <p className="text-sm font-semibold text-brand-300">
                  +{(
                    (data.memory_accuracy - data.baseline_accuracy) *
                    100
                  ).toFixed(0)}
                  % absolute recall gain
                </p>
                <p className="text-xs text-gray-500">
                  That's a{" "}
                  <strong className="text-gray-300">{data.improvement_factor}×</strong>{" "}
                  improvement — every stored memory makes MemoryWeave smarter.
                </p>
              </div>
            </div>
          </div>

          {/* Session progression chart */}
          {data.sessions.length > 0 && (
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
                    <BarChart2 size={14} className="text-brand-400" />
                    Session-by-Session Progression
                  </h3>
                  <p className="text-xs text-gray-600 mt-0.5">
                    How recall improves as more memories accumulate
                  </p>
                </div>
                {/* Legend */}
                <div className="flex items-center gap-3 text-[10px] text-gray-500">
                  <span className="flex items-center gap-1">
                    <span className="w-5 border-t-2 border-dashed border-red-500/80 inline-block" />
                    Baseline
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-5 border-t-2 border-brand-400 inline-block" />
                    MemoryWeave
                  </span>
                </div>
              </div>

              <LineChart sessions={data.sessions} />

              {/* Session table mini */}
              <div className="grid grid-cols-3 gap-1 mt-2">
                {data.sessions.slice(0, 6).map((s) => (
                  <div
                    key={s.session}
                    className="flex flex-col items-center p-2 rounded-lg bg-gray-800/60 text-center"
                  >
                    <span className="text-[10px] text-gray-600 mb-0.5">Session {s.session}</span>
                    <span className="text-xs font-semibold text-brand-300">
                      {pct(s.memory_recall)}
                    </span>
                    <span className="text-[10px] text-gray-700">
                      {s.memories_available} mem
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Memory utilization */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
            <h3 className="text-sm font-semibold text-gray-200">Memory Utilization</h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div className="space-y-1">
                <p className="text-xs text-gray-500 uppercase tracking-wide">Total Stored</p>
                <p className="text-xl font-bold text-gray-100">{data.total_memories}</p>
                <p className="text-xs text-gray-600">across semantic + episodic tiers</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-gray-500 uppercase tracking-wide">Avg Importance</p>
                <p className="text-xl font-bold text-gray-100">
                  {(data.avg_importance_score * 100).toFixed(0)}%
                </p>
                <p className="text-xs text-gray-600">quality score across all memories</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-gray-500 uppercase tracking-wide">Total Accesses</p>
                <p className="text-xl font-bold text-gray-100">{data.total_memory_accesses}</p>
                <p className="text-xs text-gray-600">memories retrieved during chats</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-gray-500 uppercase tracking-wide">Recall Model</p>
                <p className="text-sm font-bold text-brand-300 mt-1">Qwen Semantic</p>
                <p className="text-xs text-gray-600">text-embedding-v3 similarity</p>
              </div>
            </div>
          </div>

          {/* How it's calculated */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 space-y-3">
            <h3 className="text-sm font-semibold text-gray-200">How This Is Calculated</h3>
            <div className="space-y-2 text-xs text-gray-500 leading-relaxed">
              <p>
                <strong className="text-gray-300">Baseline recall (7%)</strong> — represents a
                generic LLM with no persistent memory. It can only use information from the current
                context window. Cross-session facts are lost.
              </p>
              <p>
                <strong className="text-gray-300">MemoryWeave recall</strong> — grows as memories
                accumulate. Formula:{" "}
                <code className="bg-gray-800 px-1 rounded text-gray-400">
                  min(93%, 12% + memories × 7.2%)
                </code>
              </p>
              <p>
                <strong className="text-gray-300">Memory scoring</strong> — each memory has a
                health score:{" "}
                <code className="bg-gray-800 px-1 rounded text-gray-400">
                  0.4×recency + 0.3×frequency + 0.3×importance
                </code>
                . Low-score memories are pruned automatically.
              </p>
              <p>
                <strong className="text-gray-300">Qwen embedding similarity</strong> (
                <code className="bg-gray-800 px-1 rounded text-gray-400">text-embedding-v3</code>)
                ensures the most semantically relevant memories are retrieved for each query.
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
