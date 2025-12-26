"use client";

import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Bot, User } from "lucide-react";
import { cn, formatTime, getStatusColor, getStatusIcon } from "@/lib/utils";
import { Progress } from "@/components/ui/progress";
import type { ChatMessage as ChatMessageType } from "@/types";
import { SourcesPanel } from "./SourcesPanel";

interface ChatMessageProps {
  message: ChatMessageType;
}

export function ChatMessage({ message }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isProgress = message.metadata?.isProgress;
  const progress = message.metadata?.progress;
  const result = message.metadata?.result;
  const isStreaming = message.metadata?.isStreaming;

  return (
    <div
      className={cn(
        "group flex gap-4 py-4 px-4 message-enter",
        "hover:bg-background-secondary/50 transition-colors"
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          "flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center",
          isUser ? "bg-accent-primary" : "bg-accent-success"
        )}
      >
        {isUser ? (
          <User className="w-5 h-5 text-white" />
        ) : (
          <Bot className="w-5 h-5 text-white" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 min-w-0">
        {/* Header */}
        <div className="flex items-center gap-2 mb-1">
          <span className={cn("font-semibold", isUser ? "text-accent-primary" : "text-accent-success")}>
            {isUser ? "You" : "Research Agent"}
          </span>
          <span className="text-xs text-text-muted">
            {formatTime(message.timestamp)}
          </span>
          {isStreaming && (
            <span className="text-xs text-accent-warning animate-pulse">
              ● Working...
            </span>
          )}
        </div>

        {/* Progress indicator */}
        {isProgress && progress && (
          <div className="mb-4 p-3 rounded-lg bg-background-primary border border-border-subtle">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-lg">{getStatusIcon(progress.status)}</span>
              <span className={cn("font-medium", getStatusColor(progress.status))}>
                {progress.message}
              </span>
            </div>
            <Progress value={progress.progress * 100} className="mb-2" />
            <div className="flex gap-4 text-xs text-text-muted">
              <span>Sources found: {progress.sources_found}</span>
              <span>Processed: {progress.sources_processed}</span>
            </div>
          </div>
        )}

        {/* Message content */}
        {!isProgress && message.content && (
          <div className="markdown-content">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {message.content}
            </ReactMarkdown>
          </div>
        )}

        {/* Sources panel for results - pass full result for PDF export */}
        {result && result.sources.length > 0 && (
          <SourcesPanel 
            sources={result.sources} 
            totalTime={result.total_time_seconds}
            result={result}
          />
        )}
      </div>
    </div>
  );
}
