"""Shared coaching thresholds.

One number, one place: the stub head coach, the validator and the deterministic
plan audit (`plan_audit.py`, the safety net behind the LLM head coach) all read
these limits, so they never disagree about what "too much" or "too little" is.
The prose version lives in `prompts/training_intensity_doctrine.md`.
"""

from __future__ import annotations

import math
import re
from typing import Any

from .utils import checkin_pain_text, has_niggle


# --- weekly volume -------------------------------------------------------------
# Week-to-week growth of total planned time vs the recent loaded weekly average.
MAX_WEEKLY_TOTAL_GROWTH_PCT = 15.0
# Running is the injury-prone part: run minutes / km grow by ~10% a week at most.
MAX_WEEKLY_RUN_GROWTH_PCT = 10.0
RUN_HISTORY_WEEKS = 12
RUN_HISTORY_RECENT_WEEKS = 2
RUN_HISTORY_MIN_BASELINE_WEEKS = 4
RUN_HISTORY_MIN_RECENT_SHARE = 0.4
# Weekly climbing (D+) and descent grow by ~15% a week at most.
MAX_WEEKLY_ELEVATION_GROWTH_PCT = 15.0
# "Added volume" counts as a progressing element above this growth.
VOLUME_PROGRESSION_PCT = 10.0
# Typical hours from the profile are a soft reference: more than this above warns.
OVER_REFERENCE_WARN_PCT = 15.0

# --- long sessions -------------------------------------------------------------
# A session at or above these minutes is a "long" (durability) session.
LONG_SESSION_MIN: dict[str, int] = {"Ride": 105, "Run": 75}
# Long-session progression from the longest recent one: +10-15 min, never > +15%.
LONG_STEP_MIN = 10
LONG_STEP_MAX = 15
LONG_MAX_JUMP_PCT = 0.15
# Audit tolerance: a long session more than max(15 min, 15%) above recent warns.
LONG_JUMP_MIN = 15.0
LONG_JUMP_PCT = 0.15
# Without a recent long run (break, missing data): 70% of the 56-day longest,
# else this conservative default. Never a template value.
LONG_FALLBACK_56D_FACTOR = 0.7
LONG_RUN_FALLBACK_MIN = 45
LONG_RIDE_FALLBACK_MIN = 75
# A long-session change below this is "holding", not progressing.
LONG_PROGRESSION_MIN = 5.0

# --- intensity distribution ----------------------------------------------------
MIN_GREEN_QUALITY = 2
# Pyramidal floor and ceiling of planned bike/run time above easy (moderate + high).
MIN_PLANNED_INTENSITY_PCT = 8.0
MAX_PLANNED_INTENSITY_PCT = 30.0
# Ladder families that sit in the moderate (tempo / sweet spot) zone of the
# 3-zone model; every other ladder family is high intensity.
MODERATE_FAMILIES = frozenset({"bike_sweet_spot", "run_race_pace"})
# Daniels per-session caps as a share of weekly run minutes, with a floor (min).
DANIELS_CAPS: dict[str, tuple[float, float]] = {
    "T": (0.10, 20.0),
    "I": (0.08, 12.0),
    "R": (0.05, 8.0),
}
DANIELS_FAMILY_TYPE: dict[str, str] = {
    "run_threshold": "T",
    "run_uphill_threshold": "T",
    "run_interval": "I",
}

# --- taper ---------------------------------------------------------------------
# Taper volume vs the recent loaded week, by full weeks to the priority race.
TAPER_VOLUME_BY_WEEKS_OUT: dict[int, float] = {0: 0.45, 1: 0.6, 2: 0.75}
# The audit accepts the planner's ladder within these tolerances.
TAPER_VOLUME_TOLERANCE_HIGH = 0.15
TAPER_VOLUME_TOLERANCE_LOW = 0.25

# --- progression budget ----------------------------------------------------------
# A load week progresses at most this many elements (rung steps, long-session
# duration, added volume), of which at most one is run impact (long run
# duration, run volume, descent). Exception: underload detected, readiness
# green and no ITB/niggle flags.
PROGRESSION_BUDGET_MAX = 2
PROGRESSION_BUDGET_MAX_IMPACT = 1

# --- races -----------------------------------------------------------------------
# Last quality session before a race, in hours (the audit floor is 48h for B).
B_RACE_LAST_QUALITY_H = 72
B_RACE_AUDIT_QUALITY_H = 48
B_RACE_LIGHT_DAYS = 3
C_RACE_LIGHT_DAYS = 1

