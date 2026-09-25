"""Streamlit UI for the MecroTech estimating agent. Run with: streamlit run app.py"""
import streamlit as st

import agent
import config
import tools
from tools import format_weeks

st.set_page_config(page_title="MecroTech Project Estimator", page_icon="🧭", layout="centered")

CONFIDENCE_ICON = {"high": "🟢", "medium": "🟡", "low": "🟠"}


def reset():
    for key in ("stage", "description", "questions", "qa", "result", "lead_saved"):
        st.session_state.pop(key, None)


def show_agent_error(e: Exception):
    if isinstance(e, agent.AgentConfigError):
        st.error(str(e))
    elif isinstance(e, agent.AgentBusyError):
        st.warning("We're getting a lot of requests right now. Please try again in a minute.")
    else:
        st.error("Something went wrong while generating your estimate. Please try again.")
        st.caption(f"{type(e).__name__}")


def bullets(title: str, items: list[str]):
    if items:
        st.markdown(f"**{title}**")
        st.markdown("\n".join(f"- {i}" for i in items))


st.session_state.setdefault("stage", "describe")

with st.sidebar:
    st.markdown("### MecroTech Estimator")
    st.caption("Describe your project, answer a few questions, and get a rough tier and timeline.")
    if st.button("Start over"):
        reset()
        st.rerun()
    st.caption(f"Model: `{config.MODEL}`")

st.title("Project Estimator")

# ---------------------------------------------------------------- stage 1
if st.session_state.stage == "describe":
    st.write("Tell us what you want to build. A few sentences is plenty.")
    description = st.text_area(
        "Project description",
        value=st.session_state.get("description", ""),
        height=180,
        max_chars=agent.MAX_DESCRIPTION_CHARS,
        placeholder="e.g. A marketplace app where local tutors list their services and students book and pay for sessions...",
    )
    if st.button("Continue", type="primary"):
        if len(description.strip()) < 20:
            st.warning("Please add a little more detail (at least a sentence or two).")
        else:
            st.session_state.description = description.strip()
            try:
                with st.spinner("Reading your project..."):
                    result = agent.generate_questions(description)
            except Exception as e:  # noqa: BLE001 - surfaced to the user in a friendly way
                show_agent_error(e)
            else:
                if not result.is_project_description:
                    st.info(result.redirect_message)
                else:
                    st.session_state.questions = result.questions
                    st.session_state.stage = "questions"
                    st.rerun()

# ---------------------------------------------------------------- stage 2
elif st.session_state.stage == "questions":
    st.markdown("**Your project**")
    st.info(st.session_state.description)
    st.write("A few quick questions before we estimate:")

    with st.form("questions_form"):
        answers = [
            st.text_area(q, key=f"answer_{i}", height=80)
            for i, q in enumerate(st.session_state.questions)
        ]
        submitted = st.form_submit_button("Get my estimate", type="primary")

    if submitted:
        qa = list(zip(st.session_state.questions, answers))
        try:
            with st.spinner("Working out your estimate..."):
                estimate = agent.run_estimate(st.session_state.description, qa)
        except Exception as e:  # noqa: BLE001
            show_agent_error(e)
        else:
            st.session_state.qa = qa
            st.session_state.result = estimate
            st.session_state.stage = "result"
            st.rerun()

# ---------------------------------------------------------------- stage 3
else:
    r = st.session_state.result
    fit = r["fit"]

    if fit == "needs_custom":
        st.subheader("This looks like a custom engagement")
        st.write(
            "Your project may fall outside our three standard tracks. "
            "The best next step is a short conversation with the team."
        )
    else:
        if fit == "too_small":
            st.info("Your project looks small - the tier below is the closest match, but you may need less than a full engagement.")
        st.subheader(f"Recommended: {r['tier_name']}")
        st.caption(
            f"{CONFIDENCE_ICON.get(r['confidence'], '')} Confidence: {r['confidence']}"
            f" · Complexity: {r['complexity']['label'].replace('_', ' ')} ({r['complexity']['score']} pts)"
        )
        if r["runner_up_name"]:
            st.caption(f"Runner-up: {r['runner_up_name']}")

    st.write(r["why_this_tier"])

    timeline = r["timeline"]
    if timeline:
        st.markdown(
            f"### Rough timeline: {format_weeks(timeline['total_weeks_min'], timeline['total_weeks_max'])} weeks"
        )
        st.table(
            [
                {"Phase": p["phase"], "Weeks": format_weeks(p["weeks_min"], p["weeks_max"])}
                for p in timeline["phases"]
            ]
        )
        if timeline["ongoing_support"]:
            st.caption("Plus ongoing support after launch, as part of this tier.")

    col1, col2 = st.columns(2)
    with col1:
        bullets("Assumptions", r["assumptions"])
        bullets("Out of scope", r["out_of_scope"])
    with col2:
        bullets("Risks", r["risks"])
    for note in r["complexity"]["notes"]:
        st.caption(f"Note: {note}")

    st.warning(
        "This is a rough, non-binding estimate based on the information you gave. "
        "A consultation will confirm scope, timeline and pricing."
    )
    st.link_button("Book a free 30-minute consultation", config.CALENDLY_URL, type="primary")

    st.divider()
    st.markdown("#### Want us to follow up?")
    if st.session_state.get("lead_saved"):
        st.success("Thanks! Your details and estimate have been saved. We'll be in touch.")
    else:
        with st.form("lead_form"):
            name = st.text_input("Your name")
            email = st.text_input("Email")
            consent = st.checkbox("I agree that MecroTech may contact me about this project.")
            if st.form_submit_button("Save my estimate"):
                if not consent:
                    st.error("Please tick the box so we know it's OK to contact you.")
                else:
                    outcome = tools.save_lead(
                        name,
                        email,
                        st.session_state.description,
                        st.session_state.qa,
                        r,
                    )
                    if outcome["ok"]:
                        st.session_state.lead_saved = True
                        st.rerun()
                    else:
                        st.error(outcome["error"])
