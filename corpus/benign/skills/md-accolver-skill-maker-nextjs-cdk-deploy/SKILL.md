---
name: nextjs-cdk-deploy
description: Deploy Next.js applications to AWS using CDK with a staging-then-production pipeline. Use when deploying Next.js apps to AWS, setting up CDK stacks for Next.js, configuring staging and production environments, implementing deployment approval gates, rolling back failed deployments, or managing environment-specific configuration for AWS-hosted Next.js applications. Also use when the user mentions CDK deploy, Next.js hosting on AWS, CloudFront distribution setup, or Lambda@Edge for SSR.
compatibility: Requires Node.js 18+, AWS CDK CLI v2, AWS CLI configured with credentials, Bun runtime for scripts
metadata:
  author: skill-maker
  version: "1.0"
---

# Next.js CDK Deploy

Deploy Next.js applications to AWS using CDK with a staged rollout pipeline:
build, synth, deploy to staging, manually approve, then deploy to production —
with rollback procedures at every stage.

## Overview

This skill guides the full deployment lifecycle for Next.js on AWS via CDK. The
core architecture uses S3 + CloudFront for static assets and Lambda for SSR,
managed through CDK stacks with environment-specific configurations.

## When to use

- When deploying a Next.js application to AWS
- When setting up CDK infrastructure for a Next.js project
- When implementing a staging → production deployment pipeline
- When configuring environment-specific settings (API URLs, feature flags, etc.)
- When rolling back a failed deployment on AWS
- When adding a manual approval gate between staging and production

**Do NOT use when:**

- Deploying to Vercel, Netlify, or other managed platforms (no CDK needed)
- The project is not Next.js (use a generic CDK deployment skill instead)
- Deploying a purely static site with no SSR (simpler S3-only approach suffices)

## Workflow

### 1. Verify prerequisites

Before any deployment, confirm the environment is ready:

```bash
# Check all required tools are installed
bun run scripts/preflight-check.ts
```

The preflight script verifies: Node.js 18+, AWS CDK CLI, AWS CLI with valid
credentials, and that the Next.js project builds successfully. Fix any failures
before proceeding.

### 2. Configure environment

Each environment (staging, production) needs its own configuration. Create or
verify config files at `cdk/config/`:

```
cdk/config/
├── staging.env.ts      # Staging-specific values
├── production.env.ts   # Production-specific values
└── shared.ts           # Shared across all environments
```

**Example `staging.env.ts`:**

```typescript
export const config = {
  environment: "staging",
  domainName: "staging.example.com",
  certificateArn: "arn:aws:acm:us-east-1:123456789:certificate/abc-123",
  apiUrl: "https://api-staging.example.com",
  logLevel: "debug",
  enableSourceMaps: true,
  lambdaMemory: 512,
  cloudfrontPriceClass: "PriceClass_100",
};
```

**Key principle:** Never hardcode environment values in the CDK stack. Always
read from the environment config file. This prevents staging values from leaking
into production because the config is selected at synth time, not at runtime.

### 3. Build the Next.js application

```bash
bun run scripts/build-and-synth.ts --env staging
```

This script:

1. Runs `next build` with the correct `NODE_ENV` and environment variables
2. Runs `cdk synth` targeting the specified environment's stack
3. Validates the synthesized CloudFormation template
4. Outputs a summary of resources that will be created/updated/deleted

Review the diff output carefully. If unexpected resources appear (especially
deletions), stop and investigate before deploying.

### 4. Deploy to staging

```bash
bun run scripts/deploy.ts --env staging
```

This runs `cdk deploy` with:

- `--require-approval never` (staging is pre-approved)
- `--outputs-file cdk-outputs-staging.json` (captures stack outputs)
- Automatic CloudFront invalidation after deployment

After deployment, verify staging works:

- Check the staging URL loads correctly
- Test SSR routes return proper content
- Verify API connections work with staging backend
- Check CloudWatch logs for errors

### 5. Manual approval gate

**This step is critical.** Before deploying to production, the user must
explicitly approve. Present the following information:

1. Staging URL for manual verification
2. Summary of infrastructure changes (from `cdk diff`)
3. Any CloudWatch errors or warnings from staging
4. Rollback instructions if production deployment fails

**Do NOT proceed to production deployment without explicit user approval.** Ask:
"Staging deployment is complete. Please verify at [staging URL]. Ready to deploy
to production? (yes/no)"

