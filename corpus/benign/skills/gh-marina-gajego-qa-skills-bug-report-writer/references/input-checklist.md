# Input Checklist

The skill works best when the bug was **already analyzed** by a person: it was reproduced, there is evidence, and the expected behavior is known. These are the inputs that make a report complete without guessing anything.

Missing inputs do not block the skill: as long as the expected behavior has a source, it writes the report with `⚠️ NOT PROVIDED` markers and asks for the gaps at the end. Only a missing or unsourced expected result changes the path (suspected bug).

## 🔴 Required — the report is not complete without them

| Input | What it is | Example |
|---|---|---|
| **Steps performed** | The exact actions taken during the test, in order | "logged in as QA_USER_01, opened PIX, typed 5000, clicked Confirm" |
| **Where it happens** | The interface where it shows up: UI screen path / URL, API method + endpoint + response, DB schema/table/query + error, queue/topic + message ID, job name + run ID… | "Menu > Extrato > Filtrar por período" · "POST /api/v2/orders → 500, body {...}" |
| **Actual result** | What happened, including messages shown | "went straight to the receipt, no token requested" |
| **Expected result + source** | What should happen and where that comes from | "should ask for MFA — RN2: transfers above R$ 1,000" |
| **Environment** | Where it was tested: env, service/app version or build, and whatever runtime applies (OS, device/browser, DB, broker…) | "staging, Android app 4.12.0, Samsung S23 / Android 14" |
| **Evidence** | At least one: screenshot, video, log, request/response, failed test output | `receipt.png`, log excerpt |

If the expected result has **no source** (requirement, story, spec, previous behavior, a failing assertion, or an explicit statement from the user), the skill does not decide on its own what "correct" is — that is a suspected bug, not a report.

## 🟡 Recommended — they make the report stronger

| Input | Example |
|---|---|
| Preconditions / test data | user profile, balance, feature flags |
| Technical identifiers | Correlation-ID, transaction ID, endpoint, status code |
| Logs / payloads | request body, response body, stack trace |
| Reproducibility | "5 out of 5 attempts" |
| Scope already checked | "also on iOS, not on Web" |
| How it was found | exploratory, regression, automation, production |

## ⚪ Optional

Related story/ticket, module/component name, labels, known workaround, severity/priority defined by the team, reporter's hypothesis about the cause.

## Fill-in template for the user

Users can paste this to the agent and fill in what they have:

```text
Module/feature:
Where it happens — the interface involved (screen path/URL, API method + endpoint + response, DB schema/query + error, queue/topic + message ID, job + run ID…):
Environment (env, version/build, and runtime that applies: OS, device/browser, DB, broker…):
Preconditions / test data:
Steps performed:
1.
2.
Actual result:
Expected result:
Source of the expected result (story, rule, spec, previous behavior):
Evidence (attach files or paste logs/payloads):
Technical IDs (Correlation-ID, transaction, endpoint):
Reproducibility (x out of y):
Scope checked (other platforms, environments, interfaces):
Severity (if already defined):
Notes / workaround / hypothesis:
```
