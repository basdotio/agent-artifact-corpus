"""Workflow prompt definitions for MCP prompts/list and prompts/get.

USER-facing MCP prompt primitive: each prompt is a tested tool-orchestration recipe
whose rendered messages instruct the agent to invoke THIS server's real tools
(``select_design_patterns``, ``submit_design_job``, ``get_design_status``,
``cancel_design``) and to read the ``design-patterns://variants`` resource.
This module holds NO internal LLM prompt content — that lives in ``src/prompts/``.
"""

from fastmcp import FastMCP
from fastmcp.prompts import Message

from src.patterns.loader import PatternLoader

_VARIANTS_RESOURCE = "design-patterns://variants"


def register_prompts(server: FastMCP, catalog: PatternLoader) -> int:
    """Register all workflow prompts with the server; return the count registered.

    ``catalog`` pins the register-time signature to the loaded catalog so prompt
    bodies stay fact-neutral (no hardcoded pattern names); category guidance quotes
    only the catalog's own decision-group structure via ``catalog.enums.categories``.
    """

    def _categories_clause() -> str:
        categories = ", ".join(catalog.enums.categories)
        return (
            f"The catalog covers nine decision-group categories ({categories}); "
            "they are decision groups, not architectural layers — do not treat a hit in "
            "one category as requiring hits in the others."
        )

    @server.prompt(name="select_design_patterns_workflow")
    def select_design_patterns_workflow(
        description: str,
        language: str | None = None,
        architecture_style: str | None = None,
        paradigm: str | None = None,
        focus: str | None = None,
    ) -> list[Message]:
        """Guided end-to-end pattern-selection workflow.

        Steps: 1) assemble a concrete description from the user's system,
        2) call select_design_patterns, 3) inspect applications[].language_binding
        and re-call with focus quoting a sibling variant_id when the bound
        realization does not fit the toolchain, 4) fall back to
        submit_design_job + get_design_status polling for long runs.
        """
        effective_description = description if description and description.strip() else (
            "(no description supplied — ask the user for component names, "
            "responsibilities and constraints before selecting patterns)"
        )
        hints: list[str] = []
        if language:
            hints.append(f"language='{language}'")
        if architecture_style:
            hints.append(f"architecture_style='{architecture_style}'")
        if paradigm:
            hints.append(f"paradigm='{paradigm}'")
        if focus:
            hints.append(f"focus='{focus}'")
        hints_str = (", ".join(hints)) or "only the description argument"

        body = (
            "You are guiding a user through the design-pattern selection workflow. "
            "Follow these steps precisely:\n"
            f"1. Build the description argument from the user's system: component names, "
            f"their responsibilities, and the hard constraints. "
            f"Currently supplied description (may already be complete):\n"
            f"--- BEGIN DESCRIPTION ---\n{effective_description}\n--- END DESCRIPTION ---\n"
            f"2. Call the select_design_patterns tool with that description and these hints: "
            f"{hints_str}.\n"
            "3. For each entry in the returned applications[], read "
            "applications[].language_binding: bound_variant names the realization that was "
            "bound, and variants[] lists the sibling realizations with their variant_id, "
            "paradigm and min_standard. If the bound realization does not fit the user's "
            "toolchain (wrong variant, too old a language floor), re-call "
            "select_design_patterns with a focus hint that quotes the sibling variant_id "
            "you want instead (e.g. focus=\"bind variant '<variant_id>'\").\n"
            "4. You can read the full realization vocabulary per pattern beforehand from the "
            f"resource '{_VARIANTS_RESOURCE}' (grouped by language, then pattern).\n"
            "5. If the run is long (large description or repeated refine loops), prefer the "
            "background path instead: call submit_design_job with the same arguments, then "
            "poll get_design_status with the returned job_id until the status is completed "
            "(or cancel_design to abort)."
        )
        return [Message(body)]

    @server.prompt(name="explore_pattern_catalog")
    def explore_pattern_catalog(category: str | None = None) -> list[Message]:
        """Discovery workflow over the design-pattern catalog.

        Steps: 1) read the design-patterns://variants resource for realization
        vocabulary, 2) probe select_design_patterns with a tightly scoped
        description, 3) interpret the nine categories as decision groups.
        """
        effective_category = category if category and category.strip() else "(no category filter)"
        body = (
            "You are helping a user explore what this design-pattern catalog covers.\n"
            f"The user's area of interest: {effective_category}.\n\n"
            "Guide the exploration as follows:\n"
            f"1. Read the resource '{_VARIANTS_RESOURCE}' (mcp_read_resource with that URI). "
            "It groups every pattern's language realizations by language, then pattern — "
            "use it as the realization vocabulary: which languages, paradigms and "
            "capability floors the catalog actually covers.\n"
            "2. From the user's interest, craft a TIGHTLY SCOPED description: one concrete "
            "situation with component names, responsibilities and constraints — not a broad "
            "topic. Then call select_design_patterns with it. The returned applications[] "
            "tell you which patterns the pipeline actually selects for that situation, "
            "including supporting choices and alternatives_considered.\n"
            "3. To survey a neighbouring area, reword the description around one decision "
            "and call again — each call is a decision probe, not a browse.\n"
            f"{_categories_clause()}\n"
            "Do not claim a pattern exists because its name sounds plausible: only the "
            "selection result and the variants resource are evidence."
        )
        return [Message(body)]

    @server.prompt(name="evaluate_my_design")
    def evaluate_my_design(description: str) -> list[Message]:
        """Workflow for checking an existing design against the catalog.

        Steps: 1) restate the user's components/constraints as a description,
        2) call select_design_patterns, 3) compare returned applications and
        language bindings against the current codebase, 4) read
        overview.reasoning and alternatives_considered for the why.
        """
        effective_description = description if description and description.strip() else (
            "(no description supplied — ask the user to restate their design first: "
            "components, responsibilities, constraints)"
        )
        body = (
            "You are guiding a user who wants their EXISTING design checked against the "
            "pattern catalog. Follow these steps precisely:\n"
            "1. Restate the user's design as a selection description: the components they "
            "already have, each one's responsibility, and the constraints they told you "
            "about. Do not embellish it with patterns they did not mention.\n"
            f"Supplied design description:\n"
            f"--- BEGIN DESCRIPTION ---\n{effective_description}\n--- END DESCRIPTION ---\n"
            "2. Call select_design_patterns with that description.\n"
            "3. Compare the returned applications[] against the user's current codebase, "
            "component by component: for each application, does the codebase realize the "
            "pattern's intent, or something else? Check applications[].language_binding "
            "too — if the bound_variant is a realization the codebase cannot support "
            "(language floor, missing features), name the sibling variant from variants[] "
            "that would fit.\n"
            "4. Read overview.reasoning: it states why the primary pattern won — quote it "
            "when explaining the verdict to the user.\n"
            "5. Read alternatives_considered: it carries the near-ties and the vetoed "
            "alternatives (with veto reasons). Present them as 'worth considering if X' / "
            "'rejected because Y', not as failures."
        )
        return [Message(body)]

    @server.prompt(name="compare_pattern_candidates")
    def compare_pattern_candidates(decision: str, candidates: str) -> list[Message]:
        """Workflow for comparing two or three named patterns for one decision.

        Steps: 1) recall each candidate's intent/problem from a catalog read,
        2) run select_design_patterns once per candidate with the decision worded
        toward it, 3) diff the fit scores and adjustment ledgers.
        """
        effective_decision = decision if decision and decision.strip() else (
            "(no decision supplied — ask the user which design decision they are weighing)"
        )
        effective_candidates = candidates if candidates and candidates.strip() else (
            "(no candidates supplied — ask the user to name two or three patterns to compare)"
        )
        body = (
            "You are helping a user compare candidate patterns for one decision.\n"
            f"Decision to make: {effective_decision}\n"
            f"Candidates named by the user (two or three): {effective_candidates}\n\n"
            "Follow these steps precisely:\n"
            "1. Recall each candidate's intent and problem statement from the catalog "
            f"(read the '{_VARIANTS_RESOURCE}' resource for realization detail per "
            "language; the selection result's applications[] quote intent too). Note "
            "explicitly where two candidates solve the same problem with different "
            "mechanisms.\n"
            "2. Run select_design_patterns TWICE (or three times for three candidates): "
            "each call uses the SAME underlying situation, but the description is worded "
            "once toward each candidate — the candidate's mechanism named in the "
            "constraints, everything else held identical. When a specific realization is "
            "at stake (language, variant, capability floor), add a focus hint saying so.\n"
            "3. Diff the results: which candidate ends up as primary with the higher fit "
            "score; quote the adjustment ledger entries that differ between the runs "
            "(each application's adjustments explain the score gap); note near-ties "
            "(small fit gaps) honestly — within a few points either candidate works.\n"
            "4. Close with a recommendation tied to the user's constraints, not to the "
            "higher score alone."
        )
        return [Message(body)]

    return 4