# --- return / detraining -------------------------------------------------------
# (days without a dose, rungs to step back), longest gap first; None = restart
# at the phase entry rung.
DOSE_GAP_STEP_BACK: tuple[tuple[int, int | None], ...] = (
    (56, None),
    (42, 3),
    (28, 2),
    (14, 1),
)

# --- block rhythm --------------------------------------------------------------
DEFAULT_BLOCK_LENGTH = 4  # 3 load weeks + 1 recovery week
SHORT_BLOCK_LENGTH = 3  # 2:1 after illness / a break / overreaching markers

# Body parts whose pain makes running (impact) the wrong tool this week.
RUN_IMPACT_BODY_PARTS = frozenset(
    {
        "itb",
        "achilles",
        "plantar fascia",
        "hamstring",
        "hip flexor",
        "calf",
        "knee",
        "shin",
        "ankle",
        "foot",
        "hip",
        "glute",
        "quad",
        "groin",
    }
)
PAIN_SCORE_SWAP_MIN = 5  # below 5/10 is follow-up only

# Missed-session reasons that are not athlete unreliability.
HEALTH_REASON_RE = re.compile(
    r"\b(ill|illness|sick|flu|cold|covid|fever|injur\w*|pain\w*|niggle\w*|ziek\w*|griep|blessure)\b",
    re.IGNORECASE,
)


def is_long_session(session: dict[str, Any]) -> bool:
    """A durability session: long by duration, never a race or test."""
    if session.get("race_day") or session.get("zone_focus") == "race":
        return False
    if session.get("threshold_test"):
        return False
    minimum = LONG_SESSION_MIN.get(str(session.get("discipline")))
    if minimum is None:
        return False
    return float(session.get("duration_min") or 0) >= minimum


def post_race_easy_days(priority: str | None, duration_min: float | None) -> int:
    """Easy days after a race, scaled by race duration (the race day not included)."""
    minutes = float(duration_min or 0)
    if priority == "C":
        return 1 if minutes < 90 else 2
    if minutes < 90:
        return 2
    if minutes < 180:
        return 3
    # Long trail races: roughly one more easy day per extra 2 hours, capped.
    return min(6, 4 + max(0, math.floor((minutes - 240) / 120)))


def pre_race_light_days(priority: str | None) -> int:
    """Lighter days before a race (A races are handled by the taper)."""
    if priority == "B":
        return B_RACE_LIGHT_DAYS
    if priority == "C":
        return C_RACE_LIGHT_DAYS
    return 2


def is_health_reason(reason: Any) -> bool:
    return bool(HEALTH_REASON_RE.search(str(reason or "")))


