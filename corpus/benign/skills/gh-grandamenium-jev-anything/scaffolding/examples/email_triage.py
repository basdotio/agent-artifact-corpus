"""
Example: lead/email triage with Jev (choice + noul + score in one call).
Run: OPENROUTER_API_KEY=... python email_triage.py
Copy jev_client.py next to this file (or adjust the import).
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from jev_client import decide, noul, choice, score, confident

INBOUND = (
    "Hi, we're a 40-person team evaluating your Pro plan and want a demo this week."
)

resp = decide(
    state=INBOUND,
    questions={
        "is_lead": noul("Is this a sales lead worth a human follow-up?"),
        "segment": choice(
            "Which segment?",
            {
                "smb": "Small team, self-serve",
                "midmarket": "Growing company, wants a demo",
                "enterprise": "Large org, procurement/security involved",
                "not_a_lead": "Support, spam, or irrelevant",
            },
        ),
        "urgency": score(
            "How time-sensitive is this?", ["Whenever", "This month", "This week"]
        ),
    },
)

a = resp["answers"]
# NON-AUTHORITATIVE: Jev decides, your code acts. Route only on confident answers.
if a["is_lead"]["noul"] >= 0.7 and confident(a["segment"], 0.7):
    print(
        f"ROUTE -> {a['segment']['choice']} (conf {a['segment']['confidence']:.2f}), "
        f"urgency {a['urgency']['score']:.1f}"
    )
else:
    print("ESCALATE to a human: low confidence")
print("cost $", resp["usage"].get("cost"))
