import { useEffect, useState, useCallback } from "react";
import {
  Clock,
  Brain,
  RefreshCw,
  ChevronDown,
  ChevronUp,
  Layers,
  CalendarDays,
} from "lucide-react";
import { api, TimelineGroup, TimelineEvent } from "../api/client";

interface Props {
  userId: string;
}

const TIER_STYLES: Record<string, { dot: string; badge: string; label: string }> = {
  semantic: {
    dot: "bg-brand-500 shadow-brand-500/50 shadow-md",
    badge: "bg-brand-900/60 text-brand-300 border-brand-800",
    label: "Semantic",
  },
  episodic: {
    dot: "bg-purple-500 shadow-purple-500/50 shadow-md",
    badge: "bg-purple-900/60 text-purple-300 border-purple-800",
    label: "Episodic",
  },
};

const MEM_TYPE_COLORS: Record<string, string> = {
  preference: "text-blue-400",
  fact: "text-green-400",
  skill: "text-yellow-400",
  relationship: "text-pink-400",
  episodic: "text-purple-400",
};

function formatDate(dateStr: string): string {
  const d = new Date(dateStr + "T00:00:00");
  const today = new Date();
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);

  if (d.toDateString() === today.toDateString()) return "Today";
  if (d.toDateString() === yesterday.toDateString()) return "Yesterday";
  return d.toLocaleDateString(undefined, {
    weekday: "long",
    month: "short",
    day: "numeric",
    year: d.getFullYear() !== today.getFullYear() ? "numeric" : undefined,
  });
}

