# Curator Branching Workflow

This guide explains how to create dataset-specific branches before processing a new dataset.

## Overview

Each new dataset requires its own branch in all required repositories. Branch names typically match the BioProject accession (e.g., `PRJNA123456`).

## Prerequisites

### Set Up veupathdb-repos Directory

The skills expect a `veupathdb-repos/` directory in your curation workspace directory containing the required VEuPathDB configuration repositories. The specific repositories needed depend on which skill you're using - check the skill's prerequisites section.

**Recommended Setup**: Symlink to your existing GitHub Desktop clones:

```bash
ln -s ~/Documents/GitHub veupathdb-repos
```

This way, any changes made by the skills appear directly in your actual repository clones, and you can manage branches and commits using your preferred git tools.

**Alternative**: Clone repositories into a new directory:

```bash
mkdir veupathdb-repos
cd veupathdb-repos
git clone git@github.com:VEuPathDB/ApiCommonDatasets.git
git clone git@github.com:VEuPathDB/ApiCommonPresenters.git
git clone git@github.com:VEuPathDB/EbrcModelCommon.git
cd ..
```

**Note**: The `veupathdb-repos/` directory is gitignored and won't be committed to the dataset-curator repository.

## Creating Dataset Branches

Before starting a dataset workflow, create a dataset-specific branch in each required repository.

**Branch Naming Convention**: Use the BioProject accession number (e.g., `PRJNA123456`)

### Using GitHub Desktop

1. Open each required repository in GitHub Desktop
2. Create a new branch using Branch → New Branch
3. Name the branch with the BioProject accession
4. Repeat for each required repository

### Using Command Line

Create branches in all required repositories:

```bash
for repo in ApiCommonDatasets ApiCommonPresenters EbrcModelCommon; do
  git -C veupathdb-repos/$repo checkout -b PRJNA123456
done
```

Or navigate to each repository individually:

```bash
cd veupathdb-repos/ApiCommonDatasets
git checkout -b PRJNA123456
cd ../ApiCommonPresenters
git checkout -b PRJNA123456
cd ../EbrcModelCommon
git checkout -b PRJNA123456
cd ../..
```

## Managing Parallel Release Branches

When working on multiple releases in parallel, be aware of potential conflicts with shared data (e.g., contacts, ontologies).

### Scenario: Duplicate Contacts Across Releases

Consider this example:

1. Start work on release 72, making a `release-72` branch from `master`
2. Working in `release-72` branch, you add a study that has a new contact A
3. Start work on release 73, making a `release-73` branch from `master` (before 72 has been merged)
4. Process a dataset for release 73, using `release-73` branch - the study also has contact A (by coincidence)

The AI (and a human curator) would likely make slightly different entries for the same contact - call them A and A'. This can cause issues:

**Different Contact IDs**: You'll end up with duplicate contacts A and A' in `master` after merging both release branches.

**Same ID, Different Fields**: You may be able to merge/reconcile the two versions during the merge, but this requires manual intervention.

### Recommended Approach

To avoid conflicts when processing multiple releases in parallel:

**Merge Earlier Releases Into Later Ones**: Before working on each new dataset in a later release branch, merge the latest changes from earlier release branches:

```bash
# Before processing a new dataset in release-73
git -C veupathdb-repos/EbrcModelCommon checkout release-73
git -C veupathdb-repos/EbrcModelCommon pull
git -C veupathdb-repos/EbrcModelCommon merge origin/release-72
```

Alternatively, in **GitHub Desktop**: switch to the `release-73` branch, then choose Branch → Merge into Current Branch, and select `origin/release-72`.

This ensures that any contacts added in earlier releases are available in later ones, preventing duplicates. It should not be required for datasets as they should be atomic and independent, hopefully?

**If you encounter merge conflicts**, stop and do not attempt to resolve them manually — seek help from a more experienced git user before proceeding.

## Verifying Branch Setup

Before starting the workflow, verify all repositories are on the correct branch.

**GitHub Desktop**: Check the "Current Branch" dropdown in each repository

**Command Line**: Check branch status across repositories:

```bash
for repo in ApiCommonDatasets ApiCommonPresenters EbrcModelCommon; do
  if [ -d "veupathdb-repos/$repo" ]; then
    echo "$repo: $(git -C veupathdb-repos/$repo branch --show-current)"
  fi
done
```

## Committing and Creating Pull Requests

After the skill completes its work:

1. **Review changes**: Use `git diff` or GitHub Desktop to review modifications
2. **Commit changes**: Create commits in each modified repository
3. **Push branches**: Push your branches to GitHub
4. **Create pull requests**: Open PRs for each repository following your team's review process

The curator handles all git operations - the skills only create and modify files.

## Troubleshooting

### Repository Not Found

If the skill reports a repository is missing:

1. Check that `veupathdb-repos/` exists and contains (or links to) your repositories
2. If using a symlink, verify it points to the correct location: `ls -la veupathdb-repos`
3. If repositories are genuinely missing, clone them into your GitHub directory

### Wrong Base Branch

If you need to create your dataset branch from a specific base branch (not `main`):

1. Checkout the base branch first
2. Pull latest changes
3. Create your dataset branch from there

**GitHub Desktop**: Use Branch → New Branch and select the base branch in the "From" dropdown

**Command Line**:
```bash
git -C veupathdb-repos/ApiCommonDatasets checkout base-branch-name
git -C veupathdb-repos/ApiCommonDatasets pull
git -C veupathdb-repos/ApiCommonDatasets checkout -b PRJNA123456
```
