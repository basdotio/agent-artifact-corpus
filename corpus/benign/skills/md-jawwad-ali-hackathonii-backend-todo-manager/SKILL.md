---
name: todo-manager
description: Manage Todo operations (Create, Read, Update, Delete) using SQLModel and Postgres. Use when the user wants to organize tasks.
---

# Todo Management Skill

## Executive Summary
This skill governs the lifecycle of Todos in the "Advanced AI-Todo" application. It ensures all operations are persistent, async-ready, and compliant with the project's technical mandates.

## Operational Mandates
1. **Environment First:** ALWAYS run `source .venv/bin/activate` before any backend execution or `uv` command.
2. **Dependency Management:** Use `uv` for all package operations. Never use raw `pip`.
3. **Connectivity:** Connect to Gemini 2.5 Flash using the `AsyncOpenAI` class.
4. **Docs Validation:** Before proposing code changes to `SQLModel` or `FastAPI`, call the `context-7` MCP server to verify the latest async patterns.

## Execution Workflow
- **Step 1: Planning:** Check `SKILLS/SKILL.md` for current project state.
- **Step 2: Documentation:** Query MCP `context-7` for "FastAPI SQLModel Postgres async best practices".
- **Step 3: Implementation:**
    - Use `AsyncOpenAI` for the chatbot logic.
    - Ensure Postgres connection strings are pulled from environment variables.
    - Implement CRUD operations as async functions.
- **Step 4: Verification:** Run tests using `uv run pytest`.

## Examples
- **Input:** "Create a task to buy milk."
- **Action:** Invoke `todo-manager` → Search MCP for SQLModel patterns → Generate async code to insert into Postgres → Confirm with Gemini 2.5 Flash.