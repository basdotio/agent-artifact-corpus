"""
setup_wizard.py — Conversational setup wizard for agentic governance.

Per Section 9 of the ratified spec (docs/agentic-governance-spec.md):

- The wizard is CONVERSATIONAL, not a script. It is exposed through the MCP
  server as tools the operator's agent invokes. Questions are asked natively
  in whatever tool the operator is using, with labeled options wherever the
  answer set is bounded. Nothing is filled in by hand; no config file is
  authored manually.
- Answers are written to config/setup.md and config/roster.md.
- The final step generates one persona block per roster row into
  config/personas/ (Section 9.4 template).
- It is re-runnable. Absent or incomplete config is the UNKNOWN state; the
  wizard never defaults a value.

State machine: two MCP tools drive it.
  - setup_wizard_start()   -> begins (or resumes) the wizard, returns the
                              first (or next pending) question.
  - setup_wizard_answer(v) -> records the answer to the current question and
                              returns the next question, or the completion
                              summary when all questions are done.

State is persisted to config/.wizard-state.json so a long-running or restarted
server can resume mid-wizard, and so an incomplete config is never mistaken
for a complete one.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

# --- constants ---------------------------------------------------------------

PRIVATE_NOTES_MODES = ["private_git", "local_folder"]
PRIVATE_NOTES_SKELETON = Path("docs") / "templates" / "private-notes"
PRIVATE_NOTES_SCAFFOLD = Path("config") / "private-notes"

BUDGET_MODELS = ["metered", "billed", "not-yet-known"]
ADVERSARIAL_STATES = ["in-play", "not-in-play"]
MULTI_TEAM_CHOICES = ["yes", "no"]
NETWORK_PERMISSIONS = ["allow", "deny", "unknown"]

# --- BYODS: bring your own design system --------------------------------------
# Wizard sources: the operator's own design system (link), a predefined
# codified design system (start building immediately), or a custom build
# (fonts, colors, data-viz colors, brand voice walked through in the wizard).
DS_SOURCES = ["i-have-a-link", "choose-predefined", "build-custom", "skip"]

# Predefined codified design systems. Astryx is Meta's open-source,
# agent-ready system (MCP tooling for agentic IDEs) — the recommended
# default when agents author the UI. URLs verified live 2026-09-29.
DS_PRESETS: dict[str, tuple[str, str]] = {
    "astryx": (
        "Astryx (Meta) — agent-ready, MCP tooling, recommended",
        "https://github.com/facebook/astryx",
    ),
    "material": ("Material Design (Google)", "https://m3.material.io"),
    "carbon": ("Carbon (IBM)", "https://carbondesignsystem.com"),
    "spectrum": ("Spectrum (Adobe)", "https://spectrum.adobe.com"),
    "atlassian": ("Atlassian Design System", "https://atlassian.design"),
    "polaris": ("Polaris (Shopify)", "https://polaris.shopify.com"),
    "primer": ("Primer (GitHub)", "https://primer.style"),
}

# Font recommendations are free Google Fonts (custom always allowed).
DS_FONTS_PRIMARY = [
    "Inter (recommended)",
    "Roboto",
    "Open Sans",
    "Lato",
    "DM Sans",
    "Source Sans 3",
    "IBM Plex Sans",
    "custom",
]
DS_FONTS_SECONDARY = [
    "Space Grotesk",
    "Poppins",
    "Playfair Display",
    "IBM Plex Serif",
    "Source Serif 4",
    "custom",
]

# Curated starter palettes for operators without brand colors.
# Primaries are text-safe: >= 4.5:1 contrast on white (WCAG AA), verified by
# computation 2026-09-29. Secondaries/tertiaries are accent-grade (large
# elements, graphics — not body text).
DS_PALETTES: dict[str, tuple[str, str, str, str]] = {
    "ocean": ("Ocean", "#0B5FFF", "#00A6B6", "#FF6B4A"),
    "forest": ("Forest", "#1B7A3D", "#5B8C2A", "#D97706"),
    "plum": ("Plum", "#7C3AED", "#DB2777", "#F59E0B"),
    "ink": ("Ink", "#1F2937", "#4B5563", "#2563EB"),
    "teal": ("Teal", "#0F766E", "#0284C7", "#EA580C"),
}

# CVD-safe (color-vision-deficiency) data-viz palette, recommended default:
# Okabe–Ito, the standard colorblind-safe qualitative set.
DS_VIZ_OKABE_ITO = [
    "#E69F00",
    "#56B4E9",
    "#009E73",
    "#F0E442",
    "#0072B2",
    "#D55E00",
    "#CC79A7",
    "#000000",
]
DS_VIZ_CHOICES = ["okabe-ito (CVD-safe, recommended)", "custom"]

# Brand voice styles offered in the wizard. "i-have-one-already" lets the
# operator paste sample text now or defer it to the first project kickoff.
BRAND_VOICES = [
    "direct-founder — plain-spoken, first person, no fluff",
    "warm-expert — knowledgeable, encouraging, jargon-free",
    "playful-challenger — witty, bold, anti-establishment",
    "minimal-luxury — quiet, precise, confident",
    "technical-precision — exact, terse, spec-like",
    "community-coach — inclusive, motivating, practical",
    "i-have-one-already",
]

# Scope: the recorded design system is either the default every new project
# starts from (fast development), or re-run per project at kickoff.
DS_SCOPES = ["default", "per-project"]

# --- BYODS detail tokens (quick setup vs define-each) -------------------------
# After the core custom build (fonts, colors, viz, voice), the operator picks
# "quick" (recommended values below, no further questions) or "define-each"
# (walk through every token). Every question offers its recommended value.
DS_DETAIL_MODES = ["quick (recommended)", "define-each"]

# Neutral ramps: bg / surface / text / muted / border, light + dark.
# (Slate-, stone-, and neutral-flavored ramps; hexes are fixed constants.)
DS_NEUTRALS: dict[str, tuple[str, dict[str, str], dict[str, str]]] = {
    "cool-gray": (
        "Cool gray",
        {"bg": "#F8FAFC", "surface": "#FFFFFF", "text": "#0F172A",
         "muted": "#64748B", "border": "#E2E8F0"},
        {"bg": "#0F172A", "surface": "#1E293B", "text": "#F1F5F9",
         "muted": "#94A3B8", "border": "#334155"},
    ),
    "warm-gray": (
        "Warm gray",
        {"bg": "#FAFAF9", "surface": "#FFFFFF", "text": "#1C1917",
         "muted": "#78716C", "border": "#E7E5E4"},
        {"bg": "#1C1917", "surface": "#292524", "text": "#FAFAF9",
         "muted": "#A8A29E", "border": "#44403C"},
    ),
    "true-neutral": (
        "True neutral",
        {"bg": "#FAFAFA", "surface": "#FFFFFF", "text": "#171717",
         "muted": "#737373", "border": "#E5E5E5"},
        {"bg": "#0A0A0A", "surface": "#171717", "text": "#FAFAFA",
         "muted": "#A3A3A3", "border": "#262626"},
    ),
}
DS_NEUTRAL_CHOICES = [
    "cool-gray (recommended)", "warm-gray", "true-neutral", "custom",
]
DS_DARK_MODES = [
    "auto (recommended) — light + dark ramps",
    "light-only",
    "dark-only",
    "custom",
]
DS_RADIUS_STYLES = ["rounded (recommended) — 8px", "sharp — 2px", "pill — full", "custom"]
DS_RADIUS_VALUES = {"rounded": "8px", "sharp": "2px", "pill": "9999px"}
DS_ICON_SETS = ["lucide (recommended)", "material-symbols", "heroicons", "custom"]
DS_TYPE_SCALE_DEFAULT = [12, 14, 16, 20, 24, 32, 48]
DS_TYPE_SCALE_CHOICES = ["recommended — 12/14/16/20/24/32/48px", "custom"]
DS_SPACING_CHOICES = ["8pt grid (recommended)", "4pt grid", "custom"]
DS_SPACING_DEFAULT = "8pt grid"
DS_SHADOW_CHOICES = ["subtle (recommended)", "none", "pronounced", "custom"]
DS_SHADOW_DEFAULT = "subtle"
DS_MOTION_CHOICES = [
    "subtle (recommended) — 150–250ms ease-out, honors prefers-reduced-motion",
    "none",
    "expressive",
    "custom",
]
DS_MOTION_DEFAULT = "subtle — 150–250ms ease-out, honors prefers-reduced-motion"
DS_BREAKPOINTS_DEFAULT = [640, 768, 1024, 1280]
DS_BREAKPOINTS_CHOICES = ["recommended — 640/768/1024/1280px", "custom"]

# Shown next to every operator-facing spend/budget number (same surface).
SPEND_UNIT_QUALIFIER = (
    "This framework cannot see or limit what you spend with your model provider. "
    "Set a hard spending cap in your provider's billing console. "
    "This cap counts framework units only."
)

# The question flow. Each entry:
#   id        – stable key under which the answer is stored
#   question  – the prompt shown to the operator
#   options   – None for free text, else a list of labeled choices
#   repeated  – True for roster rows (asked until the operator sends "done")
WIZARD_FLOW: list[dict[str, Any]] = [
    {
        "id": "runtime",
        "question": "What tool or system runs your AI agents? (Examples: Claude Code, Cursor, external runtime, ChatGPT, a custom setup. This only affects how each agent's instructions are wrapped — it never changes the rules.)",
        "options": None,
    },
    {
        "id": "engine",
        "question": "Which engine orchestrates your agents? (BYOE — bring your own engine. Limen is the recommended default: a one-human-many-agents harness built from files, git, and one CLI. Or bring your own: Claude Code, Cursor, Paperclip, a custom setup. The framework's harnesses and adversarial review govern any engine.)",
        "options": ["limen", "claude-code", "cursor", "paperclip", "custom"],
    },
    {
        "id": "budget_model",
        "question": (
            "How do you want to control how much work the agents can do? "
            "(metered = a set allowance of framework-visible units that resets on a schedule; "
            "billed = a numeric ceiling on those same units; not-yet-known = you'll decide later). "
            + SPEND_UNIT_QUALIFIER
        ),
        "options": BUDGET_MODELS,
    },
    # conditional sub-questions (only presented when budget_model == their key)
    {
        "id": "metered_allowance",
        "if_budget": "metered",
        "question": (
            "Metered: how many framework-visible units are allowed per cycle? "
            "(A number that resets on the schedule you set below.) "
            + SPEND_UNIT_QUALIFIER
        ),
        "options": None,
    },
    {
        "id": "metered_reset_cadence",
        "if_budget": "metered",
        "question": "Metered: how often does the allowance reset? (e.g. weekly, monthly)",
        "options": None,
    },
    {
        "id": "metered_headroom",
        "if_budget": "metered",
        "question": (
            "Metered: how much of the allowance should be held back for work already "
            "in progress, so it doesn't get cut off mid-task? "
            + SPEND_UNIT_QUALIFIER
        ),
        "options": None,
    },
    {
        "id": "billed_cap",
        "if_budget": "billed",
        "question": (
            "Billed: what numeric ceiling of framework-visible units should gated MCP "
            "operations refuse at? "
            + SPEND_UNIT_QUALIFIER
        ),
        "options": None,
    },
    {
        "id": "billed_escalation_threshold",
        "if_budget": "billed",
        "question": (
            "Billed: at what percentage of the framework-unit ceiling should the system "
            "warn you before it's reached? "
            + SPEND_UNIT_QUALIFIER
        ),
        "options": None,
    },
    {
        "id": "per_epic_budget",
        "question": (
            "How many framework-visible units may a single project (an 'epic') use "
            "before the system warns? "
            + SPEND_UNIT_QUALIFIER
        ),
        "options": None,
    },
    {
        "id": "multi_team",
        "question": "Will you run more than one project or team at once? (yes = more than one team or project in parallel; a Chief of Staff (Cos) is required and is the only role that surfaces decisions to you. no = single project/team; your CEO presents the morning queue to you directly.)",
        "options": MULTI_TEAM_CHOICES,
    },
    {
        "id": "roster",
        "question": "List the agents on your team, one per line, as: agent name | role (pm, ux, engineer, qa, ceo, researcher, cos) | team name | project folder. Type 'done' when the list is complete. In multi-team mode a Cos row is required.",
        "options": None,
        "repeated": True,
    },
    # Optional private notes when a coordinating role is on the roster.
    {
        "id": "private_notes_mode",
        "if_has_cos": True,
        "question": (
            "A coordinating role is on the roster. Where should private notes live? "
            "Choose 'private_git' (a git remote you control) or 'local_folder' "
            "(an on-machine folder). Local copy: config/private-notes/."
        ),
        "options": PRIVATE_NOTES_MODES,
    },
    {
        "id": "private_notes_label",
        "if_has_cos": True,
        "question": (
            "Give a short private label for this notes folder "
            "(e.g. notes-private or desk-notes). "
            "Do not paste paths, emails, or secrets."
        ),
        "options": None,
    },
    {
        "id": "adversarial_agents",
        "question": "Do you want independent 'adversary' reviewers to double-check the work? (in-play = yes, they review and can flag problems; not-in-play = no, skip the extra review layer)",
        "options": ADVERSARIAL_STATES,
    },
    {
        "id": "project_repos",
        "question": "Where does your team's work live, and how are project folders organized? (e.g. a git repo path, and a folder like docs/epics/ for each project's files)",
        "options": None,
    },
    {
        "id": "escalation_preferences",
        "question": "Are there any topics that should always go to a human for approval, beyond the automatic ones (harm, legal, rule changes)? (Leave blank if the automatic list is enough.)",
        "options": None,
    },
    {
        "id": "domain_risk",
        "question": "Are there any industry or legal rules that make certain decisions require a human? (e.g. healthcare, finance, privacy. Leave blank if none.)",
        "options": None,
    },
    {
        "id": "quiet_hours",
        "question": "When are you unavailable? (e.g. 23:00-08:00. Questions that need you during this window wait rather than interrupt.)",
        "options": None,
    },
    {
        "id": "quiet_hours_p0_behavior",
        "question": "During your quiet hours, how should a P0 (urgent, can't-wait) escalation reach you? (interrupt = break through with a message even at night; defer = queue at the head of the morning queue, delivered when quiet hours end)",
        "options": ["interrupt", "defer"],
    },
    {
        "id": "daytime_sla_hours",
        "question": "During the day, how quickly should an escalation that needs you reach you? (Default 4 = within 4 hours during open hours. You can tighten or loosen it.)",
        "options": None,
    },
    {
        "id": "stall_threshold",
        "question": "How many back-and-forth rounds with no real progress should pass before a stuck task is flagged for a human?",
        "options": None,
    },
    {
        "id": "precedent_decay_window",
        "question": "How old can a past decision be before it's re-checked instead of automatically reused? (e.g. 90d = 90 days)",
        "options": None,
    },
    # --- Addendum 01 config questions (A2, A3, A4, A12.4, A14) ---
    {
        "id": "autonomy_starting_level",
        "question": "How much freedom should new agents start with? (Level 1 = they check with a human before acting on their own. Higher = more independence. Default is 1.)",
        "options": None,
    },
    {
        "id": "clean_runs_per_promotion",
        "question": "How many problem-free tasks must an agent complete before it earns more freedom?",
        "options": None,
    },
    {
        "id": "retry_count",
        "question": "How many times may an agent retry a task before it stops and asks for help? (A set number, not 'until it works'.)",
        "options": None,
    },
    {
        "id": "retry_escalation_on_exhaustion",
        "question": "What should happen when an agent runs out of retries? (It should never stay silent and never just keep trying.)",
        "options": None,
    },
    {
        "id": "audit_cadence",
        "question": "How often should the system review its own recurring tasks and report on them? (e.g. weekly)",
        "options": None,
    },
    {
        "id": "research_rounds_without_findings",
        "question": "When researching, how many rounds of digging with no new information should stop the research?",
        "options": None,
    },
    {
        "id": "research_round_budget",
        "question": "How much effort (rounds) should a single research task be allowed?",
        "options": None,
    },
    {
        "id": "irreversible_action_protection",
        "question": "For actions that can't be undone (sending, publishing, deleting, spending money), what protection level should config record? (1 = intent: agents should not reach them; 2 = intent: a human must approve; 3 = intent: agents are told to be careful but can do them). This answer is written to config only — it is not a full technical wall. Only listed script/MCP sites with approval or network gates enforce anything in code; other agent runtimes remain unchecked.",
        "options": None,
    },
    # --- Network permission (explicit; UNKNOWN = no egress) ---
    {
        "id": "network_permission",
        "question": "May framework scripts make outbound network calls (Discord webhooks, remote alerts, and similar)? Choose: 'allow' (egress permitted when other gates pass), 'deny' (no egress), or 'unknown' (treat as no egress — safest default until you decide).",
        "options": NETWORK_PERMISSIONS,
    },
    # --- Messaging: the operator's alert channel, baked into the scripts ---
    # The framework sends alerts (veto telemetry, stuck-review watchdog) to the
    # operator's messaging system. This is configured here and read by the
    # scripts via ALERT_CHANNEL / ALERT_WEBHOOK_URL / ALERT_COMMAND.
    # Alerts also require network_permission=allow; unknown/deny = no egress.
    {
        "id": "alert_channel",
        "question": "Where should the framework send alerts (like 'a review is stuck' or 'a veto fired')? (discord, whatsapp, imessage, or a custom command). Only used when network_permission is allow.",
        "options": ["discord", "whatsapp", "imessage", "generic"],
    },
    {
        "id": "alert_webhook",
        "if_alert_channel": "discord",
        "question": "Discord: paste the webhook URL for the channel where alerts should appear. (You can get this from Discord's channel settings → Integrations → Webhooks.)",
        "options": None,
    },
    {
        "id": "alert_command",
        "if_alert_channel_other": True,
        "question": "WhatsApp/iMessage/custom: what command should deliver an alert? (The alert text is added as the final argument. Example: a script that sends a message.)",
        "options": None,
    },
    # --- Data source: where in_review issues + verdicts live (ADR-0007) ---
    # The stuck-review-watchdog and veto-telemetry need to know where the
    # team's issue/verdict store is. Asked in plain language because most
    # setup users won't know the framework's internal terms. Defaults to the
    # safe, portable option (file) so a user who doesn't know can proceed.
    {
        "id": "issue_source",
        "question": "Does your team have a system that tracks work waiting for review (like a task board or ticket list)? This lets the framework flag work that's been stuck in review too long. Choose: 'file' (a simple file you or your agents update — works for any team), 'paperclip' (only if you use the Paperclip tool), or 'none' (skip this for now — you can turn it on later).",
        "options": ["file", "paperclip", "none"],
    },
    {
        "id": "issues_file",
        "if_issue_source": "file",
        "question": "Where should the file of in-review work live? (We'll create it for you if it doesn't exist. Default: runs/in_review.json. The framework maintains it; agents change it only through ticket.py or the MCP ticket tools, and a hand edit stops the loop until an operator accepts it.)",
        "options": None,
    },
    {
        "id": "verdict_log",
        "question": "Where should the framework record review decisions (pass/fail and any vetoes)? This powers the veto alerts. (Default: runs/verdicts.jsonl — we create it automatically. You usually don't need to change this.)",
        "options": None,
    },
    # --- Addendum 01 A6: BYOA adoption flow ---
    # Runs after the roster. The operator adopts existing agents (reconcile,
    # never layer) and/or defines roles that do not exist yet.
    {
        "id": "adopt_existing",
        "question": "Do you already run agents you want to bring under this framework? For each one, give: name | what it does | role it maps to (pm, ux, engineer, qa, ceo, researcher, or new) | path to its current instructions (optional). Type 'done' when finished.",
        "options": None,
        "repeated": True,
    },
    {
        "id": "define_new_role",
        "question": "Is there a role your team needs that doesn't exist yet? Give the role name, or 'none' to skip. The wizard will walk you through defining it and create its instructions.",
        "options": None,
    },
    # --- BYODS: bring your own design system ---
    # Runs after BYOA adoption. Records the operator's design system (or a
    # codified/custom starter) to config/design-system.md so new projects can
    # start from it immediately instead of designing from scratch.
    {
        "id": "design_system_source",
        "question": (
            "Bring your own design system: how should new projects get their "
            "visual foundation? 'i-have-a-link' = paste a link to your design "
            "system repo or docs. 'choose-predefined' = pick a codified design "
            "system to start building immediately (Astryx is Meta's agent-ready "
            "system with MCP tooling — recommended when agents author the UI). "
            "'build-custom' = we walk through fonts, colors, data-viz colors, "
            "and brand voice together. 'skip' = no design system recorded."
        ),
        "options": DS_SOURCES,
    },
    {
        "id": "design_system_link",
        "if_answer": [["design_system_source", "i-have-a-link"]],
        "question": "Paste the link to your design system (a repo or docs URL, starting with http:// or https://).",
        "options": None,
    },
    {
        "id": "design_system_preset",
        "if_answer": [["design_system_source", "choose-predefined"]],
        "question": "Which codified design system should projects start from?",
        "options": list(DS_PRESETS),
    },
    {
        "id": "ds_font_primary",
        "if_answer": [["design_system_source", "build-custom"]],
        "question": "Primary font for UI text? (All recommendations are free Google Fonts — pick 'custom' to name your own.)",
        "options": DS_FONTS_PRIMARY,
    },
    {
        "id": "ds_font_primary_custom",
        "if_answer": [["ds_font_primary", "custom"]],
        "question": "Name the custom primary font.",
        "options": None,
    },
    {
        "id": "ds_font_secondary",
        "if_answer": [["design_system_source", "build-custom"]],
        "question": "Secondary font for headings and display? (Pick 'custom' to name your own.)",
        "options": DS_FONTS_SECONDARY,
    },
    {
        "id": "ds_font_secondary_custom",
        "if_answer": [["ds_font_secondary", "custom"]],
        "question": "Name the custom secondary font.",
        "options": None,
    },
    {
        "id": "ds_color_primary",
        "if_answer": [["design_system_source", "build-custom"]],
        "question": (
            "Primary brand color as a hex code (e.g. #1B6DE0). No brand colors "
            "defined yet? Answer 'help' and I'll offer curated, contrast-checked "
            "starter palettes to pick from."
        ),
        "options": None,
    },
    {
        "id": "ds_palette_pick",
        "if_answer": [["ds_color_primary", "help"]],
        "question": (
            "Pick a starter palette. Each primary is text-safe (>= 4.5:1 contrast "
            "on white, WCAG AA); secondaries and tertiaries are accent-grade. "
            "ocean = Ocean — #0B5FFF / #00A6B6 / #FF6B4A. "
            "forest = Forest — #1B7A3D / #5B8C2A / #D97706. "
            "plum = Plum — #7C3AED / #DB2777 / #F59E0B. "
            "ink = Ink — #1F2937 / #4B5563 / #2563EB. "
            "teal = Teal — #0F766E / #0284C7 / #EA580C."
        ),
        "options": list(DS_PALETTES),
    },
    {
        "id": "ds_color_secondary",
        "if_answer": [["design_system_source", "build-custom"]],
        "if_answer_not": [["ds_color_primary", "help"]],
        "question": "Secondary brand color as a hex code (e.g. #00A6B6).",
        "options": None,
    },
    {
        "id": "ds_color_tertiary",
        "if_answer": [["design_system_source", "build-custom"]],
        "if_answer_not": [["ds_color_primary", "help"]],
        "question": "Tertiary brand color as a hex code (e.g. #FF6B4A).",
        "options": None,
    },
    {
        "id": "ds_viz_palette",
        "if_answer": [["design_system_source", "build-custom"]],
        "question": (
            "Data-viz colors: we recommend a color-vision-deficiency-safe (CVD) "
            "palette — Okabe–Ito, the standard colorblind-safe set "
            "(#E69F00, #56B4E9, #009E73, #F0E442, #0072B2, #D55E00, #CC79A7, "
            "#000000). Use the recommended set, or pick 'custom' to paste your own."
        ),
        "options": DS_VIZ_CHOICES,
    },
    {
        "id": "ds_viz_custom",
        "if_answer": [["ds_viz_palette", "custom"]],
        "question": "Paste your data-viz colors as comma-separated hex codes (e.g. #E69F00, #56B4E9, #009E73).",
        "options": None,
    },
    {
        "id": "ds_brand_voice",
        "if_answer": [["design_system_source", "build-custom"]],
        "question": "Which brand voice should product copy use? (Pick 'i-have-one-already' to supply your own.)",
        "options": BRAND_VOICES,
    },
    {
        "id": "ds_brand_voice_sample",
        "if_answer": [["ds_brand_voice", "i-have-one-already"]],
        "question": (
            "Paste sample text in your brand voice now, or type 'later' — "
            "we'll ask for it at the first project kickoff."
        ),
        "options": None,
    },
    # --- BYODS detail tokens: quick setup vs define-each ---
    {
        "id": "ds_detail",
        "if_answer": [["design_system_source", "build-custom"]],
        "question": (
            "Quick setup for the remaining design tokens (neutrals, dark mode, "
            "corners, icons, logo, type scale, spacing, shadows, motion, "
            "breakpoints) using recommended values — or define each one?"
        ),
        "options": DS_DETAIL_MODES,
    },
    {
        "id": "ds_neutral_style",
        "if_answer": [["ds_detail", "define-each"]],
        "question": (
            "Neutral palette for backgrounds, text grays, and borders? "
            "(Pick 'custom' to paste your own bg/surface/text/muted/border hexes.)"
        ),
        "options": DS_NEUTRAL_CHOICES,
    },
    {
        "id": "ds_neutral_custom",
        "if_answer": [["ds_neutral_style", "custom"]],
        "question": (
            "Paste your neutrals as five comma-separated hex codes in order: "
            "background, surface, text, muted, border "
            "(e.g. #F8FAFC, #FFFFFF, #0F172A, #64748B, #E2E8F0)."
        ),
        "options": None,
    },
    {
        "id": "ds_dark_mode",
        "if_answer": [["ds_detail", "define-each"]],
        "question": "Dark mode? ('auto' ships light + dark ramps; 'custom' pastes your own five dark hexes.)",
        "options": DS_DARK_MODES,
    },
    {
        "id": "ds_dark_custom",
        "if_answer": [["ds_dark_mode", "custom"]],
        "question": (
            "Paste your dark-mode neutrals as five comma-separated hex codes: "
            "background, surface, text, muted, border."
        ),
        "options": None,
    },
    {
        "id": "ds_radius",
        "if_answer": [["ds_detail", "define-each"]],
        "question": "Corner radius style? ('custom' names your own, e.g. 6px.)",
        "options": DS_RADIUS_STYLES,
    },
    {
        "id": "ds_radius_custom",
        "if_answer": [["ds_radius", "custom"]],
        "question": "Your corner radius (e.g. 6px, or 'full' for pill).",
        "options": None,
    },
    {
        "id": "ds_icons",
        "if_answer": [["ds_detail", "define-each"]],
        "question": "Icon set? ('custom' names your own set or URL.)",
        "options": DS_ICON_SETS,
    },
    {
        "id": "ds_icons_custom",
        "if_answer": [["ds_icons", "custom"]],
        "question": "Name your icon set (or paste its URL).",
        "options": None,
    },
    {
        "id": "ds_logo",
        "if_answer": [["ds_detail", "define-each"]],
        "question": (
            "Link to your logo / brand assets (logo files, favicon). "
            "Type 'later' to add it at the first project kickoff, or 'none'."
        ),
        "options": None,
    },
    {
        "id": "ds_type_scale",
        "if_answer": [["ds_detail", "define-each"]],
        "question": "Type scale? ('custom' pastes your own comma-separated pixel sizes.)",
        "options": DS_TYPE_SCALE_CHOICES,
    },
    {
        "id": "ds_type_scale_custom",
        "if_answer": [["ds_type_scale", "custom"]],
        "question": "Your type scale as comma-separated pixel sizes (e.g. 12, 14, 16, 20, 24, 32, 48).",
        "options": None,
    },
    {
        "id": "ds_spacing",
        "if_answer": [["ds_detail", "define-each"]],
        "question": "Spacing grid? ('custom' describes your own.)",
        "options": DS_SPACING_CHOICES,
    },
    {
        "id": "ds_spacing_custom",
        "if_answer": [["ds_spacing", "custom"]],
        "question": "Describe your spacing grid (e.g. 4pt grid, 6px base unit).",
        "options": None,
    },
    {
        "id": "ds_shadows",
        "if_answer": [["ds_detail", "define-each"]],
        "question": "Shadows / elevation? ('custom' describes your own.)",
        "options": DS_SHADOW_CHOICES,
    },
    {
        "id": "ds_shadows_custom",
        "if_answer": [["ds_shadows", "custom"]],
        "question": "Describe your shadow / elevation style.",
        "options": None,
    },
    {
        "id": "ds_motion",
        "if_answer": [["ds_detail", "define-each"]],
        "question": "Motion / animation? ('custom' describes your own.)",
        "options": DS_MOTION_CHOICES,
    },
    {
        "id": "ds_motion_custom",
        "if_answer": [["ds_motion", "custom"]],
        "question": "Describe your motion style (durations, easing).",
        "options": None,
    },
    {
        "id": "ds_breakpoints",
        "if_answer": [["ds_detail", "define-each"]],
        "question": "Responsive breakpoints? ('custom' pastes your own comma-separated pixel widths.)",
        "options": DS_BREAKPOINTS_CHOICES,
    },
    {
        "id": "ds_breakpoints_custom",
        "if_answer": [["ds_breakpoints", "custom"]],
        "question": "Your breakpoints as comma-separated pixel widths (e.g. 640, 768, 1024, 1280).",
        "options": None,
    },
    {
        "id": "ds_scope",
        "if_answer_not": [["design_system_source", "skip"]],
        "question": (
            "Use this design system as the default for every new project "
            "(fast development), or run this section again per project at "
            "kickoff (case by case)?"
        ),
        "options": DS_SCOPES,
    },
]

# --- state persistence -------------------------------------------------------

WIZARD_STATE_FILE = "wizard-state.json"  # resolved under config/


def _state_path(repo_root: Path) -> Path:
    return repo_root / "config" / WIZARD_STATE_FILE


def _load_state(repo_root: Path) -> dict[str, Any]:
    p = _state_path(repo_root)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _save_state(repo_root: Path, state: dict[str, Any]) -> None:
    p = _state_path(repo_root)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(state, indent=2), encoding="utf-8")


# --- helpers -----------------------------------------------------------------

def _is_repeated_pending(state: dict[str, Any], q: dict[str, Any]) -> bool:
    """A repeated question (roster) is complete when the recorded value for its
    id is the 'done' sentinel. The roster rows are stored in state['roster'] and
    the sentinel in state['answers'][id] as the string '__DONE__'."""
    return state.get("answers", {}).get(q["id"]) != "__DONE__"


def _roster_has_cos(roster: list[Any] | None) -> bool:
    """True when a seated roster row has role cos / chief-of-staff."""
    for row in roster or []:
        role = (row + [""])[1] if isinstance(row, list) else ""
        if role in ("cos", "chief-of-staff"):
            return True
    return False


def _enabled(
    q: dict[str, Any],
    answers: dict[str, Any],
    roster: list[Any] | None = None,
) -> bool:
    """A question is shown only when its condition matches the answers so far.

    Supports if_budget (budget model match), if_alert_channel (alert channel
    match), if_alert_channel_other (alert channel is not discord),
    if_issue_source (issue source match), if_has_cos (Cos seated on roster),
    and the generic if_answer / if_answer_not conditions: each is a list of
    [question_id, value] pairs; if_answer requires ALL pairs to match the
    answers so far, if_answer_not requires NONE of them to match.
    """
    cond = q.get("if_budget")
    if cond is not None:
        return answers.get("budget_model") == cond
    cond = q.get("if_alert_channel")
    if cond is not None:
        return answers.get("alert_channel") == cond
    if q.get("if_alert_channel_other"):
        return answers.get("alert_channel") in ("whatsapp", "imessage", "generic")
    cond = q.get("if_issue_source")
    if cond is not None:
        return answers.get("issue_source") == cond
    if q.get("if_has_cos"):
        return _roster_has_cos(roster)
    pairs = q.get("if_answer")
    if pairs is not None:
        if not all(answers.get(qid) == qval for qid, qval in pairs):
            return False
    pairs = q.get("if_answer_not")
    if pairs is not None:
        if any(answers.get(qid) == qval for qid, qval in pairs):
            return False
    return True


def _next_question(state: dict[str, Any]) -> dict[str, Any] | None:
    answers = state.get("answers", {})
    roster = state.get("roster", [])
    flow = state.get("flow_index", 0)
    # advance past any disabled or already-answered questions
    while flow < len(WIZARD_FLOW):
        q = WIZARD_FLOW[flow]
        if not _enabled(q, answers, roster):
            flow += 1
            continue
        if q.get("repeated"):
            # repeated question stays current until 'done' recorded
            if _is_repeated_pending(state, q):
                break
            flow += 1
            continue
        if q["id"] in answers:
            flow += 1
            continue
        break
    if flow >= len(WIZARD_FLOW):
        return None
    state["flow_index"] = flow
    return WIZARD_FLOW[flow]


def _current_question(state: dict[str, Any]) -> dict[str, Any] | None:
    flow = state.get("flow_index", 0)
    if flow >= len(WIZARD_FLOW):
        return None
    q = WIZARD_FLOW[flow]
    if not _enabled(q, state.get("answers", {}), state.get("roster", [])):
        return None
    return q


def _looks_like_forbidden_notes_label(value: str) -> bool:
    """Reject secret-shaped labels (paths, emails, long tokens)."""
    v = (value or "").strip()
    if not v:
        return True
    if "/" in v or "\\" in v or v.startswith("~"):
        return True
    if "@" in v:
        return True
    if len(v) > 64:
        return True
    return False


def _apply_private_notes(
    repo_root: Path,
    mode: str,
    label: str,
    *,
    has_cos: bool,
) -> list[Path]:
    """Scaffold a private notes folder when a coordinating role is present."""
    if not has_cos:
        return []
    if mode not in PRIVATE_NOTES_MODES:
        return []
    safe_label = (label or "").strip() or "private-notes"
    if _looks_like_forbidden_notes_label(safe_label):
        return []

    dest = repo_root / PRIVATE_NOTES_SCAFFOLD
    dest.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    src = repo_root / PRIVATE_NOTES_SKELETON
    if src.is_dir():
        for path in sorted(src.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(src)
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
                written.append(target)
    else:
        stubs = {
            "README.md": (
                "# Private notes\n\n"
                "Local copy for bring-your-own-agent installs. "
                "Keep this folder out of the public product tree.\n"
            ),
            "profile.md": (
                "# Role profile\n\n"
                "## Storage mode\n\n"
                "- Mode (this install): (see STORAGE_MODE.md)\n"
            ),
            "notes.md": "# Standing notes\n\n",
        }
        for rel, body in stubs.items():
            target = dest / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                target.write_text(body, encoding="utf-8")
                written.append(target)

    mode_path = dest / "STORAGE_MODE.md"
    mode_body = (
        "# Private notes storage mode\n\n"
        "Set during product setup when a coordinating role is on the roster.\n\n"
        "- Choose `private_git` or `local_folder`.\n\n"
        f"- mode (this install): `{mode}`\n"
        f"- label: `{safe_label}`\n"
        f"- local copy: `{PRIVATE_NOTES_SCAFFOLD.as_posix()}` (not tracked)\n\n"
        "## private_git\n\n"
        "Copy this folder to a git remote you control and commit there.\n\n"
        "## local_folder\n\n"
        f"Keep this folder on the machine under `{PRIVATE_NOTES_SCAFFOLD.as_posix()}`.\n"
    )
    mode_path.write_text(mode_body, encoding="utf-8")
    written.append(mode_path)
    return written


_HEX_RE = re.compile(r"^#(?:[0-9a-fA-F]{6}|[0-9a-fA-F]{3})$")
_URL_RE = re.compile(r"^https?://\S+$", re.IGNORECASE)
_RADIUS_RE = re.compile(r"^(\d+(\.\d+)?(px|rem|em|%)?|full)$", re.IGNORECASE)


def _looks_like_hex(value: str) -> bool:
    """True for #RGB / #RRGGBB hex color codes."""
    return bool(_HEX_RE.match(value.strip()))


