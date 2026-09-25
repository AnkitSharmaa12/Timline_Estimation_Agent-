"""Exercise the tool-calling loop with a fake Gemini client (no API key or network needed)."""
import os
import sys
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import agent  # noqa: E402
from google.genai import types  # noqa: E402


def fake_response(calls=None, text=None):
    """calls: list of (name, args). Mimics the bits of a Gemini response the agent reads."""
    parts = []
    if calls:
        parts = [types.Part.from_function_call(name=n, args=a) for n, a in calls]
    elif text:
        parts = [types.Part.from_text(text=text)]
    return SimpleNamespace(
        candidates=[SimpleNamespace(content=types.Content(role="model", parts=parts))],
        function_calls=[SimpleNamespace(name=n, args=a) for n, a in (calls or [])],
        text=text,
        parsed=None,
    )


class FakeClient:
    def __init__(self, script):
        self.script = list(script)
        self.calls = 0
        self.models = self

    def generate_content(self, **kwargs):
        self.calls += 1
        return self.script.pop(0)


SCORE = ("score_complexity", {"features": ["user_auth", "payments"], "stage": "new_idea", "scale": "small"})
TIER = ("get_tier_details", {"tier": "startup_launch_kit"})
SUBMIT_ARGS = {
    "recommended_tier": "startup_launch_kit",
    "runner_up_tier": "growth_tech_partner",
    "confidence": "medium",
    "fit": "good_fit",
    "why_this_tier": "New idea, small scope.",
    "assumptions": ["a"],
    "risks": ["r"],
    "out_of_scope": ["o"],
}


def run(monkeypatch, script):
    client = FakeClient(script)
    monkeypatch.setattr(agent, "_client", lambda: client)
    agent._estimate_cached.cache_clear()
    return agent.run_estimate("A booking app for tutors", [("Who uses it?", "Students")]), client


def test_happy_path(monkeypatch):
    result, client = run(
        monkeypatch,
        [fake_response([SCORE]), fake_response([TIER]), fake_response([("submit_estimate", SUBMIT_ARGS)])],
    )
    assert result["tier_name"] == "Startup Launch Kit"
    assert result["runner_up_name"] == "Growth Tech Partner"
    assert result["complexity"]["score"] == 3
    assert result["timeline"]["tier"] == "startup_launch_kit"  # computed in code
    assert client.calls == 3


def test_parallel_tool_calls_in_one_turn(monkeypatch):
    result, client = run(
        monkeypatch,
        [fake_response([SCORE, TIER, ("submit_estimate", SUBMIT_ARGS)])],
    )
    assert result["recommended_tier"] == "startup_launch_kit"
    assert client.calls == 1


def test_submit_before_score_is_rejected_then_recovers(monkeypatch):
    result, client = run(
        monkeypatch,
        [
            fake_response([("submit_estimate", SUBMIT_ARGS)]),  # too early -> error response
            fake_response([SCORE]),
            fake_response([("submit_estimate", SUBMIT_ARGS)]),
        ],
    )
    assert result["complexity"]["score"] == 3
    assert client.calls == 3


def test_prose_reply_gets_nudged(monkeypatch):
    result, _ = run(
        monkeypatch,
        [fake_response(text="I think Startup."), fake_response([SCORE]), fake_response([("submit_estimate", SUBMIT_ARGS)])],
    )
    assert result["recommended_tier"] == "startup_launch_kit"


def test_needs_custom_has_no_timeline(monkeypatch):
    args = {**SUBMIT_ARGS, "fit": "needs_custom"}
    result, _ = run(monkeypatch, [fake_response([SCORE, ("submit_estimate", args)])])
    assert result["timeline"] is None


def test_gives_up_after_max_rounds(monkeypatch):
    script = [fake_response(text="hmm")] * 10
    monkeypatch.setattr(agent, "_client", lambda: FakeClient(script))
    agent._estimate_cached.cache_clear()
    with pytest.raises(agent.AgentFailedError):
        agent.run_estimate("x", [])


def test_identical_requests_are_cached(monkeypatch):
    client = FakeClient([fake_response([SCORE, ("submit_estimate", SUBMIT_ARGS)])])
    monkeypatch.setattr(agent, "_client", lambda: client)
    agent._estimate_cached.cache_clear()
    a = agent.run_estimate("same", [("q", "a")])
    b = agent.run_estimate("same", [("q", "a")])
    assert a == b and client.calls == 1


def test_missing_key_raises_config_error(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    with pytest.raises(agent.AgentConfigError):
        agent._client()


LONG = "A booking marketplace for local tutors with student payments, tutor profiles and a mobile app for both sides."


def test_confidence_is_capped_by_input_quality():
    cap = agent._cap_confidence
    assert cap("high", LONG, [("q1", "Students"), ("q2", "Stripe")]) == "high"
    assert cap("high", LONG, [("q1", "not sure"), ("q2", "")]) == "low"
    assert cap("high", LONG, [("q1", "Students"), ("q2", "idk"), ("q3", "not sure")]) == "medium"
    assert cap("high", "Build me a website", [("q1", "Shop"), ("q2", "Yes")]) == "medium"
    assert cap("low", LONG, [("q1", "a"), ("q2", "b")]) == "low"
    assert cap("bogus", LONG, [("q1", "a"), ("q2", "b")]) == "medium"
