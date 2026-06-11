"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import {
  TrendingUp, TrendingDown, AlertTriangle, ArrowUpRight,
  Activity, BarChart3, Target, Zap
} from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend
} from "recharts";
import { analytics, products as productsApi } from "@/lib/api";
import type { NarrativeBreakdown, NarrativeSaturation } from "@/types";
import {
  formatCurrency, formatRoas, formatCtr, formatNumber,
  formatNarrative, getFatigueBg, getCategoryColor
} from "@/lib/utils";
import Link from "next/link";
import { toast } from "sonner";

const SATURATION_COLORS: Record<string, string> = {
  oversaturated: "#ef4444",
  balanced: "#22c55e",
  undersupplied: "#3b82f6",
};

export default function ProductDashboard() {
  const { productId } = useParams<{ productId: string }>();
  const [product, setProduct] = useState<{ name: string; category: string } | null>(null);
  const [performance, setPerformance] = useState<{
    narrative_breakdown: NarrativeBreakdown[];
    daily_trend: Record<string, unknown>[];
    fatigue_distribution: Record<string, number>;
  } | null>(null);
  const [gaps, setGaps] = useState<NarrativeSaturation[]>([]);
  const [topCreatives, setTopCreatives] = useState<Record<string, unknown>[]>([]);
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!productId) return;
    setLoading(true);
    Promise.all([
      analytics.productPerformance(productId, days),
      analytics.creativeGaps(productId),
      analytics.topCreatives(productId, days),
    ])
      .then(([perf, gapsData, topC]) => {
        const p = perf as typeof performance & { product: { name: string; category: string } };
        setProduct(p.product);
        setPerformance(perf as typeof performance);
        setGaps(gapsData as NarrativeSaturation[]);
        setTopCreatives(topC as typeof topCreatives);
      })
      .catch(() => toast.error("Failed to load product data"))
      .finally(() => setLoading(false));
  }, [productId, days]);

  if (loading) {
    return (
      <div className="p-6 space-y-6">
        <div className="h-10 w-64 bg-muted animate-pulse rounded" />
        <div className="grid grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => <div key={i} className="h-24 bg-muted animate-pulse rounded-xl" />)}
        </div>
        <div className="h-64 bg-muted animate-pulse rounded-xl" />
      </div>
    );
  }

  if (!performance || !product) {
    return <div className="p-6 text-muted-foreground">Product not found.</div>;
  }

  const { narrative_breakdown, daily_trend, fatigue_distribution } = performance;

  const fatiguePieData = Object.entries(fatigue_distribution)
    .filter(([, v]) => v > 0)
    .map(([name, value]) => ({ name, value }));

  const FATIGUE_COLORS_PIE: Record<string, string> = {
    healthy: "#22c55e", watch: "#f59e0b", fatiguing: "#f97316", fatigued: "#ef4444",
  };

  const oversaturated = gaps.filter((g) => g.saturation_level === "oversaturated");
  const undersupplied = gaps.filter((g) => g.saturation_level === "undersupplied");

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <div className="flex items-center gap-3">
            <h1 className="text-2xl font-bold">{product.name}</h1>
            <span className={`text-xs px-2 py-1 rounded-full font-medium ${getCategoryColor(product.category)}`}>
              {product.category}
            </span>
          </div>
          <p className="text-sm text-muted-foreground mt-0.5">
            Product-specific creative intelligence
          </p>
        </div>
        <div className="flex items-center gap-2">
          {[7, 14, 30, 60].map((d) => (
            <button
              key={d}
              onClick={() => setDays(d)}
              className={`px-3 py-1.5 text-sm rounded-lg transition-colors ${
                days === d ? "bg-primary text-primary-foreground" : "border border-border hover:bg-accent"
              }`}
            >
              {d}d
            </button>
          ))}
        </div>
      </div>

      {/* Daily Trend */}
      <div className="bg-card border border-border rounded-xl p-5">
        <h2 className="font-semibold mb-4">Daily Performance Trend</h2>
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={(daily_trend as Array<Record<string, unknown>>).map((d) => ({
            date: String(d.date).slice(5),
            spend: Number(d.spend),
            roas: Number(d.roas),
            purchases: Number(d.purchases),
          }))}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} />
            <YAxis yAxisId="left" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `₹${(v/1000).toFixed(0)}K`} />
            <YAxis yAxisId="right" orientation="right" domain={[0, 5]} tick={{ fontSize: 11 }} />
            <Tooltip formatter={(v: number, name: string) => [
              name === "spend" ? formatCurrency(v) : name === "roas" ? formatRoas(v) : formatNumber(v),
              name,
            ]} />
            <Area yAxisId="left" type="monotone" dataKey="spend" stroke="#3b82f6" fill="#eff6ff" strokeWidth={2} name="spend" />
            <Area yAxisId="right" type="monotone" dataKey="roas" stroke="#22c55e" fill="transparent" strokeWidth={2} strokeDasharray="4 2" name="roas" />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Narrative Breakdown + Fatigue */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Narrative Performance */}
        <div className="lg:col-span-2 bg-card border border-border rounded-xl p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <BarChart3 className="h-4 w-4 text-primary" />
            Narrative Performance
          </h2>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart
              data={narrative_breakdown.slice(0, 8).map((n) => ({
                name: formatNarrative(n.narrative_type).slice(0, 12),
                roas: n.avg_roas,
                spend_pct: n.spend_pct,
                purchase_share_pct: n.purchase_pct,
                creative_count: n.creative_count,
              }))}
            >
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="name" tick={{ fontSize: 10 }} />
              <YAxis yAxisId="roas" tick={{ fontSize: 11 }} />
              <YAxis yAxisId="pct" orientation="right" domain={[0, 100]} tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v}%`} />
              <Tooltip />
              <Bar yAxisId="roas" dataKey="roas" name="Avg ROAS" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              <Bar yAxisId="pct" dataKey="purchase_share_pct" name="Purchase Share %" fill="#22c55e" radius={[4, 4, 0, 0]} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Creative Health */}
        <div className="bg-card border border-border rounded-xl p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Activity className="h-4 w-4" />
            Creative Health
          </h2>
          {fatiguePieData.length > 0 ? (
            <PieChart width={200} height={180}>
              <Pie data={fatiguePieData} cx={100} cy={80} innerRadius={50} outerRadius={75} dataKey="value">
                {fatiguePieData.map((entry) => (
                  <Cell key={entry.name} fill={FATIGUE_COLORS_PIE[entry.name] || "#94a3b8"} />
                ))}
              </Pie>
              <Legend wrapperStyle={{ fontSize: 11 }} />
            </PieChart>
          ) : (
            <div className="text-center text-sm text-muted-foreground py-8">No fatigue data yet</div>
          )}
        </div>
      </div>

      {/* Creative Gaps */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Undersupplied — Create More */}
        <div className="bg-card border border-border rounded-xl p-5">
          <h2 className="font-semibold mb-1 flex items-center gap-2">
            <Target className="h-4 w-4 text-blue-500" />
            Creative Gaps — Opportunity
          </h2>
          <p className="text-xs text-muted-foreground mb-4">
            High-performing narratives with insufficient creative supply
          </p>
          {undersupplied.length === 0 ? (
            <p className="text-sm text-muted-foreground">No major gaps identified. Portfolio is balanced.</p>
          ) : (
            <div className="space-y-3">
              {undersupplied.slice(0, 5).map((gap) => (
                <div key={gap.narrative_type} className="flex items-center justify-between p-3 bg-blue-50 border border-blue-100 rounded-lg">
                  <div>
                    <p className="font-medium text-sm text-blue-900">{gap.narrative_name || formatNarrative(gap.narrative_type)}</p>
                    <p className="text-xs text-blue-700 mt-0.5">
                      Drives {gap.purchase_share_pct.toFixed(1)}% of purchases but only {gap.volume_share_pct.toFixed(1)}% of creatives
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs text-muted-foreground">Avg ROAS</p>
                    <p className="font-semibold text-green-700">{formatRoas(gap.avg_roas)}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Oversaturated — Cut Back */}
        <div className="bg-card border border-border rounded-xl p-5">
          <h2 className="font-semibold mb-1 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-orange-500" />
            Oversaturated Narratives
          </h2>
          <p className="text-xs text-muted-foreground mb-4">
            Narratives dominating spend but underperforming on purchases
          </p>
          {oversaturated.length === 0 ? (
            <p className="text-sm text-muted-foreground">No oversaturation detected. Creative distribution looks healthy.</p>
          ) : (
            <div className="space-y-3">
              {oversaturated.slice(0, 5).map((gap) => (
                <div key={gap.narrative_type} className="flex items-center justify-between p-3 bg-orange-50 border border-orange-100 rounded-lg">
                  <div>
                    <p className="font-medium text-sm text-orange-900">{gap.narrative_name || formatNarrative(gap.narrative_type)}</p>
                    <p className="text-xs text-orange-700 mt-0.5">
                      {gap.volume_share_pct.toFixed(1)}% of creatives but only {gap.purchase_share_pct.toFixed(1)}% of purchases
                    </p>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="text-xs text-muted-foreground">Active</p>
                    <p className="font-semibold text-orange-700">{gap.active_creatives}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Top Creatives */}
      {topCreatives.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold flex items-center gap-2">
              <Zap className="h-4 w-4 text-yellow-500" />
              Top Performing Creatives ({days}d)
            </h2>
            <Link href={`/library?product_id=${productId}`} className="text-sm text-primary hover:underline flex items-center gap-1">
              View all <ArrowUpRight className="h-3 w-3" />
            </Link>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {["Creative", "Spend", "ROAS", "CTR", "CPA", "Purchases"].map((h) => (
                    <th key={h} className="text-left pb-2 text-xs font-medium text-muted-foreground pr-6">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(topCreatives as Array<Record<string, unknown>>).map((c) => (
                  <tr key={String(c.creative_id)} className="border-b border-border/50 hover:bg-muted/20">
                    <td className="py-2 pr-6">
                      <Link href={`/creatives/${c.creative_id}`} className="flex items-center gap-2 hover:text-primary">
                        {c.thumbnail_url ? (
                          <img src={String(c.thumbnail_url)} alt="" className="w-8 h-8 rounded object-cover" />
                        ) : (
                          <div className="w-8 h-8 rounded bg-muted" />
                        )}
                        <span className="truncate max-w-[140px]">{String(c.name || c.creative_id)}</span>
                      </Link>
                    </td>
                    <td className="py-2 pr-6">{formatCurrency(Number(c.total_spend))}</td>
                    <td className={`py-2 pr-6 font-semibold ${Number(c.avg_roas) >= 3 ? "text-green-600" : ""}`}>
                      {formatRoas(Number(c.avg_roas))}
                    </td>
                    <td className="py-2 pr-6">{formatCtr(Number(c.avg_ctr_pct) / 100)}</td>
                    <td className="py-2 pr-6">{formatCurrency(Number(c.avg_cpa))}</td>
                    <td className="py-2">{formatNumber(Number(c.total_purchases))}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
