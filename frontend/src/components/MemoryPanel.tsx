import { useState } from "react";
import {
  Database,
  Clock,
  Trash2,
  RefreshCw,
  Zap,
  Download,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
} from "lucide-react";
import { api, MemoryItem, MemoriesResponse, ConsolidationResponse } from "../api/client";

interface Props {
  userId: string;
  memories: MemoriesResponse | null;
  loading: boolean;
  onRefresh: () => void;
}

const TYPE_COLORS: Record<string, string> = {
  preference: "bg-blue-900 text-blue-300 border-blue-800",
  fact: "bg-green-900 text-green-300 border-green-800",
  skill: "bg-yellow-900 text-yellow-300 border-yellow-800",
  relationship: "bg-pink-900 text-pink-300 border-pink-800",
  episodic: "bg-purple-900 text-purple-300 border-purple-800",
};

function ScoreBar({ score }: { score: number }) {
  const pct = Math.round(score * 100);
  const color = score > 0.6 ? "bg-green-500" : score > 0.35 ? "bg-yellow-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-1.5 rounded-full bg-gray-700">
        <div className={`h-1.5 rounded-full ${color} transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-[10px] text-gray-400 w-7 text-right">{pct}%</span>
    </div>
  );
}

function MemoryRow({
  mem,
  onDelete,
}: {
  mem: MemoryItem;
  onDelete: (id: string, tier: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const handleDelete = async () => {
    setDeleting(true);
    await onDelete(mem.id, mem.tier);
    setDeleting(false);
  };

  return (
    <div className="border border-gray-800 rounded-lg overflow-hidden">
      <div
        className="flex items-center gap-3 px-3 py-2.5 hover:bg-gray-800/50 cursor-pointer transition-colors"
        onClick={() => setExpanded((v) => !v)}
      >
        <span
          className={`flex-shrink-0 text-[10px] font-semibold px-1.5 py-0.5 rounded border ${
            TYPE_COLORS[mem.memory_type] ?? "bg-gray-800 text-gray-400 border-gray-700"
          }`}
        >
          {mem.memory_type.toUpperCase().slice(0, 4)}
        </span>
        <p className="flex-1 text-sm text-gray-300 truncate">{mem.content}</p>
        <div className="flex items-center gap-2 flex-shrink-0">
          <div className="w-20 hidden sm:block">
            <ScoreBar score={mem.importance_score} />
          </div>
          <button
            onClick={(e) => {
              e.stopPropagation();
              handleDelete();
            }}
            disabled={deleting}
            className="p-1 rounded text-gray-600 hover:text-red-400 hover:bg-red-900/30 transition-colors disabled:opacity-40"
            title="Delete memory"
          >
            <Trash2 size={13} />
          </button>
          {expanded ? <ChevronUp size={13} className="text-gray-500" /> : <ChevronDown size={13} className="text-gray-500" />}
        </div>
      </div>
      {expanded && (
        <div className="px-3 pb-3 pt-1 bg-gray-900/50 text-xs text-gray-400 space-y-1 border-t border-gray-800">
          <p className="text-gray-200 text-sm leading-relaxed">{mem.content}</p>
          <div className="flex gap-4 mt-2">
            <span>Score: <strong className="text-gray-300">{(mem.importance_score * 100).toFixed(0)}%</strong></span>
            <span>Created: <strong className="text-gray-300">{new Date(mem.created_at).toLocaleDateString()}</strong></span>
            <span>ID: <code className="text-gray-500">{mem.id.slice(0, 8)}…</code></span>
          </div>
        </div>
      )}
    </div>
  );
}

export default function MemoryPanel({ userId, memories, loading, onRefresh }: Props) {
  const [consolidating, setConsolidating] = useState(false);
  const [consolidationResult, setConsolidationResult] = useState<ConsolidationResponse | null>(null);
  const [deletingAll, setDeletingAll] = useState(false);
  const [activeTab, setActiveTab] = useState<"semantic" | "episodic">("semantic");

  const handleDelete = async (id: string, tier: string) => {
    try {
      if (tier === "semantic") await api.deleteSemanticMemory(id);
      else await api.deleteEpisodicMemory(id);
      onRefresh();
    } catch (err) {
      console.error("Delete failed:", err);
    }
  };

  const handleConsolidate = async () => {
    setConsolidating(true);
    setConsolidationResult(null);
    try {
      const result = await api.consolidate(userId);
      setConsolidationResult(result);
      onRefresh();
    } catch (err) {
      console.error("Consolidation failed:", err);
    } finally {
      setConsolidating(false);
    }
  };

  const handleDeleteAll = async () => {
    if (!confirm(`Delete ALL memories for ${userId}? This cannot be undone.`)) return;
    setDeletingAll(true);
    try {
      await api.deleteAllMemories(userId);
      onRefresh();
    } finally {
      setDeletingAll(false);
    }
  };

  const handleExport = async () => {
    try {
      const data = await api.exportMemories(userId);
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `memoryweave-${userId}-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Export failed:", err);
    }
  };

  const semanticMems = memories?.semantic ?? [];
  const episodicMems = memories?.episodic ?? [];
  const shownMems = activeTab === "semantic" ? semanticMems : episodicMems;

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar */}
      <div className="flex items-center gap-2 p-3 border-b border-gray-800 flex-wrap">
        <button
          onClick={onRefresh}
          disabled={loading}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={13} className={loading ? "animate-spin" : ""} />
          Refresh
        </button>
        <button
          onClick={handleConsolidate}
          disabled={consolidating}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-brand-600/20 hover:bg-brand-600/30 text-sm text-brand-300 border border-brand-700 transition-colors disabled:opacity-50"
        >
          <Zap size={13} className={consolidating ? "animate-pulse" : ""} />
          {consolidating ? "Consolidating…" : "Consolidate"}
        </button>
        <button
          onClick={handleExport}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm text-gray-300 transition-colors"
        >
          <Download size={13} />
          Export
        </button>
        <button
          onClick={handleDeleteAll}
          disabled={deletingAll}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-red-900/20 hover:bg-red-900/40 text-sm text-red-400 border border-red-900 transition-colors ml-auto disabled:opacity-50"
        >
          <AlertTriangle size={13} />
          Clear All
        </button>
      </div>

      {/* Consolidation result */}
      {consolidationResult && (
        <div className="mx-3 mt-3 p-3 rounded-lg bg-brand-900/30 border border-brand-700 text-xs text-brand-300 flex flex-wrap gap-3">
          <span>✓ Episodic processed: <strong>{consolidationResult.episodic_processed}</strong></span>
          <span>✓ Facts extracted: <strong>{consolidationResult.facts_extracted}</strong></span>
          <span>✓ Stored: <strong>{consolidationResult.facts_stored}</strong></span>
          <span>✓ Contradictions resolved: <strong>{consolidationResult.contradictions_resolved}</strong></span>
          <span>✓ Pruned: <strong>{consolidationResult.memories_pruned}</strong></span>
        </div>
      )}

      {/* Tabs */}
      <div className="flex gap-1 p-3 pb-0">
        {(["semantic", "episodic"] as const).map((tab) => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-t-lg text-sm font-medium transition-colors ${
              activeTab === tab
                ? "bg-gray-800 text-gray-100 border border-gray-700 border-b-gray-800"
                : "text-gray-500 hover:text-gray-300"
            }`}
          >
            {tab === "semantic" ? <Database size={13} /> : <Clock size={13} />}
            {tab.charAt(0).toUpperCase() + tab.slice(1)}
            <span className="ml-1 text-[10px] bg-gray-700 text-gray-400 rounded-full px-1.5 py-0.5">
              {tab === "semantic" ? semanticMems.length : episodicMems.length}
            </span>
          </button>
        ))}
      </div>

      {/* Memory list */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 scrollbar-thin">
        {loading && (
          <div className="flex items-center justify-center py-12 text-gray-500 gap-2">
            <RefreshCw size={16} className="animate-spin" />
            <span className="text-sm">Loading memories…</span>
          </div>
        )}

        {!loading && shownMems.length === 0 && (
          <div className="flex flex-col items-center justify-center py-12 text-gray-600 space-y-2">
            {activeTab === "semantic" ? <Database size={32} /> : <Clock size={32} />}
            <p className="text-sm">No {activeTab} memories yet.</p>
            <p className="text-xs text-gray-700 text-center max-w-xs">
              {activeTab === "semantic"
                ? "Semantic memories are created by consolidation after enough chat turns."
                : "Episodic memories are saved after each conversation turn."}
            </p>
          </div>
        )}

        {!loading &&
          shownMems.map((mem) => (
            <MemoryRow key={mem.id} mem={mem} onDelete={handleDelete} />
          ))}
      </div>

      {/* Footer stats */}
      <div className="px-3 py-2 border-t border-gray-800 text-xs text-gray-600 flex justify-between">
        <span>{semanticMems.length} semantic · {episodicMems.length} episodic</span>
        <span>Total: {(memories?.total ?? 0)} memories</span>
      </div>
    </div>
  );
}