### 6. Deploy to production

Only after explicit approval:

```bash
bun run scripts/deploy.ts --env production
```

This runs `cdk deploy` with:

- `--require-approval broadening` (alerts on IAM/security changes)
- `--outputs-file cdk-outputs-production.json`
- Automatic CloudFront invalidation

### 7. Post-deployment verification

After production deployment:

- Verify the production URL loads correctly
- Check CloudWatch for errors in the first 5 minutes
- Confirm SSR routes work
- Test critical user flows

If issues are found, proceed to rollback immediately.

## Rollback Procedures

### Quick rollback (CloudFront)

If the issue is with static assets or client-side code:

```bash
bun run scripts/rollback.ts --env production --strategy cloudfront
```

This points CloudFront back to the previous S3 deployment prefix. Fastest option
(~2-5 minutes for propagation).

### Full rollback (CDK)

If the issue is with infrastructure or Lambda code:

```bash
bun run scripts/rollback.ts --env production --strategy cdk
```

This runs `cdk deploy` using the previous known-good snapshot. Takes longer
(~5-10 minutes) but rolls back everything including Lambda functions and
infrastructure changes.

### Emergency rollback

If both strategies fail, use the AWS Console:

1. CloudFront → Distributions → Edit origin to point to previous S3 prefix
2. Lambda → Functions → Deploy previous version from $LATEST history
3. Document what happened for post-mortem

## Checklist

- [ ] Preflight check passes (Node.js, CDK CLI, AWS credentials)
- [ ] Environment config exists for target environment
- [ ] `next build` succeeds without errors
- [ ] `cdk synth` produces valid CloudFormation template
- [ ] `cdk diff` reviewed — no unexpected resource deletions
- [ ] Staging deployment succeeds
- [ ] Staging manually verified (URL loads, SSR works, APIs connect)
- [ ] User explicitly approves production deployment
- [ ] Production deployment succeeds
- [ ] Production verified (URL loads, SSR works, no CloudWatch errors)
- [ ] Rollback plan communicated to user

## Common mistakes

| Mistake                                              | Fix                                                          |
| ---------------------------------------------------- | ------------------------------------------------------------ |
| Deploying to production without staging verification | Always deploy staging first and get explicit approval        |
| Hardcoding environment values in CDK stack           | Use config files in `cdk/config/` selected at synth time     |
| Forgetting CloudFront invalidation after deploy      | The deploy script handles this automatically; verify it ran  |
| Not capturing stack outputs after deployment         | Always use `--outputs-file` flag to persist outputs          |
| Skipping `cdk diff` before deploy                    | Always review diff — unexpected deletions can cause outages  |
| Using `cdk destroy` instead of rollback              | Never destroy in production; use rollback strategies instead |

## Quick reference

| Operation             | Command                                                         |
| --------------------- | --------------------------------------------------------------- |
| Preflight check       | `bun run scripts/preflight-check.ts`                            |
| Build + synth         | `bun run scripts/build-and-synth.ts --env <env>`                |
| Deploy                | `bun run scripts/deploy.ts --env <env>`                         |
| Rollback (CloudFront) | `bun run scripts/rollback.ts --env <env> --strategy cloudfront` |
| Rollback (CDK)        | `bun run scripts/rollback.ts --env <env> --strategy cdk`        |
| View diff             | `cdk diff --app 'npx ts-node cdk/app.ts' -c env=<env>`          |
| View stack outputs    | `cat cdk-outputs-<env>.json`                                    |

## Key principles

1. **Staging before production, always.** Never skip staging. The approval gate
   exists because production outages cost real money and trust. Even "trivial"
   changes can break SSR or invalidate caches.

2. **Environment isolation through config.** Each environment gets its own
   config file, its own CDK stack, and its own AWS resources. Shared config goes
   in `shared.ts`. This prevents cross-environment contamination.

3. **Rollback readiness at every step.** Before deploying, know how to undo it.
   The deploy script captures the current state so rollback is always possible.
   Communicate rollback procedures to the user before they approve production.

4. **Diff before deploy.** Always run and review `cdk diff` before `cdk deploy`.
   Unexpected resource deletions or security changes must be investigated, not
   rubber-stamped.

5. **Outputs are artifacts.** Stack outputs, deployment logs, and CloudFormation
   templates are saved to files. This creates an audit trail and enables
   debugging when things go wrong.
