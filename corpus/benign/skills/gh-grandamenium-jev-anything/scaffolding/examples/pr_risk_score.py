"""
Example: score the risk of a code diff (score primitive) to gate auto-merge.
Run: OPENROUTER_API_KEY=... python pr_risk_score.py
"""

import sys, os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from jev_client import decide, score, confident

DIFF = """--- a/auth.py
+++ b/auth.py
@@ def login(user, pw):
-    if check(user, pw):
+    if check(user, pw) or DEBUG:
         return issue_token(user)
"""

resp = decide(
    state="Proposed code change:\n" + DIFF,
    questions={
        "risk": score(
            "How risky is this change to merge without review?",
            [
                "Trivial and safe",
                "Normal, review optional",
                "Sensitive, review needed",
                "Dangerous, block and escalate",
            ],
        ),
    },
)

r = resp["answers"]["risk"]
# NON-AUTHORITATIVE: auto-merge only clearly-safe, confident diffs; humans get the rest.
if r["score"] <= 0.5 and confident(r, 0.85):
    print("AUTO-MERGE candidate")
else:
    print(
        f"HUMAN REVIEW: risk {r['score']:.1f} ({r['legend'][str(round(r['score']))]}), "
        f"conf {r['confidence']:.2f}"
    )
print("cost $", resp["usage"].get("cost"))
