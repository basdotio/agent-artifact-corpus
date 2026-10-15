# Development workflows

The helper is intentionally small and agent-neutral. It accepts JSON on stdin and prints JSON on
stdout; a non-success backend result is emitted as `status: unknown` with `auto_action: false`.

## Status and exit codes

| Result | Meaning | What the caller does |
| --- | --- | --- |
| `status: advisory`, exit 0 | A decision was produced. Read `needs_review` before automating on it. | Use it together with the deterministic policy in the same payload |
| `status: unknown`, exit 2 | No decision: timeout, protocol mismatch, backend degraded, credentials rejected, input truncated or rejected locally. `error.code` says which. | Continue with the main model or a human; never read it as a negative answer |
| `status: degraded`, exit 2 | Only from `selftest`: a pinned baseline case drifted. | Re-measure on your own samples; the plumbing is fine |

`auto_action` is always `false`. Nothing in this payload authorises a command, a write, or a model
switch.

## Language

Send English semantic text. The gateway routes on Unicode script, so Chinese or Japanese input goes
to the multilingual checkpoint, which measured clearly weaker on these schemas: the same `select`
question scored `debug` fit 0.80 in English and 0.31 in Chinese (where `none` won at 0.88 and the fit
gate correctly withheld a suggestion). Translate the request, the candidate descriptions and the
question instructions; keep code identifiers, file paths and error strings verbatim.

## Modes

| Mode | Input | Questions | Useful output |
| --- | --- | --- | --- |
| `decide` | `{state, questions}` | caller-defined typed questions | validated answers |
| `select` | `{request, candidates:[{id,description}]}`; 1–6 items | one `choice` plus one `noul` fit check per candidate | `suggested_id`, fit probabilities, `top_margin` |
| `rerank` | `{query, candidates:[{id,text}]}`; 1–6 short excerpts | one `choice` over candidates plus an explicit `none` | selected evidence, ranking, margin |
| `triage` | `first_error` plus optional request/command/exit code/environment/change | failure area plus insufficient-evidence check | investigation direction |
| `verify` | `{claim,evidence}` | supported, contradicted, or insufficient | evidence status |
| `change-review` | `summary`, `changed_files`; optional stats/tests/notes | risk and four atomic review signals | risk floor, minimum test scope, review tags |
| `preset` | plain text plus explicit `laya-preset-*` model | deployment-owned fixed schema | unverified preset answers |
| `selftest` | none | deployment-owned fixtures | contract and baseline case results |

`select` and `rerank` are deliberately capped at 1–6 candidates. The caller should retrieve or
filter candidates first, then ask Laya to make a bounded judgment. Do not pass an entire repository,
issue tracker, or log archive as one state. The protocol itself allows a `choice` question up to 20
options (and a custom `decide` may use that), but accuracy falls off well before 20 — shortlist first.

## Examples

Select a development workflow:

```bash
printf '%s' '{"request":"这个 Python 测试因为导入失败而挂了","candidates":[{"id":"debugging","description":"定位异常并修复源代码"},{"id":"dependency","description":"检查依赖版本和安装状态"},{"id":"release","description":"发布服务并观察线上指标"}]}' \
  | python3 "$SKILL_ROOT/scripts/laya.py" select
```

Triage a first failure:

```bash
printf '%s' '{"request":"修复 CI","command":"pytest -q","exit_code":1,"first_error":"ModuleNotFoundError: No module requests","environment":"Ubuntu CI"}' \
  | python3 "$SKILL_ROOT/scripts/laya.py" triage
```

Check evidence before using it in a review:

```bash
printf '%s' '{"claim":"补丁修复了空列表访问","evidence":"新增测试覆盖空列表，测试在本地通过；尚未运行集成测试"}' \
  | python3 "$SKILL_ROOT/scripts/laya.py" verify
```

Review a proposed change without sending the full diff:

```bash
printf '%s' '{"summary":"Add OAuth session validation and a token table migration","changed_files":["app/auth/session.py","migrations/004_tokens.sql","tests/test_auth.py"],"diff_stats":{"files":3,"additions":140,"deletions":12},"tests":{"unit":"passed","integration":"not_run"}}' \
  | python3 "$SKILL_ROOT/scripts/laya.py" change-review
```

Use `--dry-run` to inspect the generated protocol without contacting the backend. Use `decide` when a workflow does not fit the built-in modes; its top-level object must contain exactly `state` and `questions`.

## Interpreting results

- `select.suggested_id` is a gated recommendation, not an instruction to load or execute a skill. The raw model choice is preserved as `laya_suggested_id`; a candidate is only surfaced as `suggested_id` when its fit probability clears the conservative 0.5 proposition gate. When nothing is surfaced (`none` won, or the gate blocked the pick) `needs_review` is `true`, so "no suggestion" is never reported as a clean result. `none_probability`, `choice_confidence` and `top_margin` are there so the caller can judge the decision rather than just consume it.
- `rerank` follows a `Choice + none` pattern: `selected_id` is the model's best evidence candidate, `ranking` retains all candidate probabilities, and a weak margin or `none` sets `needs_review`. Keep each excerpt under 240 characters; retrieve candidates before calling Laya.
- `triage.suggested_area` combines a transparent first-error heuristic with the Laya signal, and the heuristic wins whenever it matched a known error pattern. The output carries `laya_role: "tiebreaker_only"` because the deployment measured `laya_area` wrong on both an English and a Chinese fixture (it chose `test` and `environment` for a `ModuleNotFoundError`) where the heuristic was right. Treat a disagreement as `needs_review`, not as two equal opinions; when `insufficient_evidence.noul` is high, collect the next diagnostic artifact before editing code.
- `verify` can only classify the supplied evidence. It cannot establish facts absent from that evidence, and an `insufficient` result is a review signal.
- `change-review.policy_floor` is derived deterministically from file paths. Security/auth and migrations are high risk; dependencies, infrastructure, API contracts, and ordinary source changes set lower floors. `effective_risk` and `minimum_test_scope` cannot fall below those floors. Structured test evidence reports `test_scope_satisfied` and `test_scope_gap`; for example, unit tests do not satisfy an integration floor. Review tags name areas to inspect; they do not authorize tools or claim the implementation is correct.
- Keep the answer, probability, model, latency, and policy branch in safe structured logs; omit raw secrets and unnecessary source text.

## Protocol constraints

The dynamic envelope is `laya.decision.v1`. The client and adapter reject unknown question fields, unsupported types, non-finite numbers, oversized option text, and requests that would make Laya silently truncate the question or state. A malformed or degraded result is `unknown`; it is never converted into approval.

The protocol follows the TypeSafe pattern of code-owned workflows and typed judgments, but it is not a TypeSafe Jev call. The adapter routes English semantic text to the English checkpoint and Chinese/non-Latin text to multilingual. Routing deliberately ignores path-heavy fields when a semantic field is available. The response exposes the actual checkpoint and route reason. `laya-typed-decisions` remains an explicit specialized model and is not selected implicitly.

The deployment reports `calibration: deployment_unverified`. Raw probabilities help compare options inside one response, but they are not production-calibrated thresholds. Keep labeled examples for the actual development workflows before automating even a low-risk branch.

## Adding a workflow

Prefer adding a small pure transformation in `scripts/dev_workflows.py` only when it will be reused. Keep candidate limits, labels, state fields, and output interpretation explicit. Add a dry-run example and a labeled evaluation set before making a new workflow eligible for automatic branching.
