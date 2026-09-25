"""Deterministic tools the agent can call. No LLM logic here, so they are easy to test."""
import json
import math
import os
import re
import sqlite3
from datetime import datetime, timezone

import config

_TIERS_PATH = os.path.join(os.path.dirname(__file__), "tiers.md")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _load_tier_sections() -> dict[str, str]:
    """Split tiers.md into one text block per tier key."""
    with open(_TIERS_PATH, encoding="utf-8") as f:
        text = f.read()
    sections = {}
    for key, name in config.TIER_NAMES.items():
        match = re.search(rf"^## \d\. {re.escape(name)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
        sections[key] = f"{name}\n{match.group(1).strip()}" if match else name
    return sections


def get_tier_details(tier: str) -> dict:
    """Return the official scope of a tier so the model never invents it."""
    sections = _load_tier_sections()
    if tier not in sections:
        return {"error": f"Unknown tier '{tier}'. Valid: {config.TIER_KEYS}"}
    return {"tier": tier, "details": sections[tier]}


def score_complexity(features: list[str], stage: str = "new_idea", scale: str = "small") -> dict:
    """Score project complexity from a fixed rubric and suggest a tier."""
    if stage not in config.STAGES:
        stage = "new_idea"
    if scale not in config.SCALE_POINTS:
        scale = "small"

    known = [f for f in dict.fromkeys(features) if f in config.FEATURE_WEIGHTS]
    unknown = [f for f in dict.fromkeys(features) if f not in config.FEATURE_WEIGHTS]

    score = sum(config.FEATURE_WEIGHTS[f][0] for f in known) + config.SCALE_POINTS[scale]
    label = next(name for limit, name, _ in config.COMPLEXITY_BANDS if score <= limit)

    if stage == "existing_business_systems" or score > 16:
        suggested = "transformation_suite"
    elif stage == "existing_product":
        suggested = "growth_tech_partner"
    else:
        suggested = "startup_launch_kit"

    notes = []
    if stage == "new_idea" and score > 10:
        notes.append("Large scope for a first launch - consider phasing the MVP.")
    if stage == "existing_product" and score > 16:
        notes.append("Scope is heavy for a growth engagement; Transformation Suite may fit.")

    return {
        "complexity_score": score,
        "complexity_label": label,
        "matched_features": known,
        "unrecognized_features": unknown,
        "stage": stage,
        "scale": scale,
        "suggested_tier": suggested,
        "notes": notes,
    }


def _half_week(weeks: float) -> float:
    return math.floor(weeks * 2 + 0.5) / 2


def format_weeks(lo: float, hi: float) -> str:
    """'0.5' when the range is a single value, otherwise '1.5-2'."""
    return f"{lo:g}" if lo == hi else f"{lo:g}–{hi:g}"


def calculate_timeline(complexity_score: int, tier: str) -> dict:
    """Turn a tier and complexity score into phase-by-phase week ranges (placeholder numbers)."""
    if tier not in config.TIER_BASE_WEEKS:
        return {"error": f"Unknown tier '{tier}'. Valid: {config.TIER_KEYS}"}

    multiplier = next(m for limit, _, m in config.COMPLEXITY_BANDS if complexity_score <= limit)
    base_min, base_max = config.TIER_BASE_WEEKS[tier]
    total_min = base_min * multiplier
    total_max = base_max * multiplier

    phases = []
    for name, share in config.PHASE_SHARES:
        lo = max(0.5, _half_week(total_min * share))
        hi = max(lo, _half_week(total_max * share))
        phases.append({"phase": name, "weeks_min": lo, "weeks_max": hi})

    return {
        "tier": tier,
        "total_weeks_min": sum(p["weeks_min"] for p in phases),
        "total_weeks_max": sum(p["weeks_max"] for p in phases),
        "phases": phases,
        "ongoing_support": tier in config.ONGOING_SUPPORT_TIERS,
        "complexity_multiplier": multiplier,
        "placeholder_numbers": True,
    }


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.execute(
        """CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            project_description TEXT,
            answers TEXT,
            estimate TEXT
        )"""
    )
    return conn


def save_lead(name: str, email: str, project_description: str, answers: list, estimate: dict) -> dict:
    """Store a lead. Called by the UI only after the visitor opts in."""
    name = (name or "").strip()
    email = (email or "").strip()
    if not name:
        return {"ok": False, "error": "Please enter your name."}
    if not _EMAIL_RE.match(email):
        return {"ok": False, "error": "Please enter a valid email address."}

    conn = _connect()
    try:
        with conn:
            conn.execute(
                "INSERT INTO leads (created_at, name, email, project_description, answers, estimate)"
                " VALUES (?, ?, ?, ?, ?, ?)",
                (
                    datetime.now(timezone.utc).isoformat(timespec="seconds"),
                    name,
                    email,
                    project_description,
                    json.dumps(answers, ensure_ascii=False),
                    json.dumps(estimate, ensure_ascii=False),
                ),
            )
    finally:
        conn.close()
    return {"ok": True}
