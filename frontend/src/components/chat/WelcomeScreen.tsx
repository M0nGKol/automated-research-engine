"use client";

import React from "react";
import { Search, FileText, Zap, Shield } from "lucide-react";

interface WelcomeScreenProps {
  onExampleClick: (topic: string) => void;
}

const EXAMPLE_TOPICS = [
  "Latest advancements in quantum computing 2024",
  "Impact of AI on healthcare diagnostics",
  "Climate change mitigation strategies",
  "Web3 and decentralized identity solutions",
];

const FEATURES = [
  {
    icon: Search,
    title: "Web Search",
    description: "Searches multiple sources using Google Custom Search Engine",
  },
  {
    icon: Shield,
    title: "Credibility Filter",
    description: "Filters sources by domain reputation",
  },
  {
    icon: FileText,
    title: "Content Extraction",
    description: "Extracts clean text from web pages",
  },
  {
    icon: Zap,
    title: "AI Synthesis",
    description: "Summarizes and synthesizes findings",
  },
];

export function WelcomeScreen({ onExampleClick }: WelcomeScreenProps) {
  return (
    <div className="flex flex-col items-center justify-center min-h-[calc(100vh-200px)] px-4 py-12">
      {/* Logo */}
      <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-accent-primary to-accent-success flex items-center justify-center mb-6 shadow-lg">
        <span className="text-4xl">🔬</span>
      </div>

      <h2 className="text-2xl font-bold text-text-normal mb-2">
        Research Agent
      </h2>
      <p className="text-text-muted text-center max-w-md mb-8">
        Enter any research topic and I&apos;ll search the web, analyze credible
        sources, and synthesize a comprehensive briefing.
      </p>

      {/* Features grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-10 w-full max-w-2xl">
        {FEATURES.map((feature) => (
          <div
            key={feature.title}
            className="p-4 rounded-lg bg-background-secondary border border-border-subtle text-center"
          >
            <feature.icon className="w-6 h-6 mx-auto mb-2 text-accent-primary" />
            <h3 className="font-medium text-sm text-text-normal mb-1">
              {feature.title}
            </h3>
            <p className="text-xs text-text-muted">{feature.description}</p>
          </div>
        ))}
      </div>

      {/* Example topics */}
      <div className="w-full max-w-2xl">
        <p className="text-sm text-text-muted mb-3 text-center">
          Try an example topic:
        </p>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {EXAMPLE_TOPICS.map((topic) => (
            <button
              key={topic}
              onClick={() => onExampleClick(topic)}
              className="p-3 rounded-lg bg-background-secondary border border-border-subtle text-left text-sm text-text-normal hover:border-accent-primary hover:bg-background-tertiary transition-colors"
            >
              {topic}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
