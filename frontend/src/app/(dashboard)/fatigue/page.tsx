"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle, Clock, Activity, RefreshCw, ChevronDown, ChevronUp, Info
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from "recharts";
import { fatigue as fatigueApi, products as productsApi } from "@/lib/api";
import type { FatigueDashboard, NarrativeLifespan, Product, FatigueCurvePoint } from "@/types";
import {
  getFatigueBg, getFatigueLabel, getFatigueScoreColor,
  formatDays, formatDate, formatRoas
} from "@/lib/utils";
import { toast } from "sonner";

const FATIGUE_COLORS = {
  healthy: "#22c55e",
  watch: "#f59e0b",
  fatiguing: "#f97316",
  fatigued: "#ef4444",
};

// ─── Fatigue scoring criteria (mirrors backend run_fatigue.py) ────────────────

const SCORE_BANDS = [
  { stage: "healthy",   range: "0 – 30",  color: "#22c55e", bg: "bg-green-50",  border: "border-green-200",  text: "text-green-700",  desc: "Creative is performing well. Metrics are stable or improving. No action needed." },
  { stage: "watch",     range: "31 – 60", color: "#f59e0b", bg: "bg-amber-50",  border: "border-amber-200",  text: "text-amber-700",  desc: "Early decline signals. Start planning a refresh or test new variants in parallel." },
  { stage: "fatiguing", range: "61 – 80", color: "#f97316", bg: "bg-orange-50", border: "border-orange-200", text: "text-orange-700", desc: "Clear performance decay. Scale down spend on this creative and push new variants now." },
  { stage: "fatigued",  range: "81 – 100",color: "#ef4444", bg: "bg-red-50",    border: "border-red-200",    text: "text-red-700",    desc: "Severe decay. Pause or cut spend. Audience is fully saturated by this creative." },
];

const COMPONENTS = [
  { key: "ctr_decay",        label: "CTR Decay",          desc: "Drop in click-through rate vs early baseline" },
  { key: "roas_decay",       label: "ROAS Decay",         desc: "Drop in return on ad spend vs early baseline" },
  { key: "cpa_inflation",    label: "CPA Inflation",      desc: "Rise in cost per purchase vs early baseline" },
  { key: "cpc_inflation",    label: "CPC Inflation",      desc: "Rise in cost per click vs early baseline" },
  { key: "cpm_inflation",    label: "CPM Inflation",      desc: "Rise in cost per 1,000 impressions" },
  { key: "frequency",        label: "Frequency",          desc: "Current ad frequency vs format danger thresholds" },
  { key: "hook_decay",       label: "Hook Rate Decay",    desc: "Drop in 3-sec view rate (video/reel only)" },
  { key: "hold_decay",       label: "Hold Rate Decay",    desc: "Drop in 75% completion rate (video/reel only)" },
];

// Weights per format (mirrors FORMAT_WEIGHTS in run_fatigue.py)
const FORMAT_WEIGHTS: Record<string, Record<string, number>> = {
  reel:     { ctr_decay: 15, roas_decay: 15, cpa_inflation: 12, cpc_inflation: 10, cpm_inflation: 8,  frequency: 8,  hook_decay: 20, hold_decay: 12 },
  video:    { ctr_decay: 15, roas_decay: 15, cpa_inflation: 12, cpc_inflation: 10, cpm_inflation: 10, frequency: 8,  hook_decay: 18, hold_decay: 12 },
  static:   { ctr_decay: 30, roas_decay: 12, cpa_inflation: 8,  cpc_inflation: 25, cpm_inflation: 20, frequency: 5,  hook_decay: 0,  hold_decay: 0  },
  carousel: { ctr_decay: 28, roas_decay: 12, cpa_inflation: 10, cpc_inflation: 22, cpm_inflation: 18, frequency: 10, hook_decay: 0,  hold_decay: 0  },
};

const FREQ_THRESHOLDS: Record<string, { warn: number; danger: number }> = {
  reel:     { warn: 2.5, danger: 4.0 },
  video:    { warn: 2.5, danger: 4.0 },
  static:   { warn: 3.0, danger: 5.0 },
  carousel: { warn: 2.8, danger: 4.5 },
};

// ─── Component ─────────────────────────────────────────────────────────────────

