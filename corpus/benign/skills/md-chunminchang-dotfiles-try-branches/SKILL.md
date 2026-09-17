---
name: try-branches
description: Push a commit to try on multiple Firefox branches (beta, release, ESR). Use when testing if a patch builds/works on older Firefox versions for uplift.
argument-hint: <commit> <branch1> [branch2] ...
context: fork
---

# Try Branches

Push a commit to the try server on multiple Firefox branches using the Lando API directly.
This is useful for testing uplift compatibility on beta, release, and ESR branches.

## Arguments

$ARGUMENTS should be: `<commit-hash> <branch1> [branch2] ...`

Where branches can be: `beta`, `release`, `esr115`, `esr128`, `esr140`, or any branch name
available under `upstream/` remote (which should point to `https://github.com/mozilla-firefox/firefox.git`).

Example: `/try-branches HEAD beta release esr128 esr115`

## Process

1. Parse the commit hash and target branches from arguments
2. Ensure `upstream` remote exists pointing to `https://github.com/mozilla-firefox/firefox.git`
3. Fetch the target branches from upstream if not already fetched
4. For each target branch:
   a. Create a temporary local branch `try-<branch>` from `upstream/<branch>`
   b. Cherry-pick the commit onto it
   c. If there are conflicts, resolve them and inform the user about the resolution
   d. Generate a `git format-patch` of the cherry-picked commit
   e. Push to try via the Lando API
5. Generate patch files in the repo root for any branches that required conflict resolution
6. Switch back to the original branch
7. Print a summary table with Treeherder links

## Cherry-pick conflict handling

If a cherry-pick has conflicts:
- Try to resolve them automatically if possible
- If auto-resolution fails, abort, inform the user, and skip that branch
- For branches with resolved conflicts, generate a `.patch` file at the repo root (e.g., `esr115.patch`)

## Lando API push method

Use a Python script to call the Lando API directly. This avoids issues with `mach try` on older
branches that lack Lando support or have incompatible `git-cinnabar` requirements.

The script should:

1. Read the auth token from `~/.mozbuild/lando_auth0_user_token.json`
2. Generate the patch with `git format-patch -1 <commit> --stdout`
3. Generate the correct `try_task_config.json` as a second patch:
   ```json
   {
       "parameters": {
           "filters": ["try_auto"],
           "optimize_strategies": "gecko_taskgraph.optimize:tryselect.bugbug_reduced_manifests_config_selection_medium",
           "optimize_target_tasks": true,
           "test_manifest_loader": "bugbug",
           "try_mode": "try_auto",
           "try_task_config": {}
       },
       "version": 2
   }
   ```
4. POST to `https://api.lando.services.mozilla.com/try/patches` with:
   ```json
   {
       "base_commit": "<upstream branch tip git SHA>",
       "base_commit_vcs": "git",
       "patch_format": "git-format-patch",
       "patches": ["<base64 commit patch>", "<base64 try_task_config patch>"]
   }
   ```
5. The try_task_config patch should be a valid `git format-patch` style patch that creates `try_task_config.json`

## Auth token

If the auth token at `~/.mozbuild/lando_auth0_user_token.json` doesn't exist or is expired,
tell the user to run `./mach try auto` on any branch first to authenticate, which will cache
the token.

## Important notes

- Always switch back to the user's original branch when done
- Clean up any temporary state (stashed changes, staged files)
- The `try-<branch>` local branches are left around for reference but can be deleted
- If a branch already has a `try-<branch>` local branch, delete and recreate it