def _looks_like_radius(value: str) -> bool:
    """True for CSS-like radii: 6px, 0.5rem, 50%, or 'full'."""
    return bool(_RADIUS_RE.match(value.strip()))


def _looks_like_url(value: str) -> bool:
    """True for http(s) URLs. Guards the BYODS design-system link."""
    return bool(_URL_RE.match(value.strip()))


def _ds_font(answers: dict[str, Any], key: str) -> str:
    """Resolve a font answer: 'custom' reads the free-text follow-up."""
    val = answers.get(key, "") or ""
    if val == "custom":
        custom = answers.get(f"{key}_custom", "") or ""
        return custom or "(unset custom font)"
    # strip the " (recommended)" style suffixes for the recorded value
    return val.split(" (")[0] if val else "(unset)"


def _ds_choice(answers: dict[str, Any], key: str, default: str) -> str:
    """Resolve a detail-token answer: 'custom' reads the free-text follow-up,
    quick mode (unanswered) returns the recommended default."""
    val = answers.get(key, "") or ""
    if val == "custom":
        return answers.get(f"{key}_custom", "") or "(unset custom value)"
    if not val:
        return default
    return val.split(" (")[0]


def _ds_int_list(answers: dict[str, Any], key: str, default: list[int]) -> list[int]:
    """Resolve a numeric-list token (type scale, breakpoints)."""
    val = answers.get(key, "") or ""
    if val == "custom":
        raw = answers.get(f"{key}_custom", "") or ""
        return [int(p.strip()) for p in raw.split(",") if p.strip().isdigit()] or default
    return default if not val else default


