"""
Fatigue Engine — Man Matters Creative OS

Calculates multi-dimensional fatigue scores for each creative.
Never compares formats directly. Normalizes by format.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

import numpy as np

from app.core.config import settings


# ---------------------------------------------------------------------------
# Format-specific metric weights
# ---------------------------------------------------------------------------

FORMAT_WEIGHTS: Dict[str, Dict[str, float]] = {
    "reel": {
        "hook_decay": 0.20,
        "hold_decay": 0.15,
        "ctr_decay": 0.15,
        "roas_decay": 0.15,
        "cpa_inflation": 0.12,
        "cpm_inflation": 0.08,
        "frequency": 0.08,
        "conversion_decay": 0.07,
    },
    "video": {
        "hook_decay": 0.18,
        "hold_decay": 0.15,
        "ctr_decay": 0.15,
        "roas_decay": 0.15,
        "cpa_inflation": 0.12,
        "cpm_inflation": 0.10,
        "frequency": 0.08,
        "conversion_decay": 0.07,
    },
    "static": {
        "ctr_decay": 0.30,
        "cpc_inflation": 0.25,
        "cpm_inflation": 0.20,
        "roas_decay": 0.12,
        "cpa_inflation": 0.08,
        "frequency": 0.05,
        # No video metrics for static
        "hook_decay": 0.0,
        "hold_decay": 0.0,
        "conversion_decay": 0.0,
    },
    "carousel": {
        "ctr_decay": 0.28,
        "cpc_inflation": 0.22,
        "cpm_inflation": 0.18,
        "roas_decay": 0.12,
        "cpa_inflation": 0.10,
        "frequency": 0.10,
        "hook_decay": 0.0,
        "hold_decay": 0.0,
        "conversion_decay": 0.0,
    },
    "story": {
        "ctr_decay": 0.32,
        "cpc_inflation": 0.22,
        "cpm_inflation": 0.18,
        "roas_decay": 0.12,
        "cpa_inflation": 0.08,
        "frequency": 0.08,
        "hook_decay": 0.0,
        "hold_decay": 0.0,
        "conversion_decay": 0.0,
    },
    "default": {
        "ctr_decay": 0.22,
        "cpc_inflation": 0.18,
        "cpm_inflation": 0.15,
        "roas_decay": 0.15,
        "cpa_inflation": 0.12,
        "frequency": 0.08,
        "hook_decay": 0.05,
        "hold_decay": 0.05,
        "conversion_decay": 0.0,
    },
}

# Frequency danger thresholds by format
FREQUENCY_THRESHOLDS = {
    "reel": {"warn": 2.5, "danger": 4.0},
    "static": {"warn": 3.0, "danger": 5.0},
    "carousel": {"warn": 2.8, "danger": 4.5},
    "story": {"warn": 3.5, "danger": 6.0},
    "video": {"warn": 2.5, "danger": 4.0},
    "default": {"warn": 3.0, "danger": 5.0},
}


@dataclass
class DailyMetricRow:
    date: date
    spend: float = 0
    ctr: float = 0
    link_ctr: float = 0
    cpc: float = 0
    cpm: float = 0
    cpa: float = 0
    roas: float = 0
    hook_rate: float = 0
    hold_rate: float = 0
    thumb_stop_rate: float = 0
    frequency: float = 0
    purchases: int = 0
    conversion_rate: float = 0
    impressions: int = 0


@dataclass
class FatigueResult:
    fatigue_score: float
    fatigue_stage: str
    confidence: float

    # Component scores (0-100 each)
    component_scores: Dict[str, float] = field(default_factory=dict)

    # Lifecycle
    days_since_launch: int = 0
    expected_remaining_days: Optional[int] = None
    days_to_peak: Optional[int] = None

    # Baselines
    baseline_ctr: Optional[float] = None
    baseline_cpc: Optional[float] = None
    baseline_cpm: Optional[float] = None
    baseline_cpa: Optional[float] = None
    baseline_roas: Optional[float] = None
    baseline_hook_rate: Optional[float] = None
    current_frequency: Optional[float] = None

    # Alerts
    alerts: List[str] = field(default_factory=list)


def _safe_mean(values: List[float], min_val: float = 0) -> Optional[float]:
    """Return mean of non-zero values above min_val, or None if insufficient data."""
    filtered = [v for v in values if v is not None and v > min_val]
    return float(np.mean(filtered)) if filtered else None


def _decay_score(baseline: float, current: float, scale: float = 2.0) -> float:
    """
    Convert a percentage decay into a 0-100 score.
    - 0% decay → 0 score
    - 50% decay → ~100 score (with scale=2.0)
    scale parameter adjusts sensitivity.
    """
    if baseline <= 0:
        return 0.0
    decay_pct = (baseline - current) / baseline
    return float(min(100.0, max(0.0, decay_pct * 100.0 * scale)))


def _inflation_score(baseline: float, current: float, scale: float = 2.0) -> float:
    """Convert a percentage increase into a 0-100 score."""
    if baseline <= 0:
        return 0.0
    inflation_pct = (current - baseline) / baseline
    return float(min(100.0, max(0.0, inflation_pct * 100.0 * scale)))


def _frequency_score(current_freq: float, format_type: str) -> float:
    """Score frequency danger: 0 = safe, 100 = extremely fatigued by frequency."""
    thresholds = FREQUENCY_THRESHOLDS.get(format_type, FREQUENCY_THRESHOLDS["default"])
    warn = thresholds["warn"]
    danger = thresholds["danger"]

    if current_freq <= warn:
        return 0.0
    elif current_freq >= danger:
        return 100.0
    else:
        return (current_freq - warn) / (danger - warn) * 100.0


def _estimate_remaining_life(
    metrics: List[DailyMetricRow],
    fatigue_score: float,
    format_type: str
) -> Optional[int]:
    """
    Estimate remaining creative life based on fatigue trajectory.
    Uses linear extrapolation of the fatigue curve.
    """
    if len(metrics) < 5 or fatigue_score >= 100:
        return 0

    # At healthy (<30): likely weeks remaining
    # At watch (30-60): roughly 30-100 - score days
    # At fatiguing (60-80): days remaining ≈ (100-score) * 0.5
    # At fatigued (>80): days remaining ≈ (100-score) * 0.2

    remaining = 100 - fatigue_score
    if fatigue_score < 30:
        multiplier = 0.8
    elif fatigue_score < 60:
        multiplier = 0.5
    elif fatigue_score < 80:
        multiplier = 0.3
    else:
        multiplier = 0.15

    return max(0, int(remaining * multiplier))


def _detect_peak(metrics: List[DailyMetricRow]) -> Optional[int]:
    """Find the day index where ROAS was highest (post-warm-up)."""
    if len(metrics) < 5:
        return None

    # Skip first 3 days (warm-up period)
    roas_values = [(i, m.roas) for i, m in enumerate(metrics[3:], start=3)
                   if m.roas and m.roas > 0 and m.spend > 100]
    if not roas_values:
        return None

    peak_idx = max(roas_values, key=lambda x: x[1])[0]
    return peak_idx


def calculate_fatigue_score(
    metrics: List[DailyMetricRow],
    format_type: str = "default",
    product_id: Optional[str] = None,
) -> FatigueResult:
    """
    Calculate the fatigue score for a creative given its daily metrics history.

    Uses format-specific weights to normalize across different creative types.
    Requires at least 3 days of data with meaningful spend.

    Returns FatigueResult with score 0-100 and detailed component breakdown.
    """
    # Filter to days with meaningful spend (avoid noise)
    meaningful = [m for m in metrics if m.spend >= 200]

    if len(meaningful) < 3:
        return FatigueResult(
            fatigue_score=0.0,
            fatigue_stage="insufficient_data",
            confidence=0.0,
            days_since_launch=len(metrics),
            alerts=["Insufficient data for fatigue calculation (< 3 days with spend > ₹200)"],
        )

    # Sort chronologically
    meaningful = sorted(meaningful, key=lambda m: m.date)

    n = len(meaningful)
    # Baseline window: first 20% of data, minimum 3 days, maximum 7 days
    baseline_n = max(3, min(7, n // 5))
    baseline = meaningful[:baseline_n]
    recent = meaningful[-3:]  # Last 3 days

    weights = FORMAT_WEIGHTS.get(format_type, FORMAT_WEIGHTS["default"])
    component_scores: Dict[str, float] = {}
    alerts: List[str] = []

    # ----- CTR Decay -----
    b_ctr = _safe_mean([m.ctr for m in baseline])
    r_ctr = _safe_mean([m.ctr for m in recent])
    if b_ctr and r_ctr is not None:
        component_scores["ctr_decay"] = _decay_score(b_ctr, r_ctr, scale=2.5)
        if component_scores["ctr_decay"] > 60:
            alerts.append(f"CTR dropped {((b_ctr - r_ctr)/b_ctr*100):.0f}% from baseline ({b_ctr*100:.2f}% → {r_ctr*100:.2f}%)")
    else:
        component_scores["ctr_decay"] = 0.0

    # ----- CPC Inflation -----
    b_cpc = _safe_mean([m.cpc for m in baseline], min_val=0.1)
    r_cpc = _safe_mean([m.cpc for m in recent], min_val=0.1)
    if b_cpc and r_cpc:
        component_scores["cpc_inflation"] = _inflation_score(b_cpc, r_cpc, scale=2.0)
        if component_scores["cpc_inflation"] > 60:
            alerts.append(f"CPC inflated {((r_cpc-b_cpc)/b_cpc*100):.0f}% from baseline (₹{b_cpc:.0f} → ₹{r_cpc:.0f})")
    else:
        component_scores["cpc_inflation"] = 0.0

    # ----- CPM Inflation -----
    b_cpm = _safe_mean([m.cpm for m in baseline], min_val=1.0)
    r_cpm = _safe_mean([m.cpm for m in recent], min_val=1.0)
    if b_cpm and r_cpm:
        component_scores["cpm_inflation"] = _inflation_score(b_cpm, r_cpm, scale=1.5)
    else:
        component_scores["cpm_inflation"] = 0.0

    # ----- ROAS Decay -----
    b_roas = _safe_mean([m.roas for m in baseline], min_val=0.1)
    r_roas = _safe_mean([m.roas for m in recent], min_val=0.1)
    if b_roas and r_roas is not None:
        component_scores["roas_decay"] = _decay_score(b_roas, r_roas, scale=2.5)
        if component_scores["roas_decay"] > 60:
            alerts.append(f"ROAS decayed {((b_roas-r_roas)/b_roas*100):.0f}% from baseline ({b_roas:.1f}x → {r_roas:.1f}x)")
    else:
        component_scores["roas_decay"] = 0.0

    # ----- CPA Inflation -----
    b_cpa = _safe_mean([m.cpa for m in baseline], min_val=1.0)
    r_cpa = _safe_mean([m.cpa for m in recent], min_val=1.0)
    if b_cpa and r_cpa:
        component_scores["cpa_inflation"] = _inflation_score(b_cpa, r_cpa, scale=2.0)
        if component_scores["cpa_inflation"] > 60:
            alerts.append(f"CPA inflated {((r_cpa-b_cpa)/b_cpa*100):.0f}% from baseline (₹{b_cpa:.0f} → ₹{r_cpa:.0f})")
    else:
        component_scores["cpa_inflation"] = 0.0

    # ----- Hook Rate Decay (video only) -----
    b_hook = _safe_mean([m.hook_rate for m in baseline], min_val=0.001)
    r_hook = _safe_mean([m.hook_rate for m in recent], min_val=0.001)
    if b_hook and r_hook is not None and weights.get("hook_decay", 0) > 0:
        component_scores["hook_decay"] = _decay_score(b_hook, r_hook, scale=3.0)
        if component_scores["hook_decay"] > 60:
            alerts.append(f"Hook rate dropped {((b_hook-r_hook)/b_hook*100):.0f}% — viewers scrolling past")
    else:
        component_scores["hook_decay"] = 0.0

    # ----- Hold Rate Decay (video only) -----
    b_hold = _safe_mean([m.hold_rate for m in baseline], min_val=0.001)
    r_hold = _safe_mean([m.hold_rate for m in recent], min_val=0.001)
    if b_hold and r_hold is not None and weights.get("hold_decay", 0) > 0:
        component_scores["hold_decay"] = _decay_score(b_hold, r_hold, scale=2.5)
    else:
        component_scores["hold_decay"] = 0.0

    # ----- Frequency Score -----
    current_freq = meaningful[-1].frequency if meaningful else 0
    component_scores["frequency"] = _frequency_score(current_freq, format_type)
    if component_scores["frequency"] > 60:
        thresholds = FREQUENCY_THRESHOLDS.get(format_type, FREQUENCY_THRESHOLDS["default"])
        alerts.append(f"Frequency {current_freq:.1f}x is approaching saturation threshold ({thresholds['danger']}x)")

    # ----- Conversion Rate Decay -----
    b_conv = _safe_mean([m.conversion_rate for m in baseline], min_val=0.0001)
    r_conv = _safe_mean([m.conversion_rate for m in recent], min_val=0.0001)
    if b_conv and r_conv is not None and weights.get("conversion_decay", 0) > 0:
        component_scores["conversion_decay"] = _decay_score(b_conv, r_conv, scale=2.0)
    else:
        component_scores["conversion_decay"] = 0.0

    # ----- Weighted Composite Score -----
    total_weight = sum(weights[k] for k in component_scores if weights.get(k, 0) > 0)
    if total_weight > 0:
        weighted_sum = sum(
            component_scores[k] * weights.get(k, 0)
            for k in component_scores
            if weights.get(k, 0) > 0
        )
        fatigue_score = min(100.0, max(0.0, weighted_sum / total_weight))
    else:
        fatigue_score = 0.0

    # ----- Stage Classification -----
    if fatigue_score <= settings.FATIGUE_HEALTHY_MAX:
        stage = "healthy"
    elif fatigue_score <= settings.FATIGUE_WATCH_MAX:
        stage = "watch"
    elif fatigue_score <= settings.FATIGUE_FATIGUING_MAX:
        stage = "fatiguing"
    else:
        stage = "fatigued"

    # ----- Confidence (based on data volume) -----
    # Full confidence at 14+ days of data, scales down for less
    confidence = min(1.0, n / 14.0)
    # If we have only 3-5 days, extra penalty
    if n < 5:
        confidence *= 0.6

    # ----- Peak Detection -----
    peak_day = _detect_peak(meaningful)

    # ----- Remaining Life Estimate -----
    remaining = _estimate_remaining_life(meaningful, fatigue_score, format_type)

    return FatigueResult(
        fatigue_score=round(fatigue_score, 2),
        fatigue_stage=stage,
        confidence=round(confidence, 3),
        component_scores={k: round(v, 2) for k, v in component_scores.items()},
        days_since_launch=n,
        expected_remaining_days=remaining,
        days_to_peak=peak_day,
        baseline_ctr=b_ctr,
        baseline_cpc=b_cpc,
        baseline_cpm=b_cpm,
        baseline_cpa=b_cpa,
        baseline_roas=b_roas,
        baseline_hook_rate=b_hook,
        current_frequency=current_freq if current_freq > 0 else None,
        alerts=alerts,
    )


def calculate_narrative_lifespan(
    creative_lifespans: List[int],
    fatigue_scores_at_death: List[float],
) -> Dict[str, float]:
    """
    Given a list of creative lifespans for a narrative + product combination,
    compute statistical summary of that narrative's lifespan profile.
    """
    if not creative_lifespans:
        return {}

    arr = np.array(creative_lifespans)
    return {
        "avg_lifespan_days": float(np.mean(arr)),
        "median_lifespan_days": float(np.median(arr)),
        "p25_lifespan_days": float(np.percentile(arr, 25)),
        "p75_lifespan_days": float(np.percentile(arr, 75)),
        "min_lifespan_days": float(np.min(arr)),
        "max_lifespan_days": float(np.max(arr)),
        "std_lifespan_days": float(np.std(arr)),
        "sample_count": len(arr),
    }


def compute_decay_rates(
    time_series: List[DailyMetricRow],
) -> Dict[str, float]:
    """
    Compute daily decay rates for key metrics using linear regression on log-scale.
    Returns % change per day.
    """
    if len(time_series) < 5:
        return {}

    days = np.arange(len(time_series))
    results = {}

    for metric_name, getter in [
        ("ctr", lambda m: m.ctr),
        ("roas", lambda m: m.roas),
        ("hook_rate", lambda m: m.hook_rate),
        ("cpa", lambda m: m.cpa),
    ]:
        values = np.array([getter(m) for m in time_series])
        valid = values > 0
        if valid.sum() < 4:
            continue

        # Fit log-linear model: log(y) = a + b*t → decay rate = b
        try:
            log_values = np.log(values[valid])
            coeffs = np.polyfit(days[valid], log_values, 1)
            daily_rate_pct = float(coeffs[0] * 100)  # % per day (negative = decay)
            results[f"{metric_name}_daily_rate_pct"] = round(daily_rate_pct, 4)
        except Exception:
            pass

    return results
