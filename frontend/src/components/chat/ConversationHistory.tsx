"use client";

import React, { useEffect, useState, useRef, useCallback } from "react";
import { MessageSquare, Trash2, Loader2 } from "lucide-react";
import { useAuth } from "@clerk/nextjs";
import {
  listConversations,
  deleteConversation,
  setAuthTokenGetter,
} from "@/lib/api";
import { cn } from "@/lib/utils";
import type { ConversationListItem } from "@/types";

interface ConversationHistoryProps {
  onSelectConversation: (conversation: ConversationListItem) => void;
  refreshTrigger?: number;
}

export function ConversationHistory({
  onSelectConversation,
  refreshTrigger = 0,
}: ConversationHistoryProps) {
  const [conversations, setConversations] = useState<ConversationListItem[]>(
    []
  );
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<number | null>(null);
  const [isAuthReady, setIsAuthReady] = useState(false);

  const { getToken, isSignedIn, isLoaded } = useAuth();

  // Set up the auth token getter FIRST
  useEffect(() => {
    if (isLoaded && isSignedIn && getToken) {
      console.log("Setting up auth token getter");
      setAuthTokenGetter(async () => {
        try {
          const token = await getToken();
          return token;
        } catch (e) {
          console.error("Failed to get token:", e);
          return null;
        }
      });
      setIsAuthReady(true);
    } else if (isLoaded && !isSignedIn) {
      setIsAuthReady(false);
      setIsLoading(false);
    }
  }, [getToken, isSignedIn, isLoaded]);

  const loadConversations = useCallback(async () => {
    if (!isAuthReady) {
      console.log("Auth not ready, skipping load");
      return;
    }

    try {
      setIsLoading(true);
      setError(null);
      console.log("Loading conversations...");
      const data = await listConversations();
      console.log("Loaded conversations:", data.length);
      setConversations(data);
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to load history";
      setError(message);
      console.error("Failed to load conversations:", err);
    } finally {
      setIsLoading(false);
    }
  }, [isAuthReady]);

  // Load conversations when auth is ready
  useEffect(() => {
    if (isAuthReady) {
      loadConversations();
    }
  }, [isAuthReady, refreshTrigger, loadConversations]);

  const handleDelete = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!confirm("Delete this conversation?")) return;

    try {
      setDeletingId(id);
      await deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
    } catch (err) {
      console.error("Failed to delete:", err);
    } finally {
      setDeletingId(null);
    }
  };

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diffDays = Math.floor(
      (now.getTime() - date.getTime()) / (1000 * 60 * 60 * 24)
    );

    if (diffDays === 0) return "Today";
    if (diffDays === 1) return "Yesterday";
    if (diffDays < 7) return `${diffDays} days ago`;
    return date.toLocaleDateString();
  };

  // Show loading while Clerk is loading
  if (!isLoaded) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-muted">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
    );
  }

  // Show sign in message if not authenticated
  if (!isSignedIn) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-text-muted p-4">
        <p className="text-sm">Sign in to see your history</p>
      </div>
    );
  }

  // Show loading while fetching
  if (isLoading) {
    return (
      <div className="flex-1 flex items-center justify-center text-text-muted">
        <Loader2 className="w-5 h-5 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-text-muted p-4">
        <p className="text-sm mb-2">{error}</p>
        <button
          onClick={loadConversations}
          className="text-xs text-accent-primary hover:underline"
        >
          Try again
        </button>
      </div>
    );
  }

  if (conversations.length === 0) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center text-text-muted p-4">
        <MessageSquare className="w-8 h-8 mb-2 opacity-50" />
        <p className="text-sm">No conversations yet</p>
      </div>
    );
  }

  return (
    <div className="flex-1 overflow-y-auto">
      {conversations.map((conv) => (
        <div
          key={conv.id}
          onClick={() => onSelectConversation(conv)}
          className={cn(
            "group flex items-start gap-3 p-3 cursor-pointer",
            "hover:bg-background-modifier transition-colors",
            "border-b border-border-subtle"
          )}
        >
          <MessageSquare className="w-4 h-4 text-text-muted flex-shrink-0 mt-0.5" />

          <div className="flex-1 min-w-0">
            <p className="text-sm text-text-normal truncate">{conv.topic}</p>
            <p className="text-xs text-text-muted">
              {formatDate(conv.created_at)} • {conv.message_count} messages
            </p>
          </div>

          <button
            onClick={(e) => handleDelete(conv.id, e)}
            className={cn(
              "opacity-0 group-hover:opacity-100 p-1 rounded",
              "text-text-muted hover:text-accent-danger hover:bg-background-primary",
              "transition-all"
            )}
            disabled={deletingId === conv.id}
          >
            {deletingId === conv.id ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Trash2 className="w-3.5 h-3.5" />
            )}
          </button>
        </div>
      ))}
    </div>
  );
}
