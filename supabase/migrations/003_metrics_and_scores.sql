-- =============================================================================
-- Migration 003: Metrics, Fatigue Scores, Performance Tables
-- =============================================================================

-- =============================================================================
-- CREATIVE DAILY METRICS
-- =============================================================================

CREATE TABLE creative_daily_metrics (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creative_id     UUID NOT NULL REFERENCES creatives(id) ON DELETE CASCADE,
    product_id      UUID NOT NULL REFERENCES products(id),
    date            DATE NOT NULL,

    -- Spend & Delivery
    spend               NUMERIC(14, 4) DEFAULT 0,
    impressions         INTEGER DEFAULT 0,
    reach               INTEGER DEFAULT 0,
    frequency           NUMERIC(8, 4) DEFAULT 0,

    -- Click Metrics
    clicks              INTEGER DEFAULT 0,
    ctr                 NUMERIC(8, 6) DEFAULT 0,  -- as decimal, e.g. 0.023 = 2.3%
    link_clicks         INTEGER DEFAULT 0,
    link_ctr            NUMERIC(8, 6) DEFAULT 0,
    outbound_clicks     INTEGER DEFAULT 0,
    outbound_ctr        NUMERIC(8, 6) DEFAULT 0,
    cpc                 NUMERIC(10, 4) DEFAULT 0,
    cpp                 NUMERIC(10, 4) DEFAULT 0,  -- cost per 1000 people reached

    -- CPM
    cpm                 NUMERIC(10, 4) DEFAULT 0,

    -- Conversions
    purchases               INTEGER DEFAULT 0,
    purchase_value          NUMERIC(14, 4) DEFAULT 0,
    add_to_cart             INTEGER DEFAULT 0,
    initiate_checkout       INTEGER DEFAULT 0,
    view_content            INTEGER DEFAULT 0,
    cpa                     NUMERIC(10, 4) DEFAULT 0,   -- cost per purchase
    roas                    NUMERIC(8, 4) DEFAULT 0,
    conversion_rate         NUMERIC(8, 6) DEFAULT 0,   -- purchases / link_clicks

    -- Video Metrics
    video_views             INTEGER DEFAULT 0,
    video_avg_watch_pct     NUMERIC(8, 4) DEFAULT 0,   -- 0-100
    video_p25_watched       INTEGER DEFAULT 0,
    video_p50_watched       INTEGER DEFAULT 0,
    video_p75_watched       INTEGER DEFAULT 0,
    video_p95_watched       INTEGER DEFAULT 0,
    video_p100_watched      INTEGER DEFAULT 0,
    three_sec_video_views   INTEGER DEFAULT 0,

    -- Calculated Video KPIs
    hook_rate           NUMERIC(8, 6) DEFAULT 0,   -- 3sec_views / impressions
    hold_rate           NUMERIC(8, 6) DEFAULT 0,   -- p75 / p25
    thumb_stop_rate     NUMERIC(8, 6) DEFAULT 0,   -- 3sec_views / impressions (alias)

    -- Attribution
    attribution_window  attribution_window DEFAULT '7d_click',

    -- Engagement
    post_engagements    INTEGER DEFAULT 0,
    post_reactions      INTEGER DEFAULT 0,
    post_shares         INTEGER DEFAULT 0,
    post_comments       INTEGER DEFAULT 0,

    created_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(creative_id, date, attribution_window)
);

CREATE INDEX idx_daily_metrics_creative_date ON creative_daily_metrics(creative_id, date DESC);
CREATE INDEX idx_daily_metrics_product_date ON creative_daily_metrics(product_id, date DESC);
CREATE INDEX idx_daily_metrics_date ON creative_daily_metrics(date DESC);

-- =============================================================================
-- FATIGUE SCORES (calculated daily per creative)
-- =============================================================================

