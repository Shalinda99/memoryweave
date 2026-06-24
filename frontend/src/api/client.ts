const BASE_URL = import.meta.env.VITE_API_URL ?? "";

export interface ChatResponse {
  reply: string;
  user_id: string;
  session_id: string;
  memories_used: string[];
  tokens_used: number;
}

export interface MemoryItem {
  id: string;
  content: string;
  memory_type: string;
  importance_score: number;
  created_at: string;
  tier: string;
}

export interface MemoriesResponse {
  user_id: string;
  semantic: MemoryItem[];
  episodic: MemoryItem[];
  total: number;
}

export interface MetricsResponse {
  user_id: string;
  semantic_memories: number;
  episodic_memories: number;
  avg_health_score: number;
  prune_candidates: number;
  memory_type_breakdown: Record<string, number>;
  active_sessions: number;
  top_memories: {
    id: string;
    content: string;
    memory_type: string;
    importance_score: number;
    access_count: number;
  }[];
}

export interface ConsolidationResponse {
  user_id: string;
  episodic_processed: number;
  facts_extracted: number;
  facts_stored: number;
  contradictions_resolved: number;
  memories_pruned: number;
}

export interface ExportResponse {
  user_id: string;
  exported_at: string;
  semantic: object[];
  episodic: object[];
}

async function request<T>(
  path: string,
  options?: RequestInit
): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail ?? "Request failed");
  }
  return res.json() as Promise<T>;
}

export const api = {
  ping: () => request<{ qwen_response: string; status: string }>("/api/v1/ping"),

  chat: (user_id: string, message: string, session_id?: string) =>
    request<ChatResponse>("/api/v1/chat", {
      method: "POST",
      body: JSON.stringify({ user_id, message, session_id }),
    }),

  getMemories: (user_id: string) =>
    request<MemoriesResponse>(`/api/v1/memories/${user_id}`),

  deleteSemanticMemory: (memory_id: string) =>
    request<{ deleted: string }>(`/api/v1/memories/semantic/${memory_id}`, {
      method: "DELETE",
    }),

  deleteEpisodicMemory: (memory_id: string) =>
    request<{ deleted: string }>(`/api/v1/memories/episodic/${memory_id}`, {
      method: "DELETE",
    }),

  deleteAllMemories: (user_id: string) =>
    request<{ semantic_deleted: number; episodic_deleted: number }>(
      `/api/v1/memories/${user_id}/all`,
      { method: "DELETE" }
    ),

  consolidate: (user_id: string) =>
    request<ConsolidationResponse>(`/api/v1/consolidate/${user_id}`, {
      method: "POST",
    }),

  getMetrics: (user_id: string) =>
    request<MetricsResponse>(`/api/v1/metrics/${user_id}`),

  exportMemories: (user_id: string) =>
    request<ExportResponse>(`/api/v1/export/${user_id}`),

  clearSession: (session_id: string) =>
    request<{ cleared: string }>(`/api/v1/sessions/${session_id}`, {
      method: "DELETE",
    }),
};
