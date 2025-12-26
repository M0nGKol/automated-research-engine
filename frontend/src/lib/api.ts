/**
 * API client for the Research Agent backend
 */

import type {
  Conversation,
  ConversationListItem,
  PDFExportRequest,
  ResearchProgress,
  ResearchRequest,
  ResearchResult,
} from "@/types";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

// Token getter function - will be set by the auth hook
let getAuthToken: (() => Promise<string | null>) | null = null;

/**
 * Set the auth token getter function (called from useResearch hook)
 */
export function setAuthTokenGetter(getter: () => Promise<string | null>) {
  getAuthToken = getter;
}

/**
 * Get headers with optional auth token
 */
async function getHeaders(includeAuth: boolean = true): Promise<HeadersInit> {
  const headers: HeadersInit = {
    "Content-Type": "application/json",
  };

  if (includeAuth && getAuthToken) {
    const token = await getAuthToken();
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
  }

  return headers;
}

export type StreamCallback = {
  onProgress: (progress: ResearchProgress) => void;
  onResult: (result: ResearchResult) => void;
  onError: (error: string) => void;
  onComplete: () => void;
};

/**
 * Start a research task and stream progress updates
 */
export async function startResearch(
  request: ResearchRequest,
  callbacks: StreamCallback
): Promise<void> {
  const headers = await getHeaders();
  
  const response = await fetch(`${API_BASE_URL}/api/research`, {
    method: "POST",
    headers,
    body: JSON.stringify(request),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Please sign in to use the research agent.");
    }
    if (response.status === 429) {
      throw new Error("Rate limit exceeded. Please wait a moment and try again.");
    }
    throw new Error(`HTTP error! status: ${response.status}`);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    throw new Error("No response body");
  }

  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();

      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      // Process complete SSE messages
      const lines = buffer.split("\n");
      buffer = lines.pop() || "";

      for (const line of lines) {
        if (line.startsWith("data: ")) {
          const data = line.slice(6);
          if (data === "[DONE]") {
            callbacks.onComplete();
            return;
          }

          try {
            const parsed = JSON.parse(data);

            if (parsed.status) {
              // It's a progress event
              callbacks.onProgress(parsed as ResearchProgress);
            } else if (parsed.briefing) {
              // It's a result event
              callbacks.onResult(parsed as ResearchResult);
            } else if (parsed.message && !parsed.status) {
              // It's an error event
              callbacks.onError(parsed.message);
            }
          } catch (e) {
            // Skip invalid JSON
            console.warn("Invalid JSON in SSE:", data);
          }
        } else if (line.startsWith("event: ")) {
          // SSE event type - we handle by data content instead
        }
      }
    }

    callbacks.onComplete();
  } catch (error) {
    callbacks.onError(error instanceof Error ? error.message : "Unknown error");
  } finally {
    reader.releaseLock();
  }
}

/**
 * Health check
 */
export async function checkHealth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/health`);
    return response.ok;
  } catch {
    return false;
  }
}

/**
 * Get backend configuration
 */
export async function getConfig(): Promise<{
  llm_provider: string;
  llm_model: string;
  max_sources: number;
  max_search_results: number;
} | null> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/config`);
    if (!response.ok) return null;
    return response.json();
  } catch {
    return null;
  }
}

// ============================================================================
// Conversation API (requires authentication)
// ============================================================================

/**
 * List all conversations for the current user
 */
export async function listConversations(
  limit: number = 20,
  offset: number = 0
): Promise<ConversationListItem[]> {
  const headers = await getHeaders();
  
  const response = await fetch(
    `${API_BASE_URL}/api/conversations?limit=${limit}&offset=${offset}`,
    { headers }
  );
  
  if (response.status === 401) {
    throw new Error("Please sign in to view conversations");
  }
  if (!response.ok) {
    throw new Error("Failed to fetch conversations");
  }
  return response.json();
}

/**
 * Get a single conversation by ID
 */
export async function getConversation(id: number): Promise<Conversation> {
  const headers = await getHeaders();
  
  const response = await fetch(`${API_BASE_URL}/api/conversations/${id}`, {
    headers,
  });
  
  if (response.status === 401) {
    throw new Error("Please sign in to view this conversation");
  }
  if (response.status === 403) {
    throw new Error("You don't have access to this conversation");
  }
  if (!response.ok) {
    throw new Error("Conversation not found");
  }
  return response.json();
}

/**
 * Create a new conversation
 */
export async function createConversation(
  topic: string,
  depth: string = "standard"
): Promise<Conversation> {
  const headers = await getHeaders();
  
  const response = await fetch(`${API_BASE_URL}/api/conversations`, {
    method: "POST",
    headers,
    body: JSON.stringify({ topic, depth, messages: [] }),
  });
  
  if (response.status === 401) {
    throw new Error("Please sign in to create conversations");
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || "Failed to create conversation");
  }
  return response.json();
}

/**
 * Update a conversation with research results
 */
export async function updateConversation(
  id: number,
  data: {
    briefing?: string;
    sources_json?: string;
    total_time_seconds?: number;
    model_used?: string;
    messages?: { role: string; content: string }[];
  }
): Promise<Conversation> {
  const headers = await getHeaders();
  
  const response = await fetch(`${API_BASE_URL}/api/conversations/${id}`, {
    method: "PUT",
    headers,
    body: JSON.stringify(data),
  });
  
  if (response.status === 401) {
    throw new Error("Please sign in to update conversations");
  }
  if (response.status === 403) {
    throw new Error("You don't have access to this conversation");
  }
  if (!response.ok) {
    throw new Error("Failed to update conversation");
  }
  return response.json();
}

/**
 * Delete a conversation
 */
export async function deleteConversation(id: number): Promise<void> {
  const headers = await getHeaders();
  
  const response = await fetch(`${API_BASE_URL}/api/conversations/${id}`, {
    method: "DELETE",
    headers,
  });
  
  if (response.status === 401) {
    throw new Error("Please sign in to delete conversations");
  }
  if (response.status === 403) {
    throw new Error("You don't have access to this conversation");
  }
  if (!response.ok) {
    throw new Error("Failed to delete conversation");
  }
}

// ============================================================================
// PDF Export API
// ============================================================================

/**
 * Export research briefing as PDF
 */
export async function exportPDF(data: PDFExportRequest): Promise<Blob> {
  const headers = await getHeaders();
  
  const response = await fetch(`${API_BASE_URL}/api/export/pdf`, {
    method: "POST",
    headers,
    body: JSON.stringify(data),
  });

  if (!response.ok) {
    throw new Error("Failed to generate PDF");
  }

  return response.blob();
}

/**
 * Download PDF helper
 */
export function downloadPDF(blob: Blob, filename: string): void {
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
}

// ============================================================================
// Cache API
// ============================================================================

/**
 * Get cache statistics
 */
export async function getCacheStats(): Promise<{
  size: number;
  maxsize: number;
  ttl_hours: number;
  hits: number;
  misses: number;
  total_requests: number;
  hit_rate_percent: number;
}> {
  const response = await fetch(`${API_BASE_URL}/api/cache/stats`);
  if (!response.ok) {
    throw new Error("Failed to fetch cache stats");
  }
  return response.json();
}

/**
 * Clear all cache entries
 */
export async function clearCache(): Promise<{ status: string; entries_removed: number }> {
  const response = await fetch(`${API_BASE_URL}/api/cache/clear`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error("Failed to clear cache");
  }
  return response.json();
}
