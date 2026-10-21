# Portable browser entry contract

## Capabilities and setup

The host needs Python 3.11+, local process/file access, and its own supported
browser tool with user-authorized Garmin access. A browser-only host can perform
UI actions but cannot run this local MCP. The supplied CUA worker is one adapter,
not the portability contract. Different hosts require actual acceptance; a shared
Skill does not install a native plugin or guarantee model-equivalent judgments.

Clone the public repository, create a venv, install `requirements.lock` with
`python -m pip install --require-hashes -r requirements.lock`, then install the
checkout with `python -m pip install --no-deps --no-build-isolation .`. The build
requires setuptools>=68. Run with that venv's Python. No model API key, Intervals
connection, user Mac, public MCP server or publisher health database is required.

Start with `python -m garmin_agent_tools.browser inspect`. Success prints actual
initialize instructions, tool schemas, prompt metadata and inspection_complete
with tool_invoked:false. This verifies the local protocol, not Garmin access.
Locate the installed Skill with the browser CLI's `skill-path` command. Read it
and keep its references directory with it when packaging for a client.

Private state defaults outside source under
`~/.local/share/garmin-agent-tools-browser`. A trusted operator can set
`GARMIN_AGENT_BROWSER_HOME` to an absolute private directory outside the checkout.
Use 0700 directories and 0600 observation files. Preserve the original runtime
and receipts across retries. VM replacement can lose state; no retention period
or Garmin browser-session lifetime is guaranteed.

## Read one authorized workout

Run `python -m garmin_agent_tools.browser read-workout --workout-id WORKOUT_ID`.
The SDK prints its real context, then request_ready. Keep that client running.
Verify that the requested ID is in the user's scope. The parent refreshes the
canonical `https://connect.garmin.com/app/workout/WORKOUT_ID` after request
creation, checks the current URL and reads visible fields with its own browser.
Stop at login, MFA, CAPTCHA, permission denial or ambiguity. Complete a normal
private login only within the user's authorization, then start a fresh read;
never reuse an expired request or pretend old data is fresh.

For the supplied Dot CUA adapter, read [the CUA adapter contract](cua.md). For another supported browser, save a private JSON report
matching `publisher.ParentBrowserObservation` and run:

```sh
python -m garmin_agent_tools.browser record-read --run-dir RUN_DIR --request-id REQUEST_ID --observation-file PRIVATE_JSON
```

The report includes the original request_id, operation:read_workout, workout_id,
source_type:browser_ui, agent_mediated:true,
observation_method:parent_browser_tool, observed_url (the exact canonical URL),
refreshed_at and observed_at (actual timezone-aware timestamps), name, sport and
steps. Each step has name, duration_seconds and targets; unread fields are null.
calendar_evidence, watch_evidence and api_authentication remain unknown for this
workout-only read. Never copy the proposal or an offline example as observation.
The parent reports these observations; the recorder cannot independently inspect
a browser, verify identity or prove the page refresh actually occurred.

record-read enforces request/workout IDs, canonical URL, freshness order,
expiry, selected-field schema and file protection before publishing. It retains
the parent's report and refuses overwrites. After an interrupted local publication,
the identical report may complete the same unexpired request; changed reports and
expired requests remain blocked. No new observation time is generated. Success is observation_published;
the original MCP client must also finish with observed and isError:false. Other
results are NOT VERIFIED, not a negative training result. A lost process handle
is INCONCLUSIVE; inspect retained receipts before considering another operation.

## Exact test delivery

Read [the packaged delivery contract](delivery.md) for preview, exact owner
confirmation, account consistency, execution and selected readback. It contains
the complete workflow and commands; no repository README is required at runtime.
Use an AGENT-prefixed test name for a host-neutral proposal. Existing DOT-prefixed
proposals remain valid. The existing status pending_parent_cua names the trusted
parent-browser handoff; it does not install CUA into other hosts. There are no
automatic browser write selectors.

## What leaves the agent computer

Local MCP is stdio. The browser connects to Garmin and its normal site resources.
Returned fields also enter the supervising agent/model platform and may be
retained there. Selected observations and journals remain in private runtime;
GitHub and package registries supply installation code, not a health backend.
No credentials, raw page exports or provider payloads belong in source or public
reports. This is not a promise of device-only data processing or zero risk.

## Other health sources

ChatGPT Health can use authorized Apple Health data after iPhone setup, subject to
account availability. Dot supports some installed plugins, but this does not
establish Health availability in Dot or a third-party plugin. Detect an actual
supported Health tool before using it; never infer access from a shared account.
This package has no phone/HealthKit connector. File import or an authorized iPhone
HealthKit app would be a separate data adapter.