CREATE TABLE fatigue_scores (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creative_id             UUID NOT NULL REFERENCES creatives(id) ON DELETE CASCADE,
    product_id              UUID NOT NULL REFERENCES products(id),
    calculated_date         DATE NOT NULL,

    -- Primary Score
    fatigue_score           NUMERIC(5, 2) NOT NULL DEFAULT 0,  -- 0-100
    fatigue_stage           fatigue_stage NOT NULL DEFAULT 'healthy',

    -- Component Scores (each 0-100)
    ctr_decay_score         NUMERIC(5, 2) DEFAULT 0,
    cpc_inflation_score     NUMERIC(5, 2) DEFAULT 0,
    cpm_inflation_score     NUMERIC(5, 2) DEFAULT 0,
    cpa_inflation_score     NUMERIC(5, 2) DEFAULT 0,
    roas_decay_score        NUMERIC(5, 2) DEFAULT 0,
    hook_decay_score        NUMERIC(5, 2) DEFAULT 0,
    hold_decay_score        NUMERIC(5, 2) DEFAULT 0,
    frequency_score         NUMERIC(5, 2) DEFAULT 0,
    conversion_decay_score  NUMERIC(5, 2) DEFAULT 0,

    -- Lifecycle
    days_since_launch           INTEGER DEFAULT 0,
    days_to_peak                INTEGER,
    expected_remaining_days     INTEGER,
    confidence_score            NUMERIC(4, 3) DEFAULT 0,  -- 0-1

    -- Baselines used for comparison
    baseline_ctr            NUMERIC(8, 6),
    baseline_cpc            NUMERIC(10, 4),
    baseline_cpm            NUMERIC(10, 4),
    baseline_cpa            NUMERIC(10, 4),
    baseline_roas           NUMERIC(8, 4),
    baseline_hook_rate      NUMERIC(8, 6),
    baseline_hold_rate      NUMERIC(8, 6),
    current_frequency       NUMERIC(8, 4),

    created_at              TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(creative_id, calculated_date)
);

CREATE INDEX idx_fatigue_creative ON fatigue_scores(creative_id, calculated_date DESC);
CREATE INDEX idx_fatigue_stage ON fatigue_scores(fatigue_stage, calculated_date DESC);
CREATE INDEX idx_fatigue_score_value ON fatigue_scores(fatigue_score DESC);

-- =============================================================================
-- NARRATIVE PERFORMANCE (per product, recalculated periodically)
-- =============================================================================

CREATE TABLE narrative_performance (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id              UUID NOT NULL REFERENCES products(id),
    narrative_id            UUID NOT NULL REFERENCES narratives(id),

    -- Volume
    total_creatives         INTEGER DEFAULT 0,
    active_creatives        INTEGER DEFAULT 0,
    winner_count            INTEGER DEFAULT 0,  -- top 25% by ROAS
    loser_count             INTEGER DEFAULT 0,  -- bottom 25% by ROAS

    -- Aggregated Performance
    avg_ctr                 NUMERIC(8, 6),
    avg_cpc                 NUMERIC(10, 4),
    avg_cpa                 NUMERIC(10, 4),
    avg_roas                NUMERIC(8, 4),
    avg_hook_rate           NUMERIC(8, 6),
    avg_hold_rate           NUMERIC(8, 6),
    avg_thumb_stop_rate     NUMERIC(8, 6),
    total_spend             NUMERIC(14, 4),
    total_purchases         INTEGER,
    total_purchase_value    NUMERIC(14, 4),

    -- Fatigue Profile
    avg_lifespan_days       NUMERIC(6, 2),
    median_lifespan_days    NUMERIC(6, 2),
    avg_peak_day            NUMERIC(6, 2),
    avg_fatigue_start_day   NUMERIC(6, 2),
    max_frequency_at_fatigue NUMERIC(8, 4),

    -- Decay Rates (% per day)
    ctr_decay_rate_pct      NUMERIC(8, 4),
    cpa_increase_rate_pct   NUMERIC(8, 4),
    roas_decay_rate_pct     NUMERIC(8, 4),

    -- Saturation Status
    is_oversaturated        BOOLEAN DEFAULT FALSE,
    saturation_score        NUMERIC(5, 2) DEFAULT 0,  -- 0-100

    -- Share of spend/purchases
    spend_share_pct         NUMERIC(6, 3),
    purchase_share_pct      NUMERIC(6, 3),
    volume_share_pct        NUMERIC(6, 3),

    last_calculated_at      TIMESTAMPTZ,
    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(product_id, narrative_id)
);

CREATE TRIGGER set_narrative_perf_updated_at
    BEFORE UPDATE ON narrative_performance
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
-- FORMAT PERFORMANCE (per product)
-- =============================================================================

