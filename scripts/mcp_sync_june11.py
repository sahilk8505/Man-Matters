"""
One-shot sync for 2026-06-11 — Man Matters Creative OS

Actual campaign-level spend for 2026-06-11 fetched via Meta Ads MCP
(both accounts: MM25 act_920799776816968 + Nutrition25 act_2080540322400218).

Strategy:
  1. Copy 2026-06-10 creative distribution to 2026-06-11 (if not already there).
  2. Scale each product's rows to match real 2026-06-11 spend.
  3. Re-run fatigue.
"""
from __future__ import annotations

import subprocess
import psycopg2
import psycopg2.extras
from datetime import date

DB_DSN = "host=localhost port=5433 dbname=man_matters_cos user=postgres password=postgres"

TARGET_DATE = date(2026, 6, 11)
SOURCE_DATE = date(2026, 6, 10)

# Aggregated from Meta Ads MCP on 2026-06-12 for date 2026-06-11
PRODUCT_SPEND = {
    "Stage 3":              674_872.21,
    "Stage 2":              466_193.13,
    "Beard Growth Kit":     208_927.74,
    "Shilajit Gummies":     215_874.09,
    "Advance Regime":       162_126.91,
    "Biotin Gummies":       144_599.08,
    "Stage 1 Serum":        123_398.22,
    "Creatine Powder":       40_363.79,
    "Creatine Electrolyte":  27_182.37,
    "Magnesium Gummies":     18_668.93,
}


