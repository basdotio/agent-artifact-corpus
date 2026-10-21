# Exact test proposal and approved delivery

```sh
python -m garmin_agent_tools.browser preview --name 'DOT MCP BROWSER TEST example' --date YYYY-MM-DD
```

Choose the explicit name/date. This only saves a fixed running connectivity test:
warmup 300 seconds, run 600 seconds, cooldown 300 seconds, all NoTarget. It permits
only a newly created tool-owned workout and its calendar date; no existing-workout
edits, deletions or device sends. It is not a coaching recommendation.

Show the exact saved proposal and effects to the owner. Its SHA256 covers canonical
UTF-8 JSON, sorted keys, compact separators, ASCII escapes and one trailing LF.
Neither the ID nor SHA is approval. Only after an actual current owner reply may
the trusted operator create a separate private confirmation with the
`OwnerConfirmation` schema in `browser/write_protocol.py`: schema version, exact
preview ID/SHA/name/date, verified owner-reply reference and timestamp, record
timestamp, explicit expiry and `browser_account_key`. Save it exclusively as
`approvals/<preview_id>.json`, mode 0600, outside source. The operator must verify
the real human reply, identity and permission; the file cannot prove those itself.
The account key is a local SHA256 fingerprint of the current owner's visible
`View Profile` link in their own `Profile & Account` menu. Do not use a friendly
display name, the workout author's profile, cookies or hidden state. Use the
documented `account_key_from_profile_url` helper, or the equivalent pure local
`accountKeyFromProfileUrl` function loaded with the CUA worker. The observed own
profile route is `/app/profile/<identifier>`. Keep the href in the CUA runtime;
do not print, store, or pass it as a literal command argument. Unknown identity
blocks dispatch; this fingerprint is parent-reported session consistency, not
independent identity attestation or a claim of stability across future logins.
It does not change the saved proposal bytes or require another athlete action.
Same-UID file trust is not a cryptographic human signature. There is no approve
MCP tool or credential input.

```sh
python -m garmin_agent_tools.browser apply-existing --preview-id PREVIEW_ID --proposal-sha256 PROPOSAL_SHA256
```

Without a current exact confirmation, this returns `awaiting_owner_confirmation`
and creates no queue. Otherwise, it creates one durable dispatch claim/journal and
returns pending. A queue is not a Garmin write. Before any possible browser
mutation, the trusted parent calls
`write_protocol.claim_execution(write_protocol.PRIVATE, binding, browser_account_key=current_account_key)` outside MCP,
using the same ID/SHA binding. It must return successfully; a lost/failed result
means stop and reconcile read-only. Recheck the correct owner account, current
approval and duplicate-name absence. Use fresh supported UI to create only that
new workout and schedule only it on the exact date. No write browser selectors or
automatic browser write controller are included.

After actual workout/calendar readback, the parent saves a mode 0600 (or 0400)
private selected JSON with `schema_version: "selected-browser-observation-v1"`
matching `BrowserObservation`: proposal binding, `browser_ui`,
`agent_mediated:true`, actual timezone-aware observation timestamp, actual workout
ID/name/raw visible sport/step/target labels, actual seconds, the matching calendar
workout ID/date, and a fresh own-menu `browser_account_key` matching execution.
The comparison normalizes only the listed English labels: `Run`/`Running` for
sport, `Warm up`/`warmup`, `Run`, `Cool down`/`cooldown` for steps, and
`No Target`/`NoTarget` for targets (case/whitespace insensitive). Original labels
remain in the private receipt. Unknown labels never imply NoTarget. Do not copy
the expected proposal as though it were observed. Missing or mismatched evidence
cannot establish delivery. Then record the observation outside MCP:

```sh
python -m garmin_agent_tools.browser record-observation --preview-id PREVIEW_ID --proposal-sha256 PROPOSAL_SHA256 --observation-file PRIVATE_SELECTED_JSON
```

Run the same `apply-existing` command to read back status. An existing dispatch
claim never redispatches. Exact selected matching can report
`browser_observed_scheduled`, explicitly agent-reported rather than independently
verified; API authentication and watch receipt remain unknown. Partial/uncertain
effects require read-only reconciliation, never automatic replay. Preserve the
original claims, queues, outcomes, observations and journals.
