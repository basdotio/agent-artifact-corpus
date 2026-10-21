# Probe recipes

Shell recipes that were run, as written here, during the skill's first complete run (MoonAliza, Linux container, 2026-10-03). Adapt names and runners to the project; keep the shape. `$S` is one absolute scratch directory outside the checkout that holds every throwaway clone, cache and log.

## Session layout

```sh
S=/path/to/scratch; mkdir -p "$S/tmp" "$S/logs"
export TMPDIR="$S/tmp"                      # tests that use the OS temp dir stay inside the scratch area
git clone -q /path/to/checkout "$S/clone-probe"     # probes
git clone -q /path/to/checkout "$S/clone-node22"    # a second toolchain
git clone -q -c core.autocrlf=true /path/to/checkout "$S/clone-autocrlf"
```

A clone can share the checkout's installed dependencies when the toolchain is the same: `ln -s /path/to/checkout/node_modules "$S/clone-autocrlf/node_modules"`. A clone for another toolchain gets its own install.

## The declared toolchain, installed session-locally

When the declared version is not on the machine and a version manager is available, install into a directory under `$S` and put it first on `PATH` for the run only. Nothing global changes.

```sh
export NVM_DIR="$S/nvm"; mkdir -p "$NVM_DIR"; . /path/to/nvm.sh
nvm install 24.21.0                              # the version in .node-version
export PATH="$NVM_DIR/versions/node/v24.21.0/bin:$PATH"
```

Record in the report that the environment lacked the version and that it was installed for the run.

## A gate script

One script runs the gate and leaves a per-step log and exit code, so the same command serves baseline, probes and the final check.

```sh
step() { name=$1; shift; printf '### %s: %s\n' "$name" "$*" | tee -a "$L/gate.log"
  "$@" > "$L/$name.log" 2>&1; rc=$?; printf '### %s rc=%s\n' "$name" "$rc" | tee -a "$L/gate.log"; return $rc; }
step install   npm ci
step prepare   node scripts/prepare-research-kit.mjs
step typecheck npm run typecheck
step lint      npm run lint
step build     npm run build
step test1     npx vitest run --reporter=json --outputFile="$L/tests1.json" --reporter=default
```

## Baseline and comparison by failure set

Save the set of failing test identifiers per run and compare sets, never counts.

```python
# summarize.py <json> [out.txt]: prints totals, writes sorted "file::full test name" per failure
import json, sys
f = json.load(open(sys.argv[1])); names = []
for t in f["testResults"]:
    fn = t["name"].split("/tests/")[-1]
    names += [fn + "::" + a["fullName"] for a in t["assertionResults"] if a["status"] == "failed"]
print(f["numTotalTests"], f["numPassedTests"], f["numFailedTests"])
if len(sys.argv) > 2: open(sys.argv[2], "w").write("\n".join(sorted(names)) + "\n")
```

```sh
comm -13 baseline-fail.txt probe-fail.txt    # new failures under the probe
comm -23 baseline-fail.txt probe-fail.txt    # baseline failures the probe made pass (also a signal)
```

Run three baseline runs and `diff` the three files; identical files mean no intermittent test in the baseline.

## Order and flakiness

```sh
npx vitest run --sequence.shuffle --sequence.seed=1
npx vitest run --sequence.shuffle --sequence.seed=20261003
for i in $(seq 1 10); do npx vitest run tests/a.test.ts tests/b.test.ts --reporter=json --outputFile="$L/t$i.json"; done
cat "$L"/fail*.txt | sort | uniq -c | sort -rn      # how many of the runs each failure appeared in
```

Run one suite at a time on the machine. If two must overlap, any new failure is reproduced alone before it counts.

## Timezone, locale, bare environment, limits

```sh
TZ=Pacific/Kiritimati LANG=C LC_ALL=C npx vitest run
TZ=America/St_Johns LANG=de_DE.UTF-8 LC_ALL=de_DE.UTF-8 npx vitest run
env -i PATH="$PATH" HOME=/nonexistent npx vitest run
( ulimit -n 256; NODE_OPTIONS=--max-old-space-size=512 npx vitest run )
```

## No network, loopback up

`unshare -rn` gives a network namespace with no external route, but its loopback interface starts **down**. Tests that use a local fake server then fail for a reason the project does not have. Bring `lo` up first (no `ip` binary needed):

```python
# lo-up.py
import socket, fcntl, struct
IFF_UP, SIOCGIFFLAGS, SIOCSIFFLAGS = 1, 0x8913, 0x8914
s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM); ifr = struct.pack('16sh', b'lo', 0)
flags = struct.unpack('16sh', fcntl.ioctl(s, SIOCGIFFLAGS, ifr))[1]
fcntl.ioctl(s, SIOCSIFFLAGS, struct.pack('16sh', b'lo', flags | IFF_UP))
```

```sh
unshare -rn bash -c "python3 $S/lo-up.py && \
  (curl -sS --max-time 5 https://registry.npmjs.org/ >/dev/null && echo 'network reachable: probe invalid' || echo 'offline') && \
  node scripts/prepare-research-kit.mjs && npx vitest run --reporter=json --outputFile=$OUT"
```

