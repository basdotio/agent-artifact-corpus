#!/usr/bin/env python3
"""Pick worker model/effort settings bandit-style from past workflow runs.

  tools/bandit.py record <workflow transcript dir>   # add a finished run to tools/bandit_stats.json
  tools/bandit.py next [agents] [explore]             # print next run's per-agent configs (JSON)
  tools/bandit.py report                              # table of per-setting stats

Score = committed code bytes per agent-hour, older runs decayed by DECAY each record; only arms
with >= MIN_HOURS can be exploited. The best setting gets agents-explore slots;
the explore slots go to the other settings with the fewest agent-hours sampled.
"""
import datetime, glob, json, os, re, sys
sys.path.insert(0, os.path.dirname(__file__))
from split import load_funcs

# BANDIT_CONTEXT=retry keeps separate stats for retry runs (hard near-misses behave differently
# from fresh functions: low effort is cheap on small fresh ones but loses on large retries)
_ctx = os.environ.get("BANDIT_CONTEXT", "")
STATS = os.path.join(os.path.dirname(__file__), "bandit_stats%s.json" % ("_" + _ctx if _ctx else ""))
# $/MTok (input, output, cache write 5-min = 1.25x input, cache read); "default" = session model Opus 5.5
PRICES = {"opus": (4.00, 20.00, 5.00, 0.20), "sonnet": (2.00, 10.00, 2.50, 0.20)}
DECAY = 0.7      # weight of previous data each time a run is recorded
MIN_HOURS = 1.0  # decayed agent-time an arm needs before it can be exploited (an explore slot
                 # plateaus near 0.5/(1-DECAY) = 1.7 h, so this must stay below that)
CONFIGS = {"sonnet-low": {"model": "sonnet", "effort": "low"},
           "sonnet-medium": {"model": "sonnet", "effort": "medium"},
           "sonnet-high": {"model": "sonnet", "effort": "high"},
           "default-low": {"effort": "low"},
           "default-high": {"effort": "high"},
           "default-medium": {"effort": "medium"}}


def load():
    return json.load(open(STATS)) if os.path.exists(STATS) else {"runs": [], "configs": {}}


def ts(s):
    return datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))


def record(d):
    st = load()
    key = os.path.basename(d.rstrip("/"))  # run id only: no local paths in the committed stats
    if key in st["runs"]:
        sys.exit("already recorded: " + key)
    size = {"%08X" % f[0]: f[1] - f[0] for f in load_funcs()}
    # Non-stationary: remaining functions get harder over time, so discount older runs
    for c in st["configs"].values():
        for k in ("hours", "bytes", "claimed", "committed", "tokens", "dollars", "norm_dollars"):
            c[k] = c.get(k, 0) * DECAY
    run_rows = []  # (tag, dollars, bytes) for this run, for difficulty normalisation
    for line in open(os.path.join(d, "journal.jsonl")):
        e = json.loads(line)
        if e.get("type") != "result" or not e.get("agentId"):
            continue
        base = os.path.join(d, "agent-%s" % e["agentId"])
        label = json.load(open(base + ".meta.json")).get("description", "")
        m = re.match(r"stream-(\d+)(?:-(.+))?$", label)
        if not m:
            continue
        tag = m.group(2) or "default-default"
        if tag == "default-default":
            tag = "default-medium"  # unset effort = session effort, which is medium (verified in transcripts)
        v = e.get("result") or {}
        mine = v.get("functions", []) if isinstance(v, dict) else []
        L = [json.loads(l) for l in open(base + ".jsonl")]
        t = [ts(x["timestamp"]) for x in L if x.get("timestamp")]
        # one usage per API message (streamed entries repeat the same message id; keep the last)
        um = {}
        for x in L:
            m = x.get("message")
            if isinstance(m, dict) and m.get("usage"):
                um[m.get("id") or id(x)] = m["usage"]
        u = list(um.values())
        pr = PRICES["sonnet" if tag.startswith("sonnet") else "opus"]
        dollars = sum(((x.get("input_tokens") or 0) * pr[0] + (x.get("output_tokens") or 0) * pr[1]
                       + (x.get("cache_creation_input_tokens") or 0) * pr[2]
                       + (x.get("cache_read_input_tokens") or 0) * pr[3]) / 1e6 for x in u)
        c = st["configs"].setdefault(tag, {"hours": 0, "bytes": 0, "claimed": 0, "committed": 0, "tokens": 0})
        c["dollars"] = c.get("dollars", 0) + dollars
        run_rows.append((tag, dollars, sum(size.get(f["addr"], 0) for f in mine if f.get("committed"))))
        c["hours"] += (max(t) - min(t)).total_seconds() / 3600 if t else 0
        c["claimed"] += len(mine)
        c["committed"] += sum(1 for f in mine if f.get("committed"))
        c["bytes"] += sum(size.get(f["addr"], 0) for f in mine if f.get("committed"))
        c["tokens"] += sum((x.get("input_tokens") or 0) + (x.get("output_tokens") or 0)
                           + (x.get("cache_creation_input_tokens") or 0) for x in u)
    # Function size varies along the address-ordered queue (runs over tiny functions yield few
    # bytes for everyone), so weight each arm's cost by its run's overall bytes/$: score becomes
    # bytes / sum(dollars * run_rate) = performance relative to the run average (1.0 = average).
    tb, td = sum(r[2] for r in run_rows), sum(r[1] for r in run_rows)
    rate = tb / td if td else 0
    for tag, dl, _ in run_rows:
        c = st["configs"][tag]
        c["norm_dollars"] = c.get("norm_dollars", 0) + dl * rate
    st["runs"].append(key)
    json.dump(st, open(STATS, "w"), indent=1)


