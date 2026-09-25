import json
import os
import sqlite3
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config  # noqa: E402
import tools  # noqa: E402


def test_tier_details_come_from_tiers_md():
    for key in config.TIER_KEYS:
        d = tools.get_tier_details(key)
        assert config.TIER_NAMES[key] in d["details"]
        assert "Includes" in d["details"]
    assert "MVP Development" in tools.get_tier_details("startup_launch_kit")["details"]
    assert "AI Automation" in tools.get_tier_details("transformation_suite")["details"]


def test_unknown_tier_returns_error():
    assert "error" in tools.get_tier_details("platinum")
    assert "error" in tools.calculate_timeline(5, "platinum")


def test_score_and_suggested_tier():
    r = tools.score_complexity(["user_auth", "payments"], "new_idea", "small")
    assert r["complexity_score"] == 3
    assert r["complexity_label"] == "low"
    assert r["suggested_tier"] == "startup_launch_kit"

    r = tools.score_complexity(["user_auth", "payments"], "existing_product", "medium")
    assert r["suggested_tier"] == "growth_tech_partner"

    r = tools.score_complexity(["legacy_migration", "ai_features"], "existing_business_systems", "large")
    assert r["suggested_tier"] == "transformation_suite"


def test_score_handles_bad_input():
    r = tools.score_complexity(["user_auth", "user_auth", "teleportation"], "???", "huge")
    assert r["complexity_score"] == 1  # duplicate ignored, unknown ignored, defaults used
    assert r["unrecognized_features"] == ["teleportation"]
    assert r["stage"] == "new_idea" and r["scale"] == "small"


def test_timeline_is_consistent():
    t = tools.calculate_timeline(8, "startup_launch_kit")
    assert t["total_weeks_min"] == sum(p["weeks_min"] for p in t["phases"])
    assert t["total_weeks_max"] == sum(p["weeks_max"] for p in t["phases"])
    assert all(p["weeks_min"] >= 0.5 and p["weeks_max"] >= p["weeks_min"] for p in t["phases"])
    assert t["total_weeks_min"] <= t["total_weeks_max"]


def test_timeline_grows_with_complexity_and_tier():
    low = tools.calculate_timeline(3, "startup_launch_kit")
    high = tools.calculate_timeline(20, "startup_launch_kit")
    assert high["total_weeks_max"] > low["total_weeks_max"]
    assert (
        tools.calculate_timeline(8, "transformation_suite")["total_weeks_max"]
        > tools.calculate_timeline(8, "startup_launch_kit")["total_weeks_max"]
    )
    assert tools.calculate_timeline(8, "growth_tech_partner")["ongoing_support"] is True


def test_save_lead(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "DB_PATH", str(tmp_path / "leads.db"))
    assert tools.save_lead("", "a@b.com", "d", [], {})["ok"] is False
    assert tools.save_lead("Asha", "not-an-email", "d", [], {})["ok"] is False

    out = tools.save_lead("Asha", "asha@example.com", "An app", [("Q?", "A")], {"tier": "x"})
    assert out["ok"] is True
    row = sqlite3.connect(config.DB_PATH).execute("SELECT name, email, estimate FROM leads").fetchone()
    assert row[0] == "Asha" and row[1] == "asha@example.com"
    assert json.loads(row[2]) == {"tier": "x"}


def test_format_weeks_collapses_equal_ranges():
    assert tools.format_weeks(0.5, 0.5) == "0.5"
    assert tools.format_weeks(1.5, 2.0) == "1.5\u20132"
    assert tools.format_weeks(1, 1) == "1"


def test_heavy_features_score_higher():
    r = tools.score_complexity(["mobile_app", "ai_features", "third_party_integrations"], "existing_business_systems", "medium")
    assert r["complexity_score"] == 11 and r["complexity_label"] == "high"
