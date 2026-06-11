"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Clock, Activity, TrendingDown } from "lucide-react";
import {
  AreaChart, Area, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, Legend,
} from "recharts";
import { fatigue as fatigueApi, products as productsApi } from "@/lib/api";
import type { FatigueDashboard, NarrativeLifespan, Product, FatigueCurvePoint } from "@/types";
import {
  getFatigueBg, getFatigueLabel, getFatigueScoreColor,
  formatCurrency, formatDays, formatDate, formatPct, formatRoas
} from "@/lib/utils";
import { toast } from "sonner";

const FATIGUE_COLORS = {
  healthy: "#22c55e",
  watch: "#f59e0b",
  fatiguing: "#f97316",
  fatigued: "#ef4444",
};

export default function FatigueDashboard() {
  const [dashboard, setDashboard] = useState<FatigueDashboard | null>(null);
  const [lifespans, setLifespans] = useState<NarrativeLifespan[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>("");
  const [selectedCreative, setSelectedCreative] = useState<string | null>(null);
  const [fatigueCurve, setFatigueCurve] = useState<FatigueCurvePoint[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      productsApi.list(),
      fatigueApi.dashboard(),
      fatigueApi.narrativeLifespans(),
    ])
      .then(([prods, dash, lifespanData]) => {
        setProducts(prods as Product[]);
        setDashboard(dash as FatigueDashboard);
        setLifespans(lifespanData as NarrativeLifespan[]);
      })
      .catch(() => toast.error("Failed to load fatigue data"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (selectedCreative) {
      fatigueApi.curve(selectedCreative).then(setFatigueCurve);
    }
  }, [selectedCreative]);

  const handleProductFilter = (pid: string) => {
    setSelectedProduct(pid);
    fatigueApi.dashboard(pid || undefined).then(setDashboard);
    fatigueApi.narrativeLifespans(pid || undefined).then(setLifespans);
  };

  if (loading) return <LoadingSkeleton />;

  const dist = (dashboard?.distribution || {}) as Record<string, { count: number; avg_score: number }>;
  const total = Object.values(dist).reduce((sum, d) => sum + (d?.count || 0), 0);

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Fatigue Monitor</h1>
          <p className="text-sm text-muted-foreground">
            As of {formatDate(dashboard?.as_of_date)} · Multi-dimensional fatigue scoring
          </p>
        </div>
        <select
          value={selectedProduct}
          onChange={(e) => handleProductFilter(e.target.value)}
          className="text-sm border border-border rounded-lg px-3 py-2 bg-background"
        >
          <option value="">All Products</option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* Stage Distribution */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {(["healthy", "watch", "fatiguing", "fatigued"] as const).map((stage) => {
          const d = dist[stage] || { count: 0, avg_score: 0 };
          return (
            <div
              key={stage}
              className="bg-card border border-border rounded-xl p-4"
            >
              <div className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border mb-3 ${getFatigueBg(stage)}`}>
                {getFatigueLabel(stage)}
              </div>
              <p className="text-3xl font-bold">{d.count}</p>
              <p className="text-xs text-muted-foreground mt-1">
                Avg score: {d.avg_score.toFixed(0)}/100
              </p>
              {total > 0 && (
                <div className="mt-2 bg-muted rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full"
                    style={{
                      width: `${(d.count / total) * 100}%`,
                      backgroundColor: FATIGUE_COLORS[stage],
                    }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Urgent Creatives */}
      {dashboard && dashboard.urgent_creatives.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <AlertTriangle className="h-5 w-5 text-red-500" />
            <h2 className="font-semibold">Requires Immediate Action</h2>
            <span className="text-sm text-muted-foreground">({dashboard.urgent_creatives.length})</span>
          </div>
          <div className="space-y-3">
            {dashboard.urgent_creatives.map((c) => (
              <div
                key={c.creative_id}
                className={`flex items-center gap-4 p-3 rounded-lg border cursor-pointer hover:border-primary/50 transition-colors ${
                  selectedCreative === c.creative_id ? "border-primary bg-primary/5" : "border-border"
                }`}
                onClick={() => setSelectedCreative(
                  selectedCreative === c.creative_id ? null : c.creative_id
                )}
              >
                {c.thumbnail_url ? (
                  <img src={c.thumbnail_url} alt="" className="w-12 h-12 rounded-lg object-cover" />
                ) : (
                  <div className="w-12 h-12 bg-muted rounded-lg flex items-center justify-center">
                    <Activity className="h-5 w-5 text-muted-foreground" />
                  </div>
                )}
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-sm truncate">{c.name || c.creative_id}</p>
                  <p className="text-xs text-muted-foreground">{c.product_name} · {c.days_since_launch}d running</p>
                </div>
                <div className="text-right">
                  <div className="flex items-center gap-2">
                    <div
                      className="text-sm font-bold"
                      style={{ color: getFatigueScoreColor(c.fatigue_score) }}
                    >
                      {c.fatigue_score.toFixed(0)}
                    </div>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getFatigueBg(c.fatigue_stage)}`}>
                      {getFatigueLabel(c.fatigue_stage)}
                    </span>
                  </div>
                  {c.expected_remaining_days !== undefined && c.expected_remaining_days !== null && (
                    <p className="text-xs text-muted-foreground mt-1">
                      ~{c.expected_remaining_days}d remaining
                    </p>
                  )}
                </div>
                <div className="text-right min-w-[80px]">
                  {c.current_frequency !== undefined && (
                    <div>
                      <p className="text-xs text-muted-foreground">Frequency</p>
                      <p className={`text-sm font-medium ${c.current_frequency > 4 ? "text-red-600" : ""}`}>
                        {c.current_frequency.toFixed(1)}x
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Fatigue Curve for selected creative */}
          {selectedCreative && fatigueCurve.length > 0 && (
            <div className="mt-5 border-t border-border pt-5">
              <h3 className="font-medium text-sm mb-3">Fatigue Curve — Component Breakdown</h3>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={fatigueCurve}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Tooltip
                    formatter={(v: number, name: string) => [`${v.toFixed(1)}`, name.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase())]}
                  />
                  <Area type="monotone" dataKey="fatigue_score" stroke="#ef4444" fill="#fef2f2" strokeWidth={2} name="fatigue_score" />
                  <Area type="monotone" dataKey="ctr_decay" stroke="#3b82f6" fill="transparent" strokeWidth={1.5} strokeDasharray="4 2" name="ctr_decay" />
                  <Area type="monotone" dataKey="roas_decay" stroke="#8b5cf6" fill="transparent" strokeWidth={1.5} strokeDasharray="4 2" name="roas_decay" />
                  <Area type="monotone" dataKey="frequency_score" stroke="#f59e0b" fill="transparent" strokeWidth={1.5} strokeDasharray="4 2" name="frequency_score" />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* Narrative Lifespans */}
      <div className="bg-card border border-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="h-5 w-5 text-primary" />
          <h2 className="font-semibold">Narrative Lifespans by Product</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border">
                <th className="text-left pb-2 text-muted-foreground font-medium">Product</th>
                <th className="text-left pb-2 text-muted-foreground font-medium">Narrative</th>
                <th className="text-right pb-2 text-muted-foreground font-medium">Avg Life</th>
                <th className="text-right pb-2 text-muted-foreground font-medium">Fatigue Day</th>
                <th className="text-right pb-2 text-muted-foreground font-medium">CTR Decay/Day</th>
                <th className="text-right pb-2 text-muted-foreground font-medium">Active</th>
                <th className="text-right pb-2 text-muted-foreground font-medium">Avg ROAS</th>
                <th className="text-center pb-2 text-muted-foreground font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {lifespans.map((row, i) => (
                <tr key={i} className="border-b border-border/50 hover:bg-muted/30 transition-colors">
                  <td className="py-2 font-medium">{row.product_name}</td>
                  <td className="py-2 text-muted-foreground capitalize">{row.narrative_type?.replace(/_/g, " ")}</td>
                  <td className="py-2 text-right">{formatDays(row.avg_lifespan_days)}</td>
                  <td className="py-2 text-right">{formatDays(row.avg_fatigue_start_day)}</td>
                  <td className={`py-2 text-right ${row.ctr_decay_rate_pct && row.ctr_decay_rate_pct < -0.5 ? "text-red-600" : ""}`}>
                    {row.ctr_decay_rate_pct ? `${row.ctr_decay_rate_pct.toFixed(2)}%` : "—"}
                  </td>
                  <td className="py-2 text-right">{row.active_creatives}</td>
                  <td className={`py-2 text-right ${(row.avg_roas || 0) >= 3 ? "text-green-600" : "text-muted-foreground"}`}>
                    {formatRoas(row.avg_roas)}
                  </td>
                  <td className="py-2 text-center">
                    {row.is_oversaturated ? (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 border border-red-200">
                        Oversaturated
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700 border border-green-200">
                        Healthy
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

function LoadingSkeleton() {
  return (
    <div className="p-6 space-y-6">
      <div className="h-8 w-48 bg-muted animate-pulse rounded" />
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-28 bg-muted animate-pulse rounded-xl" />
        ))}
      </div>
      <div className="h-96 bg-muted animate-pulse rounded-xl" />
    </div>
  );
}
