import { useState, useCallback, useEffect } from "react";
import {
  Brain,
  MessageSquare,
  Database,
  BarChart2,
  ChevronDown,
  Plus,
  Layers,
  TrendingUp,
} from "lucide-react";
import ChatPanel from "./components/ChatPanel";
import MemoryPanel from "./components/MemoryPanel";
import MetricsPanel from "./components/MetricsPanel";
import TimelinePanel from "./components/TimelinePanel";
import AccuracyPanel from "./components/AccuracyPanel";
import { api, MemoriesResponse } from "./api/client";

type Tab = "chat" | "memories" | "metrics" | "timeline" | "accuracy";

const PRESET_USERS = ["alice", "bob", "carol", "dave"];

function generateSessionId() {
  return `session-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;
}

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");
  const [userId, setUserId] = useState("alice");
  const [customUser, setCustomUser] = useState("");
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [sessionId] = useState(generateSessionId);
  const [memories, setMemories] = useState<MemoriesResponse | null>(null);
  const [memoriesLoading, setMemoriesLoading] = useState(false);

  const fetchMemories = useCallback(async () => {
    setMemoriesLoading(true);
    try {
      const data = await api.getMemories(userId);
      setMemories(data);
    } catch {
      setMemories(null);
    } finally {
      setMemoriesLoading(false);
    }
  }, [userId]);

  useEffect(() => {
    fetchMemories();
  }, [fetchMemories]);

  const selectUser = (u: string) => {
    setUserId(u);
    setShowUserMenu(false);
    setMemories(null);
  };

  const applyCustomUser = () => {
    const u = customUser.trim();
    if (u) {
      selectUser(u);
      setCustomUser("");
    }
  };

  const tabs: { id: Tab; label: string; icon: React.ReactNode }[] = [
    { id: "chat", label: "Chat", icon: <MessageSquare size={15} /> },
    { id: "memories", label: "Memories", icon: <Database size={15} /> },
    { id: "metrics", label: "Metrics", icon: <BarChart2 size={15} /> },
    { id: "timeline", label: "Timeline", icon: <Layers size={15} /> },
    { id: "accuracy", label: "Accuracy", icon: <TrendingUp size={15} /> },
  ];

  return (
    <div className="flex flex-col h-screen bg-gray-950 text-gray-100">
      {/* Header */}
      <header className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-950 flex-shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center">
            <Brain size={18} className="text-white" />
          </div>
          <div>
            <h1 className="text-sm font-bold text-gray-100 leading-none">MemoryWeave</h1>
            <p className="text-[10px] text-gray-500 leading-none mt-0.5">
              Persistent AI Memory · Powered by Alibaba Cloud Qwen
            </p>
          </div>
        </div>

        {/* User selector */}
        <div className="relative">
          <button
            onClick={() => setShowUserMenu((v) => !v)}
            className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-gray-800 hover:bg-gray-700 border border-gray-700 text-sm transition-colors"
          >
            <div className="w-5 h-5 rounded-full bg-brand-600 flex items-center justify-center text-[10px] font-bold text-white uppercase">
              {userId[0]}
            </div>
            <span className="text-gray-300">{userId}</span>
            <ChevronDown size={13} className="text-gray-500" />
          </button>

          {showUserMenu && (
            <div className="absolute right-0 top-full mt-1 w-52 rounded-xl bg-gray-900 border border-gray-800 shadow-xl z-50 overflow-hidden">
              <div className="p-2 space-y-0.5">
                {PRESET_USERS.map((u) => (
                  <button
                    key={u}
                    onClick={() => selectUser(u)}
                    className={`w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                      userId === u
                        ? "bg-brand-600/20 text-brand-300"
                        : "hover:bg-gray-800 text-gray-300"
                    }`}
                  >
                    <div className="w-5 h-5 rounded-full bg-gray-700 flex items-center justify-center text-[10px] font-bold uppercase">
                      {u[0]}
                    </div>
                    {u}
                  </button>
                ))}
              </div>
              <div className="border-t border-gray-800 p-2">
                <div className="flex gap-1.5">
                  <input
                    value={customUser}
                    onChange={(e) => setCustomUser(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && applyCustomUser()}
                    placeholder="Custom user ID…"
                    className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-2.5 py-1.5 text-xs text-gray-300 placeholder-gray-600 outline-none focus:border-brand-500"
                  />
                  <button
                    onClick={applyCustomUser}
                    className="px-2 py-1.5 rounded-lg bg-brand-600 hover:bg-brand-500 transition-colors"
                  >
                    <Plus size={13} className="text-white" />
                  </button>
                </div>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* Tab bar */}
      <div className="flex gap-0 border-b border-gray-800 bg-gray-950 flex-shrink-0 px-4">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
              tab === t.id
                ? "border-brand-500 text-brand-400"
                : "border-transparent text-gray-500 hover:text-gray-300"
            }`}
          >
            {t.icon}
            {t.label}
            {t.id === "memories" && memories && (
              <span className="ml-1 text-[10px] bg-gray-800 text-gray-400 rounded-full px-1.5 py-0.5">
                {memories.total}
              </span>
            )}
          </button>
        ))}
      </div>

      {/* Main content */}
      <div className="flex-1 overflow-hidden">
        {tab === "chat" && (
          <ChatPanel
            userId={userId}
            sessionId={sessionId}
            onMemoryUpdate={fetchMemories}
          />
        )}
        {tab === "memories" && (
          <MemoryPanel
            userId={userId}
            memories={memories}
            loading={memoriesLoading}
            onRefresh={fetchMemories}
          />
        )}
        {tab === "metrics" && <MetricsPanel userId={userId} />}
        {tab === "timeline" && <TimelinePanel userId={userId} />}
        {tab === "accuracy" && <AccuracyPanel userId={userId} />}
      </div>

      {/* Click-away for user menu */}
      {showUserMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowUserMenu(false)}
        />
      )}
    </div>
  );
}
