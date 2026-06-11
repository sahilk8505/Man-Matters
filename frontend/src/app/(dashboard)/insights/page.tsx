"use client";

import { useEffect, useState } from "react";
import { Lightbulb, CheckCircle, X, ArrowRight, RefreshCw, Bell } from "lucide-react";
import { insights as insightsApi, products as productsApi } from "@/lib/api";
import type { Insight, Product } from "@/types";
import { getPriorityColor, formatRelativeTime, getCategoryColor } from "@/lib/utils";
import { toast } from "sonner";

const INSIGHT_TYPE_LABELS: Record<string, string> = {
  fatigue_alert: "Fatigue Alert",
  opportunity: "Opportunity",
  narrative_learning: "Narrative Learning",
  performance_anomaly: "Performance Anomaly",
  saturation_warning: "Saturation Warning",
  budget_recommendation: "Budget",
  creative_gap: "Creative Gap",
  winner_pattern: "Winner Pattern",
  loser_pattern: "Loser Pattern",
  competitive_threat: "Competitive Threat",
};

const ACTION_LABELS: Record<string, string> = {
  create_creative: "Create Creative",
  pause_creative: "Pause Creative",
  reallocate_budget: "Reallocate Budget",
  test_narrative: "Test Narrative",
  scale_winner: "Scale Winner",
  refresh_creative: "Refresh Creative",
  monitor: "Monitor",
};

