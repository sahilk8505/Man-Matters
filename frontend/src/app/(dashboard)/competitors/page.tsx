"use client";

import { useEffect, useState } from "react";
import { Eye, TrendingUp, Clock, Users, Search, Filter } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer
} from "recharts";
import { competitors as competitorsApi } from "@/lib/api";
import type { CompetitorCreative } from "@/types";
import { formatDate, formatNarrative, formatDays } from "@/lib/utils";
import { toast } from "sonner";
import { NARRATIVES, HOOK_TYPES } from "@/lib/constants";

export default function CompetitorIntelligence() {
  const [creatives, setCreatives] = useState<CompetitorCreative[]>([]);
  const [emergingData, setEmergingData] = useState<{
    emerging_narratives: Record<string, unknown>[];
    longest_running: Record<string, unknown>[];
  } | null>(null);
  const [byCompetitor, setByCompetitor] = useState<Record<string, unknown>[]>([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState({ narrative: "", hook: "", competitor: "", active_only: false });
  const [tab, setTab] = useState<"library" | "emerging" | "by-competitor">("emerging");

  useEffect(() => {
    Promise.all([
      competitorsApi.emergingPatterns(30),
      competitorsApi.byCompetitor(),
    ])
      .then(([emerging, comp]) => {
        setEmergingData(emerging as typeof emergingData);
        setByCompetitor(comp as typeof byCompetitor);
      })
      .catch(() => toast.error("Failed to load competitor data"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (tab === "library") {
      const params: Record<string, string | boolean> = {};
      if (filter.narrative) params.narrative_type = filter.narrative;
      if (filter.hook) params.hook_type = filter.hook;
      if (filter.competitor) params.competitor_name = filter.competitor;
      if (filter.active_only) params.is_active = true;
      competitorsApi.list(params).then(setCreatives);
    }
  }, [tab, filter]);

  const tabs = [
    { key: "emerging", label: "Emerging Patterns" },
    { key: "library", label: "Ad Library" },
    { key: "by-competitor", label: "By Competitor" },
  ] as const;

  return (
    <div className="p-6 space-y-6">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Eye className="h-6 w-6 text-primary" />
          Competitor Intelligence
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Track competitor creatives from Meta Ad Library. Identify emerging narratives and long-running patterns.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-border">
        {tabs.map((t) => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === t.key
                ? "border-primary text-primary"
                : "border-transparent text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {/* Emerging Patterns */}
      {tab === "emerging" && emergingData && (
        <div className="space-y-6">
          {/* Momentum Chart */}
          {emergingData.emerging_narratives.length > 0 && (
            <div className="bg-card border border-border rounded-xl p-5">
              <h2 className="font-semibold mb-4 flex items-center gap-2">
                <TrendingUp className="h-4 w-4 text-green-500" />
                Emerging Narrative Momentum (Last 30 Days)
              </h2>
              <ResponsiveContainer width="100%" height={220}>
                <BarChart
                  data={(emergingData.emerging_narratives as Array<Record<string, unknown>>)
                    .sort((a, b) => (b.momentum_score as number) - (a.momentum_score as number))
                    .slice(0, 8)
                    .map((n) => ({
                      name: String(n.narrative_type || "").replace(/_/g, " "),
                      momentum: n.momentum_score,
                      ads: n.ad_count,
                      active: n.active_count,
                      competitors: n.competitor_count,
                    }))}
                  margin={{ left: 0 }}
                >
                  <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                  <XAxis dataKey="name" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 11 }} />
                  <Tooltip />
                  <Bar dataKey="momentum" name="Momentum Score" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="active" name="Active Ads" fill="#22c55e" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          )}

          {/* Longest Running */}
          <div className="bg-card border border-border rounded-xl p-5">
            <h2 className="font-semibold mb-4 flex items-center gap-2">
              <Clock className="h-4 w-4 text-orange-500" />
              Longest-Running Competitor Ads (Proven Formats)
            </h2>
            {loading ? (
              <div className="space-y-3">
                {[1, 2, 3].map((i) => <div key={i} className="h-16 bg-muted animate-pulse rounded-lg" />)}
              </div>
            ) : emergingData.longest_running.length === 0 ? (
              <p className="text-sm text-muted-foreground py-4 text-center">
                No competitor ads analyzed yet. Use the search functionality to import ads.
              </p>
            ) : (
              <div className="space-y-3">
                {(emergingData.longest_running as Array<Record<string, unknown>>).map((ad) => (
                  <div key={String(ad.id)} className="flex items-center gap-4 p-3 border border-border rounded-lg hover:border-primary/30 transition-colors">
                    <div className={`w-3 h-3 rounded-full shrink-0 ${ad.is_active ? "bg-green-500" : "bg-gray-300"}`} />
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{String(ad.competitor_name)}</p>
                      <p className="text-xs text-muted-foreground truncate">{String(ad.headline || "—")}</p>
                    </div>
                    <div className="flex items-center gap-6 shrink-0 text-sm">
                      <div>
                        <p className="text-xs text-muted-foreground">Narrative</p>
                        <p className="font-medium">{formatNarrative(String(ad.narrative_type || ""))}</p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">Running</p>
                        <p className={`font-medium ${Number(ad.estimated_lifespan_days) >= 21 ? "text-green-600" : ""}`}>
                          {formatDays(Number(ad.estimated_lifespan_days))}
                        </p>
                      </div>
                      <div>
                        <p className="text-xs text-muted-foreground">First seen</p>
                        <p className="font-medium">{formatDate(String(ad.first_seen_date || ""))}</p>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Ad Library */}
      {tab === "library" && (
        <div className="space-y-4">
          <div className="flex gap-3 flex-wrap">
            <select
              value={filter.narrative}
              onChange={(e) => setFilter((f) => ({ ...f, narrative: e.target.value }))}
              className="text-sm border border-border rounded-lg px-3 py-2 bg-background"
            >
              <option value="">All Narratives</option>
              {NARRATIVES.map((n) => <option key={n} value={n}>{formatNarrative(n)}</option>)}
            </select>
            <select
              value={filter.hook}
              onChange={(e) => setFilter((f) => ({ ...f, hook: e.target.value }))}
              className="text-sm border border-border rounded-lg px-3 py-2 bg-background"
            >
              <option value="">All Hooks</option>
              {HOOK_TYPES.map((h) => <option key={h} value={h}>{formatNarrative(h)}</option>)}
            </select>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={filter.active_only}
                onChange={(e) => setFilter((f) => ({ ...f, active_only: e.target.checked }))}
                className="rounded"
              />
              Active only
            </label>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {creatives.map((c) => (
              <div key={c.id} className="bg-card border border-border rounded-xl overflow-hidden hover:border-primary/30 transition-colors">
                <div className="aspect-video bg-muted flex items-center justify-center">
                  {c.thumbnail_url ? (
                    <img src={c.thumbnail_url} alt="" className="w-full h-full object-cover" />
                  ) : (
                    <Eye className="h-8 w-8 text-muted-foreground" />
                  )}
                </div>
                <div className="p-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-semibold text-primary">{c.competitor_name}</span>
                    <span className={`text-xs px-2 py-0.5 rounded-full ${c.is_active ? "bg-green-100 text-green-700" : "bg-muted text-muted-foreground"}`}>
                      {c.is_active ? "Active" : "Ended"}
                    </span>
                  </div>
                  <p className="text-sm font-medium line-clamp-2 mb-2">{c.headline || "—"}</p>
                  <div className="flex flex-wrap gap-1">
                    {c.narrative_type && (
                      <span className="text-xs px-2 py-0.5 bg-blue-50 text-blue-700 rounded-full">
                        {formatNarrative(c.narrative_type)}
                      </span>
                    )}
                    {c.hook_type && (
                      <span className="text-xs px-2 py-0.5 bg-purple-50 text-purple-700 rounded-full">
                        {formatNarrative(c.hook_type)}
                      </span>
                    )}
                  </div>
                  <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
                    <span>First seen: {formatDate(c.first_seen_date)}</span>
                    {c.estimated_lifespan_days && (
                      <span className="font-medium">{formatDays(c.estimated_lifespan_days)}</span>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
          {creatives.length === 0 && (
            <div className="text-center py-12 text-muted-foreground">
              <Eye className="h-8 w-8 mx-auto mb-2 opacity-30" />
              <p>No competitor creatives yet. Use the Meta Ad Library search to import ads.</p>
            </div>
          )}
        </div>
      )}

      {/* By Competitor */}
      {tab === "by-competitor" && (
        <div className="bg-card border border-border rounded-xl p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Users className="h-4 w-4" />
            Competitor Activity Summary
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  {["Competitor", "Total Ads", "Active Ads", "Latest Ad", "Avg Lifespan"].map((h) => (
                    <th key={h} className="text-left pb-2 text-muted-foreground font-medium pr-6">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(byCompetitor as Array<Record<string, unknown>>).map((row) => (
                  <tr key={String(row.competitor_name)} className="border-b border-border/50 hover:bg-muted/20">
                    <td className="py-3 font-medium pr-6">{String(row.competitor_name)}</td>
                    <td className="py-3 pr-6">{String(row.total_ads)}</td>
                    <td className="py-3 pr-6">
                      <span className={`font-medium ${Number(row.active_ads) > 0 ? "text-green-600" : "text-muted-foreground"}`}>
                        {String(row.active_ads)}
                      </span>
                    </td>
                    <td className="py-3 pr-6">{formatDate(String(row.latest_ad_date || ""))}</td>
                    <td className="py-3">{formatDays(Number(row.avg_lifespan_days))}</td>
                  </tr>
                ))}
                {byCompetitor.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-muted-foreground">
                      No competitor data yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
