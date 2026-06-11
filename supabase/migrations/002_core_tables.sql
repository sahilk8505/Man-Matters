-- =============================================================================
-- Migration 002: Core Tables
-- =============================================================================

-- updated_at trigger function
CREATE OR REPLACE FUNCTION trigger_set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- PRODUCTS
-- =============================================================================

CREATE TABLE products (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) NOT NULL,
    slug        VARCHAR(100) UNIQUE NOT NULL,
    category    product_category NOT NULL,
    description TEXT,
    is_active   BOOLEAN DEFAULT TRUE,
    sort_order  SMALLINT DEFAULT 0,
    created_at  TIMESTAMPTZ DEFAULT NOW(),
    updated_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TRIGGER set_products_updated_at
    BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
-- META AD ACCOUNTS
-- =============================================================================

CREATE TABLE meta_accounts (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    account_id      VARCHAR(100) UNIQUE NOT NULL,
    account_name    VARCHAR(255),
    currency        VARCHAR(10) DEFAULT 'INR',
    timezone        VARCHAR(50) DEFAULT 'Asia/Kolkata',
    business_id     VARCHAR(100),
    is_active       BOOLEAN DEFAULT TRUE,
    last_synced_at  TIMESTAMPTZ,
    access_token    TEXT, -- stored encrypted in practice
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- TAXONOMY TABLES
-- =============================================================================

CREATE TABLE narratives (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(255) UNIQUE NOT NULL,
    slug                VARCHAR(100) UNIQUE NOT NULL,
    description         TEXT,
    narrative_type      narrative_type,
    is_auto_discovered  BOOLEAN DEFAULT FALSE,
    example_hook        TEXT,
    created_at          TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE hooks (
    id          UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name        VARCHAR(255) UNIQUE NOT NULL,
    slug        VARCHAR(100) UNIQUE NOT NULL,
    description TEXT,
    hook_type   hook_type,
    example     TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE formats (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            VARCHAR(100) UNIQUE NOT NULL,
    slug            VARCHAR(50) UNIQUE NOT NULL,
    format_type     creative_format NOT NULL,
    -- Which metrics matter most for this format
    primary_metrics TEXT[] DEFAULT ARRAY['ctr','cpc','cpm'],
    -- Video-specific weight overrides
    uses_video_metrics  BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE archetypes (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name                VARCHAR(255) UNIQUE NOT NULL,
    slug                VARCHAR(100) UNIQUE NOT NULL,
    description         TEXT,
    typical_hook_type   hook_type,
    typical_narrative   narrative_type,
    typical_format      creative_format,
    typical_creator     creator_type,
    is_auto_discovered  BOOLEAN DEFAULT FALSE,
    cluster_id          INTEGER,
    centroid_embedding  vector(768),
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- CREATIVES (master table)
-- =============================================================================

CREATE TABLE creatives (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    product_id      UUID NOT NULL REFERENCES products(id),
    meta_ad_id      VARCHAR(100) UNIQUE,
    meta_campaign_id    VARCHAR(100),
    meta_adset_id       VARCHAR(100),
    meta_account_id     VARCHAR(100),
    meta_creative_id    VARCHAR(100),

    -- Taxonomy (populated by AI analysis)
    format_id       UUID REFERENCES formats(id),
    narrative_id    UUID REFERENCES narratives(id),
    hook_id         UUID REFERENCES hooks(id),
    archetype_id    UUID REFERENCES archetypes(id),

    -- Display
    name            VARCHAR(500),
    status          creative_status DEFAULT 'active',

    -- Media
    media_type          media_type,
    media_url           TEXT,   -- Original URL (Meta CDN)
    storage_url         TEXT,   -- Supabase Storage URL (persistent)
    thumbnail_url       TEXT,
    duration_seconds    INTEGER,
    aspect_ratio        VARCHAR(20),
    width_px            INTEGER,
    height_px           INTEGER,

    -- Ad copy
    headline        TEXT,
    body_text       TEXT,
    cta_type        VARCHAR(100),
    destination_url TEXT,

    -- Lifecycle tracking
    launch_date                     DATE,
    peak_performance_date           DATE,
    fatigue_start_date              DATE,
    fatigue_acceleration_date       DATE,
    death_date                      DATE,
    days_to_peak                    INTEGER,

    -- Analysis
    analysis_status analysis_status DEFAULT 'pending',
    analyzed_at     TIMESTAMPTZ,
    analysis_error  TEXT,

    -- Data source
    source          source DEFAULT 'meta',

    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_creatives_product ON creatives(product_id);
CREATE INDEX idx_creatives_status ON creatives(status);
CREATE INDEX idx_creatives_meta_ad ON creatives(meta_ad_id);
CREATE INDEX idx_creatives_analysis_status ON creatives(analysis_status);
CREATE INDEX idx_creatives_launch_date ON creatives(launch_date);

CREATE TRIGGER set_creatives_updated_at
    BEFORE UPDATE ON creatives
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
-- CREATIVE METADATA (AI-extracted attributes)
-- =============================================================================

CREATE TABLE creative_metadata (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creative_id     UUID UNIQUE NOT NULL REFERENCES creatives(id) ON DELETE CASCADE,

    -- Narrative & Story
    narrative_type          narrative_type,
    story_structure         VARCHAR(100), -- linear, problem_solution, before_after, hero_journey
    marketing_angle         VARCHAR(100),
    stage_of_funnel         funnel_stage,
    content_category        VARCHAR(100),

    -- Hook Analysis
    hook_type               hook_type,
    hook_text               TEXT,           -- exact hook opening line/phrase
    hook_duration_seconds   FLOAT,

    -- Format & Visual
    visual_style            visual_style,
    production_quality      production_quality,

    -- Creator
    creator_type            creator_type,
    ugc_type                VARCHAR(100), -- selfie, scripted, candid, talking_head
    human_presence          BOOLEAN,

    -- Offer & CTA
    offer_type              offer_type DEFAULT 'none',
    discount_percentage     FLOAT,
    price_mentioned         BOOLEAN DEFAULT FALSE,
    cta_text                VARCHAR(255),

    -- Emotional & Psychological
    emotional_trigger       emotional_trigger,
    pain_point              TEXT,
    benefit_claimed         TEXT,
    objection_handled       TEXT,

    -- Trust & Authority
    trust_signal            VARCHAR(100),  -- doctor, review, award, ingredient, clinical_study, before_after
    authority_figure        VARCHAR(100),

    -- Product & Brand
    product_visibility      visibility_level DEFAULT 'medium',
    brand_visibility        visibility_level DEFAULT 'medium',

    -- Visual
    color_theme             VARCHAR(100),
    has_captions            BOOLEAN,
    has_music               BOOLEAN,

    -- Audience & Intent
    audience_intent         VARCHAR(100),
    target_pain_keywords    TEXT[],

    -- AI Confidence
    analysis_confidence     FLOAT,
    gemini_model_version    VARCHAR(50),
    raw_gemini_response     JSONB,

    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_creative_metadata_narrative ON creative_metadata(narrative_type);
CREATE INDEX idx_creative_metadata_hook ON creative_metadata(hook_type);
CREATE INDEX idx_creative_metadata_creator ON creative_metadata(creator_type);
CREATE INDEX idx_creative_metadata_funnel ON creative_metadata(stage_of_funnel);

CREATE TRIGGER set_creative_metadata_updated_at
    BEFORE UPDATE ON creative_metadata
    FOR EACH ROW EXECUTE FUNCTION trigger_set_updated_at();

-- =============================================================================
-- CREATIVE EMBEDDINGS (pgvector)
-- =============================================================================

CREATE TABLE creative_embeddings (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    creative_id         UUID UNIQUE NOT NULL REFERENCES creatives(id) ON DELETE CASCADE,

    -- Composite embedding from: narrative + hook + visual + offer descriptions
    embedding           vector(768) NOT NULL,

    -- Component-level embeddings for fine-grained similarity
    narrative_embedding vector(768),
    hook_embedding      vector(768),
    visual_embedding    vector(768),
    offer_embedding     vector(768),

    -- Metadata
    model_version       VARCHAR(50) DEFAULT 'text-embedding-004',
    input_text          TEXT, -- what was embedded (for debugging)
    created_at          TIMESTAMPTZ DEFAULT NOW(),
    updated_at          TIMESTAMPTZ DEFAULT NOW()
);

-- IVFFlat index for fast ANN search (cosine distance)
CREATE INDEX idx_creative_emb_cosine ON creative_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

CREATE INDEX idx_creative_emb_narrative ON creative_embeddings
    USING ivfflat (narrative_embedding vector_cosine_ops) WITH (lists = 50);

-- =============================================================================
-- COMPETITOR CREATIVES
-- =============================================================================

CREATE TABLE competitor_creatives (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),

    competitor_name         VARCHAR(255) NOT NULL,
    competitor_page_id      VARCHAR(100),
    competitor_page_name    VARCHAR(255),

    -- Meta Ad Library data
    meta_ad_id              VARCHAR(100) UNIQUE,
    ad_archive_url          TEXT,

    -- Media
    media_type              media_type,
    media_url               TEXT,
    storage_url             TEXT,
    thumbnail_url           TEXT,
    duration_seconds        INTEGER,
    aspect_ratio            VARCHAR(20),

    -- Content
    headline                TEXT,
    body_text               TEXT,
    cta_type                VARCHAR(100),
    destination_url         TEXT,

    -- Lifecycle (from Ad Library)
    first_seen_date         DATE,
    last_seen_date          DATE,
    estimated_lifespan_days INTEGER,
    is_active               BOOLEAN DEFAULT TRUE,

    -- AI Analysis (same dimensions as own creatives)
    narrative_type          narrative_type,
    hook_type               hook_type,
    visual_style            visual_style,
    offer_type              offer_type,
    creator_type            creator_type,
    emotional_trigger       emotional_trigger,
    funnel_stage            funnel_stage,
    story_structure         VARCHAR(100),
    trust_signal            VARCHAR(100),
    human_presence          BOOLEAN,

    -- Analysis
    analysis_status         analysis_status DEFAULT 'pending',
    analyzed_at             TIMESTAMPTZ,
    raw_gemini_response     JSONB,

    created_at              TIMESTAMPTZ DEFAULT NOW(),
    updated_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitor_name ON competitor_creatives(competitor_name);
CREATE INDEX idx_competitor_first_seen ON competitor_creatives(first_seen_date);
CREATE INDEX idx_competitor_narrative ON competitor_creatives(narrative_type);
CREATE INDEX idx_competitor_active ON competitor_creatives(is_active);

CREATE TABLE competitor_embeddings (
    id                      UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    competitor_creative_id  UUID UNIQUE NOT NULL REFERENCES competitor_creatives(id) ON DELETE CASCADE,
    embedding               vector(768) NOT NULL,
    model_version           VARCHAR(50) DEFAULT 'text-embedding-004',
    created_at              TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_competitor_emb ON competitor_embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 50);

-- =============================================================================
-- SYNC LOGS
-- =============================================================================

CREATE TABLE sync_logs (
    id                  UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    sync_type           sync_type NOT NULL,
    status              sync_status DEFAULT 'running',
    account_id          VARCHAR(100),
    date_range_start    DATE,
    date_range_end      DATE,
    records_fetched     INTEGER DEFAULT 0,
    records_processed   INTEGER DEFAULT 0,
    records_failed      INTEGER DEFAULT 0,
    error_message       TEXT,
    meta                JSONB DEFAULT '{}',
    started_at          TIMESTAMPTZ DEFAULT NOW(),
    completed_at        TIMESTAMPTZ
);
