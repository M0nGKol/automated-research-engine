import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function generateId(): string {
  return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
}

export function formatTime(date: Date): string {
  return date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

export function formatDuration(seconds: number): string {
  if (seconds < 60) {
    return `${seconds.toFixed(1)}s`;
  }
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;
  return `${minutes}m ${remainingSeconds.toFixed(0)}s`;
}

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    pending: "text-text-muted",
    searching: "text-accent-warning",
    extracting: "text-accent-warning",
    summarizing: "text-accent-primary",
    synthesizing: "text-accent-primary",
    completed: "text-accent-success",
    error: "text-accent-danger",
  };
  return colors[status] || "text-text-muted";
}

export function getStatusIcon(status: string): string {
  const icons: Record<string, string> = {
    pending: "⏳",
    searching: "🔍",
    extracting: "📄",
    summarizing: "📝",
    synthesizing: "🧠",
    completed: "✅",
    error: "❌",
  };
  return icons[status] || "⏳";
}

