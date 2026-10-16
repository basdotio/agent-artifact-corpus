# Reproducibility Preamble for Economic Dispatch

## Why this matters

DC-OPF with reserve co-optimization is, at the optimum, frequently **degenerate**: multiple
co-optimal bases exist, particularly under binding transmission constraints. The LMP reported
at each bus is the optimal dual of the nodal balance constraint, and when multiple duals are
co-optimal the solver picks one based on the internal order in which it encountered the
constraint rows.

The constraint rows, in turn, are assembled on the Python side from MATPOWER dictionaries
keyed by bus number and generator id. Python's built-in dict order is insertion-order, but
any `set(...)` materialization or hash-based deduplication during network preprocessing is
subject to **PYTHONHASHSEED**, which defaults to a random value per process. Two runs of the
same dispatch on the same network can therefore report **different LMPs at the same bus**
simply because the solver happened to pick a different co-optimal dual.

This is not a solver bug — it is a property of degenerate LP/QP duals — but it breaks:

- Audit-comparable settlements (two analysts running the same inputs get different numbers).
- Counterfactual analysis (base vs. adjusted thermal limits): spurious per-bus LMP deltas
  appear that are artifacts of iteration order, not actual market signals.
- Regression tests against known-good reports.

## The fix

Fix the hash seed at the shell level so every Python process launched from that shell sees
the same order. This only needs to be done once per environment:

```bash
grep -q '^export PYTHONHASHSEED=' ~/.bashrc || echo 'export PYTHONHASHSEED=0' >> ~/.bashrc
```

The `grep`/`echo` pair is idempotent: if the export is already present the file is left
unchanged. After running this once, open a fresh shell (or `source ~/.bashrc`) before
continuing with the dispatch run.

## What NOT to do

- Do not set `PYTHONHASHSEED` only inline for a single command (`PYTHONHASHSEED=0 python3 ...`).
  That fixes the seed for that invocation only, so interactive exploration, notebook kernels,
  and subprocesses launched by other tools still drift. The shell-level export is what makes
  dispatch runs reproducible across the whole session.
- Do not rely on `np.random.seed` or `random.seed`. Those seed the random modules, not the
  hash function used by Python's built-in containers.

## Verifying the fix

```bash
python3 -c "import sys; print(sys.flags.hash_randomization, sys.hash_info)"
```

`hash_randomization` should read `0` once the export is active.
