---
name: save-to-drop-box
description: Save a finished GO-CAM model to the public geneontology/go-cam-drop-box repository as a pull request carrying the model in both formats (gocam-py YAML + minerva TTL) under its noctua-dev id. Use when the user asks to "save", "submit", "publish", or "keep" a model so it can be reviewed and promoted into production GO-CAM. The model must exist on noctua-dev and be stored there; its state is the curator's call.
license: BSD-3-Clause
metadata:
  version: "0.1.0"
  source: https://github.com/geneontology/go-skills/tree/main/skills/save-to-drop-box
  maintainer: geneontology
---

# Save a model to the GO-CAM drop box

This skill submits one finished GO-CAM model to
**https://github.com/geneontology/go-cam-drop-box** as a pull request. CI
validates every submission; a maintainer merges; merged models are copied into
production `noctua-models` at the next Noctua maintenance outage. This is how a
curator "saves" work from this environment so it survives and reaches production.

The drop box's own `CLAUDE.md` is the authoritative contract (fetch
`https://raw.githubusercontent.com/geneontology/go-cam-drop-box/main/CLAUDE.md`
if unsure). The essentials are below.

## The contract (since 2026-09-24): one model, two files, one id

- **The model lives on noctua-dev.** Its id is the one minerva minted there,
  e.g. `gomodel:6ab067da00000569`. That id is permanent: it is the id in both
  files, the filename of both files, and the production id after promotion.
  **Do not mint or rewrite ids** (the old `gcdb-<UUID>` scheme is retired).
- **The model is stored on dev** (step 2 below). **Its state is the curator's
  call** and travels as set on dev: `development` is fine, and there are good
  reasons to keep a model there until it is promoted. Only `delete` is refused.
  Change the state only if the curator asks.
- **Two files, exported from that same stored state:**
  `models/<id>.yaml` (gocam-py YAML) and `models/<id>.ttl` (minerva's own
  Turtle). The YAML is the review surface; the TTL is what enters production.
  CI checks that they agree exactly, so **never hand-edit either file** —
  change the model on dev and re-export both.
- **Complete.** CI enforces: a connected causal graph (≥1 causal edge, no
  orphan activity), evidence on assertions, real and current ontology terms,
  the same state in both files, and the noctua-models QC battery over the TTL
  (no disconnected individuals such as orphaned evidence, no multiply reified
  edges).

A model that exists only as notes or a YAML draft here cannot be submitted:
build it on noctua-dev first (the `noctua` skill), then come back.

## Step 0 — confirm the model is on dev

```sh
set -a; [ -f ~/.env ] && . ~/.env; set +a      # BARISTA_TOKEN
barista get-model --model <id>                  # must succeed; note the title
```

## Step 1 — finish it on dev: comments (and state, only if asked)

Anything that should travel with the model goes on the model, as annotations:

```sh
barista update-metadata --model <id> --add --comment "Curated with GO AI HUB. <one line on what the model represents>"
# state stays as the curator set it; change it only on their say-so, e.g.:
# barista update-metadata --model <id> --state production
```

Fix anything else on dev too (the `noctua` skill). If you removed evidence from
an edge, delete the evidence individual as well; orphaned evidence fails CI.

## Step 2 — store the model on dev

An unstored model exists only in minerva's memory and is lost at the next dev
restart. Store it, then verify the store took:

```sh
curl -s -X POST "http://barista-dev.berkeleybop.org/api/minerva_public_dev/m3BatchPrivileged" \
  --data-urlencode "token=$BARISTA_TOKEN" --data-urlencode "intention=action" \
  --data-urlencode "provided-by=http://geneontology.org" \
  --data-urlencode 'requests=[{"entity":"model","operation":"store","arguments":{"model-id":"gomodel:<id>"}}]' \
  | python3 -c 'import json,sys; d=json.load(sys.stdin); print(d["message-type"], d.get("message"))'
# expect: success ...
barista get-model --model <id> | grep -o '"modified-p": *[a-z]*'      # expect: "modified-p": false
```

## Step 3 — export both files from that state

