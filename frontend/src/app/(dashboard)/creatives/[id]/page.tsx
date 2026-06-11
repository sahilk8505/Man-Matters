"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { ArrowLeft, RefreshCw, ExternalLink } from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import Link from "next/link";
import { creatives as creativesApi, fatigue as fatigueApi, predictions as predictionsApi } from "@/lib/api";
import type { CreativeDetail, DailyMetric, FatigueCurvePoint, PredictionResult } from "@/types";
import {
  formatCurrency, formatRoas, formatCtr, formatDate, formatNarrative,
  getFatigueBg, getFatigueLabel, getRecommendationColor, getRecommendationLabel,
  getScoreColor, getScoreBg
} from "@/lib/utils";
import { toast } from "sonner";

export default function CreativeDetailPage() {
  const { id } = useParams<{ id: string }>();
  const [creative, setCreative] = useState<CreativeDetail | null>(null);
  const [metrics, setMetrics] = useState<DailyMetric[]>([]);
  const [curve, setCurve] = useState<FatigueCurvePoint[]>([]);
  const [prediction, setPrediction] = useState<PredictionResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [reanalyzing, setReanalyzing] = useState(false);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    Promise.all([
      creativesApi.get(id),
      creativesApi.getMetrics(id, 30),
      fatigueApi.curve(id, 60),
      predictionsApi.get(id).catch(() => null),
    ])
      .then(([c, m, fc, pred]) => {
        setCreative(c as CreativeDetail);
        setMetrics(m as DailyMetric[]);
        setCurve(fc as FatigueCurvePoint[]);
        setPrediction(pred as PredictionResult | null);
      })
      .catch(() => toast.error("Failed to load creative"))
      .finally(() => setLoading(false));
  }, [id]);

  const handleReanalyze = async () => {
    if (!id) return;
    setReanalyzing(true);
    try {
      await creativesApi.reanalyze(id);
      toast.success("Re-analysis queued. Refresh in 30 seconds.");
    } catch {
      toast.error("Failed to queue re-analysis");
    } finally {
      setReanalyzing(false);
    }
  };

  if (loading) {
    return <div className="p-6"><div className="h-8 w-64 bg-muted animate-pulse rounded mb-4" /><div className="h-64 bg-muted animate-pulse rounded-xl" /></div>;
  }

  if (!creative) {
    return <div className="p-6 text-muted-foreground">Creative not found.</div>;
  }

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex items-center gap-4">
        <Link href="/library" className="text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div className="flex-1">
          <h1 className="text-xl font-bold">{creative.name || creative.id}</h1>
          <p className="text-sm text-muted-foreground">{creative.product_name} · Launched {formatDate(creative.launch_date)}</p>
        </div>
        <button onClick={handleReanalyze} disabled={reanalyzing}
          className="flex items-center gap-2 text-sm px-3 py-2 border border-border rounded-lg hover:bg-accent disabled:opacity-50">
          <RefreshCw className={`h-4 w-4 ${reanalyzing ? "animate-spin" : ""}`} />
          Re-analyze
        </button>
        {creative.media_url && (
          <a href={creative.media_url} target="_blank" rel="noopener"
            className="flex items-center gap-2 text-sm px-3 py-2 border border-border rounded-lg hover:bg-accent">
            <ExternalLink className="h-4 w-4" /> View Original
          </a>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Creative Preview + Metadata */}
        <div className="space-y-4">
          {/* Preview */}
          <div className="bg-card border border-border rounded-xl overflow-hidden">
            {creative.storage_url || creative.media_url ? (
              creative.media_type === "video" ? (
                <video src={creative.storage_url || creative.media_url!} controls className="w-full" />
              ) : (
                <img src={creative.storage_url || creative.thumbnail_url || creative.media_url!} alt="" className="w-full" />
              )
            ) : (
              <div className="aspect-video bg-muted flex items-center justify-center text-muted-foreground text-sm">No preview</div>
            )}
          </div>

          {/* Ad Copy */}
          {(creative.headline || creative.body_text) && (
            <div className="bg-card border border-border rounded-xl p-4 space-y-2">
              <h3 className="text-xs font-semibold text-muted-foreground uppercase">Ad Copy</h3>
              {creative.headline && <p className="font-semibold text-sm">{creative.headline}</p>}
              {creative.body_text && <p className="text-sm text-muted-foreground">{creative.body_text}</p>}
              {creative.cta_type && (
                <span className="inline-flex items-center px-2 py-0.5 bg-primary/10 text-primary text-xs rounded-full">{creative.cta_type}</span>
              )}
            </div>
          )}

          {/* AI Metadata */}
          <div className="bg-card border border-border rounded-xl p-4">
            <h3 className="text-xs font-semibold text-muted-foreground uppercase mb-3">AI Analysis</h3>
            <dl className="space-y-2 text-sm">
              {[
                ["Narrative", creative.narrative_type],
                ["Hook", creative.hook_type],
                ["Creator", creative.creator_type],
                ["Visual Style", creative.visual_style],
                ["Offer", creative.offer_type],
                ["Funnel Stage", creative.stage_of_funnel],
                ["Trust Signal", creative.trust_signal],
                ["Emotional Trigger", creative.emotional_trigger],
              ].filter(([, v]) => v).map(([k, v]) => (
                <div key={k as string} className="flex justify-between">
                  <dt className="text-muted-foreground">{k as string}</dt>
                  <dd className="font-medium capitalize">{formatNarrative(v as string)}</dd>
                </div>
              ))}
              {creative.analysis_confidence && (
                <div className="flex justify-between">
                  <dt className="text-muted-foreground">Confidence</dt>
                  <dd className="font-medium">{(creative.analysis_confidence * 100).toFixed(0)}%</dd>
                </div>
              )}
            </dl>
            {creative.pain_point && (
              <div className="mt-3 pt-3 border-t border-border">
                <p className="text-xs text-muted-foreground">Pain point addressed</p>
                <p className="text-sm mt-1">{creative.pain_point}</p>
              </div>
            )}
            {creative.benefit_claimed && (
              <div className="mt-2">
                <p className="text-xs text-muted-foreground">Benefit claimed</p>
                <p className="text-sm mt-1">{creative.benefit_claimed}</p>
              </div>
            )}
          </div>
        </div>

        {/* Charts + Prediction */}
        <div className="lg:col-span-2 space-y-6">
          {/* Performance Chart */}
          {metrics.length > 0 && (
            <div className="bg-card border border-border rounded-xl p-5">
              <h2 className="font-semibold mb-4">Performance (30d)</h2>
              <ResponsiveContainer width="100%" height={200}>
                <AreaChart data={metrics}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis yAxisId="roas" domain={[0, "auto"]} tick={{ fontSize: 11 }} />
                  <YAxis yAxisId="spend" orientation="right" tick={{ fontSize: 11 }} tickFormatter={(v: number) => `₹${(v/1000).toFixed(0)}K`} />
                  <Tooltip formatter={(v: number, name: string) => [
                    name === "roas" ? `${v.toFixed(2)}x` : name === "spend" ? `₹${v.toFixed(0)}` : `${v.toFixed(2)}%`,
                    name,
                  ]} />
                  <Area yAxisId="roas" type="monotone" dataKey="roas" stroke="#22c55e" fill="#f0fdf4" strokeWidth={2} name="roas" />
                  <Area yAxisId="spend" type="monotone" dataKey="spend" stroke="#3b82f6" fill="#eff6ff" strokeWidth={2} name="spend" />
                  <Legend wrapperStyle={{ fontSize: 11 }} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Fatigue Curve */}
          {curve.length > 0 && (
            <div className="bg-card border border-border rounded-xl p-5">
              <h2 className="font-semibold mb-4">Fatigue Curve</h2>
              <ResponsiveContainer width="100%" height={160}>
                <AreaChart data={curve}>
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="date" tick={{ fontSize: 10 }} tickFormatter={(v: string) => v.slice(5)} />
                  <YAxis domain={[0, 100]} tick={{ fontSize: 11 }} />
                  <Tooltip formatter={(v: number, name: string) => [`${v.toFixed(1)}`, name]} />
                  <Area type="monotone" dataKey="fatigue_score" stroke="#ef4444" fill="#fef2f2" strokeWidth={2} name="fatigue_score" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Prediction Score */}
          {prediction && (
            <div className="bg-card border border-border rounded-xl p-5">
              <h2 className="font-semibold mb-4">Pre-Launch Prediction Score</h2>
              <div className="grid grid-cols-3 gap-4 mb-4">
                {[
                  { label: "Success Score", score: prediction.creative_success_score },
                  { label: "Narrative", score: prediction.narrative_score },
                  { label: "Novelty", score: prediction.novelty_score },
                ].map(({ label, score }) => (
                  <div key={label} className="text-center">
                    <p className="text-xs text-muted-foreground mb-1">{label}</p>
                    <p className={`text-2xl font-bold ${getScoreColor(score)}`}>{score.toFixed(0)}</p>
                    <div className="mt-1 bg-muted rounded-full h-1.5">
                      <div className={`h-1.5 rounded-full ${getScoreBg(score)}`} style={{ width: `${score}%` }} />
                    </div>
                  </div>
                ))}
              </div>
              <span className={`inline-flex items-center px-3 py-1 rounded-lg text-sm font-medium border ${getRecommendationColor(prediction.recommendation)}`}>
                {getRecommendationLabel(prediction.recommendation)}
              </span>
              {prediction.recommendation_reason && (
                <p className="text-sm text-muted-foreground mt-2">{prediction.recommendation_reason}</p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