def _ds_neutrals(answers: dict[str, Any]) -> tuple[str, dict[str, str], dict[str, str] | None]:
    """Resolve the neutral ramp: (style_name, light, dark_or_None).

    Quick mode (or unset) returns the recommended cool-gray ramp with its
    dark pair. 'custom' parses the five-hex free-text answer.
    """
    keys = ["bg", "surface", "text", "muted", "border"]
    style = (answers.get("ds_neutral_style", "") or "").split(" (")[0]
    dark_mode = (answers.get("ds_dark_mode", "") or "").split(" (")[0]
    if not style:
        style = "cool-gray"  # quick setup
    if style == "custom":
        raw = answers.get("ds_neutral_custom", "") or ""
        light = dict(zip(keys, [p.strip() for p in raw.split(",") if p.strip()]))
    else:
        _name, light, _dark_pair = DS_NEUTRALS.get(style, DS_NEUTRALS["cool-gray"])
    dark: dict[str, str] | None = None
    if dark_mode in ("", "auto"):
        if style == "custom":
            raw = answers.get("ds_dark_custom", "") or ""
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            dark = dict(zip(keys, parts)) if len(parts) == 5 else None
        else:
            _name, _light, dark = DS_NEUTRALS.get(style, DS_NEUTRALS["cool-gray"])
    elif dark_mode == "dark-only":
        if style == "custom":
            raw = answers.get("ds_dark_custom", "") or ""
            parts = [p.strip() for p in raw.split(",") if p.strip()]
            dark = dict(zip(keys, parts)) if len(parts) == 5 else None
            light = dark or light
        else:
            _name, _light, dark = DS_NEUTRALS.get(style, DS_NEUTRALS["cool-gray"])
            light = dark or light
    # "light-only": dark stays None
    return style, light, dark


