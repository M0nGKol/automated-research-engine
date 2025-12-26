"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import { useAuth } from "@clerk/nextjs";
import { startResearch, createConversation, updateConversation, getConversation, setAuthTokenGetter, type StreamCallback } from "@/lib/api";
import { generateId } from "@/lib/utils";
import type {
  ChatMessage,
  ResearchDepth,
  ResearchProgress,
  ResearchResult,
  MessageRole,
} from "@/types";

interface UseResearchReturn {
  messages: ChatMessage[];
  isLoading: boolean;
  currentProgress: ResearchProgress | null;
  lastResult: ResearchResult | null;
  submitTopic: (topic: string, depth: ResearchDepth, includeAcademic: boolean) => Promise<void>;
  clearMessages: () => void;
  loadConversation: (conversationId: number) => Promise<void>;
}

export function useResearch(): UseResearchReturn {
  const { getToken } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [currentProgress, setCurrentProgress] =
    useState<ResearchProgress | null>(null);
  const [lastResult, setLastResult] = useState<ResearchResult | null>(null);
  const assistantMessageIdRef = useRef<string | null>(null);
  const currentConversationIdRef = useRef<number | null>(null);

  // Set up auth token getter for API calls
  useEffect(() => {
    setAuthTokenGetter(async () => {
      try {
        return await getToken();
      } catch {
        return null;
      }
    });
  }, [getToken]);

  const addMessage = useCallback((message: Omit<ChatMessage, "id">) => {
    const newMessage: ChatMessage = {
      ...message,
      id: generateId(),
    };
    setMessages((prev) => [...prev, newMessage]);
    return newMessage.id;
  }, []);

  const updateMessage = useCallback(
    (id: string, updates: Partial<ChatMessage>) => {
      setMessages((prev) =>
        prev.map((msg) => (msg.id === id ? { ...msg, ...updates } : msg))
      );
    },
    []
  );

  const submitTopic = useCallback(
    async (topic: string, depth: ResearchDepth, includeAcademic: boolean) => {
      if (!topic.trim() || isLoading) return;

      setIsLoading(true);
      setCurrentProgress(null);
      setLastResult(null);
      currentConversationIdRef.current = null;

      // Add user message with academic indicator
      const userContent = includeAcademic 
        ? `${topic} [📚 Including academic sources]`
        : topic;

      addMessage({
        role: "user",
        content: userContent,
        timestamp: new Date(),
      });

      // Create conversation in database
      try {
        const conversation = await createConversation(topic, depth);
        currentConversationIdRef.current = conversation.id;
        console.log("✓ Created conversation:", conversation.id);
      } catch (error) {
        console.error("Failed to create conversation:", error);
        // Continue anyway - don't block research
      }

      // Add assistant message placeholder
      const assistantId = addMessage({
        role: "assistant",
        content: "",
        timestamp: new Date(),
        metadata: { isStreaming: true },
      });
      assistantMessageIdRef.current = assistantId;

      const callbacks: StreamCallback = {
        onProgress: (progress) => {
          setCurrentProgress(progress);
          updateMessage(assistantId, {
            content: `${progress.message}\n\nProgress: ${Math.round(
              progress.progress * 100
            )}%`,
            metadata: {
              isProgress: true,
              progress,
              isStreaming: true,
            },
          });
        },
        onResult: async (result) => {
          setLastResult(result);
          updateMessage(assistantId, {
            content: result.briefing,
            metadata: {
              result,
              isStreaming: false,
            },
          });

          // Save results to conversation
          if (currentConversationIdRef.current) {
            try {
              await updateConversation(currentConversationIdRef.current, {
                briefing: result.briefing,
                sources_json: JSON.stringify(result.sources),
                total_time_seconds: result.total_time_seconds,
                model_used: result.model_used,
                messages: [
                  {
                    role: "user",
                    content: topic,
                  },
                  {
                    role: "assistant",
                    content: result.briefing,
                  },
                ],
              });
              console.log("✓ Saved conversation:", currentConversationIdRef.current);
            } catch (error) {
              console.error("Failed to save conversation:", error);
            }
          }
        },
        onError: (error) => {
          updateMessage(assistantId, {
            content: `Error: ${error}`,
            metadata: { isStreaming: false },
          });
        },
        onComplete: () => {
          setIsLoading(false);
          setCurrentProgress(null);
          assistantMessageIdRef.current = null;
        },
      };

      try {
        await startResearch({ topic, depth, include_academic: includeAcademic }, callbacks);
      } catch (error) {
        updateMessage(assistantId, {
          content: `Failed to start research: ${
            error instanceof Error ? error.message : "Unknown error"
          }`,
          metadata: { isStreaming: false },
        });
        setIsLoading(false);
        setCurrentProgress(null);
      }
    },
    [isLoading, addMessage, updateMessage]
  );

  const loadConversation = useCallback(async (conversationId: number) => {
    try {
      const conversation = await getConversation(conversationId);
      
      // Convert conversation messages to chat messages
      const chatMessages: ChatMessage[] = conversation.messages.map((msg) => ({
        id: generateId(),
        role: msg.role as MessageRole,
        content: msg.content,
        timestamp: new Date(msg.timestamp),
        metadata: conversation.briefing && msg.role === "assistant" ? {
          result: {
            topic: conversation.topic,
            briefing: conversation.briefing,
            sources: [], // Will be populated from sources_json if needed
            total_time_seconds: conversation.total_time_seconds || 0,
            model_used: conversation.model_used || "unknown",
          },
        } : undefined,
      }));

      setMessages(chatMessages);
      currentConversationIdRef.current = conversationId;
      
      if (conversation.briefing) {
        // Note: sources_json is stored but not returned in ConversationResponse
        // Sources will be empty when loading from history
        const sources: import("@/types").Source[] = [];
        
        setLastResult({
          topic: conversation.topic,
          briefing: conversation.briefing,
          sources,
          total_time_seconds: conversation.total_time_seconds || 0,
          model_used: conversation.model_used || "unknown",
        });
      }
    } catch (error) {
      console.error("Failed to load conversation:", error);
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setCurrentProgress(null);
    setLastResult(null);
    currentConversationIdRef.current = null;
  }, []);

  return {
    messages,
    isLoading,
    currentProgress,
    lastResult,
    submitTopic,
    clearMessages,
    loadConversation,
  };
}
