-- =============================================================================
-- Migration 001: Extensions and Enums
-- Man Matters Creative Operating System
-- =============================================================================

-- Enable required extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "pg_stat_statements";

-- =============================================================================
-- ENUMS
-- =============================================================================

CREATE TYPE product_category AS ENUM ('hair', 'wellness', 'fitness');

CREATE TYPE creative_status AS ENUM (
    'active', 'paused', 'deleted', 'archived', 'draft'
);

CREATE TYPE media_type AS ENUM ('image', 'video', 'carousel');

CREATE TYPE creative_format AS ENUM (
    'reel', 'static', 'carousel', 'story', 'collection',
    'instant_experience', 'playable'
);

CREATE TYPE analysis_status AS ENUM (
    'pending', 'processing', 'completed', 'failed', 'skipped'
);

CREATE TYPE fatigue_stage AS ENUM (
    'insufficient_data', 'healthy', 'watch', 'fatiguing', 'fatigued'
);

CREATE TYPE insight_type AS ENUM (
    'fatigue_alert', 'opportunity', 'narrative_learning', 'performance_anomaly',
    'saturation_warning', 'budget_recommendation', 'creative_gap',
    'winner_pattern', 'loser_pattern', 'competitive_threat'
);

CREATE TYPE insight_priority AS ENUM ('critical', 'high', 'medium', 'low');

CREATE TYPE action_type AS ENUM (
    'create_creative', 'pause_creative', 'reallocate_budget',
    'test_narrative', 'scale_winner', 'refresh_creative', 'monitor'
);

CREATE TYPE recommendation AS ENUM (
    'launch_immediately', 'launch_with_caution', 'test', 'iterate', 'avoid'
);

CREATE TYPE sync_type AS ENUM ('meta_api', 'csv_upload', 'manual', 'competitor_scrape');

CREATE TYPE sync_status AS ENUM ('running', 'completed', 'failed', 'partial');

CREATE TYPE source AS ENUM ('meta', 'csv', 'manual', 'competitor');

CREATE TYPE gap_type AS ENUM ('narrative', 'format', 'hook', 'archetype', 'creator_type');

CREATE TYPE hook_type AS ENUM (
    'authority', 'problem', 'curiosity', 'social_proof', 'question',
    'statistic', 'shock', 'transformation', 'urgency', 'relatability',
    'myth_bust', 'challenge', 'announcement', 'comparison'
);

CREATE TYPE visual_style AS ENUM (
    'talking_head', 'product_demo', 'lifestyle', 'animation',
    'screen_recording', 'text_only', 'split_screen', 'voiceover_broll',
    'interview', 'documentary', 'meme'
);

CREATE TYPE creator_type AS ENUM (
    'doctor', 'customer', 'founder', 'actor', 'influencer',
    'expert', 'celebrity', 'animated', 'none'
);

CREATE TYPE production_quality AS ENUM (
    'professional', 'semi_professional', 'ugc'
);

CREATE TYPE funnel_stage AS ENUM (
    'awareness', 'consideration', 'conversion', 'retention'
);

CREATE TYPE emotional_trigger AS ENUM (
    'fear', 'aspiration', 'trust', 'curiosity', 'urgency',
    'pride', 'guilt', 'excitement', 'nostalgia', 'social_approval'
);

CREATE TYPE offer_type AS ENUM (
    'none', 'discount', 'bundle', 'free_shipping', 'trial',
    'buy_one_get_one', 'gift_with_purchase', 'subscription'
);

CREATE TYPE visibility_level AS ENUM ('high', 'medium', 'low', 'none');

CREATE TYPE attribution_window AS ENUM (
    '1d_click', '7d_click', '28d_click', '1d_view', '7d_view'
);

CREATE TYPE narrative_type AS ENUM (
    'myth_busting', 'expert_recommendation', 'doctor_recommendation',
    'product_demo', 'before_after', 'ugc', 'testimonial', 'educational',
    'comparison', 'problem_solution', 'founder_story', 'transformation_story',
    'authority_based', 'social_proof', 'lifestyle', 'humour', 'challenge',
    'news_jacking', 'seasonal', 'other'
);
