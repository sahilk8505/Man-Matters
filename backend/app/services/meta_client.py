"""
Meta Marketing API Client — Man Matters Creative OS

Pulls campaigns, ad sets, ads, creative metadata, and performance metrics
from the Meta Ads API (Facebook Business SDK).

This client is used by the sync service to populate creative_daily_metrics.
The existing Meta MCP integration in Claude is the interactive interface;
this client handles automated backend syncs.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import date, timedelta
from typing import Any, Dict, List, Optional

import httpx
from facebook_business.api import FacebookAdsApi
from facebook_business.adobjects.adaccount import AdAccount
from facebook_business.adobjects.ad import Ad
from facebook_business.adobjects.adcreative import AdCreative
from facebook_business.adobjects.adsinsights import AdsInsights
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings


logger = logging.getLogger(__name__)

# Meta API insight fields we need
INSIGHT_FIELDS = [
    AdsInsights.Field.ad_id,
    AdsInsights.Field.ad_name,
    AdsInsights.Field.adset_id,
    AdsInsights.Field.campaign_id,
    AdsInsights.Field.date_start,
    AdsInsights.Field.date_stop,
    AdsInsights.Field.spend,
    AdsInsights.Field.impressions,
    AdsInsights.Field.reach,
    AdsInsights.Field.frequency,
    AdsInsights.Field.clicks,
    AdsInsights.Field.ctr,
    AdsInsights.Field.cpc,
    AdsInsights.Field.cpm,
    AdsInsights.Field.cpp,
    AdsInsights.Field.outbound_clicks,
    AdsInsights.Field.outbound_clicks_ctr,
    AdsInsights.Field.website_ctr,
    AdsInsights.Field.actions,
    AdsInsights.Field.action_values,
    AdsInsights.Field.video_play_actions,
    AdsInsights.Field.video_p25_watched_actions,
    AdsInsights.Field.video_p50_watched_actions,
    AdsInsights.Field.video_p75_watched_actions,
    AdsInsights.Field.video_p95_watched_actions,
    AdsInsights.Field.video_p100_watched_actions,
    AdsInsights.Field.video_avg_time_watched_actions,
    AdsInsights.Field.video_thruplay_watched_actions,
]

AD_FIELDS = [
    Ad.Field.id,
    Ad.Field.name,
    Ad.Field.status,
    Ad.Field.effective_status,
    Ad.Field.campaign_id,
    Ad.Field.adset_id,
    Ad.Field.account_id,
    Ad.Field.creative,
    Ad.Field.created_time,
    Ad.Field.updated_time,
]

CREATIVE_FIELDS = [
    AdCreative.Field.id,
    AdCreative.Field.name,
    AdCreative.Field.title,
    AdCreative.Field.body,
    AdCreative.Field.call_to_action_type,
    AdCreative.Field.object_url,
    AdCreative.Field.image_url,
    AdCreative.Field.thumbnail_url,
    AdCreative.Field.video_id,
    AdCreative.Field.object_type,
    AdCreative.Field.effective_object_story_id,
]


def _init_api() -> bool:
    """Initialize Facebook Ads API. Access token is sufficient — app_id/secret are optional."""
    if not settings.META_ACCESS_TOKEN:
        logger.warning("META_ACCESS_TOKEN not configured — Meta sync disabled")
        return False

    # Access token alone is sufficient for most API operations
    if settings.META_APP_ID and settings.META_APP_SECRET:
        FacebookAdsApi.init(
            app_id=settings.META_APP_ID,
            app_secret=settings.META_APP_SECRET,
            access_token=settings.META_ACCESS_TOKEN,
            api_version=settings.META_API_VERSION,
        )
    else:
        # Token-only init — works for all read operations
        FacebookAdsApi.init(
            access_token=settings.META_ACCESS_TOKEN,
            api_version=settings.META_API_VERSION,
        )
    return True


def _extract_action_value(actions: List[Dict], action_type: str) -> float:
    """Extract a specific action value from Meta insights actions list."""
    for action in (actions or []):
        if action.get("action_type") == action_type:
            return float(action.get("value", 0))
    return 0.0


def _extract_purchase_value(action_values: List[Dict]) -> float:
    """Extract purchase value from action_values."""
    for av in (action_values or []):
        if av.get("action_type") == "purchase":
            return float(av.get("value", 0))
    return 0.0


def _parse_video_view_actions(play_actions: List[Dict], action_type: str) -> int:
    """Extract video view count for a specific action type."""
    for action in (play_actions or []):
        if action.get("action_type") == action_type:
            return int(float(action.get("value", 0)))
    return 0


class MetaAdsClient:
    """Client for pulling Meta Ads data."""

    def __init__(self):
        self._initialized = False

    def _ensure_init(self):
        if not self._initialized:
            self._initialized = _init_api()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def get_ads(self, account_id: str) -> List[Dict]:
        """Fetch all ads from an ad account."""
        self._ensure_init()
        if not self._initialized:
            return []

        account = AdAccount(f"act_{account_id.replace('act_', '')}")
        ads = account.get_ads(fields=AD_FIELDS, params={
            "limit": 500,
            "status": ["ACTIVE", "PAUSED"],
        })

        result = []
        for ad in ads:
            d = ad.export_all_data()
            result.append(d)
        return result

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def get_creative(self, creative_id: str) -> Dict:
        """Fetch creative details."""
        self._ensure_init()
        if not self._initialized:
            return {}

        creative = AdCreative(creative_id)
        data = creative.api_get(fields=CREATIVE_FIELDS)
        return data.export_all_data()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def get_insights(
        self,
        account_id: str,
        date_start: date,
        date_stop: date,
        attribution_window: str = "7d_click",
        level: str = "ad",  # campaign, adset, ad
    ) -> List[Dict]:
        """
        Fetch daily insights for all ads in an account.
        Returns one row per (ad_id, date) combination.
        """
        self._ensure_init()
        if not self._initialized:
            return []

        account = AdAccount(f"act_{account_id.replace('act_', '')}")

        # Map our attribution window names to Meta API format
        attribution_map = {
            "1d_click": {"click": 1, "view": 0},
            "7d_click": {"click": 7, "view": 0},
            "28d_click": {"click": 28, "view": 0},
            "1d_view": {"click": 0, "view": 1},
        }
        attr_config = attribution_map.get(attribution_window, {"click": 7, "view": 0})

        params = {
            "level": level,
            "time_range": {
                "since": date_start.strftime("%Y-%m-%d"),
                "until": date_stop.strftime("%Y-%m-%d"),
            },
            "time_increment": 1,  # Daily breakdown
            "limit": 1000,
            "action_attribution_windows": [
                f"{attr_config['click']}d_click" if attr_config["click"] else "1d_view"
            ],
            "fields": [
                "ad_id", "ad_name", "adset_id", "campaign_id",
                "date_start", "spend", "impressions", "reach", "frequency",
                "clicks", "ctr", "cpc", "cpm",
                "outbound_clicks", "outbound_clicks_ctr", "website_ctr",
                "actions", "action_values",
                "video_play_actions", "video_p25_watched_actions",
                "video_p50_watched_actions", "video_p75_watched_actions",
                "video_p95_watched_actions", "video_p100_watched_actions",
                "video_avg_time_watched_actions", "video_thruplay_watched_actions",
            ],
        }

        insights = account.get_insights(params=params)
        result = []
        for row in insights:
            parsed = self._parse_insight_row(row.export_all_data(), attribution_window)
            if parsed:
                result.append(parsed)

        logger.info(f"Fetched {len(result)} insight rows from Meta for {account_id}")
        return result

    def _parse_insight_row(self, row: Dict, attribution_window: str) -> Optional[Dict]:
        """Parse a raw Meta insight row into our normalized format."""
        ad_id = row.get("ad_id")
        if not ad_id:
            return None

        spend = float(row.get("spend", 0))
        impressions = int(row.get("impressions", 0))
        actions = row.get("actions", [])
        action_values = row.get("action_values", [])

        # Video metrics
        video_plays = _parse_video_view_actions(row.get("video_play_actions", []), "video_view")
        p25 = _parse_video_view_actions(row.get("video_p25_watched_actions", []), "video_view")
        p50 = _parse_video_view_actions(row.get("video_p50_watched_actions", []), "video_view")
        p75 = _parse_video_view_actions(row.get("video_p75_watched_actions", []), "video_view")
        p95 = _parse_video_view_actions(row.get("video_p95_watched_actions", []), "video_view")
        p100 = _parse_video_view_actions(row.get("video_p100_watched_actions", []), "video_view")
        thruplay = _parse_video_view_actions(row.get("video_thruplay_watched_actions", []), "video_view")

        # 3-second views (proxy for thumb-stop)
        three_sec = thruplay if thruplay > 0 else int(p25 * 0.8)

        # Conversions
        purchases = int(_extract_action_value(actions, "purchase"))
        add_to_cart = int(_extract_action_value(actions, "add_to_cart"))
        initiate_checkout = int(_extract_action_value(actions, "initiate_checkout"))
        view_content = int(_extract_action_value(actions, "view_content"))
        link_clicks = int(_extract_action_value(actions, "link_click"))
        purchase_value = _extract_purchase_value(action_values)

        # Outbound CTR
        outbound_clicks = int(sum(
            float(oc.get("value", 0))
            for oc in (row.get("outbound_clicks") or [])
        ))

        # Derived metrics
        ctr = float(row.get("ctr", 0)) / 100  # Meta returns as percentage
        link_ctr = link_clicks / impressions if impressions > 0 else 0
        outbound_ctr = outbound_clicks / impressions if impressions > 0 else 0
        cpc = float(row.get("cpc", 0))
        cpm = float(row.get("cpm", 0))
        cpa = spend / purchases if purchases > 0 else 0
        roas = purchase_value / spend if spend > 0 else 0
        conversion_rate = purchases / link_clicks if link_clicks > 0 else 0
        hook_rate = three_sec / impressions if impressions > 0 else 0
        hold_rate = p75 / p25 if p25 > 0 else 0
        thumb_stop_rate = hook_rate  # same as hook_rate

        return {
            "meta_ad_id": ad_id,
            "meta_campaign_id": row.get("campaign_id"),
            "meta_adset_id": row.get("adset_id"),
            "date": row.get("date_start"),
            "spend": spend,
            "impressions": impressions,
            "reach": int(row.get("reach", 0)),
            "frequency": float(row.get("frequency", 0)),
            "clicks": int(row.get("clicks", 0)),
            "ctr": ctr,
            "link_clicks": link_clicks,
            "link_ctr": link_ctr,
            "outbound_clicks": outbound_clicks,
            "outbound_ctr": outbound_ctr,
            "cpc": cpc,
            "cpm": cpm,
            "purchases": purchases,
            "purchase_value": purchase_value,
            "add_to_cart": add_to_cart,
            "initiate_checkout": initiate_checkout,
            "view_content": view_content,
            "cpa": cpa,
            "roas": roas,
            "conversion_rate": conversion_rate,
            "video_views": video_plays,
            "video_p25_watched": p25,
            "video_p50_watched": p50,
            "video_p75_watched": p75,
            "video_p95_watched": p95,
            "video_p100_watched": p100,
            "three_sec_video_views": three_sec,
            "hook_rate": hook_rate,
            "hold_rate": hold_rate,
            "thumb_stop_rate": thumb_stop_rate,
            "attribution_window": attribution_window,
        }

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=15))
    def search_ad_library(
        self,
        search_terms: List[str],
        country: str = "IN",
        limit: int = 50,
    ) -> List[Dict]:
        """
        Search Meta Ad Library for competitor ads.
        Uses the Ad Library API endpoint.
        """
        results = []
        for term in search_terms:
            try:
                url = f"https://graph.facebook.com/{settings.META_API_VERSION}/ads_archive"
                params = {
                    "search_terms": term,
                    "ad_reached_countries": country,
                    "ad_type": "ALL",
                    "fields": ",".join([
                        "id", "page_id", "page_name", "ad_creative_bodies",
                        "ad_creative_link_captions", "ad_creative_link_descriptions",
                        "ad_creative_link_titles", "ad_delivery_start_time",
                        "ad_delivery_stop_time", "ad_snapshot_url",
                        "media_type", "bylines"
                    ]),
                    "access_token": settings.META_ACCESS_TOKEN,
                    "limit": limit,
                }

                import requests
                response = requests.get(url, params=params, timeout=30)
                if response.status_code == 200:
                    data = response.json()
                    results.extend(data.get("data", []))
            except Exception as e:
                logger.error(f"Ad Library search failed for term '{term}': {e}")

        return results


# Singleton client instance
meta_client = MetaAdsClient()
