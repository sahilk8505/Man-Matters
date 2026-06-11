"use client";

import { useEffect, useState } from "react";
import { Dna, Trophy, XCircle, TrendingUp } from "lucide-react";
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell
} from "recharts";
import { genome as genomeApi, products as productsApi } from "@/lib/api";
import type { GenomePattern, Product } from "@/types";
import { formatRoas, formatCurrency, formatPct, formatDays, formatNumber } from "@/lib/utils";
import { toast } from "sonner";

export default function GenomeDashboard() {
  const [products, setProducts] = useState<Product[]>([]);
  const [selectedProduct, setSelectedProduct] = useState("");
  const [winners, setWinners] = useState<GenomePattern[]>([]);
  const [losers, setLosers] = useState<GenomePattern[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    productsApi.list().then(setProducts);
  }, []);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      genomeApi.winningCombinations(selectedProduct || undefined),
      genomeApi.losingPatterns(selectedProduct || undefined),
    ])
      .then(([w, l]) => {
        setWinners(w as GenomePattern[]);
        setLosers(l as GenomePattern[]);
      })
      .catch(() => toast.error("Failed to load genome data"))
      .finally(() => setLoading(false));
  }, [selectedProduct]);

  const topWinnersChart = winners.slice(0, 8).map((p, i) => ({
    name: p.description || `Pattern ${i + 1}`,
    roas: p.avg_roas || 0,
    creatives: p.total_creatives,
  }));

  return (
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <Dna className="h-6 w-6 text-primary" />
            Creative Genome
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Which creative building block combinations consistently win?
          </p>
        </div>
        <select
          value={selectedProduct}
          onChange={(e) => setSelectedProduct(e.target.value)}
          className="text-sm border border-border rounded-lg px-3 py-2 bg-background"
        >
          <option value="">All Products</option>
          {products.map((p) => (
            <option key={p.id} value={p.id}>{p.name}</option>
          ))}
        </select>
      </div>

      {/* Winning Patterns Chart */}
      {!loading && topWinnersChart.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5">
          <h2 className="font-semibold mb-4 flex items-center gap-2">
            <Trophy className="h-4 w-4 text-yellow-500" />
            Top Winning Patterns by ROAS
          </h2>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={topWinnersChart} layout="vertical" margin={{ left: 0 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" horizontal={false} />
              <XAxis type="number" domain={[0, "auto"]} tick={{ fontSize: 11 }} tickFormatter={(v: number) => `${v}x`} />
              <YAxis type="category" dataKey="name" width={160} tick={{ fontSize: 11 }} />
              <Tooltip formatter={(v: number, name: string) => [name === "roas" ? `${v.toFixed(1)}x` : v, name === "roas" ? "ROAS" : "Creatives"]} />
              <Bar dataKey="roas" name="roas" radius={[0, 4, 4, 0]}>
                {topWinnersChart.map((_, i) => (
                  <Cell key={i} fill={i < 3 ? "#22c55e" : i < 6 ? "#3b82f6" : "#94a3b8"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {/* Winning Patterns Table */}
      <div className="bg-card border border-border rounded-xl p-5">
        <div className="flex items-center gap-2 mb-4">
          <Trophy className="h-5 w-5 text-yellow-500" />
          <h2 className="font-semibold">Winning Combinations</h2>
          <span className="text-sm text-muted-foreground">(min. 2 creatives, ranked by ROAS)</span>
        </div>
        {loading ? (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => <div key={i} className="h-16 bg-muted animate-pulse rounded-lg" />)}
          </div>
        ) : winners.length === 0 ? (
          <p className="text-sm text-muted-foreground py-4 text-center">
            Not enough data yet. Need at least 2 creatives per pattern to surface learnings.
          </p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-border">
                  <th className="text-left pb-2 text-muted-foreground font-medium">#</th>
                  <th className="text-left pb-2 text-muted-foreground font-medium">Combination</th>
                  <th className="text-right pb-2 text-muted-foreground font-medium">Creatives</th>
                  <th className="text-right pb-2 text-muted-foreground font-medium">Avg ROAS</th>
                  <th className="text-right pb-2 text-muted-foreground font-medium">Win Rate</th>
                  <th className="text-right pb-2 text-muted-foreground font-medium">Avg Lifespan</th>
                  <th className="text-right pb-2 text-muted-foreground font-medium">Purchases</th>
                  <th className="text-right pb-2 text-muted-foreground font-medium">Total Spend</th>
                </tr>
              </thead>
              <tbody>
                {winners.map((p, i) => (
                  <tr key={p.pattern_hash} className="border-b border-border/50 hover:bg-muted/30">
                    <td className="py-3 text-muted-foreground">{i + 1}</td>
                    <td className="py-3">
                      <div className="flex flex-wrap gap-1">
                        {[p.hook_type, p.narrative_type, p.format_type, p.creator_type]
                          .filter(Boolean)
                          .map((attr, j) => (
                            <span key={j} className="inline-flex items-center px-2 py-0.5 bg-primary/10 text-primary text-xs rounded-full">
                              {attr!.replace(/_/g, " ")}
                            </span>
                          ))}
                      </div>
                      {p.description && (
                        <p className="text-xs text-muted-foreground mt-1">{p.description}</p>
                      )}
                    </td>
                    <td className="py-3 text-right">{p.total_creatives}</td>
                    <td className={`py-3 text-right font-semibold ${(p.avg_roas || 0) >= 3 ? "text-green-600" : ""}`}>
                      {formatRoas(p.avg_roas)}
                    </td>
                    <td className="py-3 text-right">
                      {p.win_rate_pct !== undefined ? (
                        <span className={`font-medium ${p.win_rate_pct >= 50 ? "text-green-600" : ""}`}>
                          {p.win_rate_pct.toFixed(0)}%
                        </span>
                      ) : "—"}
                    </td>
                    <td className="py-3 text-right">{formatDays(p.avg_lifespan_days)}</td>
                    <td className="py-3 text-right">{formatNumber(p.total_purchases)}</td>
                    <td className="py-3 text-right">{formatCurrency(p.total_spend)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Losing Patterns */}
      {losers.length > 0 && (
        <div className="bg-card border border-border rounded-xl p-5">
          <div className="flex items-center gap-2 mb-4">
            <XCircle className="h-5 w-5 text-red-500" />
            <h2 className="font-semibold">Patterns to Avoid</h2>
            <span className="text-sm text-muted-foreground">(avg ROAS below 1.5x)</span>
          </div>
          <div className="space-y-3">
            {losers.map((p) => (
              <div key={p.pattern_hash} className="flex items-center gap-4 p-3 bg-red-50 border border-red-100 rounded-lg">
                <div className="flex flex-wrap gap-1 flex-1">
                  {[p.hook_type, p.narrative_type, p.format_type, p.creator_type]
                    .filter(Boolean)
                    .map((attr, j) => (
                      <span key={j} className="inline-flex items-center px-2 py-0.5 bg-red-100 text-red-700 text-xs rounded-full">
                        {attr!.replace(/_/g, " ")}
                      </span>
                    ))}
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-red-700">{formatRoas(p.avg_roas)}</p>
                  <p className="text-xs text-muted-foreground">{p.total_creatives} tested</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