def per_hour(c):
    return c["bytes"] / c["hours"] if c["hours"] else 0


def score(c):
    """Selection score: bytes per cost unit relative to the run average (1.0 = average)."""
    return c["bytes"] / c["norm_dollars"] if c.get("norm_dollars") else 0


def raw_score(c):
    return c["bytes"] / c["dollars"] if c.get("dollars") else 0


def nxt(agents=8, explore=2, draws=None):
    """Thompson sampling: each slot goes to the arm with the highest sampled score. An arm's
    score is drawn around its mean with spread ~ 1/sqrt(agent-hours) (untested arms: wide prior
    around the best mean). Until a challenger has MIN_HOURS, the most-sampled arm keeps
    `explore` slots as a floor so one lucky run can't take everything."""
    import random
    st = load()["configs"]
    means = {k: score(st[k]) for k in CONFIGS if k in st and st[k]["hours"] > 0}
    top = max(means.values()) if means else 1.0
    def draw(k):
        h = st.get(k, {}).get("hours", 0)
        m = means.get(k, top)
        sd = m * (1.5 if h <= 0 else min(1.5, 0.5 / h ** 0.5))
        return max(0.0, random.gauss(m, sd))
    picks = [max(CONFIGS, key=draw) for _ in range(agents)]
    incumbent = max(st, key=lambda k: st[k]["hours"]) if st else "default-medium"
    challengers_ready = any(st.get(k, {}).get("hours", 0) >= MIN_HOURS for k in set(picks) if k != incumbent)
    if not challengers_ready:
        need = explore - picks.count(incumbent)
        for n in range(len(picks)):
            if need <= 0:
                break
            if picks[n] != incumbent:
                picks[n] = incumbent; need -= 1
    # Decay keeps rarely-picked arms "uncertain" forever, so cap clearly-worse arms (mean < 60% of
    # the best) to one slot in total per run; their extra slots go to the best-mean arm.
    # Replacement slots go to the best arm with enough data, so a lucky short run can't amplify itself.
    proven = {k: m for k, m in means.items() if st[k]["hours"] >= MIN_HOURS}
    best_mean = max(proven, key=proven.get) if proven else incumbent
    weak = {k for k, m in means.items() if m < 0.6 * top}
    untested = {k for k in CONFIGS if k not in means}
    provisional = {k for k in means if k not in proven}  # some data, < MIN_HOURS: up to `explore` slots each
    used = {}
    for n, k in enumerate(picks):
        cap = 1 if k in weak or k in untested else (explore if k in provisional else agents)
        used[k] = used.get(k, 0) + 1
        if used[k] > cap:
            picks[n] = best_mean
    picks.sort()
    if draws is not None:
        return picks
    print(json.dumps([CONFIGS[k] for k in picks]))


def report():
    print("%-16s %6s %7s %9s %8s %8s %9s %8s" % ("setting", "hours", "commit", "bytes", "dollars", "relative", "bytes/$", "bytes/h"))
    for k, c in sorted(load()["configs"].items(), key=lambda kv: -score(kv[1])):
        print("%-16s %6.2f %7.1f %9.0f %8.2f %8.2f %9.0f %8.0f" % (k, c["hours"], c["committed"], c["bytes"],
                                                        c.get("dollars", 0), score(c), raw_score(c), per_hour(c)))


def markdown():
    st = load()
    rows = sorted(st["configs"].items(), key=lambda kv: -score(kv[1]))
    out = ["| Setting | Decayed agent-hours | Committed / claimed | Relative score (1.0 = run avg) | Bytes per cost unit | Bytes / agent-hour | Cost units / agent-hour |",
           "|---|---|---|---|---|---|---|"]
    for k, c in rows:
        out.append("| %s | %.2f | %.1f / %.1f | %.2f | %.0f | %.0f | %.2f |" % (
            k, c["hours"], c["committed"], c["claimed"], score(c), raw_score(c), per_hour(c),
            c.get("dollars", 0) / c["hours"] if c["hours"] else 0))
    return "\n".join(out) + ("\n\n_Cost unit = API list-price dollars, used as a proxy for subscription quota "
        "(heavier models consume quota faster); not an actual bill. %d runs recorded; older runs decayed x%.1f "
        "per run; updated by post_run.py._\n" % (len(st["runs"]), DECAY))


def update_doc(path="docs/STRATEGY.md"):
    s = open(path).read()
    a, b = "<!-- bandit:start -->", "<!-- bandit:end -->"
    if a in s and b in s:
        s = s[:s.index(a) + len(a)] + "\n" + markdown() + s[s.index(b):]
        open(path, "w").write(s)


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "report"
    if cmd == "record":
        record(sys.argv[2])
    elif cmd == "rebuild":  # re-record all runs in order: bandit.py rebuild WORKFLOWS_DIR
        runs = load()["runs"]
        os.remove(STATS)
        for r in runs:
            record(os.path.join(sys.argv[2], os.path.basename(r)))
    elif cmd == "md":
        update_doc()
    elif cmd == "next":
        nxt(*map(int, sys.argv[2:4]))
    else:
        report()
