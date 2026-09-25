"""Central settings for the estimating agent. Edit the numbers here, not in the code."""
import os

from dotenv import load_dotenv

load_dotenv()

# Free-tier friendly default. Override with GEMINI_MODEL in .env (e.g. gemini-2.5-flash).
MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

CALENDLY_URL = "https://calendly.com/mecrotechnologya/30min"
DB_PATH = os.path.join(os.path.dirname(__file__), "leads.db")

MAX_TOOL_ROUNDS = 6  # safety cap on the tool-calling loop
MAX_RETRIES = 3  # retries on rate-limit / transient errors

TIER_KEYS = ["startup_launch_kit", "growth_tech_partner", "transformation_suite"]
TIER_NAMES = {
    "startup_launch_kit": "Startup Launch Kit",
    "growth_tech_partner": "Growth Tech Partner",
    "transformation_suite": "Transformation Suite",
}

# ---------------------------------------------------------------------------
# PLACEHOLDER timelines (weeks) - MecroTech has not published real numbers.
# Replace with real figures. Only the "launch in ~4 weeks" claim comes from the site.
# ---------------------------------------------------------------------------
TIER_BASE_WEEKS = {
    "startup_launch_kit": (4, 6),
    "growth_tech_partner": (6, 10),
    "transformation_suite": (10, 16),
}

# Share of total time spent in each phase (matches the site's "How We Work" steps).
PHASE_SHARES = [
    ("Discovery & Planning", 0.10),
    ("Design", 0.15),
    ("Build & Iterate", 0.50),
    ("QA & Testing", 0.15),
    ("Launch & Delivery", 0.10),
]

# Growth Tech Partner includes ongoing support; the others only mention it as a final step.
ONGOING_SUPPORT_TIERS = {"growth_tech_partner"}

# ---------------------------------------------------------------------------
# Complexity rubric: feature key -> (points, description)
# ---------------------------------------------------------------------------
FEATURE_WEIGHTS = {
    "user_auth": (1, "Sign-up / login / accounts"),
    "multi_role_access": (1, "Multiple user roles and permissions"),
    "admin_panel": (1, "Admin dashboard / back office"),
    "payments": (2, "Payments, subscriptions or billing"),
    "mobile_app": (3, "Native or cross-platform mobile app"),
    "third_party_integrations": (3, "Integrations with external APIs / CRM / ERP"),
    "realtime_features": (2, "Chat, live updates, notifications, collaboration"),
    "ecommerce_catalog": (2, "Product catalog, cart, inventory"),
    "analytics_reporting": (1, "Dashboards, reports, tracking"),
    "ai_features": (4, "AI agents, automation, LLM features"),
    "legacy_migration": (4, "Migrating / modernizing an existing system"),
    "compliance_security": (2, "Compliance, audit, high-grade security needs"),
}

SCALE_POINTS = {"small": 0, "medium": 1, "large": 3}

# Complexity score -> label and timeline multiplier
COMPLEXITY_BANDS = [
    (5, "low", 0.85),
    (10, "medium", 1.0),
    (16, "high", 1.4),
    (10**6, "very_high", 1.75),
]

STAGES = ["new_idea", "existing_product", "existing_business_systems"]
