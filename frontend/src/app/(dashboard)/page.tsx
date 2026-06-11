"use client";

import { useEffect, useState } from "react";
import {
  TrendingUp, TrendingDown, AlertTriangle, CheckCircle,
  Zap, RefreshCw, Bell, ArrowRight, ShoppingCart, DollarSign
} from "lucide-react";
import {
  BarChart, Bar, LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import Link from "next/link";
import { analytics, insights as insightsApi } from "@/lib/api";
import type { ExecutiveSummary, Insight } from "@/types";
import {
  formatCurrency, formatRoas, formatCtr, formatNumber,
  getFatigueBg, getFatigueLabel, getPriorityColor, formatRelativeTime
} from "@/lib/utils";
import { toast } from "sonner";

const FATIGUE_COLORS = {
  healthy: "#22c55e",
  watch: "#f59e0b",
  fatiguing: "#f97316",
  fatigued: "#ef4444",
};

export default function ExecutiveDashboard() {
  const [summary, setSummary] = useState<ExecutiveSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  useEffect(() => {
    analytics.executiveSummary()
      .then(setSummary)
      .catch(() => toast.error("Failed to load dashboard data"))
      .finally(() => setLoading(false));
  }, []);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const { sync } = await import("@/lib/api");
      await sync.triggerMeta();
      toast.success("Meta sync started. Data will update shortly.");
    } catch {
      toast.error("Sync failed. Check your Meta credentials.");
    } finally {
      setSyncing(false);
    }
  };

  const handleMarkInsightRead = async (id: string) => {
    await insightsApi.markRead(id);
    if (summary) {
      setSummary({
        ...summary,
        insights: {
          ...summary.insights,
          recent_critical: summary.insights.recent_critical.map((ins) =>
            ins.id === id ? { ...ins, is_read: true } : ins
          ),
        },
      });
    }
  };

  if (loading) {
    return (
      <div className="p-8 space-y-6">
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 bg-muted animate-pulse rounded-xl" />
        ))}
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="p-8 text-center text-muted-foreground">
        No data available. Configure your Meta account and sync.
      </div>
    );
  }

  const { portfolio, creative_health, insights: insightData, products } = summary;

  const fatigueChartData = [
    { name: "Healthy", value: creative_health.healthy, color: FATIGUE_COLORS.healthy },
    { name: "Watch", value: creative_health.watch, color: FATIGUE_COLORS.watch },
    { name: "Fatiguing", value: creative_health.fatiguing, color: FATIGUE_COLORS.fatiguing },
    { name: "Fatigued", value: creative_health.fatigued, color: FATIGUE_COLORS.fatigued },
  ].filter((d) => d.value > 0);

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Creative Intelligence</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Man Matters · Meta Ads · Last 30 days
          </p>
        </div>
        <div className="flex items-center gap-3">
          {insightData.unread_count > 0 && (
            <Link
              href="/insights"
              className="flex items-center gap-2 text-sm px-3 py-1.5 bg-red-50 text-red-700 border border-red-200 rounded-lg hover:bg-red-100 transition-colors"
            >
              <Bell className="h-4 w-4" />
              {insightData.unread_count} new insights
            </Link>
          )}
          <button
            onClick={handleSync}
            disabled={syncing}
            className="flex items-center gap-2 text-sm px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${syncing ? "animate-spin" : ""}`} />
            {syncing ? "Syncing..." : "Sync Meta"}
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard
          label="Total Spend (30d)"
          value={formatCurrency(portfolio.total_spend_30d)}
          icon={<DollarSign className="h-5 w-5 text-blue-500" />}
          bg="bg-blue-50"
        />
        <StatCard
          label="Avg ROAS (30d)"
          value={formatRoas(portfolio.avg_roas_30d)}
          icon={<TrendingUp className="h-5 w-5 text-green-500" />}
          bg="bg-green-50"
          positive={portfolio.avg_roas_30d >= 2.5}
        />
        <StatCard
          label="Total Purchases (30d)"
          value={formatNumber(portfolio.total_purchases_30d)}
          icon={<ShoppingCart className="h-5 w-5 text-purple-500" />}
          bg="bg-purple-50"
        />
        <StatCard
          label="Avg CPA (30d)"
          value={formatCurrency(portfolio.avg_cpa_30d)}
          icon={<Zap className="h-5 w-5 text-orange-500" />}
          bg="bg-orange-50"
        />
      </div>

      {/* Creative Health + Product Spend */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Creative Health */}
        <div className="bg-card border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Creative Health</h2>
            <span className="text-sm text-muted-foreground">{creative_health.total_active} active</span>
          </div>

          <div className="flex items-center gap-4">
            <div className="flex-1">
              <PieChart width={140} height={140}>
                <Pie
                  data={fatigueChartData}
                  cx={70} cy={70}
                  innerRadius={45} outerRadius={65}
                  dataKey="value"
                >
                  {fatigueChartData.map((entry) => (
                    <Cell key={entry.name} fill={entry.color} />
                  ))}
                </Pie>
              </PieChart>
            </div>
            <div className="space-y-2 flex-1">
              {fatigueChartData.map((item) => (
                <div key={item.name} className="flex items-center justify-between text-sm">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full" style={{ backgroundColor: item.color }} />
                    <span className="text-muted-foreground">{item.name}</span>
                  </div>
                  <span className="font-medium">{item.value}</span>
                </div>
              ))}
            </div>
          </div>

          {(creative_health.fatiguing + creative_health.fatigued) > 0 && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
              <AlertTriangle className="h-4 w-4 inline mr-1" />
              {creative_health.fatigued} creatives need immediate replacement
            </div>
          )}

          <Link
            href="/fatigue"
            className="mt-3 flex items-center gap-1 text-sm text-primary hover:underline"
          >
            View fatigue monitor <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {/* Product Spend */}
        <div className="lg:col-span-2 bg-card border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold">Product Performance (7d)</h2>
          </div>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={products} margin={{ left: 0, right: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis
                dataKey="product_name"
                tick={{ fontSize: 11 }}
                tickFormatter={(v: string) => v.split(" ")[0]}
              />
              <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `₹${(v/1000).toFixed(0)}K`} />
              <YAxis yAxisId="right" orientation="right" tick={{ fontSize: 11 }} domain={[0, 5]} />
              <Tooltip
                formatter={(value: number, name: string) => [
                  name === "spend_7d" ? formatCurrency(value) : formatRoas(value),
                  name === "spend_7d" ? "Spend" : "ROAS",
                ]}
              />
              <Bar yAxisId="left" dataKey="spend_7d" fill="#3b82f6" name="spend_7d" radius={[4, 4, 0, 0]} />
              <Line yAxisId="right" type="monotone" dataKey="roas_7d" stroke="#22c55e" strokeWidth={2} name="roas_7d" />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* AI Insights */}
      <div className="bg-card border border-border rounded-xl p-5">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <h2 className="font-semibold">AI Insights</h2>
            {insightData.unread_count > 0 && (
              <span className="px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full font-medium">
                {insightData.unread_count} new
              </span>
            )}
          </div>
          <Link href="/insights" className="text-sm text-primary hover:underline flex items-center gap-1">
            View all <ArrowRight className="h-3 w-3" />
          </Link>
        </div>

        {insightData.recent_critical.length === 0 ? (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-4">
            <CheckCircle className="h-4 w-4 text-green-500" />
            No critical insights. Your creative portfolio looks healthy.
          </div>
        ) : (
          <div className="space-y-3">
            {insightData.recent_critical.map((ins) => (
              <InsightRow key={ins.id} insight={ins} onRead={handleMarkInsightRead} />
            ))}
          </div>
        )}
      </div>

      {/* Product Overview Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
        {products.map((product) => (
          <Link
            key={product.product_id}
            href={`/products/${product.product_id}`}
            className="bg-card border border-border rounded-xl p-4 hover:border-primary/50 hover:shadow-sm transition-all group"
          >
            <div className="flex items-center justify-between mb-3">
              <p className="font-medium text-sm">{product.product_name}</p>
              <ArrowRight className="h-4 w-4 text-muted-foreground group-hover:text-primary transition-colors" />
            </div>
            <div className="grid grid-cols-2 gap-2 text-sm">
              <div>
                <p className="text-muted-foreground text-xs">Spend 7d</p>
                <p className="font-semibold">{formatCurrency(product.spend_7d)}</p>
              </div>
              <div>
                <p className="text-muted-foreground text-xs">ROAS</p>
                <p className={`font-semibold ${product.roas_7d >= 2.5 ? "text-green-600" : "text-orange-600"}`}>
                  {formatRoas(product.roas_7d)}
                </p>
              </div>
            </div>
          </Link>
        ))}
      </div>
    </div>
  );
}

function StatCard({
  label, value, icon, bg, positive,
}: {
  label: string;
  value: string;
  icon: React.ReactNode;
  bg: string;
  positive?: boolean;
}) {
  return (
    <div className="bg-card border border-border rounded-xl p-4">
      <div className="flex items-center justify-between mb-2">
        <p className="text-sm text-muted-foreground">{label}</p>
        <div className={`p-1.5 rounded-lg ${bg}`}>{icon}</div>
      </div>
      <p className={`text-2xl font-bold ${positive === false ? "text-red-600" : ""}`}>{value}</p>
    </div>
  );
}

function InsightRow({ insight, onRead }: { insight: Insight; onRead: (id: string) => void }) {
  return (
    <div
      className={`flex items-start gap-3 p-3 rounded-lg border transition-colors ${
        !insight.is_read ? "bg-muted/50 border-border" : "border-transparent"
      }`}
    >
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border whitespace-nowrap ${getPriorityColor(insight.priority)}`}
      >
        {insight.priority}
      </span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium leading-tight">{insight.title}</p>
        <p className="text-xs text-muted-foreground mt-0.5">{formatRelativeTime(insight.created_at)}</p>
      </div>
      {!insight.is_read && (
        <button
          onClick={() => onRead(insight.id)}
          className="text-xs text-muted-foreground hover:text-foreground shrink-0"
        >
          Mark read
        </button>
      )}
    </div>
  );
}