def _baseline_week_windows(snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    classified = {
        item.get("week_start"): item.get("week_type")
        for item in (snapshot.get("periodization_state") or {}).get("classified_weeks", []) or []
    }
    complete = [
        window
        for window in snapshot.get("weekly_windows") or []
        if not window.get("partial")
        and classified.get(window.get("week_start")) != "in_progress"
    ]
    windows = [window for window in complete[-4:] if float(window.get("minutes") or 0) > 0]
    if not windows:
        return []
    peak = max(float(window["minutes"]) for window in windows)
    loaded = [
        window
        for window in windows
        if classified.get(window.get("week_start")) != "recovery"
        and float(window["minutes"]) >= 0.6 * peak
    ]
    return loaded or windows


def baseline_week_minutes(snapshot: dict[str, Any]) -> float | None:
    """Recent loaded weekly average (min), excluding recovery/illness dips and the running week."""
    windows = _baseline_week_windows(snapshot)
    if not windows:
        return None
    return sum(float(window["minutes"]) for window in windows) / len(windows)


def baseline_week_run_minutes(snapshot: dict[str, Any]) -> float | None:
    """Average non-race running from the same weeks used for the total-time baseline."""
    windows = _baseline_week_windows(snapshot)
    run_weeks = {
        week.get("week_start"): safe_float(week.get("training_run_minutes"))
        for week in (((snapshot.get("training_load") or {}).get("run_load") or {}).get("weeks") or [])
    }
    if not windows or any(
        window.get("week_start") not in run_weeks
        or run_weeks[window.get("week_start")] is None
        for window in windows
    ):
        return None
    return sum(run_weeks[window.get("week_start")] or 0.0 for window in windows) / len(windows)


def safe_float(value: Any) -> float | None:
    try:
        return float(value) if value not in (None, "") else None
    except (TypeError, ValueError):
        return None


def historical_run_volume_allowed(
    snapshot: dict[str, Any], *, readiness: str, load_week: bool
) -> bool:
    """Whether established run history may relax the recent run-volume ceiling."""
    load = snapshot.get("training_load") or {}
    run_load = load.get("run_load") or {}
    baseline = run_load.get("established_baseline") or {}
    if readiness != "green" or not load_week or baseline.get("status") != "available":
        return False
    if (load.get("return_from_break") or {}).get("status") == "returning":
        return False
    if (load.get("ramp") or {}).get("status") in {"elevated", "high"}:
        return False
    if (load.get("overreaching") or {}).get("status") in {"functional", "non_functional_risk"}:
        return False
    if (run_load.get("acwr") or {}).get("status") in {"elevated", "high"} or run_load.get("flags"):
        return False
    weekly = snapshot.get("weekly_checkin") or {}
    pain_scores = weekly.get("pain_scores") or {}
    if isinstance(pain_scores, dict) and any(
        (safe_float(score) or 0) >= 5 for score in pain_scores.values()
    ):
        return False
    if has_niggle(checkin_pain_text(weekly)):
        return False
    if any(flag.get("kind") == "pain" for flag in snapshot.get("activity_note_flags") or []):
        return False
    return True


def effective_run_week_caps(
    snapshot: dict[str, Any], *, allow_historical: bool = False
) -> dict[str, Any]:
    """Shared weekly run limits for the planner, validator and final audit."""
    run_load = ((snapshot.get("training_load") or {}).get("run_load") or {})
    caps = run_load.get("week_caps") or {}
    recent_km = safe_float(run_load.get("avg_weekly_run_km_4w"))
    recent_min = safe_float(run_load.get("avg_weekly_run_min_4w"))
    max_km = safe_float(caps.get("max_run_km"))
    max_min = safe_float(caps.get("max_run_min"))
    recent_limit_km = (
        recent_km * (1 + MAX_WEEKLY_RUN_GROWTH_PCT / 100) if recent_km else None
    )
    recent_limit_min = (
        recent_min * (1 + MAX_WEEKLY_RUN_GROWTH_PCT / 100) if recent_min else None
    )
    if max_km is None:
        max_km = recent_limit_km
    if max_min is None:
        max_min = recent_limit_min

    history = run_load.get("established_baseline") or {}
    historical_km_used = False
    historical_minutes_used = False
    if allow_historical and history.get("status") == "available":
        historical_km = safe_float(history.get("run_km_median"))
        historical_min = safe_float(history.get("run_minutes_median"))
        if historical_km and historical_km * (1 + MAX_WEEKLY_RUN_GROWTH_PCT / 100) > (max_km or 0):
            max_km = historical_km * (1 + MAX_WEEKLY_RUN_GROWTH_PCT / 100)
            historical_km_used = True
        if historical_min and historical_min * (1 + MAX_WEEKLY_RUN_GROWTH_PCT / 100) > (max_min or 0):
            max_min = historical_min * (1 + MAX_WEEKLY_RUN_GROWTH_PCT / 100)
            historical_minutes_used = True
    return {
        "max_run_km": round(max_km, 1) if max_km is not None else None,
        "max_run_min": round(max_min) if max_min is not None else None,
        "historical_used": historical_km_used or historical_minutes_used,
        "historical_km_used": historical_km_used,
        "historical_minutes_used": historical_minutes_used,
    }


def weekly_total_growth_limit(
    snapshot: dict[str, Any],
    *,
    allow_historical: bool = False,
    planned_run_minutes: float = 0.0,
) -> float | None:
    """Recent total-time ceiling plus only the planned running increase history supports."""
    baseline = baseline_week_minutes(snapshot)
    if not baseline:
        return None
    limit = baseline * (1 + MAX_WEEKLY_TOTAL_GROWTH_PCT / 100)
    if allow_historical:
        baseline_run_min = baseline_week_run_minutes(snapshot)
        run_caps = effective_run_week_caps(snapshot, allow_historical=True)
        run_limit = run_caps["max_run_min"]
        if (
            baseline_run_min is not None
            and run_caps["historical_minutes_used"]
            and run_limit is not None
        ):
            supported_run = min(max(0.0, planned_run_minutes), run_limit)
            limit += max(0.0, supported_run - baseline_run_min)
    return limit
