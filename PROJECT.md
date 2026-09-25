# MecroTech Estimating Agent - Project Documentation

## 1. Overview

A small web app that acts like a consultant before a quote. A visitor describes a software project; the agent asks 2-3 clarifying questions, then recommends one of MecroTech's three service tiers and gives a rough, phase-by-phase timeline.

| Tier (from mecro.tech) | Best for |
|---|---|
| **Startup Launch Kit** | Startups, early-stage founders, new launches |
| **Growth Tech Partner** | Growing businesses, SaaS products, digital platforms |
| **Transformation Suite** | SMEs, enterprise teams, digital transformation |

The result is always presented as a **rough, non-binding estimate**. The visitor can opt in to have their details and estimate saved as a lead.

### User flow
1. **Describe** - visitor pastes a project description (minimum 20 characters).
2. **Clarify** - the agent returns 2-3 questions (or a polite redirect if the text is not a tech project).
3. **Estimate** - the agent scores complexity, checks tier details, and submits a recommendation.
4. **Result** - tier, confidence, why, timeline table, assumptions, risks, out of scope, Calendly button.
5. **Lead (optional)** - name, email and a consent tick save the lead to SQLite.

## 2. Tech stack

| Layer | Choice |
|---|---|
| Language | Python 3.11 |
| UI | Streamlit (>=1.40; developed on 1.47) |
| LLM | Google Gemini via the `google-genai` SDK (developed on 2.25). Default model `gemini-3.5-flash-lite` (free tier) |
| Data validation | Pydantic v2 (structured output schema for the questions step) |
| Config | `python-dotenv` (`.env` file) |
| Storage | SQLite (`leads.db`, Python stdlib `sqlite3`) |
| Tests | pytest |

## 3. Setup and commands

Run all commands from the project folder.

### First-time setup
```bash
python -m venv venv
venv\Scripts\activate          # Windows PowerShell / cmd
pip install -r requirements.txt
copy .env.example .env         # then edit .env
```
Get a free API key at https://aistudio.google.com/apikey and set it in **`.env`** (not `.env.example`):
```
GEMINI_API_KEY=your-key-here
# GEMINI_MODEL=gemini-3.5-flash      # optional model override
```

### Run the app
```bash
streamlit run app.py
```
Opens at http://localhost:8501. Restart it after editing `.env`, `config.py`, or prompts.

### Run the tests (no API key needed)
```bash
python -m pytest tests -q
```

### Live evaluation (uses API quota)
```bash
python tests/eval_cases.py
```
Runs 5 sample projects through Gemini and compares the recommended tier with the expected one. The expected tiers are a judgement call, so review them.

### View saved leads
```bash
python -c "import sqlite3; [print(r) for r in sqlite3.connect('leads.db').execute('SELECT id, created_at, name, email FROM leads')]"
```

## 4. Project structure

```
Estimating Agent/
├── app.py              Streamlit UI and session state (3 screens)
├── agent.py            Gemini calls: questions step + tool-calling estimate step
├── tools.py            Deterministic tools: score_complexity, get_tier_details,
│                       calculate_timeline, save_lead, format_weeks
├── config.py           Model, retry limits, tier timelines, complexity rubric
├── tiers.md            Tier scope copied from mecro.tech (source of truth for the model)
├── requirements.txt    Python dependencies
├── .env / .env.example API key and optional model override
├── leads.db            SQLite database, created on first saved lead
├── README.md           Short quick-start
├── PROJECT.md          This document
└── tests/
    ├── test_tools.py        Unit tests for the deterministic tools
    ├── test_agent_loop.py   Tool-calling loop tested with a fake Gemini client
    └── eval_cases.py        Live evaluation against Gemini
```

## 5. How the agent works

### Step 1 - clarifying questions (`agent.generate_questions`)
- One Gemini call with a **structured JSON schema** (`QuestionSet`): `is_project_description`, `redirect_message`, `questions`.
- Off-topic input returns a redirect instead of questions.
- Questions are trimmed to at most 3 and padded with defaults to at least 2.

### Step 2 - estimate with tool calls (`agent.run_estimate`)
Gemini is given three tools and runs a manual loop (max 6 rounds):

| Tool | Purpose |
|---|---|
| `score_complexity(features, stage, scale)` | Scores the project on a fixed rubric and suggests a tier |
| `get_tier_details(tier)` | Returns the official tier scope from `tiers.md` |
| `submit_estimate(...)` | Delivers the final recommendation (used as structured output) |

The loop rejects `submit_estimate` if `score_complexity` was not called first, and nudges the model back to the tools if it replies in prose.

