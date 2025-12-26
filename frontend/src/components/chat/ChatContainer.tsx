"use client";

import React, { useEffect, useRef, useState } from "react";
import Image from "next/image";
import { History, Plus } from "lucide-react";
import {
  SignedIn,
  SignedOut,
  SignInButton,
  SignUpButton,
  UserButton,
} from "@clerk/nextjs";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Button } from "@/components/ui/button";
import { ChatMessage } from "./ChatMessage";
import { ChatInput } from "./ChatInput";
import { WelcomeScreen } from "./WelcomeScreen";
import { ConversationHistory } from "./ConversationHistory";
import { useResearch } from "@/hooks/useResearch";

export function ChatContainer() {
  const {
    messages,
    isLoading,
    lastResult,
    submitTopic,
    clearMessages,
    loadConversation,
  } = useResearch();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [showHistory, setShowHistory] = useState(false);
  const historyRefreshKeyRef = useRef(0);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  // Refresh history when a conversation is saved (triggered by result completion)
  useEffect(() => {
    if (lastResult && showHistory) {
      historyRefreshKeyRef.current += 1;
    }
  }, [lastResult, showHistory]);

  const handleSelectConversation = async (conversation: { id: number }) => {
    await loadConversation(conversation.id);
    setShowHistory(false);
    // Trigger history refresh
    historyRefreshKeyRef.current += 1;
  };

  const handleNewConversation = () => {
    clearMessages();
    setShowHistory(false);
  };

  return (
    <>
      {/* Not signed in - show sign in prompt */}
      <SignedOut>
        <div className="flex h-screen bg-background-primary items-center justify-center">
          <div className="text-center p-8 max-w-md">
            <div className="w-full h-full flex items-center justify-center mx-auto mb-6">
              <Image
                src="/postcss.config.jpeg"
                alt="Research Agent"
                width={256}
                height={256}
                className="object-cover"
              />
            </div>
            <h1 className="text-2xl font-bold text-text-normal mb-2">
              Research Agent
            </h1>
            <p className="text-text-muted mb-8">
              AI-powered research assistant. Sign in to start researching and
              save your conversation history.
            </p>
            <div className="flex gap-4 justify-center">
              <SignInButton mode="modal">
                <Button variant="default" size="lg">
                  Sign In
                </Button>
              </SignInButton>
              <SignUpButton mode="modal">
                <Button variant="outline" size="lg">
                  Sign Up
                </Button>
              </SignUpButton>
            </div>
          </div>
        </div>
      </SignedOut>

      {/* Signed in - show main app */}
      <SignedIn>
        <div className="flex h-screen bg-background-primary">
          {/* Sidebar - Conversation History */}
          {showHistory && (
            <div className="w-72 border-r border-border-subtle bg-background-secondary flex flex-col">
              <div className="p-3 border-b border-border-subtle flex items-center justify-between">
                <h2 className="font-semibold text-text-normal text-sm">
                  History
                </h2>
                <button
                  onClick={() => setShowHistory(false)}
                  className="text-text-muted hover:text-text-normal transition-colors"
                >
                  ✕
                </button>
              </div>
              <ConversationHistory
                key={historyRefreshKeyRef.current}
                onSelectConversation={handleSelectConversation}
              />
            </div>
          )}

          {/* Main Chat Area */}
          <div className="flex-1 flex flex-col">
            {/* Header */}
            <header className="flex-shrink-0 h-14 border-b border-border-subtle bg-background-tertiary flex items-center px-4">
              <Button
                variant="ghost"
                size="icon"
                onClick={() => setShowHistory(!showHistory)}
                className="mr-2"
              >
                <History className="w-4 h-4" />
              </Button>

              <div className="flex items-center gap-3">
                <div className="w-8 h-8  flex items-center justify-center overflow-hidden">
                  <Image
                    src="/postcss.config.jpeg"
                    alt="Research Agent"
                    width={32}
                    height={32}
                    className="object-cover"
                  />
                </div>
                <div>
                  <h1 className="font-semibold text-text-normal">
                    Research Agent
                  </h1>
                  <p className="text-xs text-text-muted">
                    AI-powered research assistant
                  </p>
                </div>
              </div>

              <div className="ml-auto flex items-center gap-3">
                {messages.length > 0 && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleNewConversation}
                    className="text-xs text-text-muted hover:text-text-normal"
                  >
                    <Plus className="w-3.5 h-3.5 mr-1" />
                    New
                  </Button>
                )}
                <UserButton
                  afterSignOutUrl="/"
                  appearance={{
                    elements: {
                      avatarBox: "w-8 h-8",
                    },
                  }}
                />
              </div>
            </header>

            {/* Messages area */}
            <ScrollArea className="flex-1" ref={scrollRef}>
              <div className="max-w-4xl mx-auto">
                {messages.length === 0 ? (
                  <WelcomeScreen
                    onExampleClick={(topic) =>
                      submitTopic(topic, "standard", false)
                    }
                  />
                ) : (
                  <div className="py-4">
                    {messages.map((message) => (
                      <ChatMessage key={message.id} message={message} />
                    ))}
                  </div>
                )}
              </div>
            </ScrollArea>

            {/* Input area */}
            <ChatInput onSubmit={submitTopic} isLoading={isLoading} />
          </div>
        </div>
      </SignedIn>
    </>
  );
}
