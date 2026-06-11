// =============================================================================
// Man Matters Creative OS — TypeScript Types
// =============================================================================

export type ProductCategory = "hair" | "wellness" | "fitness";
export type FatigueStage = "insufficient_data" | "healthy" | "watch" | "fatiguing" | "fatigued";
export type Recommendation = "launch_immediately" | "launch_with_caution" | "test" | "iterate" | "avoid";
export type InsightPriority = "critical" | "high" | "medium" | "low";
export type InsightType =
  | "fatigue_alert"
  | "opportunity"
  | "narrative_learning"
  | "performance_anomaly"
  | "saturation_warning"
  | "budget_recommendation"
  | "creative_gap"
  | "winner_pattern"
  | "loser_pattern"
  | "competitive_threat";

export interface Product {
  id: string;
  name: string;
  slug: string;
  category: ProductCategory;
  description?: string;
}

export interface CreativeListItem {
  id: string;
  name?: string;
  product_id: string;
  product_name?: string;
  status: string;
  media_type?: string;
  thumbnail_url?: string;
  launch_date?: string;
  analysis_status: string;
  narrative_type?: string;
  hook_type?: string;
  creator_type?: string;
  visual_style?: string;
  offer_type?: string;
  stage_of_funnel?: string;
  fatigue_score?: number;
  fatigue_stage?: FatigueStage;
  expected_remaining_days?: number;
  spend_7d?: number;
  roas_7d?: number;
  ctr_7d?: number;
  cpa_7d?: number;
  purchases_7d?: number;
  creative_success_score?: number;
  recommendation?: Recommendation;
}

export interface CreativeDetail extends CreativeListItem {
  headline?: string;
  body_text?: string;
  cta_type?: string;
  duration_seconds?: number;
  aspect_ratio?: string;
  media_url?: string;
  storage_url?: string;
  pain_point?: string;
  benefit_claimed?: string;
  trust_signal?: string;
  emotional_trigger?: string;
  production_quality?: string;
  analysis_confidence?: number;
  peak_performance_date?: string;
  fatigue_start_date?: string;
}

export interface DailyMetric {
  date: string;
  spend: number;
  ctr: number;        // as percentage
  roas: number;
  cpa: number;
  hook_rate: number;  // as percentage
  hold_rate: number;  // as percentage
  frequency: number;
  purchases: number;
}

export interface FatigueCurvePoint {
  date: string;
  fatigue_score: number;
  fatigue_stage: FatigueStage;
  ctr_decay: number;
  roas_decay: number;
  cpa_inflation: number;
  hook_decay: number;
  frequency_score: number;
  expected_remaining_days?: number;
  confidence: number;
}

export interface PredictionResult {
  creative_success_score: number;
  narrative_score: number;
  hook_score: number;
  visual_score: number;
  offer_score: number;
  novelty_score: number;
  launch_confidence_score: number;
  fatigue_risk_score: number;
  winner_similarity_pct: number;
  loser_similarity_pct: number;
  predicted_ctr?: number;
  predicted_cpa?: number;
  predicted_roas?: number;
  predicted_lifespan_days?: number;
  recommendation: Recommendation;
  recommendation_reason: string;
  similar_winner_ids: string[];
  similar_loser_ids: string[];
  risk_factors: string[];
  opportunity_factors: string[];
  prediction_confidence: number;
  narrative_type?: string;
  hook_type?: string;
  visual_style?: string;
  creator_type?: string;
}

export interface AnalysisResult {
  narrative_type?: string;
  hook_type?: string;
  hook_text?: string;
  visual_style?: string;
  production_quality?: string;
  creator_type?: string;
  offer_type?: string;
  emotional_trigger?: string;
  pain_point?: string;
  benefit_claimed?: string;
  trust_signal?: string;
  stage_of_funnel?: string;
  analysis_confidence?: number;
}

export interface Insight {
  id: string;
  product_id?: string;
  creative_id?: string;
  insight_type: InsightType;
  priority: InsightPriority;
  title: string;
  body: string;
  recommended_action?: string;
  action_type?: string;
  is_read: boolean;
  is_actioned: boolean;
  is_dismissed: boolean;
  data?: Record<string, unknown>;
  created_at: string;
}

export interface ExecutiveSummary {
  period: { start: string; end: string };
  portfolio: {
    total_spend_30d: number;
    total_purchases_30d: number;
    total_revenue_30d: number;
    avg_roas_30d: number;
    avg_ctr_pct_30d: number;
    avg_cpa_30d: number;
  };
  creative_health: {
    total_active: number;
    healthy: number;
    watch: number;
    fatiguing: number;
    fatigued: number;
    unscored: number;
  };
  insights: {
    unread_count: number;
    recent_critical: Insight[];
  };
  products: ProductSpend[];
}

export interface ProductSpend {
  product_id: string;
  product_name: string;
  category: ProductCategory;
  spend_7d: number;
  roas_7d: number;
  purchases_7d: number;
}

export interface NarrativeBreakdown {
  narrative_type: string;
  creative_count: number;
  spend: number;
  spend_pct: number;
  purchases: number;
  purchase_pct: number;
  revenue: number;
  avg_roas: number;
  avg_ctr_pct: number;
  avg_cpa: number;
}

export interface GenomePattern {
  pattern_hash: string;
  hook_type?: string;
  narrative_type?: string;
  format_type?: string;
  creator_type?: string;
  offer_type?: string;
  visual_style?: string;
  trust_signal?: string;
  funnel_stage?: string;
  description?: string;
  total_creatives: number;
  avg_roas?: number;
  avg_ctr?: number;
  avg_cpa?: number;
  avg_lifespan_days?: number;
  win_rate?: number;
  total_spend: number;
  total_purchases: number;
  win_rate_pct?: number;
}

export interface CompetitorCreative {
  id: string;
  competitor_name: string;
  competitor_page_name?: string;
  thumbnail_url?: string;
  media_type?: string;
  headline?: string;
  first_seen_date?: string;
  last_seen_date?: string;
  estimated_lifespan_days?: number;
  is_active: boolean;
  narrative_type?: string;
  hook_type?: string;
  visual_style?: string;
  offer_type?: string;
  creator_type?: string;
  emotional_trigger?: string;
  analysis_status: string;
}

export interface FatigueDashboard {
  as_of_date: string;
  distribution: Record<FatigueStage, { count: number; avg_score: number }>;
  urgent_creatives: UrgentCreative[];
}

export interface UrgentCreative {
  creative_id: string;
  name?: string;
  thumbnail_url?: string;
  product_id: string;
  product_name: string;
  fatigue_score: number;
  fatigue_stage: FatigueStage;
  expected_remaining_days?: number;
  days_since_launch: number;
  current_frequency?: number;
  ctr_decay_score?: number;
  roas_decay_score?: number;
}

export interface NarrativeLifespan {
  product_id: string;
  product_name: string;
  narrative_name: string;
  narrative_type: string;
  avg_lifespan_days?: number;
  median_lifespan_days?: number;
  avg_fatigue_start_day?: number;
  ctr_decay_rate_pct?: number;
  active_creatives: number;
  is_oversaturated: boolean;
  avg_roas?: number;
}

export interface NarrativeSaturation {
  narrative_name: string;
  narrative_type: string;
  active_creatives: number;
  purchase_share_pct: number;
  volume_share_pct: number;
  gap_magnitude: number;
  avg_roas: number;
  saturation_level: "oversaturated" | "balanced" | "undersupplied";
}

export type SortDirection = "asc" | "desc";

export interface ApiResponse<T> {
  data?: T;
  error?: string;
}