The `curl` line is the control that the probe is actually offline. `npm ci --offline --cache "$S/emptycache"` fails for every project (`EAI_AGAIN`) and is not informative; what matters is whether provisioning and tests work once dependencies are installed.

## Another toolchain

```sh
PATH=/opt/node22/bin:$PATH npm ci && ... full gate ...      # a version outside package.json#engines
```

Success here is a finding (the constraint is not enforced). The fix, `engine-strict=true` in a repository `.npmrc`, is verified both ways: the unsupported version must now fail at install with `EBADENGINE`, and the declared version must still install, twice.

## Generated files and line endings

```sh
node scripts/generate-research-fixtures.mjs --inventory-only; node --import tsx scripts/capture-collector-golden.ts
git status --porcelain && git diff --exit-code                 # in the throwaway clone
git -C "$S/clone-autocrlf" ls-files --eol | awk '{print $2}' | sort | uniq -c   # how many files became CRLF
```

Then run, in the autocrlf clone, every check that hashes or byte-compares committed files.

## Fix application in the pinned-branch setup

Verify the fix in a clone, then copy the file into the checkout and read the diff before committing:

```sh
cp "$S/clone-probe/scripts/x.mjs" /path/to/checkout/scripts/x.mjs
git -C /path/to/checkout diff --stat && git -C /path/to/checkout add scripts/x.mjs && git -C /path/to/checkout commit -F msg.txt
```

Never run `git checkout -- <file>`, `stash`, `reset` or `clean` with the checkout as the working directory during the run. In the first run, one such command aimed at a clone ran in the checkout and reverted an uncommitted fix; it was restored from the clone's verified copy, which is why the copy-then-diff step above exists.

## What the first run taught

Each rule added to SKILL.md on 2026-10-03, and the observation behind it.

| Rule | Observation (MoonAliza, 2026-10-03) |
|------|-------------------------------------|
| Principle 2 and the control step: a probe can manufacture a failure | `unshare -rn npx vitest run` produced 3 new failures in `research-collector-protocol`; with loopback up and the network still unreachable, all 706 tests matched the baseline. The 3 were the probe's. |
| Baseline is a set of identifiers, compared with `comm` | The baseline had 74 documented failures; "still 74" would not have shown a swap. Every comparison was done on names. |
| One suite at a time | Vitest runs were timed at 91 to 99 s alone; the flakiness loop and offline run were kept in separate clones and never overlapped with a comparison run. |
| Section 0 item 4: state-changing git only in throwaway paths; copy-then-diff when applying fixes | A `git checkout -- scripts/prepare-research-kit.mjs` meant for a clone ran in the checkout and discarded an uncommitted fix. |
| Section 0 item 7: install the declared toolchain session-locally and say so | The container had Node 22.22.0; `.node-version` says 24.21.0. Node 24.21.0 was installed under the scratch nvm directory for the run. |
| Section 1: record the environment and what CI steps it cannot run | 74 tests need the Windows native helper; running as root made permission probes void; e2e needs Electron on Windows. |
| Probe 2: read installer warnings | `npm ci` under npm 11 warned that `esbuild` and `electron-winstaller` install scripts were "not yet covered by allowScripts"; under npm 10 the policy does not exist and `EBADENGINE` is only a warning. |
| Probe 3: run the maintainer-only regeneration scripts in the throwaway clone | `generate-research-fixtures.mjs --inventory-only` and `capture-collector-golden.ts` are documented as never-in-CI; both reproduced byte-identical output, which nothing else was checking. |
| Probe 4: success under an unsupported version is a finding | The whole gate passed identically under Node 22. Fixed with `engine-strict=true`. |
| Probe 9: offline install proves nothing; probe provisioning and tests offline instead | `npm ci --offline` failed with `EAI_AGAIN` as expected; the informative results were the kit-preparation script's raw stack without a pin and the clean pass with one. |
| Probe 10: half-made state directories; root voids permission probes | An empty `.build/research-kit-pin` made every later preparation fail with "not a git repository". Read-only probes were recorded as not probed (root). |
| Probe 12: audit production and development separately | `npm audit`: 8 high; `npm audit --omit=dev`: 0. The decision is about packaging tooling, not the shipped app. |
| Severity: an all-Low result is reported as all-Low | All four findings were Low; the report says so. |
| Report: probe defects, environment, probes-run table, repo-relative repro commands | The first offline result would otherwise have been reported as three findings; scratch paths in commands were useless to the reader. |
| Principle 7 and the *External facts* section: a tool's behaviour is fetched through Research-Kit, not recalled | Two facts the probes could not settle (what npm 11 does with an uncovered install script; whether esbuild's skipped postinstall matters on Windows) had shaped a recommendation. Closed from the owner's pages in a nested kit project (`docs/research/2026-10-03-break-test-external-facts/`, gate PASS, keyless); see `references/research-kit.md`. |
| Research-Kit rule 2: read doctor's whole verdict | `doctor` at the repository root raised a critical the research did not need: a private-key block in `tests/fixtures/github-tls/leaf.key`. |
| Fix step 6: follow the repository's commit convention | AGENTS.md prescribes a five-part body ("What changed / Why / ... / What you got wrong and fixed"); the fix commits use it. |
