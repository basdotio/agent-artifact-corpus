"""What a UAT run is made of, and how it is read from a file.

A persona is defined by what changes the path it takes — where it enters, at
what width and language, signed in or not, what it is trying to do, how we know
it got there, how many steps it gets, and what it must not do — not by a
backstory. These models hold exactly that, plus the target the run may touch,
the brain that plays the persona, and the limits the server enforces.

Files are YAML or JSON. A run file may nest everything, or point at other files
(``persona_file``, ``target_file``, ``brief_file``, ``prior_findings_file``)
resolved relative to itself, so one target and one round brief serve many
personas.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

_ID = re.compile(r"^[a-z0-9][a-z0-9_-]{0,31}$")
_VIEWPORT = re.compile(r"^\s*(\d{3,5})\s*[x×]\s*(\d{3,5})\s*$")

Backend = Literal[
    "anthropic", "openrouter", "ollama", "openai-compat", "claude-code", "codex", "scripted"
]
"""Who plays the persona. ``scripted`` replays a fixed list of tool calls (tests, e2e gates)."""

Severity = Literal["blocker", "major", "minor"]
Outcome = Literal["reached_goal", "partial", "blocked"]
Verdict = Literal["FIXED", "STILL_THERE", "COULD_NOT_CHECK"]


class Strict(BaseModel):
    """Unknown keys are mistakes, not extensions: a misspelt ``step_budget`` must not
    silently become "no budget"."""

    model_config = ConfigDict(extra="forbid")


class Viewport(Strict):
    width: int = Field(1280, ge=200, le=10000)
    height: int = Field(800, ge=200, le=10000)

    @classmethod
    def parse(cls, value: object) -> Viewport:
        if isinstance(value, Viewport):
            return value
        if isinstance(value, str):
            match = _VIEWPORT.match(value)
            if not match:
                raise ValueError(f"viewport must look like 1280x800, got {value!r}")
            return cls(width=int(match.group(1)), height=int(match.group(2)))
        if isinstance(value, dict):
            return cls(**value)
        raise ValueError(f"viewport must be a string or an object, got {type(value).__name__}")

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"


class Persona(Strict):
    id: str
    name: str
    entry_url: str
    viewport: Viewport = Field(default_factory=Viewport)
    locale: str = "en-US"
    # ``none`` is an anonymous visitor. ``preseeded`` means the profile the run is
    # given (``RunSpec.data_dir``) already holds a login the hooks or the operator
    # put there; the run itself never signs in.
    account: Literal["none", "preseeded"] = "none"
    account_note: str = ""
    goal: str
    success_criteria: list[str] = Field(default_factory=list)
    # Action steps (navigate, click, type ...). Reads are free; the server stops
    # counting the moment the budget is spent and only ``finish`` remains.
    step_budget: int = Field(25, ge=1, le=500)
    must_not: list[str] = Field(default_factory=list)
    known_limits: list[str] = Field(default_factory=list)
    # Files the persona may hand to the page. Unset means ``upload_file`` is not
    # offered at all; set, every path must resolve inside this directory.
    uploads_allowed_dir: Path | None = None
    # Sites this persona needs beyond the target's (a payment provider it may open).
    extra_trusted_origins: list[str] = Field(default_factory=list)
    notes: str = ""

    @field_validator("id")
    @classmethod
    def _id(cls, value: str) -> str:
        if not _ID.match(value):
            raise ValueError("persona id must be lowercase [a-z0-9_-], at most 32 chars")
        return value

    @field_validator("entry_url")
    @classmethod
    def _entry_url(cls, value: str) -> str:
        if not value.startswith(("http://", "https://")):
            raise ValueError("entry_url must be an http(s) URL")
        return value

    @field_validator("viewport", mode="before")
    @classmethod
    def _viewport(cls, value: object) -> Viewport:
        return Viewport.parse(value)

    @field_validator("uploads_allowed_dir", mode="before")
    @classmethod
    def _expand(cls, value: object) -> object:
        return Path(value).expanduser() if isinstance(value, str) else value


class Target(Strict):
    """Where the run may go. Entries use the ``trusted_origins`` grammar of the
    server (``example.com``, ``*.example.com``, ``https://app.example.com``)."""

    trusted_origins: list[str] = Field(default_factory=list)
    # "closed": the run stays on trusted_origins and nothing outside can be approved
    # (acceptance of one's own product). "autonomous": nobody is there to ask, so the
    # server approves what a task on the open web needs: any site, and a declared
    # SUBMIT / UPLOAD / DOWNLOAD. PUBLISH, file:/data: URLs, card numbers and
    # ``deny_origins`` stay refused, and every approval is audited as ``autonomous``.
    policy: Literal["closed", "autonomous"] = "closed"
    deny_origins: list[str] = Field(default_factory=list)
    # Sites where sending is pre-approved too (SUBMIT, UPLOAD): the product under
    # test, never a third party. PUBLISH and DOWNLOAD stay asked, and in an
    # unattended run "asked" means refused.
    trusted_send_origins: list[str] = Field(default_factory=list)
    proxy: str | None = None
    # Requests whose URL matches one of these regexes are kept in full
    # (query string, POST body) in ``network.jsonl``; everything else is a summary.
    network_capture: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def _closed_needs_a_site(self) -> Target:
        # A closed run with no trusted site cannot even load its entry page.
        if self.policy == "closed" and not self.trusted_origins:
            raise ValueError("target.trusted_origins is empty: list the site under test")
        return self

    @field_validator("network_capture")
    @classmethod
    def _regexes(cls, patterns: list[str]) -> list[str]:
        for pattern in patterns:
            try:
                re.compile(pattern)
            except re.error as exc:
                raise ValueError(f"network_capture pattern {pattern!r}: {exc}") from exc
        return patterns


class BrainSpec(Strict):
    backend: Backend = "claude-code"
    # The model name as the backend spells it. None takes the backend's default.
    model: str | None = None
    # OpenAI-compatible backends: where to send requests and which env var holds
    # the key. The presets (openrouter, ollama) fill these in; openai-compat
    # requires base_url.
    base_url: str | None = None
    api_key_env: str | None = None
    # Our own loop: how many model turns before the run is cut off. A harness
    # gets this as its turn limit. Generous because reads are turns too.
    max_turns: int = Field(150, ge=1, le=2000)
    max_budget_usd: float | None = Field(None, gt=0)
    max_tokens: int = Field(16000, ge=256, le=128000)
    # Anthropic effort level; other backends ignore it.
    effort: Literal["low", "medium", "high", "xhigh", "max"] | None = None
    # ``scripted``: the tool calls to replay, in order ``[{"tool": ..., "args": {...}}]``.
    script: list[dict[str, Any]] = Field(default_factory=list)
    # Anything a backend wants that has no field: passed through unchanged.
    extra: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _needs(self) -> BrainSpec:
        if self.backend == "openai-compat" and not self.base_url:
            raise ValueError("openai-compat needs base_url")
        if self.backend == "scripted" and not self.script:
            raise ValueError("scripted needs a non-empty script")
        return self


class Hooks(Strict):
    """Shell commands around the run — seeding a profile, checking analytics
    afterwards. Their exit code and output land in the report; a failing
    ``before`` stops the run."""

    before: str | None = None
    after: str | None = None
    timeout_s: int = Field(600, ge=1)


class Limits(Strict):
    # Wall clock for the whole run, brain included. Past it the run is cut off
    # and reported as incomplete with everything recorded so far.
    wall_s: int = Field(1800, ge=30)
    # A screenshot to disk after every action step, for the trace. Not shown to
    # the model unless it asks (``screenshot``).
    auto_screenshot: bool = True
    # ``on_demand``: screenshot/read_image results reach the model as images.
    # ``never``: it gets the path only (a text-only model).
    vision: Literal["on_demand", "never"] = "on_demand"
    # Longest tool result handed to the model; the rest is cut with a marker.
    max_tool_output_chars: int = Field(12000, ge=500)


class ToolPolicy(Strict):
    """Which browser tools the persona is offered. ``allow`` None means the
    default UAT set (``DEFAULT_TOOLS``); ``deny`` is removed afterwards."""

    allow: list[str] | None = None
    deny: list[str] = Field(default_factory=list)


class PriorFinding(Strict):
    """A finding from an earlier round the persona re-checks and judges."""

    id: str
    severity: Severity = "minor"
    url: str = ""
    step: int | None = None
    expected: str = ""
    actual: str
    round: str | None = None


DEFAULT_TOOLS: tuple[str, ...] = (
    "navigate",
    "go_back",
    "reload_page",
    "click",
    "type_text",
    "press_key",
    "hover",
    "scroll",
    "read_page",
    "get_url",
    "screenshot",
    "read_image",
    "wait_for",
    "read_form",
    "select_option",
    "handle_dialog",
    "tabs",
    "list_downloads",
)
"""Browser tools a persona gets by default. ``upload_file`` joins when the
persona has ``uploads_allowed_dir``. The rest — open/close (the runner's),
editor and publish tools, the collaboration tools (nobody is watching) — stay out."""

UAT_TOOLS: tuple[str, ...] = ("report_finding", "verdict", "note", "finish")
"""Tools added by UAT mode (tools/uat.py). Always offered, never budgeted."""


class RunSpec(Strict):
    persona: Persona
    target: Target
    brain: BrainSpec = Field(default_factory=BrainSpec)
    # A round addendum shown to the persona after its definition, verbatim.
    brief: str | None = None
    prior_findings: list[PriorFinding] = Field(default_factory=list)
    hooks: Hooks = Field(default_factory=Hooks)
    limits: Limits = Field(default_factory=Limits)
    tools: ToolPolicy = Field(default_factory=ToolPolicy)
    # Where run directories are created: ``<out_dir>/<run_id>/``.
    out_dir: Path = Path("uat-runs")
    # The browser profile. None: a fresh one inside the run directory. Set: an
    # existing data dir (``LYRA_BROWSER_DATA_DIR`` layout) a hook seeded.
    data_dir: Path | None = None
    headless: bool = True
    guard_backend: Literal["route", "cdp"] = "route"
    driver: Literal["auto", "playwright", "patchright"] = "auto"
    # What the persona writes its notes, findings and summary in. A harness runs
    # as its own user would (a Korean operator's Claude answers in Korean), so the
    # language of a report is a decision of the spec, never an inheritance.
    report_language: str = "English"

    @field_validator("out_dir", "data_dir", mode="before")
    @classmethod
    def _expand(cls, value: object) -> object:
        return Path(value).expanduser() if isinstance(value, str) else value

    @field_validator("brief")
    @classmethod
    def _brief(cls, value: str | None) -> str | None:
        return value.strip() or None if value is not None else None

    @model_validator(mode="after")
    def _preseeded_needs_a_profile(self) -> RunSpec:
        # A signed-in persona is only as signed in as the profile it is given. With no
        # data_dir the run would start from an empty profile and meet the site as a
        # stranger, while the report said it ran as the account.
        if self.persona.account == "preseeded" and self.data_dir is None:
            raise ValueError(
                "persona.account is 'preseeded': give data_dir, the browser profile that "
                "already holds the login (a `before` hook may seed it)"
            )
        return self

    def offered_tools(self) -> list[str]:
        """Browser tool names the persona is given, in a stable order."""
        allowed = list(self.tools.allow) if self.tools.allow is not None else list(DEFAULT_TOOLS)
        if self.persona.uploads_allowed_dir is not None and "upload_file" not in allowed:
            allowed.append("upload_file")
        denied = set(self.tools.deny)
        return [name for name in allowed if name not in denied]

    def all_trusted_origins(self) -> list[str]:
        return [*self.target.trusted_origins, *self.persona.extra_trusted_origins]


class GroupSpec(Strict):
    name: str
    # ``parallel`` runs the group's personas at once (anonymous visitors);
    # ``sequential`` one after another (personas sharing an account).
    mode: Literal["parallel", "sequential"] = "sequential"
    personas: list[str] = Field(min_length=1)


class BatchSpec(Strict):
    """Several personas against one target, in groups."""

    target: Target
    brain: BrainSpec = Field(default_factory=BrainSpec)
    # Persona id -> persona file, resolved relative to the batch file.
    personas: dict[str, Path]
    groups: list[GroupSpec] = Field(min_length=1)
    concurrency: int = Field(4, ge=1, le=32)
    brief: str | None = None
    prior_findings: list[PriorFinding] = Field(default_factory=list)
    hooks: Hooks = Field(default_factory=Hooks)
    limits: Limits = Field(default_factory=Limits)
    tools: ToolPolicy = Field(default_factory=ToolPolicy)
    out_dir: Path = Path("uat-runs")
    # Persona id -> browser profile (``LYRA_BROWSER_DATA_DIR`` layout) that already holds
    # its login. Required for ``preseeded`` personas; others get a fresh profile.
    data_dirs: dict[str, Path] = Field(default_factory=dict)
    headless: bool = True
    guard_backend: Literal["route", "cdp"] = "route"
    driver: Literal["auto", "playwright", "patchright"] = "auto"
    report_language: str = "English"

    @field_validator("out_dir", mode="before")
    @classmethod
    def _expand(cls, value: object) -> object:
        return Path(value).expanduser() if isinstance(value, str) else value

    @field_validator("data_dirs", mode="before")
    @classmethod
    def _expand_dirs(cls, value: object) -> object:
        if isinstance(value, dict):
            return {k: Path(v).expanduser() if isinstance(v, str) else v for k, v in value.items()}
        return value

    @model_validator(mode="after")
    def _groups_name_known_personas(self) -> BatchSpec:
        unknown = [p for g in self.groups for p in g.personas if p not in self.personas]
        if unknown:
            raise ValueError(f"groups name personas not in `personas`: {sorted(set(unknown))}")
        stray = sorted(set(self.data_dirs) - set(self.personas))
        if stray:
            raise ValueError(f"data_dirs name personas not in `personas`: {stray}")
        # Two browsers on one profile cannot run at once: the second silently falls back
        # to an empty profile (see the profile lock) and runs as a stranger.
        for group in self.groups:
            if group.mode != "parallel":
                continue
            seen: dict[Path, str] = {}
            for pid in group.personas:
                directory = self.data_dirs.get(pid)
                if directory is None:
                    continue
                key = directory.expanduser().resolve()
                if key in seen:
                    raise ValueError(
                        f"group {group.name!r} runs {seen[key]!r} and {pid!r} in parallel on "
                        f"the same data_dir {directory}; make the group sequential"
                    )
                seen[key] = pid
        return self


# --- files ----------------------------------------------------------------------------

_FILE_KEYS = {
    "persona_file": "persona",
    "target_file": "target",
    "brief_file": "brief",
    "prior_findings_file": "prior_findings",
}


def load_document(path: Path) -> Any:
    """Read YAML or JSON. JSON is YAML, so the YAML reader handles both when
    installed; without it (core install) only JSON files are readable."""
    text = path.read_text(encoding="utf-8")
    try:
        import yaml  # type: ignore[import-untyped]
    except ImportError:
        if path.suffix.lower() not in (".json",):
            raise RuntimeError(
                f"{path} is not JSON and PyYAML is not installed (pip install lyra-browser[uat])"
            ) from None
        return json.loads(text)
    return yaml.safe_load(text)


def _resolve_files(document: dict[str, Any], base: Path) -> dict[str, Any]:
    """Replace ``*_file`` keys by the content of the file they name."""
    out = dict(document)
    for file_key, key in _FILE_KEYS.items():
        if file_key not in out:
            continue
        if key in out:
            raise ValueError(f"give either `{key}` or `{file_key}`, not both")
        target = (base / str(out.pop(file_key))).expanduser()
        if key == "brief":
            out[key] = target.read_text(encoding="utf-8")
        else:
            out[key] = load_document(target)
    return out


def load_run_spec(path: Path, **overrides: Any) -> RunSpec:
    """Read a run file. ``overrides`` are top-level keys from the command line
    (``brain``, ``out_dir`` ...) and win over the file.

    A file holding only a persona (no ``persona`` key) is accepted when the
    caller supplies ``target`` in ``overrides`` — the persona-per-file layout.
    """
    document = load_document(path)
    if not isinstance(document, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    document = _resolve_files(document, path.parent)
    if "persona" not in document and "id" in document and "entry_url" in document:
        document = {"persona": document}
    for key, value in overrides.items():
        if value is None:
            continue
        if isinstance(value, dict) and isinstance(document.get(key), dict):
            document[key] = {**document[key], **value}
        else:
            document[key] = value
    return RunSpec.model_validate(document)


def load_batch_spec(path: Path) -> BatchSpec:
    document = load_document(path)
    if not isinstance(document, dict):
        raise ValueError(f"{path}: expected a mapping at the top level")
    document = _resolve_files(document, path.parent)
    spec = BatchSpec.model_validate(document)
    spec.personas = {
        pid: (path.parent / Path(p).expanduser()).resolve() for pid, p in spec.personas.items()
    }
    # The key is how groups and data_dirs name a persona, the file's id is how its
    # run and report do: when they differ, a report would answer to a name nothing
    # in the batch uses. Refuse rather than pick one.
    for pid, persona_path in spec.personas.items():
        persona = load_persona(persona_path)
        if persona.id != pid:
            raise ValueError(
                f"batch persona key {pid!r} does not match the id {persona.id!r} in {persona_path}"
            )
        if persona.account == "preseeded" and pid not in spec.data_dirs:
            raise ValueError(
                f"persona {pid!r} is 'preseeded': add its browser profile to `data_dirs`"
            )
    return spec


def load_persona(path: Path) -> Persona:
    document = load_document(path)
    if isinstance(document, dict) and "persona" in document and "id" not in document:
        document = document["persona"]
    return Persona.model_validate(document)
