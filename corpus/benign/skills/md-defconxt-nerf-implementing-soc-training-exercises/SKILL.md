<!-- Copyright (c) 2026 defconxt. All rights reserved. -->
<!-- Licensed under AGPL-3.0 — see LICENSE file for details. -->
---
name: implementing-soc-training-exercises
description: >-
  SOC training exercise design and execution including tabletop exercises,
  simulated incident injection, purple team drills, skill assessment matrices,
  analyst certification tracking, and readiness evaluation across real SIEM
  environments with controlled attack scenarios.
domain: cybersecurity
subdomain: soc-operations
tags:
  - soc-training
  - tabletop
  - simulation
  - purple-team
  - skill-assessment
  - exercises
  - readiness
version: "1.0"
author: defconxt
license: AGPL-3.0
metadata:
  mitre-attack: []
---

# Implementing SOC Training Exercises

## Overview

Regular training exercises maintain analyst readiness, validate procedures,
and identify skill gaps before real incidents expose them. Exercises range
from discussion-based tabletops to live-fire simulated attacks. This skill
covers exercise design, execution, and effectiveness measurement.

## Prerequisites

| Requirement | Purpose |
|---|---|
| SIEM with test/training environment | Safe exercise execution |
| Attack simulation tools (Atomic Red Team/Caldera) | Controlled TTPs |
| Exercise coordinator | Scenario management |
| Scoring rubric | Objective performance evaluation |

## Key Concepts

### Exercise Types

```
TRAINING EXERCISE SPECTRUM:
├── Tabletop — Discussion-based scenario walkthrough
│   Duration: 1-2 hours | Disruption: None
│   Goal: Validate procedures, identify decision gaps
├── Inject Exercise — Simulated alerts in training SIEM
│   Duration: 2-4 hours | Disruption: Low
│   Goal: Practice triage, escalation, and documentation
├── Purple Team Drill — Red team executes, blue team detects
│   Duration: 4-8 hours | Disruption: Medium
│   Goal: Validate detection coverage and response capability
├── Live-Fire Exercise — Real attack simulation in production
│   Duration: 1-3 days | Disruption: High
│   Goal: Full operational readiness assessment
└── Capture the Flag — Gamified forensic challenges
    Duration: 2-8 hours | Disruption: None
    Goal: Skill development and team building
```

### Skill Assessment Matrix

```
ANALYST COMPETENCY LEVELS:
├── L1 (Junior) — Alert Triage
│   □ Navigate SIEM alert queue
│   □ Perform basic IOC enrichment
│   □ Apply disposition codes correctly
│   □ Escalate within SLA
│   □ Document investigation notes
├── L2 (Mid) — Investigation
│   □ Correlate alerts across data sources
│   □ Reconstruct attack timeline
│   □ Perform EDR investigation
│   □ Execute containment actions
│   □ Write incident reports
├── L3 (Senior) — Advanced Operations
│   □ Conduct proactive threat hunts
│   □ Develop detection rules
│   □ Perform malware analysis
│   □ Lead incident response
│   □ Mentor junior analysts
└── Assessment Scale: 1 (None) → 5 (Expert)
```

### Tabletop Scenario Template

```
EXERCISE: [Name]
DATE: YYYY-MM-DD | DURATION: [Est. hours]
PARTICIPANTS: [Roles required]

SCENARIO BRIEFING:
  [Background context and initial conditions]

INJECT 1 — [Time offset from start]
  Stimulus: [What participants receive/observe]
  Expected Actions: [What good response looks like]
  Discussion Points: [Decision points to explore]

INJECT 2 — [Time offset]
  Stimulus: [Escalation or new information]
  Expected Actions: [Escalated response]
  Discussion Points: [Policy/process questions]

INJECT 3 — [Time offset]
  Stimulus: [Complication or scope expansion]
  Expected Actions: [Management engagement, comms]
  Discussion Points: [Organizational response]

HOT WASH (immediately after):
  - What went well?
  - What needs improvement?
  - What surprised you?
  - What procedures need updating?
```

### Atomic Red Team Integration

```bash
# Execute specific ATT&CK technique for training
Invoke-AtomicTest T1059.001 -TestNumbers 1 -GetPrereqs
Invoke-AtomicTest T1059.001 -TestNumbers 1

# MITRE Caldera — start operation for exercise
curl -s -X POST "${CALDERA_URL}/api/v2/operations" \
  -H "KEY: ${CALDERA_API_KEY}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "SOC Training Exercise",
    "adversary": {"adversary_id": "training-apt"},
    "planner": {"id": "atomic"},
    "source": {"id": "training-facts"}
  }'
```

### Exercise Scoring Rubric

```
SCORING DIMENSIONS (1-5 per item):
  Detection Speed   — Time from inject to analyst awareness
  Triage Accuracy   — Correct disposition and severity
  Investigation Depth — Completeness of analysis
  Containment Speed — Time from confirmation to containment
  Documentation     — Quality and completeness of notes
  Communication     — Appropriate escalation and notification
  Procedure Compliance — Adherence to runbooks and SOPs

OVERALL SCORE:
  35-30: Excellent — Ready for production operations
  29-25: Good — Minor gaps, targeted training needed
  24-18: Needs Improvement — Significant gaps identified
  17-7:  Below Standard — Structured remediation required
```

## Workflow

1. **Plan** — Select exercise type based on training objectives
2. **Design** — Build scenario with injects and scoring criteria
3. **Prepare** — Stage environment, brief facilitators, notify participants
4. **Execute** — Run exercise with injects per timeline
5. **Observe** — Record analyst actions, timing, and decisions
6. **Debrief** — Hot wash immediately, formal AAR within 1 week
7. **Improve** — Update training plan based on identified gaps

## Verification

| Check | Method |
|---|---|
| Exercise objectives met | Post-exercise survey and scoring |
| Skill gaps identified | Assessment matrix delta from previous |
| Procedures validated | Runbook accuracy confirmed or updates filed |
| Detection gaps found | New rules created from exercise findings |
| Training plan updated | Gap-based training scheduled within 30 days |