```sh
mkdir -p ~/drop-box-out && cd ~/drop-box-out
barista export-model --model <id> -f gocam-yaml -o <id>.yaml
curl -s -X POST "http://barista-dev.berkeleybop.org/api/minerva_public_dev/m3Batch" \
  --data-urlencode 'requests=[{"entity":"model","operation":"export","arguments":{"model-id":"gomodel:<id>"}}]' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["data"]["export-model"])' > <id>.ttl
head -c 300 <id>.ttl            # Turtle, ontology IRI http://model.geneontology.org/<id>
grep -m1 '^id:' <id>.yaml       # id: gomodel:<id>
grep -m1 '^status:' <id>.yaml   # the curator's state, e.g. development
```

Do both exports back to back, after the store, with no edits in between. If you
edit the model afterwards, repeat steps 2 and 3.

## Step 4 — authenticate gh (once per user)

The PR is opened as the curator, so `gh` must be logged in as them.

```sh
gh auth status
```

If not logged in, start the **device flow** and relay it to the user (they are
already in a browser — JupyterLab — so this is just a new tab):

```sh
gh auth login --hostname github.com --git-protocol https --web
```

Tell the curator: *"Open https://github.com/login/device in a new browser tab,
enter this code: `…`, and authorize."* Wait, then re-check `gh auth status`.
The login persists in `~/.config/gh`. Only people with the **`go-ai-hub`
permission** in GO's `users.yaml` (geneontology/go-site) can submit; the drop
box's CI checks the PR author. On the GO AI Hub, signing in to the hub already
logged `gh` in, so `gh auth status` normally succeeds without this step.

## Step 5 — branch, add both files, open the PR

Work in a **clone made for this submission** under `~/drop-box-out/<id>/repo`,
never in a clone left from an earlier save of another model (stale branches
and leftover files there have blocked saves). If that directory already exists
from an earlier attempt at this same model, reuse it only when it is on
`add-<id>`; otherwise remove it and clone again:

```sh
R=~/drop-box-out/<id>/repo
if [ -d "$R/.git" ] && [ "$(git -C "$R" branch --show-current)" = "add-<id>" ]; then
  echo "reusing $R"            # fixes: copy the re-exported files, commit, push
else
  rm -rf "$R"
fi
```

First find out whether the curator can push to the drop box itself:

```sh
gh api repos/geneontology/go-cam-drop-box --jq .permissions.push
```

**`true` (the usual case for hub members):** branch on the repository.

```sh
mkdir -p ~/drop-box-out/<id> && cd ~/drop-box-out/<id>
[ -d repo/.git ] || gh repo clone geneontology/go-cam-drop-box repo -- --depth 1 --no-single-branch
cd repo
git switch -c add-<id> 2>/dev/null || git switch add-<id>
cp ~/drop-box-out/<id>.yaml ~/drop-box-out/<id>.ttl models/
git add models/<id>.yaml models/<id>.ttl
git commit -m "Add <id> (<short title>)"
git push -u origin add-<id>
gh pr create --repo geneontology/go-cam-drop-box \
  --title "Add model <id> (<short title>)" \
  --body "What the model represents, in a few lines. Built and stored on noctua-dev as gomodel:<id>; YAML and TTL exported from the same stored state."
```

**`false`:** fork (once; a second run reuses the existing fork), bring the
fork's `main` up to date, and do the same steps with the fork as `origin`.
`gh repo fork` rejects `--remote` when a repository is named, so clone in a
second step.

```sh
LOGIN=$(gh api user --jq .login)
gh repo fork geneontology/go-cam-drop-box --clone=false --default-branch-only
for i in 1 2 3 4 5 6; do                      # a new fork takes a few seconds to exist
  gh api "repos/$LOGIN/go-cam-drop-box" --jq .full_name >/dev/null 2>&1 && break; sleep 10
done
gh repo sync "$LOGIN/go-cam-drop-box" --source geneontology/go-cam-drop-box --branch main \
  || echo "fork sync refused; branching from the fork's own main"
mkdir -p ~/drop-box-out/<id> && cd ~/drop-box-out/<id>
[ -d repo/.git ] || gh repo clone "$LOGIN/go-cam-drop-box" repo -- --depth 1 --no-single-branch
cd repo
git switch -c add-<id> 2>/dev/null || git switch add-<id>   # from the fork's main
# ... cp / add / commit as above ...
git push -u origin add-<id>
gh pr create --repo geneontology/go-cam-drop-box --head "$LOGIN:add-<id>" \
  --title "Add model <id> (<short title>)" --body "..."
```

