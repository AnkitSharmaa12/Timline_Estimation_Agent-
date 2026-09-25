"""Live check against Gemini (uses quota). Run: python tests/eval_cases.py
Feeds sample projects through the agent with canned answers and compares the recommended tier."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import agent  # noqa: E402

CASES = [
    ("I have an idea for an app where freelancers can invoice clients. Nothing built yet.",
     "Freelancers, a few hundred users. Web only. Stripe payments. Want to launch in 2 months.",
     "startup_launch_kit"),
    ("We built a SaaS CRM with 300 paying customers. It's slowing down and we need new reporting features and someone to keep improving it.",
     "Web app, Node backend. No hard deadline. Need ongoing engineering help.",
     "growth_tech_partner"),
    ("Our 15-year-old ERP is a mess. We want to modernize it, connect it to our warehouse and accounting systems and add AI-based demand forecasting.",
     "About 400 internal users, legacy .NET system, must integrate with SAP and Tally.",
     "transformation_suite"),
    ("Landing page for my bakery with opening hours.",
     "Just one page, no logins, no payments.",
     "startup_launch_kit"),
    ("Early-stage marketplace for local tutors with booking, payments and a mobile app.",
     "Students and tutors, iOS and Android, launching in one city first.",
     "startup_launch_kit"),
]


def main():
    hits = 0
    for description, answers, expected in CASES:
        questions = agent.generate_questions(description).questions
        result = agent.run_estimate(description, [(q, answers) for q in questions])
        ok = result["recommended_tier"] == expected
        hits += ok
        print(f"{'PASS' if ok else 'FAIL'} expected={expected} got={result['recommended_tier']} "
              f"({result['confidence']}, fit={result['fit']}) :: {description[:50]}...")
    print(f"\n{hits}/{len(CASES)} matched")


if __name__ == "__main__":
    main()
