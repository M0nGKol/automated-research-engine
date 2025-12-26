"use client";

import React, { useState, useRef, useEffect } from "react";
import { Send, Loader2, GraduationCap } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ResearchDepth } from "@/types";

interface ChatInputProps {
  onSubmit: (topic: string, depth: ResearchDepth, includeAcademic: boolean) => void;
  isLoading: boolean;
}

export function ChatInput({ onSubmit, isLoading }: ChatInputProps) {
  const [input, setInput] = useState("");
  const [depth, setDepth] = useState<ResearchDepth>("standard");
  const [includeAcademic, setIncludeAcademic] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = `${Math.min(textarea.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSubmit = () => {
    if (input.trim() && !isLoading) {
      onSubmit(input.trim(), depth, includeAcademic);
      setInput("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-border-subtle bg-background-tertiary p-4">
      <div className="max-w-4xl mx-auto">
        {/* Options row */}
        <div className="flex items-center gap-4 mb-3">
          <div className="flex items-center gap-2">
            <span className="text-xs text-text-muted">Depth:</span>
            <Select
              value={depth}
              onValueChange={(v) => setDepth(v as ResearchDepth)}
              disabled={isLoading}
            >
              <SelectTrigger className="w-32 h-7 text-xs">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="quick">Quick (3 sources)</SelectItem>
                <SelectItem value="standard">Standard (5 sources)</SelectItem>
                <SelectItem value="deep">Deep (8 sources)</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <button
            type="button"
            onClick={() => setIncludeAcademic(!includeAcademic)}
            disabled={isLoading}
            className={`flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs transition-colors ${
              includeAcademic
                ? "bg-accent-primary text-white"
                : "bg-background-secondary text-text-muted hover:text-text-normal hover:bg-background-modifier"
            }`}
          >
            <GraduationCap className="w-3.5 h-3.5" />
            Academic
          </button>
        </div>

        {/* Input area */}
        <div className="relative flex items-end gap-2 p-3 rounded-lg bg-background-secondary border border-border-subtle focus-within:border-accent-primary transition-colors">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              includeAcademic
                ? "Enter a research topic (including arXiv & Semantic Scholar)..."
                : "Enter a research topic..."
            }
            disabled={isLoading}
            rows={1}
            className="flex-1 bg-transparent resize-none text-text-normal placeholder:text-text-muted focus:outline-none min-h-[24px] max-h-[200px]"
          />

          <Button
            onClick={handleSubmit}
            disabled={!input.trim() || isLoading}
            size="icon"
            className="flex-shrink-0"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </Button>
        </div>

        <p className="mt-2 text-xs text-text-muted text-center">
          Press Enter to send • Shift+Enter for new line
          {includeAcademic && " • 📚 Academic sources enabled"}
        </p>
      </div>
    </div>
  );
}