CREATE TABLE format_performance (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id          UUID NOT NULL REFERENCES products(id),
    format_id           UUID NOT NULL REFERENCES formats(id),

    total_creatives     INTEGER DEFAULT 0,
    active_creatives    INTEGER DEFAULT 0,

    avg_ctr             NUMERIC(8, 6),
    avg_cpc             NUMERIC(10, 4),
    avg_cpa             NUMERIC(10, 4),
    avg_roas            NUMERIC(8, 4),
    avg_lifespan_days   NUMERIC(6, 2),
    avg_hook_rate       NUMERIC(8, 6),
    avg_hold_rate       NUMERIC(8, 6),

    -- Benchmarks (percentiles across all creatives for this format+product)
    benchmark_ctr_p25   NUMERIC(8, 6),
    benchmark_ctr_p50   NUMERIC(8, 6),
    benchmark_ctr_p75   NUMERIC(8, 6),
    benchmark_cpc_p25   NUMERIC(10, 4),
    benchmark_cpc_p50   NUMERIC(10, 4),
    benchmark_cpc_p75   NUMERIC(10, 4),
    benchmark_cpm_p25   NUMERIC(10, 4),
    benchmark_cpm_p50   NUMERIC(10, 4),
    benchmark_cpm_p75   NUMERIC(10, 4),
    benchmark_roas_p25  NUMERIC(8, 4),
    benchmark_roas_p50  NUMERIC(8, 4),
    benchmark_roas_p75  NUMERIC(8, 4),

    last_calculated_at  TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(product_id, format_id)
);

-- =============================================================================
-- ARCHETYPE PERFORMANCE (per product)
-- =============================================================================

CREATE TABLE archetype_performance (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id          UUID NOT NULL REFERENCES products(id),
    archetype_id        UUID NOT NULL REFERENCES archetypes(id),

    total_creatives     INTEGER DEFAULT 0,
    active_creatives    INTEGER DEFAULT 0,

    avg_ctr             NUMERIC(8, 6),
    avg_cpa             NUMERIC(10, 4),
    avg_roas            NUMERIC(8, 4),
    avg_lifespan_days   NUMERIC(6, 2),
    avg_fatigue_rate    NUMERIC(8, 4),
    win_rate            NUMERIC(5, 3),  -- % that became top performers

    last_calculated_at  TIMESTAMPTZ,
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(product_id, archetype_id)
);

-- =============================================================================
-- CREATIVE GENOME PATTERNS
-- =============================================================================

CREATE TABLE genome_patterns (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Pattern dimensions (NULL = not specified / any)
    hook_type       hook_type,
    narrative_type  narrative_type,
    format_type     creative_format,
    creator_type    creator_type,
    offer_type      offer_type,
    visual_style    visual_style,
    trust_signal    VARCHAR(100),
    funnel_stage    funnel_stage,

    -- Fingerprint for deduplication
    pattern_hash    VARCHAR(64) UNIQUE NOT NULL,

    -- Scope (null = cross-product)
    product_id      UUID REFERENCES products(id),

    -- Performance
    total_creatives INTEGER DEFAULT 0,
    avg_ctr         NUMERIC(8, 6),
    avg_cpa         NUMERIC(10, 4),
    avg_roas        NUMERIC(8, 4),
    avg_lifespan_days NUMERIC(6, 2),
    avg_fatigue_days  NUMERIC(6, 2),
    win_rate        NUMERIC(5, 3),
    total_spend     NUMERIC(14, 4),
    total_purchases INTEGER,

    last_calculated_at TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_genome_product ON genome_patterns(product_id);
CREATE INDEX idx_genome_roas ON genome_patterns(avg_roas DESC NULLS LAST);
CREATE INDEX idx_genome_win_rate ON genome_patterns(win_rate DESC NULLS LAST);

-- =============================================================================
-- CREATIVE GAP ANALYSIS (cached results)
-- =============================================================================

CREATE TABLE creative_gaps (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id          UUID NOT NULL REFERENCES products(id),
    gap_type            gap_type NOT NULL,
    gap_value           VARCHAR(255) NOT NULL,

    -- Why it's a gap
    purchase_contribution_pct   NUMERIC(6, 3),
    volume_share_pct            NUMERIC(6, 3),
    gap_magnitude               NUMERIC(6, 3),  -- purchase% - volume%

    -- Performance of this gap category
    avg_ctr             NUMERIC(8, 6),
    avg_cpa             NUMERIC(10, 4),
    avg_roas            NUMERIC(8, 4),

    -- Active creative count in this gap
    active_count        INTEGER DEFAULT 0,

    recommendation      TEXT,
    priority            insight_priority DEFAULT 'medium',

    calculated_at       TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(product_id, gap_type, gap_value)
);
