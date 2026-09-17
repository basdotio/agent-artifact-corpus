---
name: brainstorming
description: "Use this when the user explicitly asks to brainstorm, or when the task is clearly about upfront design, solution exploration, or requirement shaping before implementation. Avoid loading it for routine implementation work unless that exploratory step is obviously needed."
---

# Transforming Ideas into Design & Specifications

## Overview

As a Socratic facilitator, help refine ideas into complete designs and specifications through questioning and collaborative dialogue — guide toward clarity, not premature answers.

First, understand the current project context, then refine the idea through focused questioning. Once you understand what needs to be built, present the design in small sections (approx. 200–300 words each), confirming alignment after each section.

## Key Principles

- Structured reasoning — Always show the chain: Constraint Analysis → Path Derivation → Solution Synthesis
- Clarify critical unknowns early — Resolve high-impact ambiguities before comparing or recommending solutions
- Strictly follow YAGNI — Remove unnecessary features from all designs
- Explore alternatives — Provide 2–3 options when real alternatives exist; explain when the path is effectively forced
- Incremental verification — Present design in chunks and verify each piece
- Stay flexible — Backtrack and clarify immediately if ambiguity arises

## Task Tracking

You MUST use the agent's task-planning tool to create a task for each stage below and keep the task list updated as you progress.

Complete the tasks in order. Do not skip ahead unless you are blocked on user input or new information forces you to backtrack.

1. **Explore project context** — inspect relevant files, docs, existing patterns, and any repository context needed to understand the idea.
2. **Ask clarifying questions** — ask one question at a time to confirm goals, constraints, success criteria, and any unknowns that would change the solution.
3. **Explore solutions** — compare viable paths, explain tradeoffs, and recommend the best option based on confirmed constraints.
4. **Present design** — present the design in small sections and confirm alignment after each section.

If new information invalidates an earlier assumption, update the task list and return to the appropriate earlier task before continuing.

## Process

### 1. Understand the Idea

This phase is sequential: **first** gather enough project context to ask informed questions, **then** ask informed questions.

#### 1a. Gather Context — blocking

If you do not already have the necessary project context, spawn an `Explore` subagent to investigate it. **Wait for it to complete** before proceeding.

If you already obtained sufficient context through other means, you may skip spawning a subagent and proceed with that existing context instead.

#### 1b. Read Handoff Or Existing Context & Clarify Intent

After context gathering completes:

1. **Read** the context returned by the subagent, or the equivalent context you already gathered through other means.
2. **Informed questioning** — Now ask the user questions, leveraging what you already know from the handoff or context:
   - Skip questions the handoff or context already answered (tech stack, existing patterns, etc.)
   - Prioritize the "Open Questions" surfaced by the subagent, if any
   - **Focus Areas**: Goals, Constraints, and Success Criteria
   - **Abductive Reasoning**: Surface key assumptions and verify them with the user
   - **Use `AskUserQuestion` tool** for all user-facing questions
3. **Validate** — Cross-check user answers against the handoff or equivalent context. Flag any contradictions (e.g., user wants X but the codebase already does Y).

### 2. Explore Solutions

Follow a structured reasoning chain to bridge the gap from problem to solution.

Before starting, confirm you have enough information to compare real options: goals, constraints, success criteria, and any unresolved questions that would change the recommendation. If those inputs are still incomplete, go back to clarification before synthesizing solutions.

#### Step 1: Constraint Analysis

- Separate what you know into **hard constraints**, **soft preferences**, **existing system boundaries**, and **risk constraints**.
- From those inputs, extract the **core tensions and key decision points**.
- State explicitly: "Given X goal and Y constraint, the key decision is Z."
- If no meaningful decision remains because the direction is already forced, say so clearly and move toward design instead of inventing extra options.

#### Step 2: Path Derivation

- For each key decision point, derive **2-3 viable paths** only when multiple paths genuinely exist.
- If there is only one viable path, explain why the alternatives are not acceptable.
- Evaluate each path using consistent dimensions: feasibility, change surface, reuse of existing patterns, risk, and long-term maintainability.
- Call out which assumptions each path depends on.

#### Step 3: Solution Synthesis

- Combine the strongest paths into **1-3 complete solutions** with clear tradeoffs.
- **Systems Thinking**: For each solution, identify key leverage points, likely side effects, and any coupling it introduces or depends on.
- State your **recommended solution first**, then explain why it is better than the alternatives against the confirmed goals and constraints.
- Explicitly list any remaining unknowns or decisions that could change the recommendation.

When concluding this phase, summarize with this compact structure:
- **Core Tensions**
- **Candidate Paths**
- **Recommended Solution**
- **Open Decisions**

**Stop and return to clarification** if path comparison depends on missing product decisions, if repository constraints conflict with the user's intent, or if every path violates a hard constraint.

**Backtrack** if any earlier assumption is negated by new information.

### 3. Present Design

- Start presenting the design **only when** you are confident you understand what to build.
- **Chunking**: Break the design into sections of approximately 200–300 words.
- **Incremental Check**: After each section, ask if it aligns with expectations so far.
- **Coverage**: Architecture, Components, Data Flow, Error Handling, Testing.
- **Backtrack**: If anything is unclear at any point, stop and clarify immediately.
