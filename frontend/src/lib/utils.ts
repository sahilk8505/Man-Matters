import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { FatigueStage, Recommendation, InsightPriority } from "@/types";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ---------------------------------------------------------------------------
// Formatting
// ---------------------------------------------------------------------------

export function formatCurrency(value: number | undefined | null, decimals = 0): string {
  if (value === undefined || value === null) return "—";
  return `₹${value.toLocaleString("en-IN", { maximumFractionDigits: decimals })}`;
}

export function formatRoas(value: number | undefined | null): string {
  if (value === undefined || value === null) return "—";
  return `${value.toFixed(2)}x`;
}

export function formatCtr(value: number | undefined | null): string {
  if (value === undefined || value === null) return "—";
  // value may be decimal (0.023) or already percentage (2.3)
  const pct = value > 1 ? value : value * 100;
  return `${pct.toFixed(2)}%`;
}

export function formatPct(value: number | undefined | null, decimals = 1): string {
  if (value === undefined || value === null) return "—";
  return `${value.toFixed(decimals)}%`;
}

export function formatNumber(value: number | undefined | null): string {
  if (value === undefined || value === null) return "—";
  return value.toLocaleString("en-IN");
}

export function formatDays(days: number | undefined | null): string {
  if (days === undefined || days === null) return "—";
  return `${days}d`;
}

export function formatDate(dateStr: string | undefined | null): string {
  if (!dateStr) return "—";
  return new Date(dateStr).toLocaleDateString("en-IN", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

export function formatRelativeTime(dateStr: string | undefined | null): string {
  if (!dateStr) return "—";
  const diff = Date.now() - new Date(dateStr).getTime();
  const hours = Math.floor(diff / 3600000);
  if (hours < 1) return "just now";
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}d ago`;
  return formatDate(dateStr);
}

// ---------------------------------------------------------------------------
// Fatigue
// ---------------------------------------------------------------------------

export function getFatigueColor(stage: FatigueStage | undefined | null): string {
  switch (stage) {
    case "healthy": return "text-green-500";
    case "watch": return "text-yellow-500";
    case "fatiguing": return "text-orange-500";
    case "fatigued": return "text-red-500";
    default: return "text-muted-foreground";
  }
}

export function getFatigueBg(stage: FatigueStage | undefined | null): string {
  switch (stage) {
    case "healthy": return "bg-green-50 text-green-700 border-green-200";
    case "watch": return "bg-yellow-50 text-yellow-700 border-yellow-200";
    case "fatiguing": return "bg-orange-50 text-orange-700 border-orange-200";
    case "fatigued": return "bg-red-50 text-red-700 border-red-200";
    default: return "bg-muted text-muted-foreground border-border";
  }
}

export function getFatigueLabel(stage: FatigueStage | undefined | null): string {
  switch (stage) {
    case "healthy": return "Healthy";
    case "watch": return "Watch";
    case "fatiguing": return "Fatiguing";
    case "fatigued": return "Fatigued";
    case "insufficient_data": return "Insufficient Data";
    default: return "Unknown";
  }
}

export function getFatigueScoreColor(score: number): string {
  if (score <= 30) return "#22c55e";
  if (score <= 60) return "#f59e0b";
  if (score <= 80) return "#f97316";
  return "#ef4444";
}

// ---------------------------------------------------------------------------
// Recommendations
// ---------------------------------------------------------------------------

export function getRecommendationColor(rec: Recommendation | undefined | null): string {
  switch (rec) {
    case "launch_immediately": return "bg-green-100 text-green-800 border-green-200";
    case "launch_with_caution": return "bg-blue-100 text-blue-800 border-blue-200";
    case "test": return "bg-yellow-100 text-yellow-800 border-yellow-200";
    case "iterate": return "bg-orange-100 text-orange-800 border-orange-200";
    case "avoid": return "bg-red-100 text-red-800 border-red-200";
    default: return "bg-muted text-muted-foreground border-border";
  }
}

export function getRecommendationLabel(rec: Recommendation | undefined | null): string {
  switch (rec) {
    case "launch_immediately": return "Launch Immediately";
    case "launch_with_caution": return "Launch with Caution";
    case "test": return "Test First";
    case "iterate": return "Iterate";
    case "avoid": return "Avoid";
    default: return "Unknown";
  }
}

// ---------------------------------------------------------------------------
// Insight Priority
// ---------------------------------------------------------------------------

export function getPriorityColor(priority: InsightPriority): string {
  switch (priority) {
    case "critical": return "bg-red-100 text-red-800 border-red-300";
    case "high": return "bg-orange-100 text-orange-800 border-orange-300";
    case "medium": return "bg-yellow-100 text-yellow-800 border-yellow-300";
    case "low": return "bg-blue-100 text-blue-800 border-blue-300";
  }
}

// ---------------------------------------------------------------------------
// Narrative formatting
// ---------------------------------------------------------------------------

export function formatNarrative(type: string | undefined | null): string {
  if (!type) return "Unknown";
  return type.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

// ---------------------------------------------------------------------------
// Score colors (0-100)
// ---------------------------------------------------------------------------

export function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600";
  if (score >= 60) return "text-blue-600";
  if (score >= 40) return "text-yellow-600";
  return "text-red-600";
}

export function getScoreBg(score: number): string {
  if (score >= 80) return "bg-green-500";
  if (score >= 60) return "bg-blue-500";
  if (score >= 40) return "bg-yellow-500";
  return "bg-red-500";
}

// ---------------------------------------------------------------------------
// Category colors
// ---------------------------------------------------------------------------

export function getCategoryColor(category: string): string {
  switch (category) {
    case "hair": return "bg-purple-100 text-purple-800";
    case "wellness": return "bg-green-100 text-green-800";
    case "fitness": return "bg-blue-100 text-blue-800";
    default: return "bg-muted text-muted-foreground";
  }
}