def _ds_radius(answers: dict[str, Any]) -> str:
    val = (answers.get("ds_radius", "") or "").split(" (")[0]
    if not val:
        return DS_RADIUS_VALUES["rounded"]  # quick setup
    if val == "custom":
        return answers.get("ds_radius_custom", "") or "(unset)"
    return DS_RADIUS_VALUES.get(val, DS_RADIUS_VALUES["rounded"])


def _ds_logo(answers: dict[str, Any]) -> str:
    val = answers.get("ds_logo", "") or ""
    if val == "__PENDING__":
        return "PENDING — ask for it at the first project kickoff"
    if val == "__NONE__":
        return "(none)"
    return val or "(unset)"


# --- config writers ----------------------------------------------------------

def _write_setup(repo_root: Path, answers: dict[str, Any]) -> Path:
    p = repo_root / "config" / "setup.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Setup",
        "",
        "Configured by the conversational setup wizard (Section 9.3). "
        "Absent or incomplete config is the unknown state; the CEO bot does not "
        "start work on unknown and re-runs the wizard instead.",
        "",
        "## Runtime",
        f"- {answers.get('runtime', '') or '(unset)'}",
        "",
        "## Engine (BYOE)",
        f"- {answers.get('engine', '') or '(unset)'}",
        "",
        "## Budget model",
        f"- {answers.get('budget_model', '') or '(unset)'}",
        "",
        "## Spend honesty",
        f"- {SPEND_UNIT_QUALIFIER}",
        "- Gated MCP operations may refuse when recorded framework units meet the configured numeric ceiling.",
    ]
    model = answers.get("budget_model")
    if model == "metered":
        lines += [
            "",
            "### Metered",
            f"- allowance per cycle: {answers.get('metered_allowance', '') or '(unset)'}",
            f"- {SPEND_UNIT_QUALIFIER}",
            f"- reset cadence: {answers.get('metered_reset_cadence', '') or '(unset)'}",
            f"- headroom reserved for in-flight work: {answers.get('metered_headroom', '') or '(unset)'}",
            f"- {SPEND_UNIT_QUALIFIER}",
        ]
    elif model == "billed":
        lines += [
            "",
            "### Billed",
            f"- total spend cap: {answers.get('billed_cap', '') or '(unset)'}",
            f"- {SPEND_UNIT_QUALIFIER}",
            f"- escalation threshold (% of cap): {answers.get('billed_escalation_threshold', '') or '(unset)'}",
            f"- {SPEND_UNIT_QUALIFIER}",
        ]
    lines += [
        "",
        "## Per-epic budget",
        f"- {answers.get('per_epic_budget', '') or '(unset)'}",
        f"- {SPEND_UNIT_QUALIFIER}",
        "",
        "## Adversarial agents",
        f"- in play: {answers.get('adversarial_agents', '') or '(unset)'}",
        "",
        "## Project repos",
        f"- {answers.get('project_repos', '') or '(unset)'}",
        "",
        "## Multi-team mode (Chief of Staff)",
        f"- multi_team: {answers.get('multi_team', '') or '(unset)'}",
        "",
        "## Private notes (optional)",
        f"- mode: {answers.get('private_notes_mode', '') or '(unset)'}",
        f"- label: {answers.get('private_notes_label', '') or '(unset)'}",
        "- Choose private_git or local_folder. Local copy: config/private-notes/.",
        "",
        "## Escalation preferences (beyond Section 10.3 mandatory list)",
        f"- {answers.get('escalation_preferences', '') or '(unset)'}",
        "",
        "## Domain risk",
        f"- {answers.get('domain_risk', '') or '(unset)'}",
        "",
        "## Quiet hours",
        f"- {answers.get('quiet_hours', '') or '(unset)'}",
        f"- P0 behavior during quiet hours: {answers.get('quiet_hours_p0_behavior', '') or '(unset)'}",
        f"- daytime escalate SLA (hours): {answers.get('daytime_sla_hours', '') or '(unset)'}",
        "",
        "## Stall threshold",
        f"- {answers.get('stall_threshold', '') or '(unset)'}",
        "",
        "## Precedent decay window",
        f"- {answers.get('precedent_decay_window', '') or '(unset)'}",
        "",
        "## Autonomy ladder (A2)",
        f"- starting level for new bots: {answers.get('autonomy_starting_level', '') or '(unset)'}",
        f"- clean runs required per promotion: {answers.get('clean_runs_per_promotion', '') or '(unset)'}",
        "",
        "## Retry budgets (A3)",
        f"- retry count: {answers.get('retry_count', '') or '(unset)'}",
        f"- escalation on exhaustion: {answers.get('retry_escalation_on_exhaustion', '') or '(unset)'}",
        "",
        "## Routine audit (A4)",
        f"- audit cadence: {answers.get('audit_cadence', '') or '(unset)'}",
        "",
        "## Research discovery loop (A12.4)",
        f"- rounds without new findings: {answers.get('research_rounds_without_findings', '') or '(unset)'}",
        f"- round budget: {answers.get('research_round_budget', '') or '(unset)'}",
        "",
        "## Irreversible action protection (A14)",
        f"- per action class: {answers.get('irreversible_action_protection', '') or '(unset)'}",
        "- config-recorded intent only — not a full technical wall; see approval/network gates for code enforcement",
        "",
        "## Network permission",
        f"- {answers.get('network_permission', '') or '(unset)'}",
        "- unknown or unset is treated as no egress (not unrestricted)",
        "",
        "## Messaging (alert channel)",
        f"- channel: {answers.get('alert_channel', '') or '(unset)'}",
        f"- webhook URL (discord): {answers.get('alert_webhook', '') or '(unset)'}",
        f"- command (whatsapp/imessage/generic): {answers.get('alert_command', '') or '(unset)'}",
        "",
        "## Data source (ADR-0007)",
        f"- issue source (watchdog): {answers.get('issue_source', '') or '(unset)'}",
        f"- issues file (if file source): {answers.get('issues_file', '') or '(unset)'}",
        f"- verdict log (telemetry): {answers.get('verdict_log', '') or '(unset)'}",
        "",
        "## Design system (BYODS)",
        f"- source: {answers.get('design_system_source', '') or '(unset)'}",
        f"- link: {answers.get('design_system_link', '') or '(unset)'}",
        f"- preset: {answers.get('design_system_preset', '') or '(unset)'}",
        f"- scope: {answers.get('ds_scope', '') or '(unset)'} "
        "('default' = every new project starts from this; 'per-project' = re-run at kickoff)",
        "- full record: config/design-system.md (advisory config — not pixel-enforced in code)",
        "",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _write_roster(repo_root: Path, roster: list[list[str]]) -> Path:
    p = repo_root / "config" / "roster.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Roster",
        "",
        "Every bot in the system, one row per bot. A bot finds its own row by its name.",
        "",
        "| Bot name | Role | Team | Default project repo(s) |",
        "|---|---|---|---|",
    ]
    for row in roster:
        while len(row) < 4:
            row.append("")
        lines.append(f"| {row[0]} | {row[1]} | {row[2]} | {row[3]} |")
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _write_personas(repo_root: Path, roster: list[list[str]], answers: dict[str, Any]) -> list[Path]:
    personas_dir = repo_root / "config" / "personas"
    personas_dir.mkdir(parents=True, exist_ok=True)
    runtime = answers.get("runtime", "runtime")
    governance_repo = "agentic-governance"  # canonical governance repo name
    # Cos's harness file is harnesses/chief-of-staff.md; role may be 'cos'.
    harness_by_role = {"cos": "chief-of-staff", "chief-of-staff": "chief-of-staff"}
    written: list[Path] = []
    for row in roster:
        bot_name, role, team, repo = (row + ["", "", "", ""])[:4]
        if not bot_name:
            continue
        harness_name = harness_by_role.get(role, role)
        memory_note = ""
        if role in ("cos", "chief-of-staff") and answers.get("private_notes_mode") in PRIVATE_NOTES_MODES:
            memory_note = (
                f"\nPrivate notes:\n"
                f"  - mode: {answers.get('private_notes_mode')}\n"
                f"  - label: {answers.get('private_notes_label') or '(unset)'}\n"
                f"  - local copy: config/private-notes/\n"
            )
        block = (
            f"You are {bot_name}, the {role} bot for {team}.\n\n"
            f"Before every task, read the following from {governance_repo}:\n"
            f"  - constitution/constitution.md\n"
            f"  - harnesses/{harness_name}.md\n"
            f"  - config/setup.md\n"
            f"  - config/roster.md\n\n"
            f"Your harness defines what you own, what you never do, who you receive from,\n"
            f"who you hand to, the artifact format you must produce, and when to stop.\n"
            f"It overrides anything in this block.\n\n"
            f"{governance_repo} is READ-ONLY to you. A commit from you to it is a\n"
            f"violation, not a correction.\n\n"
            f"Your default project repo is {repo}, unless your assignment names another.\n"
            f"You write only to your own folder in the epic you were handed.\n"
            f"Default design system: config/design-system.md — start new projects from it "
            f"unless the project kickoff overrides it. "
            f"Machine-readable tokens: config/design-tokens.json.\n"
            f"{memory_note}"
        )
        # one persona block per roster row; the runtime is the (thin) wrapper
        filename = "".join(c if c.isalnum() or c in "-_" else "_" for c in bot_name.lower())
        p = personas_dir / f"{filename}.md"
        p.write_text(f"# {bot_name}\n\nRuntime wrapper: {runtime}\n\n{block}", encoding="utf-8")
        written.append(p)
    return written