function formatTime(isoStr: string): string {
  return new Date(isoStr).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

function importanceDot(score: number): string {
  if (score >= 0.7) return "bg-green-400";
  if (score >= 0.4) return "bg-yellow-400";
  return "bg-red-400";
}

function EventCard({ event }: { event: TimelineEvent }) {
  const [expanded, setExpanded] = useState(false);
  const tier = TIER_STYLES[event.type] ?? TIER_STYLES.semantic;
  const typeColor = MEM_TYPE_COLORS[event.memory_type] ?? "text-gray-400";

  return (
    <div className="flex gap-3">
      {/* Timeline dot */}
      <div className="flex flex-col items-center mt-1.5 flex-shrink-0">
        <div className={`w-3 h-3 rounded-full border-2 border-gray-950 ${tier.dot}`} />
        <div className="w-px flex-1 bg-gray-800 mt-1" />
      </div>

      {/* Card */}
      <div className="flex-1 mb-3">
        <div
          className="rounded-xl border border-gray-800 bg-gray-900/70 hover:bg-gray-900 transition-colors cursor-pointer"
          onClick={() => setExpanded((v) => !v)}
        >
          <div className="flex items-start gap-2 p-3">
            <div className="flex-1 min-w-0">
              <div className="flex flex-wrap items-center gap-1.5 mb-1">
                <span
                  className={`text-[10px] font-semibold px-1.5 py-0.5 rounded border ${tier.badge}`}
                >
                  {tier.label}
                </span>
                <span className={`text-[10px] font-medium capitalize ${typeColor}`}>
                  {event.memory_type}
                </span>
                <span className="text-[10px] text-gray-600 ml-auto">
                  {formatTime(event.timestamp)}
                </span>
              </div>
              <p className="text-sm text-gray-300 leading-relaxed line-clamp-2">
                {event.content}
              </p>
            </div>
            <button className="flex-shrink-0 text-gray-600 hover:text-gray-400 mt-0.5">
              {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
            </button>
          </div>

          {expanded && (
            <div className="border-t border-gray-800 px-3 pb-3 pt-2 space-y-2">
              <p className="text-sm text-gray-200 leading-relaxed">{event.content}</p>
              <div className="flex flex-wrap gap-4 text-xs text-gray-500">
                <span className="flex items-center gap-1">
                  Importance:
                  <span
                    className={`w-2 h-2 rounded-full inline-block ml-0.5 ${importanceDot(
                      event.importance_score
                    )}`}
                  />
                  <strong className="text-gray-300">
                    {(event.importance_score * 100).toFixed(0)}%
                  </strong>
                </span>
                <span>
                  Accessed:{" "}
                  <strong className="text-gray-300">{event.access_count}×</strong>
                </span>
                <span>
                  ID: <code className="text-gray-600">{event.id.slice(0, 10)}…</code>
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function DayGroup({ group }: { group: TimelineGroup }) {
  return (
    <div>
      {/* Day header */}
      <div className="flex items-center gap-2 mb-3 sticky top-0 py-1 bg-gray-950 z-10">
        <CalendarDays size={13} className="text-gray-600 flex-shrink-0" />
        <span className="text-xs font-semibold text-gray-400">{formatDate(group.date)}</span>
        <div className="flex-1 h-px bg-gray-800" />
        <span className="text-[10px] text-gray-700 flex-shrink-0">
          {group.count} event{group.count !== 1 ? "s" : ""}
        </span>
      </div>

      {/* Events */}
      <div className="pl-2">
        {group.events.map((evt) => (
          <EventCard key={evt.id} event={evt} />
        ))}
      </div>
    </div>
  );
}

export default function TimelinePanel({ userId }: Props) {
  const [data, setData] = useState<{
    total_events: number;
    groups: TimelineGroup[];
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTimeline = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await api.getTimeline(userId);
      setData(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load timeline");
    } finally {
      setLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchTimeline();
  }, [fetchTimeline]);

  const semanticCount =
    data?.groups.flatMap((g) => g.events).filter((e) => e.type === "semantic").length ?? 0;
  const episodicCount =
    data?.groups.flatMap((g) => g.events).filter((e) => e.type === "episodic").length ?? 0;

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 flex-shrink-0">
        <div>
          <h2 className="text-sm font-semibold text-gray-100 flex items-center gap-2">
            <Layers size={15} className="text-brand-400" />
            Memory Timeline
          </h2>
          <p className="text-[11px] text-gray-500 mt-0.5">
            {data
              ? `${data.total_events} event${data.total_events !== 1 ? "s" : ""} · ${semanticCount} semantic · ${episodicCount} episodic`
              : `User: ${userId}`}
          </p>
        </div>
        <button
          onClick={fetchTimeline}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-4 px-4 py-2 border-b border-gray-800 flex-shrink-0">
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <div className="w-2.5 h-2.5 rounded-full bg-brand-500" />
          Semantic (long-term, ChromaDB)
        </div>
        <div className="flex items-center gap-1.5 text-xs text-gray-400">
          <div className="w-2.5 h-2.5 rounded-full bg-purple-500" />
          Episodic (short-term, Redis)
        </div>
        <div className="flex items-center gap-3 ml-auto text-[10px] text-gray-600">
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-green-400 inline-block" /> High
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-yellow-400 inline-block" /> Medium
          </span>
          <span className="flex items-center gap-1">
            <span className="w-2 h-2 rounded-full bg-red-400 inline-block" /> Low importance
          </span>
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto p-4 scrollbar-thin">
        {loading && !data && (
          <div className="flex items-center justify-center py-20 gap-2 text-gray-500">
            <RefreshCw size={18} className="animate-spin" />
            <span className="text-sm">Loading timeline…</span>
          </div>
        )}

        {error && (
          <div className="p-3 rounded-lg bg-red-900/20 border border-red-800 text-red-400 text-sm">
            {error}
          </div>
        )}

        {data && data.groups.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20 text-gray-600 space-y-3">
            <Clock size={40} className="opacity-40" />
            <p className="text-sm">No memories recorded yet.</p>
            <p className="text-xs text-gray-700 text-center max-w-xs">
              Start a chat conversation — MemoryWeave will store what it learns about you here.
            </p>
          </div>
        )}

        {data && data.groups.length > 0 && (
          <div className="space-y-6 max-w-2xl mx-auto">
            {/* Top connector */}
            <div className="flex items-center gap-2 text-xs text-gray-600">
              <Brain size={13} className="text-brand-400" />
              <span>Most recent memories first</span>
            </div>

            {data.groups.map((group) => (
              <DayGroup key={group.date} group={group} />
            ))}

            {/* Bottom cap */}
            <div className="flex items-center gap-2 pl-2">
              <div className="w-3 h-3 rounded-full bg-gray-700 border-2 border-gray-800 flex-shrink-0" />
              <span className="text-xs text-gray-700">Memory history begins</span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
