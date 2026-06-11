"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard, Grid2X2, Activity, Sparkles, Dna,
  Eye, Lightbulb, ChevronDown, Package,
} from "lucide-react";
import { cn, getCategoryColor } from "@/lib/utils";
import { NAV_ITEMS } from "@/lib/constants";
import { useState } from "react";

const ICON_MAP: Record<string, React.ReactNode> = {
  LayoutDashboard: <LayoutDashboard className="h-4 w-4" />,
  Grid2X2: <Grid2X2 className="h-4 w-4" />,
  Activity: <Activity className="h-4 w-4" />,
  Sparkles: <Sparkles className="h-4 w-4" />,
  Dna: <Dna className="h-4 w-4" />,
  Eye: <Eye className="h-4 w-4" />,
  Lightbulb: <Lightbulb className="h-4 w-4" />,
};

interface SidebarProps {
  products: Array<{ id: string; name: string; slug: string; category: string }>;
  insightCount?: number;
}

export function Sidebar({ products, insightCount = 0 }: SidebarProps) {
  const pathname = usePathname();
  const [productsOpen, setProductsOpen] = useState(true);

  const categories = [
    { key: "hair", label: "Hair", items: products.filter((p) => p.category === "hair") },
    { key: "beard", label: "Beard", items: products.filter((p) => p.category === "beard") },
    { key: "wellness", label: "Wellness", items: products.filter((p) => p.category === "wellness") },
    { key: "fitness", label: "Fitness", items: products.filter((p) => p.category === "fitness") },
  ];

  return (
    <aside className="w-64 bg-card border-r border-border flex flex-col h-full fixed left-0 top-0 bottom-0 z-30">
      {/* Logo */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-brand-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-sm">MM</span>
          </div>
          <div>
            <p className="font-semibold text-sm leading-tight">Man Matters</p>
            <p className="text-xs text-muted-foreground">Creative OS</p>
          </div>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 overflow-y-auto p-3 space-y-1">
        {NAV_ITEMS.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors relative",
                isActive
                  ? "bg-primary text-primary-foreground font-medium"
                  : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
              )}
            >
              {ICON_MAP[item.icon]}
              <span>{item.label}</span>
              {item.href === "/insights" && insightCount > 0 && (
                <span className="ml-auto bg-red-500 text-white text-xs rounded-full px-1.5 py-0.5 min-w-[20px] text-center">
                  {insightCount > 99 ? "99+" : insightCount}
                </span>
              )}
            </Link>
          );
        })}

        {/* Products Section */}
        <div className="pt-4">
          <button
            onClick={() => setProductsOpen(!productsOpen)}
            className="flex items-center justify-between w-full px-3 py-1 text-xs font-semibold text-muted-foreground uppercase tracking-wider hover:text-foreground"
          >
            <span>Products</span>
            <ChevronDown
              className={cn("h-3 w-3 transition-transform", productsOpen ? "rotate-180" : "")}
            />
          </button>

          {productsOpen && (
            <div className="mt-1 space-y-3">
              {categories.filter((cat) => cat.items.length > 0).map((cat) => (
                <div key={cat.key}>
                  <p className={cn(
                    "px-3 py-0.5 text-xs font-medium rounded-sm mb-1 w-fit",
                    getCategoryColor(cat.key)
                  )}>
                    {cat.label}
                  </p>
                  {cat.items.map((product) => {
                    const href = `/products/${product.id}`;
                    const isActive = pathname === href;
                    return (
                      <Link
                        key={product.id}
                        href={href}
                        className={cn(
                          "flex items-center gap-2 px-3 py-1.5 rounded-md text-xs transition-colors",
                          isActive
                            ? "bg-primary/10 text-primary font-medium"
                            : "text-muted-foreground hover:bg-accent hover:text-accent-foreground"
                        )}
                      >
                        <Package className="h-3 w-3" />
                        {product.name}
                      </Link>
                    );
                  })}
                </div>
              ))}
            </div>
          )}
        </div>
      </nav>

    </aside>
  );
}
