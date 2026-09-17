---
name: pure-aws-devops
description: DevOps for the pure project on AWS (ECS Fargate CMS, ALB, EFS, ECR, ACM, App Runner, Route 53). Use when deploying or fixing the CMS, syncing DB/data to AWS CMS, cleaning up a region, linking custom domains (cms or www), listing or auditing AWS resources, or debugging ALB/ECS/exec format error.
---

# Pure project – AWS DevOps

This skill captures how the **pure** repo runs on AWS: CMS on ECS Fargate + EFS + ALB, main site on App Runner, DNS in Route 53. Default region is **us-east-1**.

## Scripts and docs (repo paths)

| Purpose | Path |
|--------|------|
| Deploy CMS image to ECR | `cms/scripts/deploy-aws-ecr.sh` |
| ECS + EFS one-time setup | `cms/scripts/aws/setup-ecs-efs.sh` |
| ALB + HTTP listener | `cms/scripts/aws/setup-alb.sh` |
| ALB HTTPS listener | `cms/scripts/aws/setup-alb-https.sh` |
| Get CMS URL (task IP) | `cms/scripts/aws/get-cms-url.sh` |
| Migrate CMS region | `cms/docs/migrate-cms-to-us-east-1.md` |
| ALB + DNS + HTTPS | `cms/scripts/aws/setup-alb-and-dns.md` |
| Where to find CMS in console | `cms/docs/aws-console-cms.md` |
| App Runner: point at us-east-1 ECR | `docs/apprunner-ecr-us-east-1.md` |
| App Runner: CMS connection (500 on /page/*) | `docs/apprunner-cms-connection.md` |
| us-east-1 resource list | `docs/aws-us-east-1-resources.md` |
| GitHub: Build Pure Web (prod) | `.github/workflows/build-prod.yml` (ECR + App Runner deploy) |
| GitHub: Build Pure CMS (prod) | `.github/workflows/build-cms-prd.yml` (ECR only; roll ECS manually) |
| Sync local DB to AWS (API) | `cms/scripts/seed-and-sync.js` |
| Copy local DB file to EFS | `cms/scripts/aws/sync-db-to-aws.sh` (requires ECS Exec; see below) |

Required env for scripts: `AWS_PAGER=""`, and for ECR deploy `AWS_ACCOUNT_ID`, optionally `AWS_REGION` (default us-east-1), `SESSION_SECRET`, `CORS_ORIGINS`.

---

## Critical gotchas

### 1. Image architecture (exec format error)

Fargate is **x86_64 (linux/amd64)**. If the image is built on ARM (e.g. M1/M2 Mac) without `--platform linux/amd64`, the container logs show **exec format error** and the task exits.

- **Fix:** Build with `--platform linux/amd64` (already in `deploy-aws-ecr.sh` and `build-cms-prd.yml`). Rebuild, push, then `aws ecs update-service ... --force-new-deployment`.

### 2. IAM is global

The ECS task execution role **ecsTaskExecutionRole-pure-cms** is used by the task definition. It lives in IAM (account-level), not in a region. If you delete it during a **region** cleanup (e.g. us-east-2), ECS in **us-east-1** will fail with "unable to assume the role".

- **Fix:** Recreate the role: trust `ecs-tasks.amazonaws.com`, attach `AmazonECSTaskExecutionRolePolicy`, add inline policy **EFSClientMount-pure-cms** for the EFS ARN in the target region. See `setup-ecs-efs.sh` (task execution role block) for the exact JSON.

### 3. ALB and targets in same AZs

Target group health can show **Target.NotInUse** / "Target is in an Availability Zone that is not enabled for the load balancer" if the ECS task lands in an AZ that has no subnet on the ALB.

- **Fix:** Add that AZ’s subnet to the ALB: `aws elbv2 set-subnets --load-balancer-arn <ALB_ARN> --subnets <existing_subnets> <missing_subnet_id>` (ALB needs ≥2 AZs). Or ensure ECS uses the same subnets as the ALB.

### 4. ACM certificates are per-region

A cert in us-east-2 cannot be used by an ALB in us-east-1. Request and validate the cert in the **same region** as the ALB.

### 5. App Runner source must match CI ECR region

The **Build Pure Web (prod)** workflow pushes to **us-east-1** ECR. If the App Runner service was created with **us-east-2** ECR, `start-deployment` only redeploys from that source, so the service never gets the new image.

- **Fix:** Update the service source to us-east-1 ECR: `aws apprunner update-service --service-arn <ARN> --source-configuration '{"ImageRepository":{...}}'`. Step-by-step: **docs/apprunner-ecr-us-east-1.md**.

### 6. ECS Exec requires a task role

`aws ecs update-service ... --enable-execute-command` fails with "a valid taskRoleArn is not being used" if the task definition has no **task role** (only the execution role). ECS Exec needs a task role for the session.

- **Fix:** Add a task role to the task definition (e.g. create an IAM role that tasks can assume, add `taskRoleArn` to the task definition), register the new revision, update the service to use it, then run `--enable-execute-command`. Until then, use **API sync** (`seed-and-sync.js`) instead of file copy (`sync-db-to-aws.sh`).

---

## Common workflows

### Deploy new CMS image and roll ECS

1. Build and push (from repo root): `AWS_ACCOUNT_ID=... ./cms/scripts/deploy-aws-ecr.sh` (uses `--platform linux/amd64`).
2. Roll service: `aws ecs update-service --cluster pure-cms-cluster --service pure-cms-service --force-new-deployment --region us-east-1`.
3. CMS URL: use ALB (e.g. https://cms.conjeezou.com) or `./cms/scripts/aws/get-cms-url.sh` for task IP.

### Sync local CMS database to AWS

Use **API sync** when the AWS CMS is reachable and you have an admin account. The script `cms/scripts/seed-and-sync.js` loads **`.env` then `.env.local`** (so put `CMS_HOST`, `CMS_EMAIL`, `CMS_PASSWORD` in `.env.local` to avoid prompts). It seeds the local DB from data files (pages, comps, sitemap) then pushes to the remote CMS via API.

1. **Run seed and sync** (from repo root). To ensure you sync to **AWS** (not localhost), set `CMS_HOST` explicitly:
   ```bash
   CMS_HOST=https://cms.conjeezou.com node cms/scripts/seed-and-sync.js
   ```
   Credentials are read from `.env.local` (`CMS_EMAIL`, `CMS_PASSWORD`). The script prints `Syncing to remote CMS: <url>` so you can confirm the target.
2. **Full DB replace (optional):** To overwrite the AWS DB file with your local `cms/data/cms.db`, use `./cms/scripts/aws/sync-db-to-aws.sh cms/data/cms.db`. This requires **ECS Exec** to be enabled on the service; enabling it requires a **task role** in the task definition (see gotcha #6). If ECS Exec is not set up, use API sync only.

### ALB returns 503 or “not working”

1. **Target health:** `aws elbv2 describe-target-health --target-group-arn <TG_ARN> --region us-east-1`. If empty or unhealthy:
   - Check ECS: `runningCount` vs `desiredCount`; service events for "failed to launch" or "essential container exited".
   - Check container logs in CloudWatch `/ecs/pure-cms` for **exec format error** (wrong arch) or app crashes.
   - If target state is **unused** due to AZ, add the task’s subnet to the ALB (see gotcha #3).
2. **Listeners:** ALB must have HTTP 80 and (for HTTPS) HTTPS 443 with the correct ACM cert.
3. **Security group:** ALB SG must allow inbound 80 and 443 from 0.0.0.0/0.

### Link cms.conjeezou.com to CMS

1. Run `setup-alb.sh` and `setup-alb-https.sh` (or add HTTPS listener in console with ACM cert).
2. In Route 53 (or DNS provider): CNAME **cms** → ALB DNS name (e.g. `pure-cms-alb-1420427632.us-east-1.elb.amazonaws.com`).
3. Remove stale ACM validation CNAMEs in Route 53 if you deleted the old cert.

### Deploy main site (App Runner)

1. **CI (preferred):** Push to `main`; **Build Pure Web (prod)** (`.github/workflows/build-prod.yml`) builds the image, pushes to **us-east-1** ECR, and runs `aws apprunner start-deployment` when repo variable **APP_RUNNER_SERVICE_ARN** is set.
2. **One-time:** If the service was created with **us-east-2** ECR, it will never see new images. Repoint to us-east-1: **docs/apprunner-ecr-us-east-1.md**, then run `aws apprunner start-deployment --service-arn <ARN> --region us-east-1`.
3. **Manual deploy:** `aws apprunner start-deployment --service-arn $(aws apprunner list-services --region us-east-1 --query 'ServiceSummaryList[?ServiceName==\`pure\`].ServiceArn' --output text) --region us-east-1`.

### Link www.conjeezou.com to App Runner

1. Associate custom domain: `aws apprunner associate-custom-domain --service-arn <ARN> --domain-name www.conjeezou.com --region us-east-1`.
2. Get DNSTarget and CertificateValidationRecords: `aws apprunner describe-custom-domains --service-arn <ARN> --region us-east-1`.
3. In Route 53: add CNAME **www** → DNSTarget; add each CertificateValidationRecord as CNAME (name → value). Or use App Runner console “Link domain” with Route 53 for auto setup.

### Clean up all resources in a region (e.g. us-east-2)

Order matters (dependencies first):

1. ECS: `update-service --desired-count 0`, then `delete-service --force`, then `delete-cluster`.
2. ALB: `delete-load-balancer`.
3. After ALB is gone (wait ~10s): `delete-target-group`.
4. EFS: `delete-mount-target` for each mount target, wait, then `delete-file-system`.
5. Security groups: delete **pure-cms-alb-sg**, **pure-cms-efs-sg**, **pure-cms-ecs-sg** (after nothing references them; ECS ENIs can take 1–2 min to release).
6. CloudWatch: `delete-log-group` for `/ecs/pure-cms`.
7. IAM: delete **ecsTaskExecutionRole-pure-cms** only if no other region uses it (e.g. if us-east-1 is also being torn down). Otherwise skip.
8. Optional: delete default VPC subnets (if 0 ENIs), then ACM certs, ECR repo in that region.

### List resources in a region

Use AWS CLI per service (ECS clusters/services, EC2 VPCs/subnets/SGs/addresses, elbv2 load-balancers/target-groups, EFS, ECR, ACM, logs, apprunner, lambda, rds). See `docs/aws-us-east-1-resources.md` for the structure and a human-readable list with descriptions.

---

## Route 53 (conjeezou.com)

- **cms** → CNAME to CMS ALB DNS (us-east-1).
- **www** → CNAME to App Runner DNSTarget.
- **cdn** → A/alias to CloudFront.
- ACM validation records: CNAMEs like `_<hash>.<name>.conjeezou.com` → `_<hash>.jkddzztszm.acm-validations.aws.`. Remove only when the corresponding cert is deleted.

Hosted zone ID for conjeezou.com: **Z038191012SF55SAOLG35** (confirm with `aws route53 list-hosted-zones`).

---

## Resource names (us-east-1)

- ECS: cluster **pure-cms-cluster**, service **pure-cms-service**, task family **pure-cms**.
- ALB **pure-cms-alb**, target group **pure-cms-tg**.
- EFS name **pure-cms-data**.
- Security groups: **pure-cms-alb-sg**, **pure-cms-ecs-sg**, **pure-cms-efs-sg**.
- ECR: **pure-cms** (CMS), **pure** (main site; used by App Runner).
- App Runner service **pure** (source must be us-east-1 ECR; see docs/apprunner-ecr-us-east-1.md if it was us-east-2).
- IAM role **ecsTaskExecutionRole-pure-cms**, inline policy **EFSClientMount-pure-cms**.

For a full table with IDs and descriptions, see [reference.md](reference.md).