export default function InsightsDashboard() {
  const [allInsights, setAllInsights] = useState<Insight[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [counts, setCounts] = useState({ total_unread: 0, critical: 0, high: 0, medium: 0, low: 0 });
  const [filter, setFilter] = useState({ product_id: "", insight_type: "", priority: "", is_read: undefined as boolean | undefined });
  const [generating, setGenerating] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadInsights = () => {
    const params: Record<string, string | boolean> = {};
    if (filter.product_id) params.product_id = filter.product_id;
    if (filter.insight_type) params.insight_type = filter.insight_type;
    if (filter.priority) params.priority = filter.priority;
    if (filter.is_read !== undefined) params.is_read = filter.is_read;

    return insightsApi.list(params).then(setAllInsights);
  };

  useEffect(() => {
    Promise.all([
      productsApi.list(),
      insightsApi.counts(),
    ]).then(([prods, c]) => {
      setProducts(prods as Product[]);
      setCounts(c as typeof counts);
    });
  }, []);

  useEffect(() => {
    setLoading(true);
    loadInsights().finally(() => setLoading(false));
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter]);

  const handleMarkRead = async (id: string) => {
    await insightsApi.markRead(id);
    setAllInsights((prev) => prev.map((ins) => ins.id === id ? { ...ins, is_read: true } : ins));
    setCounts((c) => ({ ...c, total_unread: Math.max(0, c.total_unread - 1) }));
  };

  const handleDismiss = async (id: string) => {
    await insightsApi.dismiss(id);
    setAllInsights((prev) => prev.filter((ins) => ins.id !== id));
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      await insightsApi.generate();
      toast.success("Insight generation started. New insights will appear in 1-2 minutes.");
      setTimeout(() => loadInsights(), 5000);
    } catch {
      toast.error("Failed to trigger insight generation");
    } finally {
      setGenerating(false);
    }
  };

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Lightbulb className="h-6 w-6 text-yellow-500" />
            AI Insights
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Automatically generated strategic recommendations from Gemini 2.5 Pro
          </p>
        </div>
        <button
          onClick={handleGenerate}
          disabled={generating}
          className="flex items-center gap-2 text-sm px-4 py-2 border border-border rounded-lg hover:bg-accent transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`h-4 w-4 ${generating ? "animate-spin" : ""}`} />
          {generating ? "Generating..." : "Generate Now"}
        </button>
      </div>

      {/* Count Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        {[
          { key: "total_unread", label: "Unread", value: counts.total_unread, color: "bg-blue-50 text-blue-700 border-blue-200" },
          { key: "critical", label: "Critical", value: counts.critical, color: "bg-red-50 text-red-700 border-red-200" },
          { key: "high", label: "High", value: counts.high, color: "bg-orange-50 text-orange-700 border-orange-200" },
          { key: "medium", label: "Medium", value: counts.medium, color: "bg-yellow-50 text-yellow-700 border-yellow-200" },
          { key: "low", label: "Low", value: counts.low, color: "bg-blue-50 text-blue-600 border-blue-100" },
        ].map(({ key, label, value, color }) => (
          <button
            key={key}
            onClick={() => setFilter((f) => ({ ...f, priority: key === "total_unread" ? "" : key }))}
            className={`p-3 border rounded-xl text-center hover:opacity-80 transition-opacity ${color}`}
          >
            <p className="text-2xl font-bold">{value}</p>
            <p className="text-xs font-medium">{label}</p>
          </button>
        ))}
      </div>

      {/* Filters */}
      <div className="flex gap-3 flex-wrap">
        <select
          value={filter.product_id}
          onChange={(e) => setFilter((f) => ({ ...f, product_id: e.target.value }))}
          className="text-sm border border-border rounded-lg px-3 py-2 bg-background"
        >
          <option value="">All Products</option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
        <select
          value={filter.insight_type}
          onChange={(e) => setFilter((f) => ({ ...f, insight_type: e.target.value }))}
          className="text-sm border border-border rounded-lg px-3 py-2 bg-background"
        >
          <option value="">All Types</option>
          {Object.entries(INSIGHT_TYPE_LABELS).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        <select
          value={filter.is_read === undefined ? "" : String(filter.is_read)}
          onChange={(e) => setFilter((f) => ({
            ...f,
            is_read: e.target.value === "" ? undefined : e.target.value === "true",
          }))}
          className="text-sm border border-border rounded-lg px-3 py-2 bg-background"
        >
          <option value="">All (read + unread)</option>
          <option value="false">Unread only</option>
          <option value="true">Read only</option>
        </select>
      </div>

      {/* Insights List */}
      {loading ? (
        <div className="space-y-4">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-28 bg-muted animate-pulse rounded-xl" />)}
        </div>
      ) : allInsights.length === 0 ? (
        <div className="text-center py-16 text-muted-foreground">
          <Lightbulb className="h-10 w-10 mx-auto mb-3 opacity-20" />
          <p className="font-medium">No insights yet</p>
          <p className="text-sm mt-1">Click "Generate Now" to create AI insights from your performance data.</p>
        </div>
      ) : (
        <div className="space-y-4">
          {allInsights.map((ins) => (
            <InsightCard
              key={ins.id}
              insight={ins}
              onRead={handleMarkRead}
              onDismiss={handleDismiss}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function InsightCard({
  insight,
  onRead,
  onDismiss,
}: {
  insight: Insight;
  onRead: (id: string) => void;
  onDismiss: (id: string) => void;
}) {
  return (
    <div className={`bg-card border rounded-xl p-5 transition-all ${
      !insight.is_read ? "border-primary/30 shadow-sm" : "border-border"
    }`}>
      <div className="flex items-start gap-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap mb-2">
            <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getPriorityColor(insight.priority)}`}>
              {insight.priority}
            </span>
            <span className="inline-flex items-center px-2 py-0.5 bg-muted text-muted-foreground text-xs rounded-full border border-border">
              {INSIGHT_TYPE_LABELS[insight.insight_type] || insight.insight_type}
            </span>
            {!insight.is_read && (
              <span className="inline-flex items-center gap-1 text-xs text-blue-600">
                <Bell className="h-3 w-3" /> New
              </span>
            )}
          </div>

          <h3 className="font-semibold text-sm leading-snug mb-2">{insight.title}</h3>
          <p className="text-sm text-muted-foreground leading-relaxed">{insight.body}</p>

          {insight.recommended_action && (
            <div className="mt-3 flex items-start gap-2 p-3 bg-accent/50 rounded-lg">
              <ArrowRight className="h-4 w-4 text-primary mt-0.5 shrink-0" />
              <div>
                <p className="text-xs font-semibold text-primary uppercase tracking-wide mb-0.5">
                  {ACTION_LABELS[insight.action_type || ""] || "Recommended Action"}
                </p>
                <p className="text-sm">{insight.recommended_action}</p>
              </div>
            </div>
          )}

          <p className="text-xs text-muted-foreground mt-3">{formatRelativeTime(insight.created_at)}</p>
        </div>

        <div className="flex flex-col gap-2 shrink-0">
          {!insight.is_read && (
            <button
              onClick={() => onRead(insight.id)}
              title="Mark as read"
              className="p-1.5 text-muted-foreground hover:text-green-600 hover:bg-green-50 rounded-lg transition-colors"
            >
              <CheckCircle className="h-4 w-4" />
            </button>
          )}
          <button
            onClick={() => onDismiss(insight.id)}
            title="Dismiss"
            className="p-1.5 text-muted-foreground hover:text-red-600 hover:bg-red-50 rounded-lg transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
