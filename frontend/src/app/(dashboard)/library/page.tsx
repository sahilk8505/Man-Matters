"use client";

import { useEffect, useState, useCallback } from "react";
import { Grid2X2, List, Search, Filter, Upload, RefreshCw } from "lucide-react";
import { creatives as creativesApi, products as productsApi } from "@/lib/api";
import type { CreativeListItem, Product } from "@/types";
import {
  getFatigueBg, getFatigueLabel, getRecommendationColor, getRecommendationLabel,
  formatCurrency, formatRoas, formatCtr, formatDate, formatNarrative
} from "@/lib/utils";
import { NARRATIVES, HOOK_TYPES, CREATOR_TYPES, FATIGUE_STAGES } from "@/lib/constants";
import Link from "next/link";
import { toast } from "sonner";

export default function CreativeLibrary() {
  const [creativeList, setCreativeList] = useState<CreativeListItem[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [viewMode, setViewMode] = useState<"grid" | "table">("grid");
  const [search, setSearch] = useState("");
  const [filters, setFilters] = useState({
    product_id: "",
    narrative_type: "",
    hook_type: "",
    creator_type: "",
    fatigue_stage: "",
    status: "active",
  });

  useEffect(() => {
    productsApi.list().then(setProducts);
  }, []);

  const loadCreatives = useCallback(() => {
    setLoading(true);
    const params: Record<string, string> = {};
    if (filters.product_id) params.product_id = filters.product_id;
    if (filters.narrative_type) params.narrative_type = filters.narrative_type;
    if (filters.hook_type) params.hook_type = filters.hook_type;
    if (filters.creator_type) params.creator_type = filters.creator_type;
    if (filters.fatigue_stage) params.fatigue_stage = filters.fatigue_stage;
    if (filters.status) params.status = filters.status;
    if (search) params.search = search;

    creativesApi
      .list(params)
      .then(setCreativeList)
      .catch(() => toast.error("Failed to load creatives"))
      .finally(() => setLoading(false));
  }, [filters, search]);

  useEffect(() => {
    const timer = setTimeout(loadCreatives, 300);
    return () => clearTimeout(timer);
  }, [loadCreatives]);

  return (
    <div className="p-6 space-y-5">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Creative Library</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {creativeList.length} creatives · All Man Matters products
          </p>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode("grid")}
            className={`p-2 rounded-lg border ${viewMode === "grid" ? "bg-primary text-primary-foreground border-primary" : "border-border hover:bg-accent"}`}
          >
            <Grid2X2 className="h-4 w-4" />
          </button>
          <button
            onClick={() => setViewMode("table")}
            className={`p-2 rounded-lg border ${viewMode === "table" ? "bg-primary text-primary-foreground border-primary" : "border-border hover:bg-accent"}`}
          >
            <List className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-2 flex-wrap items-center">
        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search creatives..."
            className="pl-9 pr-4 py-2 text-sm border border-border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50 w-56"
          />
        </div>

        {[
          { key: "product_id", label: "Product", options: products.map((p) => ({ value: p.id, label: p.name })) },
          { key: "narrative_type", label: "Narrative", options: NARRATIVES.map((n) => ({ value: n, label: formatNarrative(n) })) },
          { key: "hook_type", label: "Hook", options: HOOK_TYPES.map((h) => ({ value: h, label: formatNarrative(h) })) },
          { key: "creator_type", label: "Creator", options: CREATOR_TYPES.map((c) => ({ value: c, label: formatNarrative(c) })) },
          { key: "fatigue_stage", label: "Fatigue", options: [
            { value: "healthy", label: "Healthy" },
            { value: "watch", label: "Watch" },
            { value: "fatiguing", label: "Fatiguing" },
            { value: "fatigued", label: "Fatigued" },
          ]},
          { key: "status", label: "Status", options: [
            { value: "active", label: "Active" },
            { value: "paused", label: "Paused" },
          ]},
        ].map(({ key, label, options }) => (
          <select
            key={key}
            value={filters[key as keyof typeof filters]}
            onChange={(e) => setFilters((f) => ({ ...f, [key]: e.target.value }))}
            className="text-sm border border-border rounded-lg px-3 py-2 bg-background"
          >
            <option value="">{label}</option>
            {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
        ))}

        {Object.values(filters).some(Boolean) && (
          <button
            onClick={() => setFilters({ product_id: "", narrative_type: "", hook_type: "", creator_type: "", fatigue_stage: "", status: "active" })}
            className="text-sm text-muted-foreground hover:text-foreground flex items-center gap-1"
          >
            Clear filters
          </button>
        )}
      </div>

      {/* Grid View */}
      {viewMode === "grid" && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4">
          {loading
            ? Array.from({ length: 10 }).map((_, i) => (
                <div key={i} className="aspect-[4/5] bg-muted animate-pulse rounded-xl" />
              ))
            : creativeList.map((c) => (
                <CreativeCard key={c.id} creative={c} />
              ))}
        </div>
      )}

      {/* Table View */}
      {viewMode === "table" && (
        <div className="bg-card border border-border rounded-xl overflow-hidden">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-muted/50">
                <tr>
                  {["Creative", "Product", "Narrative", "Fatigue", "ROAS 7d", "CPA 7d", "CTR 7d", "Spend 7d", "Recommendation"].map((h) => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-muted-foreground uppercase tracking-wide">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {loading
                  ? Array.from({ length: 8 }).map((_, i) => (
                      <tr key={i} className="border-t border-border">
                        <td colSpan={9} className="px-4 py-3"><div className="h-4 bg-muted animate-pulse rounded" /></td>
                      </tr>
                    ))
                  : creativeList.map((c) => (
                      <tr key={c.id} className="border-t border-border hover:bg-muted/20 transition-colors">
                        <td className="px-4 py-3">
                          <div className="flex items-center gap-3">
                            {c.thumbnail_url ? (
                              <img src={c.thumbnail_url} alt="" className="w-9 h-9 rounded-lg object-cover shrink-0" />
                            ) : (
                              <div className="w-9 h-9 bg-muted rounded-lg shrink-0" />
                            )}
                            <div className="min-w-0">
                              <p className="font-medium truncate max-w-[160px]">{c.name || c.id}</p>
                              <p className="text-xs text-muted-foreground">{formatDate(c.launch_date)}</p>
                            </div>
                          </div>
                        </td>
                        <td className="px-4 py-3 whitespace-nowrap">{c.product_name}</td>
                        <td className="px-4 py-3">
                          {c.narrative_type && (
                            <span className="inline-flex items-center px-2 py-0.5 bg-blue-50 text-blue-700 text-xs rounded-full">
                              {formatNarrative(c.narrative_type)}
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          {c.fatigue_stage && (
                            <span className={`inline-flex items-center px-2 py-0.5 text-xs rounded-full border ${getFatigueBg(c.fatigue_stage)}`}>
                              {c.fatigue_score?.toFixed(0)} — {getFatigueLabel(c.fatigue_stage)}
                            </span>
                          )}
                        </td>
                        <td className={`px-4 py-3 text-right font-medium ${(c.roas_7d || 0) >= 3 ? "text-green-600" : ""}`}>
                          {formatRoas(c.roas_7d)}
                        </td>
                        <td className="px-4 py-3 text-right">{formatCurrency(c.cpa_7d)}</td>
                        <td className="px-4 py-3 text-right">{formatCtr(c.ctr_7d)}</td>
                        <td className="px-4 py-3 text-right">{formatCurrency(c.spend_7d)}</td>
                        <td className="px-4 py-3">
                          {c.recommendation && (
                            <span className={`inline-flex items-center px-2 py-0.5 text-xs rounded-full border ${getRecommendationColor(c.recommendation)}`}>
                              {getRecommendationLabel(c.recommendation)}
                            </span>
                          )}
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {!loading && creativeList.length === 0 && (
        <div className="text-center py-16 text-muted-foreground">
          <Grid2X2 className="h-10 w-10 mx-auto mb-3 opacity-20" />
          <p className="font-medium">No creatives found</p>
          <p className="text-sm mt-1">Upload creatives or sync from Meta to get started.</p>
        </div>
      )}
    </div>
  );
}

function CreativeCard({ creative }: { creative: CreativeListItem }) {
  return (
    <Link
      href={`/creatives/${creative.id}`}
      className="group relative bg-card border border-border rounded-xl overflow-hidden hover:border-primary/50 hover:shadow-md transition-all"
    >
      {/* Thumbnail */}
      <div className="aspect-square bg-muted">
        {creative.thumbnail_url ? (
          <img
            src={creative.thumbnail_url}
            alt={creative.name || ""}
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-muted-foreground">
            <Grid2X2 className="h-8 w-8 opacity-30" />
          </div>
        )}
        {/* Fatigue Badge */}
        {creative.fatigue_stage && (
          <div className={`absolute top-2 right-2 text-xs px-2 py-0.5 rounded-full border font-medium ${getFatigueBg(creative.fatigue_stage)}`}>
            {creative.fatigue_score?.toFixed(0)}
          </div>
        )}
      </div>

      {/* Info */}
      <div className="p-3">
        <p className="font-medium text-xs truncate">{creative.name || creative.id}</p>
        <p className="text-xs text-muted-foreground">{creative.product_name}</p>

        <div className="flex items-center gap-1 mt-2 flex-wrap">
          {creative.narrative_type && (
            <span className="text-xs px-1.5 py-0.5 bg-blue-50 text-blue-700 rounded text-[10px]">
              {creative.narrative_type.replace(/_/g, " ").slice(0, 12)}
            </span>
          )}
        </div>

        <div className="flex items-center justify-between mt-2 text-xs">
          <span className="text-muted-foreground">ROAS</span>
          <span className={`font-semibold ${(creative.roas_7d || 0) >= 3 ? "text-green-600" : (creative.roas_7d || 0) < 1.5 ? "text-red-600" : ""}`}>
            {formatRoas(creative.roas_7d)}
          </span>
        </div>
      </div>
    </Link>
  );
}
