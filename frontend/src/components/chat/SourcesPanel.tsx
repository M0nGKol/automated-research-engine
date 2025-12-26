"use client";

import React, { useState } from "react";
import { ChevronDown, ChevronUp, ExternalLink, Shield, FileDown, Loader2 } from "lucide-react";
import { cn, formatDuration } from "@/lib/utils";
import { exportPDF, downloadPDF } from "@/lib/api";
import { Button } from "@/components/ui/button";
import type { Source, ResearchResult } from "@/types";

interface SourcesPanelProps {
  sources: Source[];
  totalTime: number;
  result?: ResearchResult;
}

export function SourcesPanel({ sources, totalTime, result }: SourcesPanelProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const handleExportPDF = async () => {
    if (!result) return;
    
    setIsExporting(true);
    try {
      const blob = await exportPDF({
        topic: result.topic,
        briefing: result.briefing,
        sources: result.sources,
        total_time_seconds: result.total_time_seconds,
        model_used: result.model_used,
      });
      
      const safeTopic = result.topic.slice(0, 50).replace(/[^a-zA-Z0-9]/g, "_");
      downloadPDF(blob, `research_${safeTopic}.pdf`);
    } catch (error) {
      console.error("Failed to export PDF:", error);
      alert("Failed to generate PDF. Please try again.");
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="mt-4 border border-border-subtle rounded-lg overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-3 bg-background-primary">
        <button
          onClick={() => setIsExpanded(!isExpanded)}
          className="flex items-center gap-2 hover:opacity-80 transition-opacity"
        >
          <Shield className="w-4 h-4 text-accent-success" />
          <span className="font-medium text-text-normal">
            {sources.length} Sources
          </span>
          <span className="text-xs text-text-muted">
            • Completed in {formatDuration(totalTime)}
          </span>
          {isExpanded ? (
            <ChevronUp className="w-4 h-4 text-text-muted" />
          ) : (
            <ChevronDown className="w-4 h-4 text-text-muted" />
          )}
        </button>

        {result && (
          <Button
            onClick={handleExportPDF}
            disabled={isExporting}
            variant="outline"
            size="sm"
            className="h-7 text-xs"
          >
            {isExporting ? (
              <>
                <Loader2 className="w-3 h-3 mr-1.5 animate-spin" />
                Exporting...
              </>
            ) : (
              <>
                <FileDown className="w-3 h-3 mr-1.5" />
                Export PDF
              </>
            )}
          </Button>
        )}
      </div>

      {/* Expanded content */}
      {isExpanded && (
        <div className="border-t border-border-subtle divide-y divide-border-subtle">
          {sources.map((source, index) => (
            <SourceItem key={index} source={source} index={index + 1} />
          ))}
        </div>
      )}
    </div>
  );
}

interface SourceItemProps {
  source: Source;
  index: number;
}

function SourceItem({ source, index }: SourceItemProps) {
  const [showSummary, setShowSummary] = useState(false);

  const credibilityColor =
    source.credibility_score >= 0.7
      ? "text-accent-success"
      : source.credibility_score >= 0.5
      ? "text-accent-warning"
      : "text-accent-danger";

  // Check if it's an academic source
  const isAcademic = source.url.includes("arxiv.org") || 
                     source.url.includes("semanticscholar.org") ||
                     source.url.includes("doi.org");

  return (
    <div className="p-3 bg-background-secondary/50">
      <div className="flex items-start gap-3">
        <span className="flex-shrink-0 w-6 h-6 rounded-full bg-background-modifier flex items-center justify-center text-xs font-medium text-text-muted">
          {index}
        </span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <a
              href={source.url}
              target="_blank"
              rel="noopener noreferrer"
              className="font-medium text-text-link hover:underline truncate flex items-center gap-1"
            >
              {source.title}
              <ExternalLink className="w-3 h-3 flex-shrink-0" />
            </a>
            {isAcademic && (
              <span className="flex-shrink-0 px-1.5 py-0.5 text-[10px] font-medium bg-accent-primary/20 text-accent-primary rounded">
                Academic
              </span>
            )}
          </div>

          <div className="flex items-center gap-3 text-xs mb-2">
            <span className={cn("font-medium", credibilityColor)}>
              Credibility: {Math.round(source.credibility_score * 100)}%
            </span>
            <span className="text-text-muted truncate">{source.url}</span>
          </div>

          <p className="text-sm text-text-muted line-clamp-2">
            {source.snippet}
          </p>

          {source.summary && (
            <>
              <button
                onClick={() => setShowSummary(!showSummary)}
                className="mt-2 text-xs text-accent-primary hover:underline"
              >
                {showSummary ? "Hide summary" : "Show summary"}
              </button>

              {showSummary && (
                <div className="mt-2 p-2 bg-background-primary rounded text-sm text-text-normal">
                  {source.summary}
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