def main():
    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Step 1: Copy SOURCE_DATE rows to TARGET_DATE if not already present
    cur.execute(
        "SELECT COUNT(*) AS n FROM creative_daily_metrics WHERE date = %s AND attribution_window = '7d_click'",
        (TARGET_DATE,)
    )
    existing = cur.fetchone()["n"]

    if existing == 0:
        cur.execute("""
            INSERT INTO creative_daily_metrics (
                id, creative_id, product_id, date, attribution_window,
                spend, impressions, reach, frequency, clicks, ctr,
                link_clicks, link_ctr, outbound_clicks, outbound_ctr,
                cpc, cpm, purchases, purchase_value, add_to_cart,
                initiate_checkout, view_content, cpa, roas,
                conversion_rate, video_views, video_p25_watched,
                video_p50_watched, video_p75_watched, video_p95_watched,
                video_p100_watched, three_sec_video_views,
                hook_rate, hold_rate, thumb_stop_rate
            )
            SELECT
                gen_random_uuid(), creative_id, product_id, %s, attribution_window,
                spend, impressions, reach, frequency, clicks, ctr,
                link_clicks, link_ctr, outbound_clicks, outbound_ctr,
                cpc, cpm, purchases, purchase_value, add_to_cart,
                initiate_checkout, view_content, cpa, roas,
                conversion_rate, video_views, video_p25_watched,
                video_p50_watched, video_p75_watched, video_p95_watched,
                video_p100_watched, three_sec_video_views,
                hook_rate, hold_rate, thumb_stop_rate
            FROM creative_daily_metrics
            WHERE date = %s AND attribution_window = '7d_click'
            ON CONFLICT (creative_id, date, attribution_window) DO NOTHING
        """, (TARGET_DATE, SOURCE_DATE))
        copied = cur.rowcount
        conn.commit()
        print(f"Copied {copied} rows from {SOURCE_DATE} to {TARGET_DATE}")
    else:
        print(f"{TARGET_DATE} already has {existing} rows -- skipping copy, will re-scale to real spend")

    # Step 2: Load product ID map
    cur.execute("SELECT id, name FROM products")
    prod_id_map = {row["name"]: str(row["id"]) for row in cur.fetchall()}

    # Step 3: Scale each product to real 2026-06-11 spend
    total_updated = 0
    for prod_name, target_spend in sorted(PRODUCT_SPEND.items()):
        prod_id = prod_id_map.get(prod_name)
        if not prod_id:
            print(f"  SKIP (not in DB): {prod_name}")
            continue

        cur.execute("""
            SELECT COALESCE(SUM(cdm.spend), 0)::float AS current_sum, COUNT(*) AS n
            FROM creative_daily_metrics cdm
            JOIN creatives c ON c.id = cdm.creative_id
            WHERE c.product_id = %s AND cdm.date = %s AND cdm.attribution_window = '7d_click'
        """, (prod_id, TARGET_DATE))
        row = cur.fetchone()
        current_sum = float(row["current_sum"])
        n_rows = int(row["n"])

        if n_rows == 0 or current_sum <= 0:
            print(f"  SKIP (no rows):  {prod_name}")
            continue

        scale = target_spend / current_sum
        cur.execute("""
            UPDATE creative_daily_metrics AS cdm SET
                spend             = ROUND((cdm.spend            * %(s)s)::numeric, 4),
                impressions       = GREATEST(1, ROUND(cdm.impressions       * %(s)s)::int),
                reach             = GREATEST(1, ROUND(cdm.reach             * %(s)s)::int),
                clicks            = GREATEST(0, ROUND(cdm.clicks            * %(s)s)::int),
                link_clicks       = GREATEST(0, ROUND(cdm.link_clicks       * %(s)s)::int),
                purchases         = GREATEST(0, ROUND(cdm.purchases         * %(s)s)::int),
                purchase_value    = ROUND((cdm.purchase_value    * %(s)s)::numeric, 4),
                video_p25_watched = GREATEST(0, ROUND(cdm.video_p25_watched * %(s)s)::int),
                video_p75_watched = GREATEST(0, ROUND(cdm.video_p75_watched * %(s)s)::int),
                three_sec_video_views = GREATEST(0, ROUND(cdm.three_sec_video_views * %(s)s)::int),
                cpa = CASE WHEN cdm.purchases * %(s)s > 0
                      THEN ROUND((cdm.spend * %(s)s / (cdm.purchases * %(s)s))::numeric, 4)
                      ELSE 0 END,
                link_ctr = CASE WHEN cdm.impressions * %(s)s > 0
                           THEN ROUND((cdm.link_clicks * %(s)s / (cdm.impressions * %(s)s))::numeric, 6)
                           ELSE 0 END,
                conversion_rate = CASE WHEN cdm.link_clicks * %(s)s > 0
                                  THEN ROUND((cdm.purchases * %(s)s / (cdm.link_clicks * %(s)s))::numeric, 6)
                                  ELSE 0 END,
                hook_rate = CASE WHEN cdm.impressions * %(s)s > 0
                            THEN ROUND((cdm.three_sec_video_views * %(s)s / (cdm.impressions * %(s)s))::numeric, 6)
                            ELSE cdm.hook_rate END
            FROM creatives c2
            WHERE cdm.creative_id = c2.id
              AND c2.product_id = %(pid)s
              AND cdm.date = %(dt)s
              AND cdm.attribution_window = '7d_click'
        """, {"s": scale, "pid": prod_id, "dt": TARGET_DATE})

        n_updated = cur.rowcount
        conn.commit()
        print(f"  {prod_name:24s}: {n_updated:3d} rows  x{scale:.3f}  INR {target_spend:>12,.0f}")
        total_updated += n_updated

    print(f"\nTotal rows scaled: {total_updated}")
    conn.close()

    # Step 4: Re-run fatigue recalculation
    print("\nRunning fatigue recalculation...")
    result = subprocess.run(
        ["python", r"scripts\run_fatigue.py"],
        cwd=r"C:\Users\Mosaic\Downloads\man-matters-cos",
        capture_output=True, text=True
    )
    if result.stdout:
        print(result.stdout[-3000:])
    if result.returncode != 0:
        print("ERROR:", result.stderr[-500:])
    else:
        print(f"\nDone -- {TARGET_DATE} is live in the DB with real spend data.")


if __name__ == "__main__":
    main()
