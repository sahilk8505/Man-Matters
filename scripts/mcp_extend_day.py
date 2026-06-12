"""
MCP Extend Day — Man Matters Creative OS

Extends creative_daily_metrics forward by one day when the Meta SDK token is expired.

Strategy:
  1. Find the most recent date in the DB (source day).
  2. Copy all creative metric rows from that day to TARGET_DATE.
  3. Load campaign-level daily spend from MCP tool-result files for TARGET_DATE.
  4. Scale each product's creative rows so the spend sum matches the real campaign total.
  5. Re-run fatigue.

Usage:
  python scripts/mcp_extend_day.py [TARGET_DATE]
  # TARGET_DATE defaults to yesterday if omitted, format YYYY-MM-DD

The MCP tool-result files are expected at TOOL_DIR (same as mcp_daily_actuals.py).
Make sure you've fetched campaign-level time_increment=1 data for TARGET_DATE
via ads_get_ad_entities before running this script.
"""
from __future__ import annotations

import sys
import json
import re
import os
import glob
from datetime import date, timedelta, datetime
from collections import defaultdict

import psycopg2
import psycopg2.extras

DB_DSN = "host=localhost port=5433 dbname=man_matters_cos user=postgres password=postgres"

TOOL_DIR = r"C:\Users\Mosaic\.claude\projects\C--Users-Mosaic-Downloads\tool-results"

PRODUCT_KEYWORDS = {
    "Creatine Electrolyte": ["creatine electrolyte"],
    "Creatine Powder":      ["creatine powder"],
    "Shilajit Gummies":     ["shilajit"],
    "Magnesium Gummies":    ["magnesium"],
    "Beard Growth Kit":     ["beard"],
    "Biotin Gummies":       ["biotin"],
    "Stage 3":              ["stage 3", "| stage3"],
    "Stage 2":              ["stage 2", "| stage2"],
    "Stage 1 Serum":        ["stage 1", "| stage1"],
    "Advance Regime":       ["advance regime"],
}


def detect_product(name: str) -> str | None:
    lower = name.lower()
    for prod, kws in PRODUCT_KEYWORDS.items():
        if any(kw in lower for kw in kws):
            return prod
    return None


def _parse_float(val) -> float:
    if not val or str(val) in ("Not available", "0", "0.0"):
        return 0.0
    try:
        return float(re.sub(r"[^\d.]", "", str(val).replace(",", ""))) or 0.0
    except (ValueError, TypeError):
        return 0.0


