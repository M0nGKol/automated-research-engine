/**
 * Type definitions for the Research Agent UI
 */

export type MessageRole = "user" | "assistant" | "system";

export type ResearchStatus =
  | "pending"
  | "searching"
  | "extracting"
  | "summarizing"
  | "synthesizing"
  | "completed"
  | "error";

export type ResearchDepth = "quick" | "standard" | "deep";

export interface Source {
  url: string;
  title: string;
  snippet: string;
  content?: string;
  credibility_score: number;
  summary?: string;
}

export interface ResearchProgress {
  status: ResearchStatus;
  message: string;
  progress: number;
  sources_found: number;
  sources_processed: number;
}

export interface ResearchResult {
  topic: string;
  briefing: string;
  sources: Source[];
  total_time_seconds: number;
  model_used: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: Date;
  metadata?: {
    isProgress?: boolean;
    progress?: ResearchProgress;
    result?: ResearchResult;
    isStreaming?: boolean;
  };
}

export interface ResearchRequest {
  topic: string;
  depth: ResearchDepth;
  include_academic: boolean;
}

// Conversation types
export interface ConversationListItem {
  id: number;
  topic: string;
  depth: string;
  created_at: string;
  message_count: number;
}

export interface ConversationMessage {
  id: number;
  role: MessageRole;
  content: string;
  timestamp: string;
}

export interface Conversation {
  id: number;
  topic: string;
  depth: string;
  briefing?: string;
  total_time_seconds?: number;
  model_used?: string;
  created_at: string;
  updated_at: string;
  messages: ConversationMessage[];
}

// SSE Event types
export interface SSEProgressEvent {
  event: "progress";
  data: ResearchProgress;
}

export interface SSEResultEvent {
  event: "result";
  data: ResearchResult;
}

export interface SSEErrorEvent {
  event: "error";
  data: { message: string };
}

export type SSEEvent = SSEProgressEvent | SSEResultEvent | SSEErrorEvent;

// PDF Export
export interface PDFExportRequest {
  topic: string;
  briefing: string;
  sources: Source[];
  total_time_seconds: number;
  model_used: string;
}