# --- A6 BYOA: adoption helpers ----------------------------------------------

# The 9-section harness skeleton (Section 4 of the spec). Used to generate a
# harness for a role that does not exist yet (A6.4).
HARNESS_SKELETON = [
    "## Read first",
    "## Identity",
    "## What you own",
    "## What you never do",
    "## Inputs and who you receive from",
    "## Outputs and who you hand to",
    "## Required artifact format",
    "## Stop conditions",
    "## Permitted plugins",
]

# The 8 fields the wizard collects to define a new role (A6.4).
NEW_ROLE_FIELDS = [
    ("role_identity", "Identity, in one sentence: who this is and what it owns."),
    ("role_never", "What it never does."),
    ("role_receives", "Who it receives work from, and what exact data crosses that edge."),
    ("role_hands_to", "Who it hands to, and what exact data crosses that edge."),
    ("role_artifact", "Its required artifact format."),
    ("role_stop", "Its stop conditions: what makes it stop and escalate rather than proceed."),
    ("role_plugins", "Which plugins it may use (comma-separated)."),
]


def _reconcile_instructions(agent_instructions: str, role: str, repo_root: Path) -> dict[str, Any]:
    """A6.3: sort an existing agent's instructions against the harness for its
    role into covered / compatible-and-specific / conflicting. Never layers.

    This is a best-effort structural reconciliation: it reads the harness for
    the role (if one exists) and the agent's instructions, and classifies each
    instruction line. The operator makes the final call on conflicts.
    """
    harness_path = repo_root / "harnesses" / f"{role}.md"
    harness_text = ""
    if harness_path.exists():
        harness_text = harness_path.read_text(encoding="utf-8")

    # Split the agent's instructions into lines; drop empties and headers.
    lines = [l.strip() for l in agent_instructions.splitlines() if l.strip()]
    covered: list[str] = []
    compatible: list[str] = []
    conflicting: list[str] = []

    for line in lines:
        if line.startswith("#") or line.startswith("---"):
            continue
        low = line.lower()
        # A line that negates something the harness states is a conflict, and
        # must be flagged for the operator BEFORE coverage is considered.
        if _looks_conflicting(low, harness_text):
            conflicting.append(line)
        elif harness_text and any(
            phrase in harness_text.lower()
            for phrase in _key_phrases(low)
        ):
            covered.append(line)
        else:
            compatible.append(line)

    return {
        "role": role,
        "harness": str(harness_path) if harness_path.exists() else None,
        "covered": covered,
        "compatible": compatible,
        "conflicting": conflicting,
        "note": (
            "Reconcile, never layer. Covered lines are dropped (the harness carries "
            "them). Compatible lines move into the harness or persona block. "
            "Conflicting lines go to the operator with both versions shown; the "
            "wizard never resolves a conflict itself."
        ),
    }


