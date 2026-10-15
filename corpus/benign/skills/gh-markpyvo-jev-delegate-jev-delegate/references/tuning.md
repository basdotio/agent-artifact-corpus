# Tuning jev-delegate

## Contents
- What Jev is asked
- How the tier is decided
- Why subagents and not the main model
- Environment variables and flags
- Calibrating on your own tasks
- Credits and what was borrowed

## What Jev is asked

One request to `POST https://api.typesafe.ai/v1/systemone` with `model: jev-latest`, a `state` of `{"task": "<description>"}`, and four questions, all scored in parallel against the same state:

| Question | Type | Purpose |
|---|---|---|
| `tier` | choice: mechanical / ordinary / hard | Main routing signal |
| `effort` | score, 4 levels (0 to 3) | Second opinion on difficulty; also gives `effort_hint` |
| `risky` | noul | Would doing the task itself change production, move money, or destroy data? |
| `wide` | noul | Does it need many files or the whole codebase at once? |

Jev never sees model names. Criteria describe situations ("unknown root cause", "rename one symbol"), not degrees, because the model matches situations far better than adjectives.

## How the tier is decided

Default is `balanced` (Sonnet). Then, in order:

1. `risky >= 0.7` gives `deep`, regardless of anything else.
2. Jev says `hard` and confidence >= `--min-upgrade` (0.3) gives `deep`. Otherwise stay `balanced`.
3. Jev says `mechanical` gives `fast` only if all of these hold: confidence >= `--min-downgrade` (0.6), effort score < 1.5, and `wide` < 0.6. Any miss stays `balanced`.
4. Anything else is `balanced`.

The bars are asymmetric on purpose. Going up too often wastes a little money; going down wrongly wastes a whole failed run plus a retry. The `wide` check keeps big-context tasks off the smaller model.

`effort_hint` maps the effort score to low / medium / high / xhigh, capped by `--max-effort` (default high).

Any error, timeout (default 2.5 s), missing key, or malformed reply returns tier `inherit` with `model: null`.

## Why subagents and not the main model

Prompt caches are per model. Switching the main conversation to another model means the new model has no cache for the context, so the whole thing is rewritten at a higher rate. One community router measured this at roughly $2.40 to hop from Opus to Sonnet at a 600k-token context versus about $0.12 to stay on a warm cache. Subagents start with small, fresh contexts, so routing them avoids the problem. Routing reasoning effort per turn is a separate lever some tools support; this skill only gives an advisory `effort_hint`.

## Environment variables and flags

| Name | Default | Meaning |
|---|---|---|
| `TYPESAFE_API_KEY` / `JEV_API_KEY` | none | API key; without it the script returns `inherit` |
| `JEV_FAST_MODEL` | `haiku` | Model name passed for the fast tier |
| `JEV_BALANCED_MODEL` | `sonnet` | Model name for the balanced tier |
| `JEV_DEEP_MODEL` | `opus` | Model name for the deep tier. Point it at whichever model you actually run |
| `JEV_MODEL` | `jev-latest` | Pin a version like `jev-1.13.0` once you have tuned thresholds |
| `JEV_URL` | TypeSafe endpoint | Override the endpoint (for testing) |
| `JEV_DELEGATE_LOG` | `1` | Set `0` to stop writing `~/.jev-delegate/decisions.jsonl` |

Flags: `--timeout`, `--min-upgrade`, `--min-downgrade`, `--max-effort`, `--file`, `--dry-run`.

The script calls TypeSafe directly. Access through Vercel AI Gateway or OpenRouter uses a different request format and is not supported here.

## Calibrating on your own tasks

The questions and thresholds are reasoned defaults, not measured ones.

1. Collect 20 to 30 real subtasks from your recent sessions and label each `fast`, `balanced`, or `deep` by what you would have wanted.
2. Run them through `route.py` and compare. Watch two failure types separately: tasks sent to `fast` that needed more (expensive, because they fail and retry), and tasks sent to `deep` that were easy (only costs money).
3. If too many easy tasks land on `balanced`, lower `--min-downgrade` slightly. If any hard task lands on `fast`, raise it and check the `effort` and `wide` gates.
4. Once results look right, pin `JEV_MODEL` to the versioned id from a response so a model update does not silently move your thresholds.

Use `python scripts/report.py` for the tier spread and a rough relative cost. Its price weights are assumptions; edit them with `--fast-weight` and `--balanced-weight`.

## Credits and what was borrowed

This skill is a fresh implementation, not a copy. The design leans on ideas from public projects built on Jev:

- moelahmady/jev-model-router: the per-model prompt-cache cost argument, the separate `risky` yes/no question, the `effort` score, the asymmetric up/down confidence bars, the 2.5 s timeout, and fail-open behavior.
- andrei10k/claude-jev-model-router: routing subagents while leaving the main conversation alone, and combining several independent questions in code instead of asking one big one.
- flaviusapop/jev-router: choosing the tier once and pinning it for the task.
- gargpratyush/jev-router: per-turn routing wrapper for Claude Code and Codex, which is the full-proxy alternative if you want automatic routing without a skill.

The request and response shapes come from the public TypeSafe walkthrough by Flavio Copes (flaviocopes.com/jev). They were not tested against the live API when this skill was written, so run one real call and compare with `--dry-run` output if anything looks off.
