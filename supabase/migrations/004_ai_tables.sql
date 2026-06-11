-- =============================================================================
-- Migration 004: AI Tables (Predictions, Clusters, Insights)
-- =============================================================================

-- =============================================================================
-- CREATIVE PREDICTIONS (pre-launch scoring)
-- =============================================================================

CREATE TABLE creative_predictions (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creative_id     UUID NOT NULL REFERENCES creatives(id) ON DELETE CASCADE,
    product_id      UUID NOT NULL REFERENCES products(id),

    -- Composite scores (0-100)
    creative_success_score  NUMERIC(5, 2),
    narrative_score         NUMERIC(5, 2),
    hook_score              NUMERIC(5, 2),
    visual_score            NUMERIC(5, 2),
    offer_score             NUMERIC(5, 2),
    novelty_score           NUMERIC(5, 2),
    launch_confidence_score NUMERIC(5, 2),

    -- Risk
    fatigue_risk_score      NUMERIC(5, 2),  -- higher = more risk

    -- Similarity analysis
    winner_similarity_pct   NUMERIC(5, 2),
    loser_similarity_pct    NUMERIC(5, 2),

    -- Predicted metrics
    predicted_ctr           NUMERIC(8, 6),
    predicted_cpa           NUMERIC(10, 4),
    predicted_roas          NUMERIC(8, 4),
    predicted_lifespan_days INTEGER,

    -- Recommendation
    recommendation          recommendation,
    recommendation_reason   TEXT,

    -- Evidence
    similar_winner_ids      UUID[] DEFAULT '{}',
    similar_loser_ids       UUID[] DEFAULT '{}',
    comparable_narratives   TEXT[],
    risk_factors            TEXT[],
    opportunity_factors     TEXT[],

    -- Model metadata
    model_version           VARCHAR(50),
    prediction_confidence   NUMERIC(4, 3),

    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_predictions_creative ON creative_predictions(creative_id);
CREATE INDEX idx_predictions_score ON creative_predictions(creative_success_score DESC);

-- =============================================================================
-- CREATIVE CLUSTERS (embedding-based clustering)
-- =============================================================================

CREATE TABLE creative_clusters (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    cluster_label           VARCHAR(255) NOT NULL,
    cluster_description     TEXT,
    product_id              UUID REFERENCES products(id),  -- null = cross-product

    -- Dominant characteristics
    dominant_narrative      narrative_type,
    dominant_format         creative_format,
    dominant_hook           hook_type,
    dominant_creator_type   creator_type,
    dominant_visual_style   visual_style,

    -- Performance summary
    avg_ctr                 NUMERIC(8, 6),
    avg_cpa                 NUMERIC(10, 4),
    avg_roas                NUMERIC(8, 4),
    avg_lifespan_days       NUMERIC(6, 2),
    creative_count          INTEGER DEFAULT 0,
    winner_count            INTEGER DEFAULT 0,

    -- Cluster geometry
    centroid_embedding      vector(768),
    intra_cluster_distance  NUMERIC(6, 4),

    -- Algorithm metadata
    algorithm               VARCHAR(50) DEFAULT 'kmeans',
    cluster_run_id          UUID,

    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE creative_cluster_assignments (
    creative_id             UUID NOT NULL REFERENCES creatives(id) ON DELETE CASCADE,
    cluster_id              UUID NOT NULL REFERENCES creative_clusters(id) ON DELETE CASCADE,
    distance_from_centroid  NUMERIC(8, 6),
    assigned_at             TIMESTAMPTZ DEFAULT NOW(),
    PRIMARY KEY (creative_id, cluster_id)
);

-- =============================================================================
-- AI-GENERATED INSIGHTS
-- =============================================================================

CREATE TABLE insights (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    -- Scope
    product_id      UUID REFERENCES products(id),  -- null = global insight
    creative_id     UUID REFERENCES creatives(id),
    narrative_id    UUID REFERENCES narratives(id),

    -- Classification
    insight_type    insight_type NOT NULL,
    priority        insight_priority DEFAULT 'medium',

    -- Content
    title           VARCHAR(500) NOT NULL,
    body            TEXT NOT NULL,
    data            JSONB DEFAULT '{}',  -- supporting metrics/evidence

    -- Action
    recommended_action  TEXT,
    action_type         action_type,

    -- Lifecycle
    is_read             BOOLEAN DEFAULT FALSE,
    is_actioned         BOOLEAN DEFAULT FALSE,
    is_dismissed        BOOLEAN DEFAULT FALSE,
    valid_until         TIMESTAMPTZ,

    -- Generation metadata
    generated_by        VARCHAR(100) DEFAULT 'gemini-2.5-pro',
    generation_prompt   TEXT,

    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_insights_product ON insights(product_id, created_at DESC);
CREATE INDEX idx_insights_unread ON insights(is_read, priority) WHERE NOT is_read AND NOT is_dismissed;
CREATE INDEX idx_insights_type ON insights(insight_type, created_at DESC);

CREATE TRIGGER set_insights_updated_at
    BEFORE UPDATE ON insights
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
-- USERS (JWT auth)
-- =============================================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email           VARCHAR(255) UNIQUE NOT NULL,
    hashed_password TEXT NOT NULL,
    full_name       VARCHAR(255),
    role            VARCHAR(50) DEFAULT 'analyst',  -- admin, analyst, viewer
    is_active       BOOLEAN DEFAULT TRUE,
    last_login_at   TIMESTAMPTZ,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- UPLOADED FILES (for manual creative uploads)
-- =============================================================================

CREATE TABLE uploaded_files (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    original_name   VARCHAR(500),
    storage_path    TEXT NOT NULL,
    storage_url     TEXT NOT NULL,
    mime_type       VARCHAR(100),
    file_size_bytes BIGINT,
    uploaded_by     UUID REFERENCES users(id),
    creative_id     UUID REFERENCES creatives(id),
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- PRODUCT BENCHMARKS (rolling window benchmarks per product)
-- =============================================================================

CREATE TABLE product_benchmarks (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL REFERENCES products(id),
    period_days     INTEGER DEFAULT 30,  -- rolling window

    -- Benchmarks (median values across active creatives in window)
    median_ctr          NUMERIC(8, 6),
    median_cpc          NUMERIC(10, 4),
    median_cpm          NUMERIC(10, 4),
    median_cpa          NUMERIC(10, 4),
    median_roas         NUMERIC(8, 4),
    median_hook_rate    NUMERIC(8, 6),
    median_hold_rate    NUMERIC(8, 6),
    median_frequency    NUMERIC(8, 4),
    median_lifespan     NUMERIC(6, 2),

    -- Winner thresholds (top 25%)
    winner_ctr_threshold    NUMERIC(8, 6),
    winner_roas_threshold   NUMERIC(8, 4),
    winner_cpa_threshold    NUMERIC(10, 4),

    -- Loser thresholds (bottom 25%)
    loser_ctr_threshold     NUMERIC(8, 6),
    loser_roas_threshold    NUMERIC(8, 4),
    loser_cpa_threshold     NUMERIC(10, 4),

    calculated_at   TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(product_id, period_days)
);