def _key_phrases(low: str) -> list[str]:
    """Extract short key phrases from an instruction line for coverage matching."""
    # Drop common filler and keep 3-5 word windows.
    words = [w for w in low.split() if w not in {"the", "a", "an", "and", "or", "to", "of", "in", "on", "for", "you", "your", "must", "should", "always", "never"}]
    phrases: list[str] = []
    for i in range(len(words) - 2):
        phrases.append(" ".join(words[i : i + 3]))
    return phrases


def _looks_conflicting(low: str, harness_text: str) -> bool:
    """Heuristic: a line conflicts if it negates something the harness states.

    A line is conflicting only when it contains a negation AND the harness
    states the positive form of what the line negates (without that same
    negation). A 'never' line that the harness also states (e.g. both say
    'never ship to production without review') is covered, not conflicting.
    """
    if not harness_text:
        return False
    low_h = harness_text.lower()
    for marker in ("never ", "do not ", "must not ", "cannot ", "refuse to "):
        idx = low.find(marker)
        if idx == -1:
            continue
        negated = low[idx + len(marker):].strip()
        # The harness states the positive form of the negated phrase, and does
        # NOT itself carry the same negation marker before that phrase.
        if negated and negated in low_h:
            # Ensure the harness isn't itself negating the same phrase.
            if marker not in low_h[: low_h.find(negated)]:
                return True
    return False


def _generate_harness(role: str, fields: dict[str, str], repo_root: Path) -> Path | None:
    """A6.4/A6.5: generate a harness for a new role from the 9-section skeleton.
    Refuses (returns None) if the harness already exists — never overwrite.
    """
    harness_path = repo_root / "harnesses" / f"{role}.md"
    if harness_path.exists():
        return None  # A6.5: refuse, never overwrite

    lines = [
        f"# {role.title()} Harness",
        "",
        "## Read first",
        "Before beginning any task, load the constitution, this harness file, `config/setup.md`, and the roster. Do this at the start of every task.",
        "",
        "## Identity",
        fields.get("role_identity", ""),
        "",
        "## What you own",
        "",
        "## What you never do",
        fields.get("role_never", ""),
        "",
        "## Inputs and who you receive from",
        fields.get("role_receives", ""),
        "",
        "## Outputs and who you hand to",
        fields.get("role_hands_to", ""),
        "",
        "## Required artifact format",
        fields.get("role_artifact", ""),
        "",
        "## Stop conditions",
        fields.get("role_stop", ""),
        "",
        "## Permitted plugins",
        fields.get("role_plugins", ""),
        "",
    ]
    harness_path.parent.mkdir(parents=True, exist_ok=True)
    harness_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return harness_path


def _answer_adopt_existing(repo_root: Path, state: dict[str, Any], value: str) -> dict[str, Any]:
    """A6.2/A6.3: collect an adopted agent and reconcile its instructions."""
    adopted = state.setdefault("adopted", [])
    if value.lower() == "done":
        state["answers"]["adopt_existing"] = "__DONE__"
        _save_state(repo_root, state)
        nxt = _next_question(state)
        if nxt is None:
            return _finalize(repo_root, state)
        _save_state(repo_root, state)
        return _question_payload(nxt, len(state.get("roster", [])))

    parts = [p.strip() for p in value.split("|")]
    if len(parts) < 2:
        return {
            "status": "invalid",
            "question": "adopt_existing",
            "error": "Format: name | what it does | role | path-to-instructions (optional).",
        }
    name, what = parts[0], parts[1]
    role = parts[2] if len(parts) > 2 and parts[2] else ""
    instr_path = parts[3] if len(parts) > 3 and parts[3] else ""

    # Read the agent's current instructions if a path was given.
    instructions = ""
    if instr_path:
        p = Path(instr_path).expanduser()
        if p.exists():
            instructions = p.read_text(encoding="utf-8")
        else:
            return {
                "status": "invalid",
                "question": "adopt_existing",
                "error": f"Instructions path not found: {instr_path}",
            }

    reconcile = None
    if role and instructions:
        reconcile = _reconcile_instructions(instructions, role, repo_root)

    adopted.append({
        "name": name,
        "what": what,
        "role": role,
        "instructions_path": instr_path,
        "reconcile": reconcile,
    })
    _save_state(repo_root, state)
    nxt = _next_question(state)
    if nxt is None:
        return _finalize(repo_root, state)
    _save_state(repo_root, state)
    return _question_payload(nxt, len(state.get("roster", [])))


def _answer_define_new_role(repo_root: Path, state: dict[str, Any], value: str) -> dict[str, Any]:
    """A6.4: collect the 8 skeleton fields for a new role, then generate a harness."""
    value = (value or "").strip()
    if value.lower() in ("none", "skip", ""):
        state["answers"]["define_new_role"] = "__SKIP__"
        _save_state(repo_root, state)
        nxt = _next_question(state)
        if nxt is None:
            return _finalize(repo_root, state)
        _save_state(repo_root, state)
        return _question_payload(nxt, len(state.get("roster", [])))

    # First answer names the role; subsequent answers fill the 8 fields.
    new_role = state.setdefault("new_role", {})
    if "name" not in new_role:
        new_role["name"] = value
        new_role["field_index"] = 0
        _save_state(repo_root, state)
        field_id, field_q = NEW_ROLE_FIELDS[0]
        return {
            "status": "question",
            "question_id": f"new_role.{field_id}",
            "question": f"For role '{value}': {field_q}",
            "free_text": True,
        }

    # Fill the current field.
    idx = new_role.get("field_index", 0)
    if idx < len(NEW_ROLE_FIELDS):
        field_id, _ = NEW_ROLE_FIELDS[idx]
        new_role[field_id] = value
        new_role["field_index"] = idx + 1
        _save_state(repo_root, state)

    # If more fields remain, ask the next one.
    if new_role.get("field_index", 0) < len(NEW_ROLE_FIELDS):
        nidx = new_role["field_index"]
        field_id, field_q = NEW_ROLE_FIELDS[nidx]
        return {
            "status": "question",
            "question_id": f"new_role.{field_id}",
            "question": f"For role '{new_role['name']}': {field_q}",
            "free_text": True,
        }

    # All fields collected — generate the harness (A6.5: refuse if exists).
    role_name = new_role["name"]
    harness_path = _generate_harness(role_name, new_role, repo_root)
    if harness_path is None:
        return {
            "status": "refused",
            "question": "define_new_role",
            "error": f"A6.5: harness for '{role_name}' already exists at harnesses/{role_name}.md. Refusing to overwrite. Edit the file to amend it.",
        }

    state["answers"]["define_new_role"] = "__DONE__"
    state["generated_harness"] = str(harness_path)
    _save_state(repo_root, state)
    nxt = _next_question(state)
    if nxt is None:
        return _finalize(repo_root, state)
    _save_state(repo_root, state)
    return _question_payload(nxt, len(state.get("roster", [])))


# --- orchestration -----------------------------------------------------------

def start_wizard(repo_root: Path) -> dict[str, Any]:
    """Begin (or resume) the wizard. Returns the first/pending question."""
    state = _load_state(repo_root)
    if not state:
        state = {"flow_index": 0, "answers": {}, "roster": []}
        _save_state(repo_root, state)
    q = _next_question(state)
    if q is None:
        return _finalize(repo_root, state)
    _save_state(repo_root, state)
    return _question_payload(q, len(state.get("roster", [])))