### Things the code enforces (not left to the model)
- **Timeline** is computed in Python from the final tier and complexity score, never taken from the model.
- **Confidence cap**: blank or "not sure" answers give at most *low*; fewer than half answered or a very short description gives at most *medium*.
- **`needs_custom` fit** hides the timeline and points to a consultation.
- **Prices**: never quoted. The prompt forbids it, and no price data exists in the code.
- **Prompt-injection**: client text is wrapped in tags and treated as data.
- **Unknown facts** must be phrased as "to be confirmed", not stated as fact.

### Complexity rubric (`config.py`)
| Feature | Points | Feature | Points |
|---|---|---|---|
| user_auth | 1 | ecommerce_catalog | 2 |
| multi_role_access | 1 | realtime_features | 2 |
| admin_panel | 1 | compliance_security | 2 |
| analytics_reporting | 1 | mobile_app | 3 |
| payments | 2 | third_party_integrations | 3 |
| ai_features | 4 | legacy_migration | 4 |

Scale adds 0 / 1 / 3 points (small / medium / large).
Bands: up to 5 = low (x0.85), up to 10 = medium (x1.0), up to 16 = high (x1.4), above = very high (x1.75).

**Suggested tier rule:** stage `existing_business_systems` or score above 16 gives Transformation Suite; `existing_product` gives Growth Tech Partner; otherwise Startup Launch Kit. The model may override this with a stated reason.

### Timeline
Base weeks per tier are multiplied by the complexity multiplier, then split over five phases: Discovery & Planning 10%, Design 15%, Build & Iterate 50%, QA & Testing 15%, Launch & Delivery 10%. Values are rounded to half weeks.

| Tier | Base range (placeholder) |
|---|---|
| Startup Launch Kit | 4-6 weeks |
| Growth Tech Partner | 6-10 weeks (plus ongoing support) |
| Transformation Suite | 10-16 weeks |

> **These numbers are placeholders.** MecroTech has not published tier timelines; only "launch in ~4 weeks" appears on the site. Replace `TIER_BASE_WEEKS` in `config.py` with real figures.

## 6. Reliability and limits

- **Rate limits / outages:** 429, 500 and 503 errors are retried up to 3 times with exponential backoff; if it still fails the user sees a "busy, try again" message.
- **Caching:** identical requests (same description and answers) are served from an in-memory cache (128 entries) to save quota. The cache is cleared when the server restarts.
- **Concurrency:** each visitor has an isolated Streamlit session. Free-tier request-per-minute limits are the practical ceiling; real traffic needs a paid key.
- **Input caps:** description 4000 characters, each answer 1000 characters.
- **Error messages:** missing key, rejected key, and unavailable model each show a specific message; other errors show a generic one.

## 7. Data and security

- `leads.db` stores name, email, project description, answers and the full estimate as JSON. This is personal data: keep it out of version control and restrict access.
- Leads are saved only after an explicit consent tick.
- The API key must live only in `.env`. Do **not** put a real key in `.env.example`, which is meant to be shared. If a key has been exposed, regenerate it in Google AI Studio.
- `.gitignore` excludes `.env`, `leads.db`, `venv/`, `.venv/`, caches.
- No authentication, encryption at rest, or spam protection is included in v1.

## 8. Customising

| To change | Edit |
|---|---|
| Tier timelines, complexity weights, model, retries | `config.py` |
| Tier descriptions | `tiers.md` (the `## N. Tier Name` headings and `**Includes:**` lines are parsed) |
| Question and estimate prompts | `QUESTIONS_SYSTEM` and `ESTIMATE_SYSTEM` in `agent.py` |
| Result layout and wording | `app.py` |
| Calendly link | `CALENDLY_URL` in `config.py` |

## 9. Known issues and lessons learned

- Google retires Gemini models over time. `gemini-2.5-flash-lite` returned a 404 for new users, so the default is now `gemini-3.5-flash-lite`. If you see "Model ... is not available", set `GEMINI_MODEL` in `.env`.
- Streamlit caches imported modules while running; restart it after changing code or `.env`.
- The estimate quality depends on how detailed the client's answers are.
- Timelines are placeholders until real figures are supplied.

## 10. Not in v1 / possible next steps

- Real timeline and pricing data from MecroTech
- Email the estimate to the client and the team (SMTP or Resend)
- PDF proposal download
- Slack or WhatsApp alert for new leads
- Lookup of similar past projects to ground timelines
- Read the client's existing website URL for context
- Admin page to view and export leads
- Authentication / CAPTCHA and per-user rate limiting
- Deployment (Streamlit Community Cloud or a small VM) with secrets set as environment variables