export default function FatigueDashboard() {
  const [dashboard, setDashboard] = useState<FatigueDashboard | null>(null);
  const [lifespans, setLifespans] = useState<NarrativeLifespan[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<string>("");
  const [selectedCreative, setSelectedCreative] = useState<string | null>(null);
  const [fatigueCurve, setFatigueCurve] = useState<FatigueCurvePoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [backendError, setBackendError] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [criteriaOpen, setCriteriaOpen] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState<"reel" | "video" | "static" | "carousel">("reel");

  const loadData = (productId?: string) => {
    setLoading(true);
    setBackendError(false);
    Promise.all([
      productsApi.list(),
      fatigueApi.dashboard(productId),
      fatigueApi.narrativeLifespans(productId),
    ])
      .then(([prods, dash, lifespanData]) => {
        setProducts(prods as Product[]);
        setDashboard(dash as FatigueDashboard);
        setLifespans(lifespanData as NarrativeLifespan[]);
        setBackendError(false);
      })
      .catch(() => {
        setBackendError(true);
        toast.error("Backend unreachable — check that the server is running.");
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setBackendError(false);
    Promise.all([
      productsApi.list(),
      fatigueApi.dashboard(),
      fatigueApi.narrativeLifespans(),
    ])
      .then(([prods, dash, lifespanData]) => {
        if (cancelled) return;
        setProducts(prods as Product[]);
        setDashboard(dash as FatigueDashboard);
        setLifespans(lifespanData as NarrativeLifespan[]);
        setBackendError(false);
      })
      .catch(() => {
        if (cancelled) return;
        setBackendError(true);
        // Auto-retry once after 5 s (backend may still be starting)
        setTimeout(() => {
          if (!cancelled) loadData();
        }, 5000);
      })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (selectedCreative) {
      fatigueApi.curve(selectedCreative)
        .then(setFatigueCurve)
        .catch(() => setFatigueCurve([]));
    }
  }, [selectedCreative]);

  const handleProductFilter = (pid: string) => {
    setSelectedProduct(pid);
    loadData(pid || undefined);
  };

  /** Recalculate scores synchronously, then auto-update the dashboard state. */
  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const result = await fatigueApi.recalculate();
      // Backend returns the new distribution directly — update state immediately
      setDashboard((prev) =>
        prev
          ? { ...prev, distribution: result.distribution, as_of_date: result.as_of_date }
          : prev
      );
      // Also reload the full dashboard (urgent creatives list etc.)
      const [freshDash, freshLifespans] = await Promise.all([
        fatigueApi.dashboard(selectedProduct || undefined),
        fatigueApi.narrativeLifespans(selectedProduct || undefined),
      ]);
      setDashboard(freshDash as FatigueDashboard);
      setLifespans(freshLifespans as NarrativeLifespan[]);
      toast.success("Fatigue scores refreshed.");
    } catch {
      toast.error("Refresh failed — check backend logs.");
    } finally {
      setRefreshing(false);
    }
  };

  if (loading) return <LoadingSkeleton />;

  const dist = (dashboard?.distribution || {}) as Record<string, { count: number; avg_score: number }>;
  const total = Object.values(dist).reduce((sum, d) => sum + (d?.count || 0), 0);
  const weights = FORMAT_WEIGHTS[selectedFormat];

  return (
    <div className="p-6 space-y-6">

      {/* ── Backend offline banner ──────────────────────────────────────── */}
      {backendError && (
        <div className="flex items-center justify-between gap-3 px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
          <div className="flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            <span>
              <strong>Backend offline.</strong> Run <code className="bg-red-100 px-1 rounded font-mono text-xs">pm2 start ecosystem.config.js</code> in the project folder, then click Reconnect.
            </span>
          </div>
          <button
            onClick={() => loadData(selectedProduct || undefined)}
            className="shrink-0 flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-red-100 hover:bg-red-200 rounded-lg transition-colors"
          >
            <RefreshCw className="h-3 w-3" />
            Reconnect
          </button>
        </div>
      )}

      {/* ── Header ─────────────────────────────────────────────────────── */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Fatigue Monitor</h1>
          <p className="text-sm text-muted-foreground">
            As of {formatDate(dashboard?.as_of_date)} · Multi-dimensional fatigue scoring
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="flex items-center gap-2 text-sm px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} />
            {refreshing ? "Refreshing..." : "Refresh Data"}
          </button>
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
      </div>

      {/* ── Stage Distribution Cards ────────────────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {(["healthy", "watch", "fatiguing", "fatigued"] as const).map((stage) => {
          const d = dist[stage] || { count: 0, avg_score: 0 };
          const band = SCORE_BANDS.find((b) => b.stage === stage)!;
          return (
            <div key={stage} className="bg-card border border-border rounded-xl p-4">
              <div className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border mb-3 ${getFatigueBg(stage)}`}>
                {getFatigueLabel(stage)}
              </div>
              <p className="text-3xl font-bold">{d.count ?? 0}</p>
              <p className="text-xs text-muted-foreground mt-1">Avg score: {(d.avg_score ?? 0).toFixed(0)}/100</p>
              <p className="text-xs text-muted-foreground mt-0.5 font-mono">{band?.range ?? ""}</p>
              {total > 0 && (
                <div className="mt-2 bg-muted rounded-full h-1.5">
                  <div
                    className="h-1.5 rounded-full"
                    style={{ width: `${(d.count / total) * 100}%`, backgroundColor: FATIGUE_COLORS[stage] }}
                  />
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Fatigue Scoring Criteria ────────────────────────────────────── */}
      <div className="bg-card border border-border rounded-xl overflow-hidden">
        <button
          onClick={() => setCriteriaOpen((o) => !o)}
          className="w-full flex items-center justify-between px-5 py-4 hover:bg-muted/40 transition-colors"
        >
          <div className="flex items-center gap-2">
            <Info className="h-4 w-4 text-primary" />
            <span className="font-semibold text-sm">Fatigue Scoring Criteria</span>
            <span className="text-xs text-muted-foreground">— how each creative gets its score</span>
          </div>
          {criteriaOpen ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
        </button>

        {criteriaOpen && (
          <div className="px-5 pb-5 space-y-6 border-t border-border">

            {/* Score bands */}
            <div className="pt-4">
              <h3 className="text-sm font-semibold mb-3">Score Bands</h3>
              <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                {SCORE_BANDS.map((b) => (
                  <div key={b.stage} className={`rounded-lg border p-3 ${b.bg} ${b.border}`}>
                    <div className="flex items-center gap-2 mb-1">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: b.color }} />
                      <span className={`font-semibold text-sm capitalize ${b.text}`}>{b.stage}</span>
                      <span className={`ml-auto font-mono text-xs ${b.text}`}>{b.range}</span>
                    </div>
                    <p className="text-xs text-muted-foreground leading-relaxed">{b.desc}</p>
                  </div>
                ))}
              </div>
            </div>

            {/* Component weights */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold">Component Weights by Format</h3>
                <div className="flex items-center gap-1 text-xs">
                  {(["reel", "video", "static", "carousel"] as const).map((fmt) => (
                    <button
                      key={fmt}
                      onClick={() => setSelectedFormat(fmt)}
                      className={`px-2.5 py-1 rounded-md capitalize transition-colors ${
                        selectedFormat === fmt
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted text-muted-foreground hover:bg-muted/80"
                      }`}
                    >
                      {fmt}
                    </button>
                  ))}
                </div>
              </div>

              <div className="space-y-2">
                {COMPONENTS.map((c) => {
                  const w = weights[c.key] ?? 0;
                  if (w === 0 && (c.key === "hook_decay" || c.key === "hold_decay")) return null;
                  return (
                    <div key={c.key} className="flex items-center gap-3">
                      <div className="w-36 text-xs font-medium text-right shrink-0">{c.label}</div>
                      <div className="flex-1 h-5 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-primary/70 transition-all duration-500"
                          style={{ width: `${w}%` }}
                        />
                      </div>
                      <div className="w-8 text-xs font-mono text-right text-muted-foreground">{w}%</div>
                      <div className="text-xs text-muted-foreground hidden lg:block w-72">{c.desc}</div>
                    </div>
                  );
                })}
              </div>

              {/* Frequency danger thresholds */}
              <div className="mt-4 p-3 bg-muted/50 rounded-lg text-xs">
                <span className="font-semibold">Frequency thresholds ({selectedFormat}):</span>
                <span className="ml-2 text-amber-700 font-medium">
                  ⚠ Warning at {FREQ_THRESHOLDS[selectedFormat]?.warn}×
                </span>
                <span className="ml-3 text-red-700 font-medium">
                  🔴 Danger at {FREQ_THRESHOLDS[selectedFormat]?.danger}×
                </span>
                <span className="ml-3 text-muted-foreground">
                  (frequency contribution scales linearly between the two)
                </span>
              </div>
            </div>

            {/* Baseline explanation */}
            <div className="text-xs text-muted-foreground border-t border-border pt-3 leading-relaxed">
              <strong>How the score is calculated:</strong> The first 3–7 days of spend (≥ ₹200/day) form the baseline.
              Each signal component compares the most recent 3 days against that baseline.
              Decay = <code className="bg-muted px-1 rounded">((baseline − recent) / baseline) × 200</code>,
              inflation flips the sign. All components are weighted, summed, and clamped to 0–100.
            </div>
          </div>
        )}
      </div>

      {/* ── Urgent Creatives ────────────────────────────────────────────── */}
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
                onClick={() => setSelectedCreative(selectedCreative === c.creative_id ? null : c.creative_id)}
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
                    <div className="text-sm font-bold" style={{ color: getFatigueScoreColor(c.fatigue_score ?? 0) }}>
                      {(c.fatigue_score ?? 0).toFixed(0)}
                    </div>
                    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium border ${getFatigueBg(c.fatigue_stage)}`}>
                      {getFatigueLabel(c.fatigue_stage)}
                    </span>
                  </div>
                  {c.expected_remaining_days != null && (
                    <p className="text-xs text-muted-foreground mt-1">~{c.expected_remaining_days}d remaining</p>
                  )}
                </div>
                <div className="text-right min-w-[80px]">
                  {c.current_frequency !== undefined && (
                    <div>
                      <p className="text-xs text-muted-foreground">Frequency</p>
                      <p className={`text-sm font-medium ${c.current_frequency > 4 ? "text-red-600" : ""}`}>
                        {(c.current_frequency ?? 0).toFixed(1)}×
                      </p>
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>

          {/* Fatigue Curve */}
          {selectedCreative && fatigueCurve.length > 0 && (
            <div className="mt-5 border-t border-border pt-5">
              <h3 className="font-medium text-sm mb-3">Fatigue Curve — Component Breakdown</h3>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={fatigueCurve}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Tooltip
                    formatter={(v: number, name: string) => [
                      `${v.toFixed(1)}`,
                      name.replace(/_/g, " ").replace(/\b\w/g, (c: string) => c.toUpperCase()),
                    ]}
                  />
                  <Area type="monotone" dataKey="fatigue_score"    stroke="#ef4444" fill="#fef2f2"    strokeWidth={2}   name="fatigue_score" />
                  <Area type="monotone" dataKey="ctr_decay"        stroke="#3b82f6" fill="transparent" strokeWidth={1.5} strokeDasharray="4 2" name="ctr_decay" />
                  <Area type="monotone" dataKey="roas_decay"       stroke="#8b5cf6" fill="transparent" strokeWidth={1.5} strokeDasharray="4 2" name="roas_decay" />
                  <Area type="monotone" dataKey="frequency_score"  stroke="#f59e0b" fill="transparent" strokeWidth={1.5} strokeDasharray="4 2" name="frequency_score" />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>
      )}

      {/* ── Narrative Lifespans ──────────────────────────────────────────── */}
      <div className="bg-card border border-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Clock className="h-5 w-5 text-primary" />
          <h2 className="font-semibold">Narrative Lifespans by Product</h2>
        </div>
        {lifespans.length === 0 ? (
          <p className="text-sm text-muted-foreground">No narrative lifespan data yet.</p>
        ) : (
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
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-50 text-red-700 border border-red-200">Oversaturated</span>
                      ) : (
                        <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-green-50 text-green-700 border border-green-200">Healthy</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
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
      <div className="h-20 bg-muted animate-pulse rounded-xl" />
      <div className="h-96 bg-muted animate-pulse rounded-xl" />
    </div>
  );
}