def answer_wizard(repo_root: Path, value: str) -> dict[str, Any]:
    """Record the answer to the current question; return the next question or
    the completion summary."""
    state = _load_state(repo_root)
    if not state:
        return {
            "status": "error",
            "error": "No wizard in progress. Call setup_wizard_start() first.",
        }
    q = _current_question(state)
    if q is None:
        return _finalize(repo_root, state)
    value = (value or "").strip()

    # roster rows are collected conversationally until 'done'
    if q.get("repeated"):
        if q["id"] == "adopt_existing":
            return _answer_adopt_existing(repo_root, state, value)
        roster = state.setdefault("roster", [])
        if value.lower() == "done":
            # mark roster complete; move on
            state["answers"][q["id"]] = "__DONE__"
        else:
            parts = [p.strip() for p in value.split("|")]
            roster.append(parts if any(parts) else [])
        _save_state(repo_root, state)
        nxt = _next_question(state)
        if nxt is None:
            return _finalize(repo_root, state)
        if nxt.get("id") == q["id"]:
            # still collecting roster rows
            return _question_payload(nxt, len(roster))
        _save_state(repo_root, state)
        return _question_payload(nxt, len(roster))

    # define_new_role collects the 8 skeleton fields one at a time
    if q["id"] == "define_new_role":
        return _answer_define_new_role(repo_root, state, value)

    # validate bounded answers
    if q.get("options") and value not in q["options"]:
        return {
            "status": "invalid",
            "question": q["id"],
            "error": f"'{value}' is not a valid choice.",
            "options": q["options"],
        }

    if q["id"] == "private_notes_label" and _looks_like_forbidden_notes_label(value):
        return {
            "status": "invalid",
            "question": q["id"],
            "error": (
                "Notes label must be a short private name only — "
                "no host paths, emails, or secrets."
            ),
            "free_text": True,
        }

    # BYODS: design-system link must be a URL; colors must be hex codes.
    if q["id"] == "design_system_link" and not _looks_like_url(value):
        return {
            "status": "invalid",
            "question": q["id"],
            "error": "That doesn't look like a URL — paste a link starting with http:// or https://.",
            "free_text": True,
        }
    if q["id"] in ("ds_color_primary", "ds_color_secondary", "ds_color_tertiary"):
        if q["id"] == "ds_color_primary" and value.lower() == "help":
            pass  # routes to the curated starter-palette picker
        elif not _looks_like_hex(value):
            return {
                "status": "invalid",
                "question": q["id"],
                "error": "Use a hex code like #1B6DE0, or answer 'help' for starter palettes.",
                "free_text": True,
            }
    if q["id"] == "ds_viz_custom":
        parts = [p.strip() for p in value.split(",") if p.strip()]
        if not parts or not all(_looks_like_hex(p) for p in parts):
            return {
                "status": "invalid",
                "question": q["id"],
                "error": "Use comma-separated hex codes, e.g. #E69F00, #56B4E9, #009E73.",
                "free_text": True,
            }
    # BYODS detail tokens: custom neutrals/dark ramps are five hexes;
    # radius is a length or 'full'; scales/breakpoints are numbers.
    if q["id"] in ("ds_neutral_custom", "ds_dark_custom"):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        if len(parts) != 5 or not all(_looks_like_hex(p) for p in parts):
            return {
                "status": "invalid",
                "question": q["id"],
                "error": "Use five comma-separated hex codes: background, surface, text, muted, border.",
                "free_text": True,
            }
    if q["id"] == "ds_radius_custom" and not _looks_like_radius(value):
        return {
            "status": "invalid",
            "question": q["id"],
            "error": "Use a radius like 6px, 0.5rem, or 'full'.",
            "free_text": True,
        }
    if q["id"] in ("ds_type_scale_custom", "ds_breakpoints_custom"):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        if not parts or not all(p.isdigit() for p in parts):
            return {
                "status": "invalid",
                "question": q["id"],
                "error": "Use comma-separated pixel numbers, e.g. 12, 14, 16, 20, 24, 32, 48.",
                "free_text": True,
            }
    if q["id"] == "ds_logo":
        low = value.lower()
        if low == "later":
            value = "__PENDING__"
        elif low == "none":
            value = "__NONE__"
        elif not _looks_like_url(value):
            return {
                "status": "invalid",
                "question": q["id"],
                "error": "Paste a link starting with http:// or https:// — or type 'later' or 'none'.",
                "free_text": True,
            }
    # Brand-voice sample may be deferred to the first project kickoff.
    if q["id"] == "ds_brand_voice_sample" and value.lower() == "later":
        value = "__PENDING__"

    state["answers"][q["id"]] = value
    _save_state(repo_root, state)
    nxt = _next_question(state)
    if nxt is None:
        return _finalize(repo_root, state)
    _save_state(repo_root, state)
    return _question_payload(nxt, len(state.get("roster", [])))


def _question_payload(q: dict[str, Any], roster_len: int) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "status": "question",
        "question_id": q["id"],
        "question": q["question"],
    }
    if q.get("options"):
        payload["options"] = q["options"]
    payload["free_text"] = q.get("options") is None
    if q.get("repeated"):
        payload["repeated"] = True
        payload["roster_rows_so_far"] = roster_len
    return payload


def _finalize(repo_root: Path, state: dict[str, Any]) -> dict[str, Any]:
    roster = state.get("roster", [])
    answers = state.get("answers", {})
    # A8 / multi-team mode: if the operator runs more than one team, a roster
    # row with role 'cos' is required. Without one the system is incomplete.
    multi_team = answers.get("multi_team") == "yes"
    has_cos = _roster_has_cos(roster)
    if multi_team and not has_cos:
        return {
            "status": "invalid",
            "error": "multi_team is 'yes' but no roster row has role 'cos'. "
            "Multi-team mode requires a Chief of Staff (Cos); add a roster row "
            "with role 'cos' before completion. (A8)",
        }
    if has_cos and answers.get("private_notes_mode") not in PRIVATE_NOTES_MODES:
        return {
            "status": "invalid",
            "error": (
                "A coordinating role is on the roster but the private-notes "
                "mode is unset. Re-run the wizard and choose private_git or "
                "local_folder. Local copy: config/private-notes/."
            ),
        }
    if has_cos and _looks_like_forbidden_notes_label(
        answers.get("private_notes_label", "")
    ):
        return {
            "status": "invalid",
            "error": (
                "A coordinating role is on the roster but the private-notes "
                "label is missing or unsafe (no host paths, emails, or secrets). "
                "Re-run the wizard."
            ),
        }
    setup_path = _write_setup(repo_root, answers)
    roster_path = _write_roster(repo_root, roster)
    persona_paths = _write_personas(repo_root, roster, answers)
    adoption_path = _write_adoption(repo_root, state)
    design_system_path = _write_design_system(repo_root, answers)
    design_tokens_path = _write_design_tokens(repo_root, answers)
    data_files = _write_data_files(repo_root, answers)
    # Optional private-notes scaffold when a coordinating role is on the roster.
    notes_files = _apply_private_notes(
        repo_root,
        answers.get("private_notes_mode") or "",
        answers.get("private_notes_label") or "",
        has_cos=has_cos,
    )
    # clear wizard state so a fresh run starts over (re-runnable)
    _state_path(repo_root).unlink(missing_ok=True)
    return {
        "status": "complete",
        "wrote": {
            "setup": str(setup_path),
            "roster": str(roster_path),
            "personas": [str(p) for p in persona_paths],
            "adoption": str(adoption_path) if adoption_path else None,
            "design_system": str(design_system_path) if design_system_path else None,
            "design_tokens": str(design_tokens_path) if design_tokens_path else None,
            "data_files": [str(p) for p in data_files],
            "private_notes": [str(p) for p in notes_files],
        },
        "roster_rows": len(roster),
        "adopted_agents": len(state.get("adopted", [])),
        "generated_harness": state.get("generated_harness"),
        "note": _completion_note(answers, has_cos=has_cos),
    }


def _completion_note(answers: dict[str, Any], has_cos: bool = False) -> str:
    parts: list[str] = []
    ds_source = answers.get("design_system_source", "") or ""
    if ds_source and ds_source != "skip":
        ds_scope = answers.get("ds_scope", "") or "(unset)"
        parts.append(
            f"Design system recorded (source: {ds_source}, scope: {ds_scope}). "
            "New projects start from config/design-system.md for fast development; "
            "a per-project kickoff may override it."
        )
    if answers.get("multi_team") == "yes":
        parts.append(
            "Multi-team mode: CEOs escalate via Cos; Cos owns the morning queue; "
            "only Cos pages you."
        )
    elif answers.get("multi_team") == "no":
        parts.append("Single-team mode: CEO → you for the morning queue.")
    if has_cos and answers.get("private_notes_mode") in PRIVATE_NOTES_MODES:
        mode = answers.get("private_notes_mode")
        label = answers.get("private_notes_label") or "(unset)"
        parts.append(
            f"Private notes ready: mode={mode}, label={label}. "
            "Local copy: config/private-notes/."
        )
    if not parts:
        return (
            "Wizard complete. Every configured value is the operator's; "
            "re-run the wizard to change anything."
        )
    return " ".join(parts)


def _write_data_files(repo_root: Path, answers: dict[str, Any]) -> list[Path]:
    """Create the default data-source files so the user doesn't have to know
    the paths (ADR-0007). Creates the in_review issues file and the verdict
    log if they don't already exist, using the configured (or default) paths.
    Returns the list of files created.
    """
    written: list[Path] = []
    source = answers.get("issue_source", "")
    if source == "file":
        issues_path = answers.get("issues_file") or "runs/in_review.json"
        p = repo_root / issues_path
        p.parent.mkdir(parents=True, exist_ok=True)
        if not p.exists():
            p.write_text("[]\n", encoding="utf-8")
            written.append(p)
    verdict_path = answers.get("verdict_log") or "runs/verdicts.jsonl"
    vp = repo_root / verdict_path
    vp.parent.mkdir(parents=True, exist_ok=True)
    if not vp.exists():
        vp.write_text("", encoding="utf-8")
        written.append(vp)
    return written


