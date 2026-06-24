import { useState, useRef, useEffect } from "react";
import { Send, Brain, User, Loader2, Sparkles, ChevronDown, ChevronUp } from "lucide-react";
import { api, ChatResponse } from "../api/client";

interface Message {
  role: "user" | "assistant";
  content: string;
  memories_used?: string[];
  tokens_used?: number;
  timestamp: Date;
}

interface Props {
  userId: string;
  sessionId: string;
  onMemoryUpdate: () => void;
}

export default function ChatPanel({ userId, sessionId, onMemoryUpdate }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [expandedMemories, setExpandedMemories] = useState<Set<number>>(new Set());
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const toggleMemories = (index: number) => {
    setExpandedMemories((prev) => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const sendMessage = async () => {
    const text = input.trim();
    if (!text || loading) return;

    const userMsg: Message = { role: "user", content: text, timestamp: new Date() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    setLoading(true);

    try {
      const res: ChatResponse = await api.chat(userId, text, sessionId);
      const assistantMsg: Message = {
        role: "assistant",
        content: res.reply,
        memories_used: res.memories_used,
        tokens_used: res.tokens_used,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMsg]);
      onMemoryUpdate();
    } catch (err) {
      const errMsg: Message = {
        role: "assistant",
        content: `⚠️ Error: ${err instanceof Error ? err.message : "Unknown error"}`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errMsg]);
    } finally {
      setLoading(false);
      inputRef.current?.focus();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin">
        {messages.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-center text-gray-500 space-y-3 py-16">
            <Brain size={48} className="text-brand-500 opacity-60" />
            <p className="text-lg font-medium text-gray-400">Start a conversation</p>
            <p className="text-sm max-w-sm">
              MemoryWeave will remember what you share — across sessions, across days.
            </p>
            <div className="mt-4 grid grid-cols-1 gap-2 text-left text-sm">
              {[
                "Hi! I'm Alex, a Python developer who loves functional programming.",
                "I prefer concise explanations with code examples.",
                "I'm working on a FastAPI project for a hackathon.",
              ].map((s) => (
                <button
                  key={s}
                  onClick={() => setInput(s)}
                  className="px-3 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-gray-300 text-left transition-colors border border-gray-700"
                >
                  "{s}"
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div
            key={i}
            className={`flex gap-3 ${msg.role === "user" ? "justify-end animate-fade-in-right" : "justify-start animate-fade-in-left"}`}
          >
            {msg.role === "assistant" && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center mt-1 glow-brand animate-brain-glow">
                <Brain size={16} className="text-white" />
              </div>
            )}

            <div className={`max-w-[75%] space-y-1 ${msg.role === "user" ? "items-end" : "items-start"} flex flex-col`}>
              <div
                className={`rounded-2xl px-4 py-3 text-sm leading-relaxed whitespace-pre-wrap ${
                  msg.role === "user"
                    ? "bg-brand-600 text-white rounded-br-sm shadow-lg shadow-brand-900/30"
                    : "bg-gray-800/90 text-gray-100 rounded-bl-sm border border-gray-700/80 shadow-lg shadow-black/20"
                }`}
              >
                {msg.content}
              </div>

              {/* Memory indicators */}
              {msg.role === "assistant" && msg.memories_used && msg.memories_used.length > 0 && (
                <button
                  onClick={() => toggleMemories(i)}
                  className="flex items-center gap-1 text-xs text-brand-400 hover:text-brand-300 transition-colors"
                >
                  <Sparkles size={12} />
                  <span>{msg.memories_used.length} memor{msg.memories_used.length === 1 ? "y" : "ies"} used</span>
                  {expandedMemories.has(i) ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
                </button>
              )}

              {expandedMemories.has(i) && msg.memories_used && (
                <div className="bg-gray-900 border border-gray-700 rounded-lg p-3 space-y-1 text-xs text-gray-400 max-w-full">
                  {msg.memories_used.map((m, j) => (
                    <div key={j} className="flex gap-2">
                      <span className={`flex-shrink-0 px-1.5 py-0.5 rounded text-[10px] font-medium ${
                        m.startsWith("[semantic]") ? "bg-blue-900 text-blue-300" : "bg-purple-900 text-purple-300"
                      }`}>
                        {m.startsWith("[semantic]") ? "SEM" : "EPI"}
                      </span>
                      <span className="truncate">{m.replace(/^\[(semantic|episodic)\] /, "")}</span>
                    </div>
                  ))}
                </div>
              )}

              <span className="text-[10px] text-gray-600 px-1">
                {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                {msg.tokens_used ? ` · ~${msg.tokens_used} tokens` : ""}
              </span>
            </div>

            {msg.role === "user" && (
              <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-700 flex items-center justify-center mt-1">
                <User size={16} className="text-gray-300" />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex gap-3 justify-start animate-fade-in-left">
            <div className="w-8 h-8 rounded-full bg-brand-600 flex items-center justify-center glow-brand">
              <Brain size={16} className="text-white" />
            </div>
            <div className="bg-gray-800/90 border border-gray-700/80 rounded-2xl rounded-bl-sm px-4 py-3.5 flex items-center gap-1.5">
              {[0, 1, 2].map((n) => (
                <span
                  key={n}
                  className="w-2 h-2 rounded-full bg-brand-400 inline-block"
                  style={{ animation: `dotBounce 1.2s ease-in-out ${n * 0.18}s infinite` }}
                />
              ))}
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="p-4 border-t border-gray-800">
        <div className="flex gap-2 items-end bg-gray-800 rounded-2xl border border-gray-700 focus-within:border-brand-500 transition-colors p-2">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message MemoryWeave… (Enter to send, Shift+Enter for newline)"
            rows={1}
            className="flex-1 bg-transparent resize-none outline-none text-sm text-gray-100 placeholder-gray-500 px-2 py-1 max-h-32 overflow-y-auto scrollbar-thin"
            style={{ minHeight: "36px" }}
            onInput={(e) => {
              const t = e.currentTarget;
              t.style.height = "auto";
              t.style.height = `${Math.min(t.scrollHeight, 128)}px`;
            }}
          />
          <button
            onClick={sendMessage}
            disabled={!input.trim() || loading}
            className="flex-shrink-0 w-9 h-9 rounded-xl bg-brand-600 hover:bg-brand-500 disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center transition-colors"
          >
            {loading ? (
              <span className="w-4 h-4 flex items-center justify-center">
                <Loader2 size={14} className="animate-spin text-white" />
              </span>
            ) : (
              <Send size={16} className="text-white" />
            )}
          </button>
        </div>
        <p className="text-[10px] text-gray-600 text-center mt-2">
          Powered by Alibaba Cloud Qwen · session: {sessionId.slice(0, 8)}…
        </p>
      </div>
    </div>
  );
}
