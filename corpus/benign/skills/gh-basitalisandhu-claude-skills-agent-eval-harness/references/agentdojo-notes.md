# From the template to AgentDojo

## What AgentDojo gives you

- Four suites (slack, banking, travel, workspace) with realistic tools, 97 user tasks and 949 attack cases (user task x injection task x placement), with ground-truth checks for utility and attack success.
- Attack templates (`important_instructions`, `tool_knowledge`, …) and the harness that places the injection into the environment fields the agent will read.
- A pipeline abstraction where the tool executor is one element, which is where a policy belongs.

## Installing

```bash
python3 -m venv .venv && .venv/bin/pip install "agentdojo==0.1.35"
```

Pin the version; task ids and checks change between releases and your numbers must be comparable over time.

## Running the benchmark with a policy

AgentDojo's pipeline has a tool executor element; that is where the policy belongs, so every proposed tool call passes through it before it runs. Port the template's `ProvenancePolicy` and `ApprovalPolicy` (from `scripts/eval_runner.py`) into a custom tool executor, then run the suites with the policy off and on, using the same model, attack template and number of runs for each.

A model-free replay (a scripted agent that obeys every injection) is a cheap first check: it shows which cases the policy blocks before any model cost is spent.

When cases share a user task, report confidence intervals with a bootstrap clustered by user task rather than treating every case as independent.

## Mapping your agent onto a suite

If your agent's tools are close to one of the suites (e-mail and calendar: workspace; chat: slack; money: banking; bookings: travel), write a thin adapter so the agent sees the suite's tool interface, run the suite, and report per-suite numbers. If not, build your own `TaskSuite`:

- environment: a pydantic model of the state
- tools: functions with typed arguments and docstrings (the docstring is the tool description the model sees, so review it like code)
- user tasks: `@task_suite.register_user_task` classes with `PROMPT` and `utility(model_output, pre_env, post_env)`
- injection tasks: `@task_suite.register_injection_task` classes with `GOAL` and `security(model_output, pre_env, post_env)`
- injection vectors: the environment fields marked `{injection_name}` where attacker text is placed

## What to report

| Metric | Definition |
|---|---|
| Benign utility | share of user tasks passed with no injection |
| Utility under attack | share of (user task, injection) cases where the user task still passed |
| Targeted ASR | share of cases where the injection goal was achieved |
| Denials | consequential calls refused by the policy; split into correct refusals and utility losses |

Report per policy, per attack template, with the model name and version, temperature, number of runs and a confidence interval. Keep raw traces for every failing case.

## Pitfalls

- A high utility with ASR 0 from a *refusing* model is not a secure agent; check the denials column and the traces.
- Injection tasks whose success check can be satisfied by the benign task are measurement errors; run every injection with no agent and confirm success is 0.
- Do not let the eval's attacker addresses, URLs or ids appear in user task prompts; the provenance policy would then pass them legitimately.
- Keep the eval suite out of the agent's context (no reading `eval/` files during a run).
