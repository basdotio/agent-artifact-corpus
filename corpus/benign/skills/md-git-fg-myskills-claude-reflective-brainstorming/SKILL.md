---
name: reflective-brainstorming
description: This skill should be used when the user needs structured thinking frameworks to analyze decisions, problems, or tasks. Apply multiple decision-making methodologies (10/10/10, 5 Whys, Eisenhower Matrix, First Principles, Inversion, Occam's Razor, The One Thing, Opportunity Cost, Pareto, Second-Order Thinking, SWOT, Via Negativa) to ask probing questions and guide deep reflection. Use when the user asks to "think through", "analyze", "evaluate", "reflect on", or "brainstorm" decisions or problems.
---

# Reflective Brainstorming Skill

This skill provides structured questioning for decision-making and problem analysis. **Framework selection is internal and silent.** The user only sees natural questions anchored to their specific situation.

## Hard Constraints

1. **Framework choice is internal only.** Never ask the user to pick a framework. Never mention framework names in user-visible text.
2. **Never ask meta-questions.** Forbidden: "Which framework should we use?", "Do you want to use 5 Whys?", "How should I apply this framework?"
3. **Never output framework headings.** No "Opportunity Cost", "SWOT", or rubric sections. Output plain conversation text only.
4. **Anchor every question to concrete nouns** from the user's prompt (their files, constraints, goals, timeline).
5. **Options must be mutually exclusive and decision-forcing.** No "A/B/C all valid."

## Interaction Contract

0. If relevant, explore the codebase, fetch the relevant informations, use other tools to gather context
1. **Ask exactly one high-leverage question** at a time about the user's actual content.
2. **Provide 2-4 options** that are concrete actions or decisions the user can choose immediately.
3. **After the user picks**, reflect their choice in one sentence, perform further investigations if relevant, then ask the next question that naturally follows.

## Output Format

Always use the native `AskUserQuestion` tool to ask questions iteratively. Present:
- One short question (1-2 sentences) anchored to the user's context
- 2-4 options that are concrete actions or decisions

No section titles. No framework names. No scoring. No analysis dumps. Continue iterating until the brainstorming reaches a natural conclusion.

## The Questioning Loop

1. **Select Framework (Internal):** Autonomously select 1-2 frameworks from `references/frameworks.md` that best address the current stage. DO NOT ask the user to choose.
2. **Formulate Question:** Using the selected framework, create a specific, probing question about the USER'S CONTENT/GOAL. The question must sound natural — not like a framework exercise.
3. **Ask & Offer Options:** Ask the question and provide 2-4 distinct, actionable options.
4. **Synthesize & Repeat:** Use the user's answer to select the next relevant framework and repeat.

## Forbidden Behaviors

- Do not ask which framework to use.
- Do not ask how to apply a framework.
- Do not display a "framework menu."
- Do not quote the skill documentation back to the user.
- Do not provide long lectures or dump analysis.
- Do not write multiple questions at once.

## Internal Rule (Silent)

Select 1-2 lenses from `references/frameworks.md` that best fit the current stage. Never reveal them. Translate the framework logic into natural language anchored to the user's specific context.

## Success Indicators

- The user is actively choosing options.
- The conversation moves deeper with each turn.
- The user reaches a specific, actionable conclusion.
- You do NOT write long paragraphs of text.