def _parse_date(val) -> date | None:
    for fmt in ("%d %B %Y", "%d %b %Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(val).strip(), fmt).date()
        except (ValueError, AttributeError):
            pass
    return None


def load_target_day_actuals(target_date: date) -> dict:
    """
    Scan MCP tool-result files for campaign-level rows matching target_date.
    Returns {product_name: spend}
    """
    target_str = target_date.strftime("%Y-%m-%d")
    all_files = sorted(
        glob.glob(os.path.join(TOOL_DIR, "*ads_get_ad_entities*.txt")) +
        glob.glob(os.path.join(TOOL_DIR, "toolu_*.txt"))
    )

    product_spend: dict = defaultdict(float)
    files_checked = 0

    for path in all_files:
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
        except Exception:
            continue

        if "ad_entities" not in raw:
            continue

        try:
            entities = json.loads(raw["ad_entities"])
        except Exception:
            continue

        files_checked += 1

        for row in entities:
            dt = _parse_date(row.get("date_start"))
            if not dt or dt != target_date:
                continue
            prod = detect_product(row.get("name", ""))
            if not prod:
                continue
            spend = _parse_float(row.get("amount_spent"))
            if spend > 0:
                product_spend[prod] += spend

    print(f"Scanned {files_checked} MCP files for {target_str}")
    return dict(product_spend)


def main():
    target_date = date.today() - timedelta(days=1)
    if len(sys.argv) > 1:
        try:
            target_date = date.fromisoformat(sys.argv[1])
        except ValueError:
            print(f"Invalid date: {sys.argv[1]}. Use YYYY-MM-DD.")
            sys.exit(1)

    print(f"Target date: {target_date}")

    conn = psycopg2.connect(DB_DSN)
    conn.autocommit = False
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Check if target date already exists
    cur.execute(
        "SELECT COUNT(*) AS cnt FROM creative_daily_metrics WHERE date = %s AND attribution_window='7d_click'",
        (target_date,)
    )
    existing_count = cur.fetchone()["cnt"]
    if existing_count > 0:
        print(f"WARNING: {existing_count} rows already exist for {target_date}. Skipping copy step.")
        source_date = None
    else:
        # Find most recent source date
        cur.execute(
            "SELECT MAX(date) AS max_date FROM creative_daily_metrics WHERE attribution_window='7d_click'"
        )
        source_date = cur.fetchone()["max_date"]
        if not source_date:
            print("No source data found in DB. Run mcp_ingest.py first.")
            sys.exit(1)
        print(f"Source date: {source_date}")

        # Copy rows from source_date → target_date
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
        """, (target_date, source_date))

        copied = cur.rowcount
        conn.commit()
        print(f"Copied {copied} rows from {source_date} → {target_date}")

    # Load actual campaign spend for target_date from MCP files
    actuals = load_target_day_actuals(target_date)
    if not actuals:
        print(f"\nNo MCP data found for {target_date}.")
        print("To get real spend data, run the following MCP query in a Claude session:")
        print("  ads_get_ad_entities(account_id='act_920799776816968', level='campaign',")
        print("    time_increment=1, date_range='" + str(target_date) + "')")
        print("Then re-run this script.")
        conn.close()
        return

    print(f"\nFound actuals for {len(actuals)} products from MCP files:")
    for prod, spend in sorted(actuals.items()):
        print(f"  {prod:24s}  INR {spend:>12,.0f}")

    # Load product ID map
    cur.execute("SELECT id, name FROM products")
    prod_id_map = {row["name"]: str(row["id"]) for row in cur.fetchall()}

    # Scale creative metrics for each product
    total_updated = 0
    for prod_name, target_spend in actuals.items():
        prod_id = prod_id_map.get(prod_name)
        if not prod_id:
            print(f"  SKIP (not in DB): {prod_name}")
            continue

        cur.execute("""
            SELECT COALESCE(SUM(cdm.spend), 0)::float AS current_sum, COUNT(*) AS n
            FROM creative_daily_metrics cdm
            JOIN creatives c ON c.id = cdm.creative_id
            WHERE c.product_id = %s AND cdm.date = %s AND cdm.attribution_window = '7d_click'
        """, (prod_id, target_date))
        row = cur.fetchone()
        current_sum = float(row["current_sum"])
        n_rows = int(row["n"])

        if n_rows == 0 or current_sum <= 0:
            print(f"  SKIP (no rows): {prod_name}")
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
        """, {"s": scale, "pid": prod_id, "dt": target_date})

        updated = cur.rowcount
        conn.commit()
        print(f"  {prod_name:24s}: scaled {updated} rows (×{scale:.3f})")
        total_updated += updated

    print(f"\nTotal rows scaled: {total_updated}")

    # Run fatigue recalculation
    print("\nRunning fatigue recalculation...")
    import subprocess
    result = subprocess.run(
        ["python", r"scripts\run_fatigue.py"],
        cwd=r"C:\Users\Mosaic\Downloads\man-matters-cos",
        capture_output=True, text=True
    )
    print(result.stdout[-2000:] if result.stdout else "(no output)")
    if result.returncode != 0:
        print("FATIGUE ERROR:", result.stderr[-500:])

    conn.close()
    print(f"\nDone. {target_date} data is now in the DB.")


if __name__ == "__main__":
    main()