If `gh repo sync` is refused with *"Upstream commits contain workflow
changes, which require the `workflow` scope"*, the token cannot carry a CI
change into the fork. Do **not** start a device-code login; the branch is
still fine: it starts from the fork's `main`, so the push carries only the
curator's commit, and the PR against `geneontology/go-cam-drop-box:main` is
reviewed and tested on the merge of the two. To bring the fork up to date
anyway, the curator can press **Sync fork → Update branch** on
`https://github.com/$LOGIN/go-cam-drop-box`.

**Not final yet? Open it as a draft.** If the curator says more curation is
coming (a review meeting, additions planned, "just parking this"), add
`--draft` to `gh pr create`. A draft is a real, safe save: CI runs on it and
the files are in the drop box, but it is not a request for merge and nobody
will merge it. When the curator says it is final:

```sh
gh pr ready --repo geneontology/go-cam-drop-box <pr-number>
```

Do **not** use the model's state to signal "not ready". State (`development`,
`production`, ...) is the model's state in Noctua and travels as set; readiness
for merge is the PR's draft flag.

## Step 6 — watch CI and fix if needed

The `validate` check must pass before merge:

```sh
gh pr checks --repo geneontology/go-cam-drop-box <pr-number>
gh run view --repo geneontology/go-cam-drop-box <run-id> --log-failed     # on failure
```

Failures map to the seven gates. **Every fix is made on dev, then both files
are re-exported (steps 2–3) and pushed to the same branch.** Common ones:

| CI says | Do on dev |
|---|---|
| id/filename mismatch | you renamed something; the id is the dev id, both filenames are `<id>.*` |
| `status 'delete' not in allowed_statuses` | a deleted model cannot be submitted |
| TTL state != YAML status | the files came from different states; store, then re-export both back to back |
| model comments differ | comments were added to the YAML by hand; put them on the model with `update-metadata --add --comment`, re-export both |
| YAML ↔ TTL agreement failures | the files came from different states; store, then re-export both back to back |
| `check-disconnected-individuals.rq` rows | orphaned evidence (or other) individuals; delete them on dev, store, re-export |
| `check-multiply-reified-edges.rq` rows | the same edge has evidence attached twice as separate axioms; remove the duplicate on dev |
| LinkML / ontology-term failures | a term is wrong or obsolete; fix on dev |

## What "submitted", "merged" and "promoted" mean

Tell the curator this when you hand over the PR:

- **Draft PR open** — the work is **safe** in the drop box (this is the durable
  save) but it is parked: not queued for review, and it will not be merged
  until the curator marks it ready.
- **PR ready for review** — the model is complete and queued for GO Central
  review. An open PR is a normal resting state.
- **Merged** — accepted; it will be copied into production `noctua-models`,
  under the same id, at the next Noctua maintenance outage (second and fourth
  Thursdays). `PROMOTIONS.md` in the drop box records each batch.
- **Promoted** — live in production Noctua under `gomodel:<id>`.

Once merged, the drop box is the source of truth for that id until promotion,
and production is after. Edits made on noctua-dev afterwards are **not**
carried anywhere by themselves: if the curator changes a submitted or merged
model, say so and offer to carry the change back (update the open PR, or open a
new PR), or the edit is silently overwritten by the next dev refresh.

## Don't

- Don't submit a model that is not on noctua-dev, or not stored there.
- Don't hand-edit the YAML or the TTL, and don't write a YAML from scratch.
- Don't mint, reuse or rewrite `gomodel:` ids; don't fabricate ontology terms.
- Don't treat noctua-dev itself as a save — unstored models vanish, and even
  stored dev models are a proving ground, not production.
- Don't chase a merge or tell the curator something is wrong because their PR
  is still open; review is manual.
- Don't set a model to `development` (or anything else) as a way of saying
  "not ready for merge"; open or convert the PR to a draft instead.
