import { useEffect, useState, useCallback } from "react";
import {
  Activity,
  Brain,
  Clock,
  Shield,
  TrendingUp,
  RefreshCw,
  Wifi,
  WifiOff,
} from "lucide-react";
import { api, MetricsResponse } from "../api/client";

interface Props {
  userId: string;
}

function StatCard({
  icon,
  label,
  value,
  sub,
  color,
}: {
  icon: React.ReactNode;
  label: string;
  value: string | number;
  sub?: string;
  color: string;
}) {
  return (
    <div className={`rounded-xl border p-4 space-y-2 ${color}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 font-medium uppercase tracking-wide">{label}</span>
        <div className="opacity-60">{icon}</div>
      </div>
      <p className="text-2xl font-bold text-gray-100">{value}</p>
      {sub && <p className="text-xs text-gray-500">{sub}</p>}
    </div>
  );
}

function HealthBar({ score, label }: { score: number; label: string }) {
  const pct = Math.round(score * 100);
  const color =
    score > 0.65 ? "bg-green-500" : score > 0.4 ? "bg-yellow-500" : "bg-red-500";
  const text =
    score > 0.65 ? "text-green-400" : score > 0.4 ? "text-yellow-400" : "text-red-400";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs">
        <span className="text-gray-400">{label}</span>
        <span className={`font-semibold ${text}`}>{pct}%</span>
      </div>
      <div className="h-2 rounded-full bg-gray-800">
        <div
          className={`h-2 rounded-full ${color} transition-all duration-500`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function TypeBreakdown({ breakdown }: { breakdown: Record<string, number> }) {
  const total = Object.values(breakdown).reduce((a, b) => a + b, 0);
  if (total === 0) return <p className="text-sm text-gray-600 text-center py-4">No memories yet.</p>;

  const COLORS: Record<string, string> = {
    preference: "bg-blue-500",
    fact: "bg-green-500",
    skill: "bg-yellow-500",
    relationship: "bg-pink-500",
  };

  return (
    <div className="space-y-3">
      {Object.entries(breakdown).map(([type, count]) => {
        const pct = total > 0 ? (count / total) * 100 : 0;
        return (
          <div key={type} className="space-y-1">
            <div className="flex justify-between text-xs">
              <span className="text-gray-400 capitalize">{type}</span>
              <span className="text-gray-300">
                {count} <span className="text-gray-600">({pct.toFixed(0)}%)</span>
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-gray-800">
              <div
                className={`h-1.5 rounded-full ${COLORS[type] ?? "bg-gray-500"} transition-all`}
                style={{ width: `${pct}%` }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export default function MetricsPanel({ userId }: Props) {
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");

  const fetchMetrics = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getMetrics(userId);
      setMetrics(data);
      setApiStatus("online");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load metrics");
      setApiStatus("offline");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchMetrics();
    const timer = setInterval(fetchMetrics, 30_000);
    return () => clearInterval(timer);
  }, [fetchMetrics]);

  const checkPing = async () => {
    try {
      await api.ping();
      setApiStatus("online");
    } catch {
      setApiStatus("offline");
    }
  };

  useEffect(() => {
    checkPing();
  }, []);

  return (
    <div className="flex flex-col h-full overflow-y-auto scrollbar-thin p-4 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-100">Memory Health</h2>
          <p className="text-xs text-gray-500">User: {userId} · Auto-refreshes every 30s</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs">
            {apiStatus === "online" ? (
              <><Wifi size={13} className="text-green-400" /><span className="text-green-400">API Online</span></>
            ) : apiStatus === "offline" ? (
              <><WifiOff size={13} className="text-red-400" /><span className="text-red-400">API Offline</span></>
            ) : (
              <><RefreshCw size={13} className="animate-spin text-gray-500" /><span className="text-gray-500">Checking…</span></>
            )}
          </div>
          <button
            onClick={fetchMetrics}
            disabled={loading}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors disabled:opacity-50"
          >
            <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-900/20 border border-red-800 text-red-400 text-sm">
          {error}
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-3">
        <StatCard
          icon={<Brain size={18} />}
          label="Semantic Memories"
          value={metrics?.semantic_memories ?? "—"}
          sub="Long-term facts in ChromaDB"
          color="bg-gray-900 border-gray-800"
        />
        <StatCard
          icon={<Clock size={18} />}
          label="Episodic Memories"
          value={metrics?.episodic_memories ?? "—"}
          sub="Recent session summaries in Redis"
          color="bg-gray-900 border-gray-800"
        />
        <StatCard
          icon={<Activity size={18} />}
          label="Avg Health Score"
          value={metrics ? `${(metrics.avg_health_score * 100).toFixed(0)}%` : "—"}
          sub="Recency × Frequency × Importance"
          color="bg-gray-900 border-gray-800"
        />
        <StatCard
          icon={<Shield size={18} />}
          label="Prune Candidates"
          value={metrics?.prune_candidates ?? "—"}
          sub="Memories below threshold (< 20%)"
          color={
            metrics && metrics.prune_candidates > 0
              ? "bg-red-950 border-red-900"
              : "bg-gray-900 border-gray-800"
          }
        />
      </div>

      {/* Health bar */}
      {metrics && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-4">
          <div className="flex items-center gap-2">
            <TrendingUp size={15} className="text-brand-400" />
            <h3 className="text-sm font-medium text-gray-200">Memory Health Score</h3>
          </div>
          <HealthBar score={metrics.avg_health_score} label="Overall Memory Health" />
          <p className="text-xs text-gray-600">
            Score formula: <code className="text-gray-500">0.4×recency + 0.3×frequency + 0.3×importance</code>
          </p>
        </div>
      )}

      {/* Type breakdown */}
      <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-4">
        <h3 className="text-sm font-medium text-gray-200">Memory Type Breakdown</h3>
        {metrics ? (
          <TypeBreakdown breakdown={metrics.memory_type_breakdown} />
        ) : (
          <p className="text-sm text-gray-600">Loading…</p>
        )}
      </div>

      {/* Top memories */}
      {metrics && metrics.top_memories.length > 0 && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 space-y-3">
          <h3 className="text-sm font-medium text-gray-200">Highest Importance Memories</h3>
          <div className="space-y-2">
            {metrics.top_memories.map((mem, i) => (
              <div key={mem.id} className="flex gap-3 items-start">
                <span className="flex-shrink-0 w-5 h-5 rounded-full bg-gray-800 flex items-center justify-center text-[10px] text-gray-500 font-bold mt-0.5">
                  {i + 1}
                </span>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-300 leading-relaxed">{mem.content}</p>
                  <div className="flex gap-3 mt-1">
                    <span className="text-[10px] text-gray-600 capitalize">{mem.memory_type}</span>
                    <span className="text-[10px] text-gray-600">
                      Importance: {(mem.importance_score * 100).toFixed(0)}%
                    </span>
                    <span className="text-[10px] text-gray-600">
                      Accessed: {mem.access_count}×
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active sessions */}
      {metrics && (
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-200">Active Sessions</p>
            <p className="text-xs text-gray-600">Currently open working memory contexts</p>
          </div>
          <span className="text-3xl font-bold text-brand-400">{metrics.active_sessions}</span>
        </div>
      )}

      {loading && !metrics && (
        <div className="flex items-center justify-center py-16 gap-2 text-gray-500">
          <RefreshCw size={18} className="animate-spin" />
          <span>Loading metrics…</span>
        </div>
      )}
    </div>
  );
}
