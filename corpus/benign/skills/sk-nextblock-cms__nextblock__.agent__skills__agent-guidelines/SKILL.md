---
name: agent-guidelines
description: When you need to understand the project's core mandate, operational rules, or "Constitution". Use this skill to align with the project's identity and strict coding standards.
---

# Agent Guidelines & Operational Rules

## 1. The "Constitution" & Project Identity

**Project Name:** NextBlock CMS
**Mandate:** Build a premium, Open-Core Next.js CMS.
**Core Stack:** Next.js (App Router), Supabase, Tailwind CSS, Tiptap v3.

### Critical Rules

1.  **Strict Separation:** `libs/ui` and `libs/db` must be publishable as standalone packages. They cannot depend on `apps/nextblock`.
2.  **Open-Core Model:** The core is open-source (AGPL); premium extensions (like E-Commerce) are source-available but license-gated.
3.  **Distribution:** Users get a standalone app via `npm create nextblock`.

## 2. Operational Rules (Global Context)

- **Context First:** Before answering complex questions, always check `docs/` (start with `docs/README.md`) and the relevant linked docs.
- **Maintain the Docs:** When you implement a new feature or make significant changes, **update the relevant doc files in `docs/`**. These are the maintained reference set for both contributors and AI agents. Keep them accurate and current.
- **Production Migrations:** NextBlock has live data. Never rewrite existing migrations for production/shared database changes. Add a new non-destructive migration, run/check `npm run db:migrate:check`, and never use reset/fresh/sandbox replay commands against databases containing orders, users, payments, or customer data.
- **Strict Types:** Always use `strict: true` TypeScript. No `any` unless absolutely unavoidable and documented.
- **Target the App, Not the Template:** NEVER edit files in `apps/create-nextblock/templates/nextblock-template` directly. Always make changes in `apps/nextblock` (the core app). The template is synced from the core app via scripts.
- **Never Edit Generated Sandbox SQL:** NEVER manually edit `apps/nextblock/app/api/cron/reset-sandbox/sandboxResetSql.ts`. This file is auto-generated from the migration folder. Run `npm run generate:sandbox` to regenerate it.

## 3. Documentation Access

- **Always** use the **`context7` MCP tool** to fetch the latest documentation for any library or framework you need (Next.js, Supabase, Nx, Tailwind, Tiptap, etc.).
- Do not guess about API surfaces or recent changes; **verify with `context7` first**.

## 4. Project Knowledge Source (NotebookLM)

> [!TIP]
> **Use this for:** High-level roadmap, monetization strategy, and architectural "why" questions.
> **Notebook:** NextBlock CMS: Roadmap and Monetization Strategy

When you need deep context about the project's direction or specific architectural decisions not explained in the code, use the NotebookLM MCP tools:

1. **Query the Notebook:** Use `mcp_notebooklm_ask_question` with your question.
2. **Browse notebooks:** Use `mcp_notebooklm_list_notebooks` to see all available notebooks.
3. **Cite the source:** Mention that the info came from the project roadmap notebook.