def _write_design_system(repo_root: Path, answers: dict[str, Any]) -> Path | None:
    """BYODS: write the operator's design system record to config/design-system.md.

    The recorded system is the default new projects start from (fast
    development) when ds_scope is 'default'; when 'per-project', the BYODS
    questions are re-run at each project kickoff instead. Returns None when
    the operator skipped the design-system section.
    """
    source = answers.get("design_system_source", "") or ""
    if source in ("", "skip"):
        return None
    p = repo_root / "config" / "design-system.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Design system (BYODS)",
        "",
        "Recorded by the conversational setup wizard. This is the operator's "
        "design system of record: new projects start from it so they can build "
        "immediately instead of designing from scratch.",
        "",
        f"Source: {source}",
        f"Scope: {answers.get('ds_scope', '') or '(unset)'} "
        "('default' = every new project starts from this; 'per-project' = re-run "
        "this section at each project kickoff)",
        "",
    ]
    if source == "i-have-a-link":
        lines += [
            "## Operator's design system",
            f"- link: {answers.get('design_system_link', '') or '(unset)'}",
            "",
        ]
    elif source == "choose-predefined":
        preset = answers.get("design_system_preset", "") or ""
        name, url = DS_PRESETS.get(preset, ("(unknown preset)", ""))
        lines += [
            "## Predefined codified design system",
            f"- preset: {preset}",
            f"- name: {name}",
            f"- url: {url}",
            "",
        ]
    elif source == "build-custom":
        # colors: palette pick maps to its hex trio; otherwise explicit hexes
        palette_id = answers.get("ds_palette_pick", "") or ""
        if palette_id in DS_PALETTES:
            pname, phex, shex, thex = DS_PALETTES[palette_id]
            color_note = f"starter palette '{palette_id}' ({pname})"
        else:
            phex = answers.get("ds_color_primary", "") or "(unset)"
            shex = answers.get("ds_color_secondary", "") or "(unset)"
            thex = answers.get("ds_color_tertiary", "") or "(unset)"
            color_note = "operator hex codes"
        # viz palette: recommended CVD-safe Okabe–Ito, or custom
        viz_choice = answers.get("ds_viz_palette", "") or ""
        if viz_choice == "custom":
            viz = answers.get("ds_viz_custom", "") or "(unset)"
        else:
            viz = ", ".join(DS_VIZ_OKABE_ITO) + " (Okabe–Ito, CVD-safe)"
        # brand voice sample may be deferred to the first project kickoff
        sample = answers.get("ds_brand_voice_sample", "") or ""
        if sample == "__PENDING__":
            sample_note = "PENDING — ask for it at the first project kickoff"
        elif sample:
            sample_note = sample
        else:
            sample_note = "(none)"
        lines += [
            "## Fonts (free Google Fonts unless marked custom)",
            f"- primary: {_ds_font(answers, 'ds_font_primary')}",
            f"- secondary: {_ds_font(answers, 'ds_font_secondary')}",
            "",
            "## Colors",
            f"- primary: {phex}",
            f"- secondary: {shex}",
            f"- tertiary: {thex}",
            f"- source: {color_note}",
            "- primaries are text-safe (>= 4.5:1 on white, WCAG AA); "
            "secondaries/tertiaries are accent-grade",
            "",
            "## Data-viz colors (CVD-safe recommended)",
            f"- {viz}",
            "",
            "## Brand voice",
            f"- style: {answers.get('ds_brand_voice', '') or '(unset)'}",
            f"- sample: {sample_note}",
            "",
        ]
        # Detail tokens: quick setup uses recommended values; define-each
        # answers resolve through the _ds_* helpers.
        nstyle, nlight, ndark = _ds_neutrals(answers)
        dark_mode = (answers.get("ds_dark_mode", "") or "").split(" (")[0] or "auto (quick setup)"
        lines += [
            "## Neutrals",
            f"- style: {nstyle}",
            f"- dark mode: {dark_mode}",
            "- light: " + ", ".join(f"{k} {v}" for k, v in nlight.items()),
        ]
        if ndark:
            lines.append("- dark: " + ", ".join(f"{k} {v}" for k, v in ndark.items()))
        lines += [
            "",
            "## Shape, icons, assets",
            f"- corner radius: {_ds_radius(answers)}",
            f"- icons: {_ds_choice(answers, 'ds_icons', 'lucide')}",
            f"- logo / brand assets: {_ds_logo(answers)}",
            "",
            "## Type & layout",
            f"- type scale (px): {', '.join(str(x) for x in _ds_int_list(answers, 'ds_type_scale', DS_TYPE_SCALE_DEFAULT))}",
            f"- spacing: {_ds_choice(answers, 'ds_spacing', DS_SPACING_DEFAULT)}",
            f"- shadows: {_ds_choice(answers, 'ds_shadows', DS_SHADOW_DEFAULT)}",
            f"- motion: {_ds_choice(answers, 'ds_motion', DS_MOTION_DEFAULT)}",
            f"- breakpoints (px): {', '.join(str(x) for x in _ds_int_list(answers, 'ds_breakpoints', DS_BREAKPOINTS_DEFAULT))}",
            "",
            "Machine-readable tokens: config/design-tokens.json",
            "",
        ]
    lines += [
        "## Advisory, not enforced",
        "The framework records this design system as config; it does not "
        "pixel-enforce it in code. Initiative-level craft gates "
        "(DESIGN_SYSTEM_FIRST, Check 7/8, Cos stamp) still apply per project — "
        "a per-project kickoff may override this default with its own "
        "design-system.md.",
        "",
    ]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p


def _write_design_tokens(repo_root: Path, answers: dict[str, Any]) -> Path | None:
    """BYODS: write machine-readable design tokens to config/design-tokens.json.

    W3C-DTCG-flavored ($value/$type) so agents and build tooling can import
    the tokens directly instead of parsing prose. Written for the custom
    build; link/predefined sources reference their external system.
    """
    source = answers.get("design_system_source", "") or ""
    if source in ("", "skip"):
        return None
    p = repo_root / "config" / "design-tokens.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    color = lambda v: {"$value": v, "$type": "color"}
    if source == "build-custom":
        palette_id = answers.get("ds_palette_pick", "") or ""
        if palette_id in DS_PALETTES:
            _pname, phex, shex, thex = DS_PALETTES[palette_id]
        else:
            phex = answers.get("ds_color_primary", "") or "#000000"
            shex = answers.get("ds_color_secondary", "") or "#000000"
            thex = answers.get("ds_color_tertiary", "") or "#000000"
        viz_choice = answers.get("ds_viz_palette", "") or ""
        if viz_choice == "custom":
            viz = [c.strip() for c in (answers.get("ds_viz_custom", "") or "").split(",") if c.strip()]
        else:
            viz = DS_VIZ_OKABE_ITO
        nstyle, nlight, ndark = _ds_neutrals(answers)
        tokens: dict[str, Any] = {
            "$description": "BYODS design tokens — recorded by the setup wizard (advisory config, not pixel-enforced).",
            "source": source,
            "scope": answers.get("ds_scope", "") or "(unset)",
            "color": {
                "brand": {
                    "primary": color(phex),
                    "secondary": color(shex),
                    "tertiary": color(thex),
                },
                "neutral": {
                    "style": nstyle,
                    "light": {k: color(v) for k, v in nlight.items()},
                    **({"dark": {k: color(v) for k, v in ndark.items()}} if ndark else {}),
                },
                "dataViz": {
                    "palette": [color(c) for c in viz],
                    "cvdSafe": viz_choice != "custom",
                },
            },
            "font": {
                "family": {
                    "primary": {"$value": _ds_font(answers, "ds_font_primary"), "$type": "fontFamily"},
                    "secondary": {"$value": _ds_font(answers, "ds_font_secondary"), "$type": "fontFamily"},
                },
                "scale": {
                    "$value": _ds_int_list(answers, "ds_type_scale", DS_TYPE_SCALE_DEFAULT),
                    "$type": "fontSizes",
                },
            },
            "radius": {"$value": _ds_radius(answers), "$type": "borderRadius"},
            "spacing": {"$value": _ds_choice(answers, "ds_spacing", DS_SPACING_DEFAULT), "$type": "other"},
            "shadow": {"$value": _ds_choice(answers, "ds_shadows", DS_SHADOW_DEFAULT), "$type": "other"},
            "motion": {"$value": _ds_choice(answers, "ds_motion", DS_MOTION_DEFAULT), "$type": "other"},
            "breakpoints": {
                "$value": _ds_int_list(answers, "ds_breakpoints", DS_BREAKPOINTS_DEFAULT),
                "$type": "other",
            },
            "icons": {"$value": _ds_choice(answers, "ds_icons", "lucide"), "$type": "other"},
            "logo": {"$value": _ds_logo(answers), "$type": "other"},
            "brandVoice": {
                "style": answers.get("ds_brand_voice", "") or "(unset)",
                "sample": answers.get("ds_brand_voice_sample", "") or "(none)",
            },
        }
    else:
        ref = answers.get("design_system_link", "") or ""
        if source == "choose-predefined":
            preset = answers.get("design_system_preset", "") or ""
            _name, url = DS_PRESETS.get(preset, ("(unknown)", ""))
            ref = url
        tokens = {
            "$description": "BYODS design tokens — external design system; tokens live in the linked system.",
            "source": source,
            "scope": answers.get("ds_scope", "") or "(unset)",
            "externalReference": ref,
        }
    p.write_text(json.dumps(tokens, indent=2) + "\n", encoding="utf-8")
    return p


def _write_adoption(repo_root: Path, state: dict[str, Any]) -> Path | None:
    """Write the BYOA adoption record (A6) to config/adoption.md."""
    adopted = state.get("adopted", [])
    generated = state.get("generated_harness")
    if not adopted and not generated:
        return None
    p = repo_root / "config" / "adoption.md"
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Adoption (BYOA, A6)",
        "",
        "Agents brought under governance and roles defined through the setup wizard.",
        "",
    ]
    if adopted:
        lines += ["## Adopted agents", "", "| Name | What it does | Role | Instructions |", "|---|---|---|---|"]
        for a in adopted:
            lines.append(f"| {a['name']} | {a['what']} | {a['role'] or '(unmapped)'} | {a['instructions_path'] or '(none)'} |")
        lines.append("")
        # Reconcile results
        for a in adopted:
            if a.get("reconcile"):
                r = a["reconcile"]
                lines += [
                    f"### {a['name']} — reconcile vs {r['role']} harness",
                    "",
                    f"- Covered (dropped, harness carries): {len(r['covered'])}",
                    f"- Compatible (moves into harness/persona): {len(r['compatible'])}",
                    f"- Conflicting (operator decides): {len(r['conflicting'])}",
                    "",
                ]
                if r["conflicting"]:
                    lines += ["Conflicting lines (operator must decide):", ""]
                    for c in r["conflicting"]:
                        lines.append(f"- {c}")
                    lines.append("")
    if generated:
        lines += ["## Generated harness", "", f"- {generated}", ""]
    p.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return p
