-- =============================================================================
-- Migration 005: Functions and Views
-- =============================================================================

-- =============================================================================
-- SIMILARITY SEARCH FUNCTIONS
-- =============================================================================

-- Find most similar creatives by full embedding
CREATE OR REPLACE FUNCTION find_similar_creatives(
    query_embedding vector(768),
    product_filter  UUID DEFAULT NULL,
    limit_count     INTEGER DEFAULT 10,
    exclude_id      UUID DEFAULT NULL
)
RETURNS TABLE (
    creative_id         UUID,
    name                VARCHAR,
    product_id          UUID,
    similarity          FLOAT,
    narrative_type      narrative_type,
    hook_type           hook_type,
    avg_roas            FLOAT,
    is_winner           BOOLEAN
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        c.id AS creative_id,
        c.name,
        c.product_id,
        1 - (ce.embedding <=> query_embedding) AS similarity,
        cm.narrative_type,
        cm.hook_type,
        COALESCE(
            (SELECT AVG(m.roas)
             FROM creative_daily_metrics m
             WHERE m.creative_id = c.id
               AND m.roas > 0
               AND m.spend > 100),
            0
        )::FLOAT AS avg_roas,
        COALESCE(
            (SELECT AVG(m.roas) > (
                SELECT pb.winner_roas_threshold
                FROM product_benchmarks pb
                WHERE pb.product_id = c.product_id
                LIMIT 1
            )
            FROM creative_daily_metrics m
            WHERE m.creative_id = c.id
              AND m.roas > 0),
            FALSE
        ) AS is_winner
    FROM creative_embeddings ce
    JOIN creatives c ON c.id = ce.creative_id
    LEFT JOIN creative_metadata cm ON cm.creative_id = c.id
    WHERE
        (product_filter IS NULL OR c.product_id = product_filter)
        AND (exclude_id IS NULL OR c.id != exclude_id)
        AND c.status != 'deleted'
    ORDER BY ce.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- Find similar competitor creatives
CREATE OR REPLACE FUNCTION find_similar_competitors(
    query_embedding vector(768),
    limit_count     INTEGER DEFAULT 10
)
RETURNS TABLE (
    competitor_creative_id  UUID,
    competitor_name         VARCHAR,
    similarity              FLOAT,
    narrative_type          narrative_type,
    hook_type               hook_type,
    first_seen_date         DATE,
    estimated_lifespan_days INTEGER
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        cc.id AS competitor_creative_id,
        cc.competitor_name,
        1 - (ce.embedding <=> query_embedding) AS similarity,
        cc.narrative_type,
        cc.hook_type,
        cc.first_seen_date,
        cc.estimated_lifespan_days
    FROM competitor_embeddings ce
    JOIN competitor_creatives cc ON cc.id = ce.competitor_creative_id
    ORDER BY ce.embedding <=> query_embedding
    LIMIT limit_count;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- FATIGUE CALCULATION FUNCTION
-- =============================================================================

-- Get time-series data needed for fatigue calculation
CREATE OR REPLACE FUNCTION get_fatigue_input(p_creative_id UUID, p_days INTEGER DEFAULT 30)
RETURNS TABLE (
    date            DATE,
    ctr             FLOAT,
    link_ctr        FLOAT,
    cpc             FLOAT,
    cpm             FLOAT,
    cpa             FLOAT,
    roas            FLOAT,
    hook_rate       FLOAT,
    hold_rate       FLOAT,
    thumb_stop_rate FLOAT,
    frequency       FLOAT,
    spend           FLOAT,
    purchases       INTEGER,
    conversion_rate FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT
        m.date,
        m.ctr::FLOAT,
        m.link_ctr::FLOAT,
        m.cpc::FLOAT,
        m.cpm::FLOAT,
        m.cpa::FLOAT,
        m.roas::FLOAT,
        m.hook_rate::FLOAT,
        m.hold_rate::FLOAT,
        m.thumb_stop_rate::FLOAT,
        m.frequency::FLOAT,
        m.spend::FLOAT,
        m.purchases,
        m.conversion_rate::FLOAT
    FROM creative_daily_metrics m
    WHERE m.creative_id = p_creative_id
      AND m.date >= CURRENT_DATE - p_days
      AND m.attribution_window = '7d_click'
    ORDER BY m.date ASC;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- NARRATIVE SATURATION FUNCTION
-- =============================================================================

CREATE OR REPLACE FUNCTION get_narrative_saturation(p_product_id UUID)
RETURNS TABLE (
    narrative_name          VARCHAR,
    narrative_type          narrative_type,
    active_creatives        INTEGER,
    purchase_share_pct      FLOAT,
    volume_share_pct        FLOAT,
    gap_magnitude           FLOAT,
    avg_roas                FLOAT,
    saturation_level        TEXT  -- 'oversaturated', 'balanced', 'undersupplied'
) AS $$
BEGIN
    RETURN QUERY
    WITH narrative_stats AS (
        SELECT
            n.name AS narrative_name,
            cm.narrative_type,
            COUNT(DISTINCT c.id)::INTEGER AS active_count,
            COALESCE(SUM(m.purchases), 0) AS total_purchases,
            COALESCE(SUM(m.spend), 0) AS total_spend,
            COALESCE(AVG(NULLIF(m.roas, 0)), 0) AS avg_roas
        FROM creatives c
        JOIN creative_metadata cm ON cm.creative_id = c.id
        JOIN narratives n ON n.narrative_type = cm.narrative_type
        LEFT JOIN creative_daily_metrics m ON m.creative_id = c.id
            AND m.date >= CURRENT_DATE - 30
            AND m.attribution_window = '7d_click'
        WHERE c.product_id = p_product_id
          AND c.status = 'active'
          AND cm.narrative_type IS NOT NULL
        GROUP BY n.name, cm.narrative_type
    ),
    totals AS (
        SELECT
            SUM(total_purchases) AS grand_purchases,
            SUM(active_count) AS grand_count
        FROM narrative_stats
    )
    SELECT
        ns.narrative_name,
        ns.narrative_type,
        ns.active_count AS active_creatives,
        CASE WHEN t.grand_purchases > 0
            THEN (ns.total_purchases * 100.0 / t.grand_purchases)::FLOAT
            ELSE 0
        END AS purchase_share_pct,
        CASE WHEN t.grand_count > 0
            THEN (ns.active_count * 100.0 / t.grand_count)::FLOAT
            ELSE 0
        END AS volume_share_pct,
        CASE WHEN t.grand_purchases > 0 AND t.grand_count > 0
            THEN ((ns.total_purchases * 100.0 / t.grand_purchases) -
                  (ns.active_count * 100.0 / t.grand_count))::FLOAT
            ELSE 0
        END AS gap_magnitude,
        ns.avg_roas::FLOAT,
        CASE
            WHEN t.grand_count > 0 AND (ns.active_count * 100.0 / t.grand_count) > 30 THEN 'oversaturated'
            WHEN t.grand_purchases > 0 AND t.grand_count > 0
                 AND ((ns.total_purchases * 100.0 / t.grand_purchases) -
                      (ns.active_count * 100.0 / t.grand_count)) > 10 THEN 'undersupplied'
            ELSE 'balanced'
        END AS saturation_level
    FROM narrative_stats ns
    CROSS JOIN totals t
    ORDER BY gap_magnitude DESC;
END;
$$ LANGUAGE plpgsql;

-- =============================================================================
-- VIEWS
-- =============================================================================

-- Executive summary view (latest fatigue score per creative)
CREATE VIEW v_creative_health AS
SELECT
    c.id,
    c.name,
    c.product_id,
    p.name AS product_name,
    p.category,
    c.status,
    c.media_type,
    c.launch_date,
    cm.narrative_type,
    cm.hook_type,
    cm.creator_type,
    cm.visual_style,
    cm.offer_type,
    cm.stage_of_funnel,
    -- Latest fatigue
    fs.fatigue_score,
    fs.fatigue_stage,
    fs.days_since_launch,
    fs.expected_remaining_days,
    fs.calculated_date AS fatigue_calculated_at,
    -- Last 7-day performance
    (SELECT SUM(m.spend) FROM creative_daily_metrics m
     WHERE m.creative_id = c.id AND m.date >= CURRENT_DATE - 7
       AND m.attribution_window = '7d_click') AS spend_7d,
    (SELECT AVG(m.roas) FROM creative_daily_metrics m
     WHERE m.creative_id = c.id AND m.date >= CURRENT_DATE - 7
       AND m.attribution_window = '7d_click' AND m.roas > 0) AS roas_7d,
    (SELECT AVG(m.ctr) FROM creative_daily_metrics m
     WHERE m.creative_id = c.id AND m.date >= CURRENT_DATE - 7
       AND m.attribution_window = '7d_click' AND m.ctr > 0) AS ctr_7d,
    (SELECT AVG(m.cpa) FROM creative_daily_metrics m
     WHERE m.creative_id = c.id AND m.date >= CURRENT_DATE - 7
       AND m.attribution_window = '7d_click' AND m.cpa > 0) AS cpa_7d,
    (SELECT SUM(m.purchases) FROM creative_daily_metrics m
     WHERE m.creative_id = c.id AND m.date >= CURRENT_DATE - 7
       AND m.attribution_window = '7d_click') AS purchases_7d,
    -- Latest prediction
    pred.creative_success_score,
    pred.launch_confidence_score,
    pred.recommendation
FROM creatives c
JOIN products p ON p.id = c.product_id
LEFT JOIN creative_metadata cm ON cm.creative_id = c.id
LEFT JOIN LATERAL (
    SELECT * FROM fatigue_scores fs
    WHERE fs.creative_id = c.id
    ORDER BY fs.calculated_date DESC
    LIMIT 1
) fs ON TRUE
LEFT JOIN LATERAL (
    SELECT * FROM creative_predictions pred
    WHERE pred.creative_id = c.id
    ORDER BY pred.created_at DESC
    LIMIT 1
) pred ON TRUE
WHERE c.status != 'deleted';

-- Product-level summary
CREATE VIEW v_product_summary AS
SELECT
    p.id,
    p.name,
    p.slug,
    p.category,
    COUNT(DISTINCT c.id) AS total_creatives,
    COUNT(DISTINCT c.id) FILTER (WHERE c.status = 'active') AS active_creatives,
    COUNT(DISTINCT c.id) FILTER (WHERE fs.fatigue_stage IN ('fatiguing', 'fatigued')) AS fatiguing_creatives,
    COUNT(DISTINCT ins.id) FILTER (WHERE NOT ins.is_read AND NOT ins.is_dismissed) AS unread_insights,
    (SELECT AVG(m.roas) FROM creative_daily_metrics m
     JOIN creatives c2 ON c2.id = m.creative_id
     WHERE c2.product_id = p.id AND m.date >= CURRENT_DATE - 7
       AND m.attribution_window = '7d_click' AND m.roas > 0) AS avg_roas_7d,
    (SELECT SUM(m.spend) FROM creative_daily_metrics m
     JOIN creatives c2 ON c2.id = m.creative_id
     WHERE c2.product_id = p.id AND m.date >= CURRENT_DATE - 30
       AND m.attribution_window = '7d_click') AS total_spend_30d,
    (SELECT SUM(m.purchases) FROM creative_daily_metrics m
     JOIN creatives c2 ON c2.id = m.creative_id
     WHERE c2.product_id = p.id AND m.date >= CURRENT_DATE - 30
       AND m.attribution_window = '7d_click') AS total_purchases_30d
FROM products p
LEFT JOIN creatives c ON c.product_id = p.id AND c.status != 'deleted'
LEFT JOIN LATERAL (
    SELECT fs.fatigue_stage FROM fatigue_scores fs
    WHERE fs.creative_id = c.id
    ORDER BY fs.calculated_date DESC LIMIT 1
) fs ON TRUE
LEFT JOIN insights ins ON ins.product_id = p.id
WHERE p.is_active
GROUP BY p.id, p.name, p.slug, p.category;
