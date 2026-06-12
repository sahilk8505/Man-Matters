// =============================================================================
// API Client — Man Matters Creative OS
// =============================================================================

const BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";
const API_PREFIX = "/api/v1";

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("mm_cos_token");
}

async function request<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const token = getToken();
  const url = `${BASE_URL}${API_PREFIX}${path}`;

  const res = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(options.headers || {}),
    },
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }

  if (res.status === 204) return undefined as T;
  return res.json();
}

async function multipartRequest<T>(
  path: string,
  formData: FormData
): Promise<T> {
  const token = getToken();
  const url = `${BASE_URL}${API_PREFIX}${path}`;

  const res = await fetch(url, {
    method: "POST",
    body: formData,
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Upload failed");
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export const auth = {
  login: (email: string, password: string) =>
    request<{ access_token: string; user: Record<string, string> }>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),
};

// ---------------------------------------------------------------------------
// Products
// ---------------------------------------------------------------------------

export const products = {
  list: () => request<import("@/types").Product[]>("/products"),
};

// ---------------------------------------------------------------------------
// Creatives
// ---------------------------------------------------------------------------

export const creatives = {
  list: (params?: Record<string, string | number | undefined>) => {
    const qs = params
      ? "?" + Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== "")
          .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
          .join("&")
      : "";
    return request<import("@/types").CreativeListItem[]>(`/creatives${qs}`);
  },

  get: (id: string) => request<import("@/types").CreativeDetail>(`/creatives/${id}`),

  getMetrics: (id: string, days = 30) =>
    request<import("@/types").DailyMetric[]>(`/creatives/${id}/metrics?days=${days}`),

  getSimilar: (id: string, limit = 10) =>
    request<Record<string, unknown>[]>(`/creatives/${id}/similar?limit=${limit}`),

  reanalyze: (id: string) =>
    request<{ status: string }>(`/creatives/${id}/reanalyze`, { method: "POST" }),
};

// ---------------------------------------------------------------------------
// Analytics
// ---------------------------------------------------------------------------

export const analytics = {
  executiveSummary: () =>
    request<import("@/types").ExecutiveSummary>("/analytics/executive-summary"),

  productPerformance: (productId: string, days = 30) =>
    request<{
      product: import("@/types").Product;
      period_days: number;
      narrative_breakdown: import("@/types").NarrativeBreakdown[];
      daily_trend: Record<string, unknown>[];
      fatigue_distribution: Record<string, number>;
    }>(`/analytics/products/${productId}/performance?days=${days}`),

  creativeGaps: (productId: string) =>
    request<import("@/types").NarrativeSaturation[]>(`/analytics/products/${productId}/gaps`),

  topCreatives: (productId: string, days = 30) =>
    request<Record<string, unknown>[]>(`/analytics/products/${productId}/top-creatives?days=${days}`),
};

// ---------------------------------------------------------------------------
// Fatigue
// ---------------------------------------------------------------------------

export const fatigue = {
  dashboard: (productId?: string) =>
    request<import("@/types").FatigueDashboard>(
      `/fatigue/dashboard${productId ? `?product_id=${productId}` : ""}`
    ),

  curve: (creativeId: string, days = 60) =>
    request<import("@/types").FatigueCurvePoint[]>(`/fatigue/creatives/${creativeId}/curve?days=${days}`),

  narrativeLifespans: (productId?: string) =>
    request<import("@/types").NarrativeLifespan[]>(
      `/fatigue/narrative-lifespans${productId ? `?product_id=${productId}` : ""}`
    ),
};

// ---------------------------------------------------------------------------
// Predictions
// ---------------------------------------------------------------------------

export const predictions = {
  get: (creativeId: string) =>
    request<import("@/types").PredictionResult>(`/predictions/${creativeId}`),

  analyzeUpload: (formData: FormData) =>
    multipartRequest<{
      analysis: import("@/types").AnalysisResult;
      prediction: import("@/types").PredictionResult;
    }>("/predictions/analyze-upload", formData),
};

// ---------------------------------------------------------------------------
// Competitors
// ---------------------------------------------------------------------------

export const competitors = {
  list: (params?: Record<string, string | boolean | undefined>) => {
    const qs = params
      ? "?" + Object.entries(params)
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
          .join("&")
      : "";
    return request<import("@/types").CompetitorCreative[]>(`/competitors${qs}`);
  },

  emergingPatterns: (days = 30) =>
    request<{
      emerging_narratives: Record<string, unknown>[];
      longest_running: Record<string, unknown>[];
    }>(`/competitors/emerging-patterns?days=${days}`),

  byCompetitor: () =>
    request<Record<string, unknown>[]>("/competitors/by-competitor"),
};

// ---------------------------------------------------------------------------
// Genome
// ---------------------------------------------------------------------------

export const genome = {
  patterns: (productId?: string) =>
    request<import("@/types").GenomePattern[]>(
      `/genome/patterns${productId ? `?product_id=${productId}` : ""}`
    ),

  winningCombinations: (productId?: string) =>
    request<import("@/types").GenomePattern[]>(
      `/genome/winning-combinations${productId ? `?product_id=${productId}` : ""}`
    ),

  losingPatterns: (productId?: string) =>
    request<import("@/types").GenomePattern[]>(
      `/genome/losing-patterns${productId ? `?product_id=${productId}` : ""}`
    ),

  productLearnings: (productId: string) =>
    request<{
      product_id: string;
      winning_patterns: import("@/types").GenomePattern[];
      losing_patterns: import("@/types").GenomePattern[];
      key_insights: string[];
    }>(`/genome/product-learnings/${productId}`),
};

// ---------------------------------------------------------------------------
// Insights
// ---------------------------------------------------------------------------

export const insights = {
  list: (params?: Record<string, string | boolean | undefined>) => {
    const qs = params
      ? "?" + Object.entries(params)
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => `${k}=${encodeURIComponent(String(v))}`)
          .join("&")
      : "";
    return request<import("@/types").Insight[]>(`/insights${qs}`);
  },

  counts: () =>
    request<{ total_unread: number; critical: number; high: number; medium: number; low: number }>(
      "/insights/count"
    ),

  markRead: (id: string) =>
    request<{ status: string }>(`/insights/${id}/read`, { method: "POST" }),

  dismiss: (id: string) =>
    request<{ status: string }>(`/insights/${id}/dismiss`, { method: "POST" }),

  action: (id: string) =>
    request<{ status: string }>(`/insights/${id}/action`, { method: "POST" }),

  generate: () =>
    request<{ status: string }>("/insights/generate", { method: "POST" }),
};

// ---------------------------------------------------------------------------
// Sync
// ---------------------------------------------------------------------------

export const sync = {
  triggerMeta: () =>
    request<{ status: string }>("/sync/meta/trigger", { method: "POST" }),

  status: () =>
    request<{ last_date: string | null; total_rows: number; is_current: boolean; days_behind: number | null }>(
      "/sync/status"
    ),

  syncYesterday: () =>
    request<{ status: string; date: string; message: string }>("/sync/yesterday", { method: "POST" }),

  logs: (limit = 20) =>
    request<Record<string, unknown>[]>(`/sync/logs?limit=${limit}`),

  uploadCsv: (formData: FormData) =>
    multipartRequest<{ status: string; rows_processed: number; rows_failed: number }>(
      "/sync/upload/csv-metrics",
      formData
    ),

  uploadCreative: (formData: FormData) =>
    multipartRequest<{ creative_id: string; storage_url: string; status: string }>(
      "/sync/upload/creative",
      formData
    ),
};
