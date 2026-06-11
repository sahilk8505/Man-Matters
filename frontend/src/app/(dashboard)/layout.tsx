"use client";

import { useEffect, useState } from "react";
import { Sidebar } from "@/components/layout/sidebar";
import { products as productsApi, insights as insightsApi } from "@/lib/api";
import type { Product } from "@/types";
import { Toaster } from "sonner";

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const [productList, setProductList] = useState<Product[]>([]);
  const [insightCount, setInsightCount] = useState(0);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    Promise.all([
      productsApi.list().catch(() => []),
      insightsApi.counts().catch(() => ({ total_unread: 0 })),
    ]).then(([prods, counts]) => {
      setProductList(prods as Product[]);
      setInsightCount((counts as { total_unread: number }).total_unread || 0);
      setLoaded(true);
    });
  }, []);

  if (!loaded) {
    return (
      <div className="flex items-center justify-center h-screen bg-background">
        <div className="flex flex-col items-center gap-3">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center animate-pulse">
            <span className="text-white font-bold text-sm">MM</span>
          </div>
          <p className="text-sm text-muted-foreground">Loading Creative OS...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex h-screen bg-background overflow-hidden">
      <Sidebar products={productList} insightCount={insightCount} />
      <main className="flex-1 ml-64 overflow-y-auto">
        <div className="min-h-full">{children}</div>
      </main>
      <Toaster richColors position="top-right" />
    </div>
  );
}
