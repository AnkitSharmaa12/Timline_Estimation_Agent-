# MecroTech Estimating Agent

Describe a project → the agent asks 2–3 clarifying questions → it recommends a tier
(Startup Launch Kit / Growth Tech Partner / Transformation Suite) with a rough timeline.

## Setup
```bash
pip install -r requirements.txt
copy .env.example .env        # then paste your free key from https://aistudio.google.com/apikey
streamlit run app.py
```

## How it works
1. `generate_questions` (Gemini, structured JSON) → 2–3 questions, or a polite redirect if off-topic.
2. `run_estimate` (Gemini + tool calls): `score_complexity` → `get_tier_details` → `submit_estimate`.
3. The timeline is computed in Python (`calculate_timeline`) from the final tier, never by the model.
4. The visitor can opt in to `save_lead` (SQLite `leads.db`).

## Files
- `config.py` – model, tier timelines (**placeholders – edit these**), complexity rubric
- `tiers.md` – tier scope, taken from mecro.tech
- `tools.py` – deterministic tools · `agent.py` – Gemini calls · `app.py` – Streamlit UI
- `tests/` – `pytest tests` (no API key needed) · `python tests/eval_cases.py` (live, uses quota)

## Notes
- Model defaults to `gemini-3.5-flash-lite`; change with `GEMINI_MODEL` in `.env`.
- Free-tier rate limits apply. 429s are retried with backoff; identical requests are cached.
- Leads in `leads.db` contain personal data - keep it out of git (already in `.gitignore`).
