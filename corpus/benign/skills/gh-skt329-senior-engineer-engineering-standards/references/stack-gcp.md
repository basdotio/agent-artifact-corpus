# GCP stack guide

Every change to cloud resources needs the user's approval; the shell guard asks before deploy and infrastructure commands. Prefer infrastructure as code (Terraform) for anything that should outlive a session.

## Choosing compute
| Option | Use when |
|---|---|
| Cloud Run | The default for containerized HTTP services and workers. Scales to zero, revisions make rollback easy |
| Cloud Run functions | Small event handlers (Pub/Sub, Storage, Firestore triggers) with little shared code |
| App Engine | Only for existing apps already on it |
| GKE | Only with a clear need (many services, special networking, existing Kubernetes skills), through a decision brief |

## Cloud Run settings to decide explicitly
- Region close to users (for example asia-south1 for users in India).
- Concurrency per instance, CPU and memory, and the request timeout.
- Minimum instances (removes cold starts, costs money) and maximum instances (caps cost and protects the database).
- CPU allocation: request-only for pure HTTP; always allocated for services doing background work.
- One service account per service with only the roles it needs.
- Traffic splitting between revisions for gradual rollouts, and tagged revisions for previews.

## Identity and access
- Least privilege: grant roles on the specific resource, not the project, wherever possible.
- No service account JSON keys. Use the attached service account at runtime and Workload Identity Federation for CI.
- Separate projects per environment (dev, staging, prod) so a mistake in one cannot touch another.

## Secrets
- Secret Manager for every secret, mounted into Cloud Run as environment variables or files, with access granted per secret to the service account that needs it.

## Data
- Cloud SQL for PostgreSQL for relational data. Connect with the Cloud SQL connector or private IP. Turn on automated backups and point-in-time recovery for production.
- Firestore for document data with simple access patterns. Keep security rules and index definitions in the repository.
- Memorystore for Redis for caches and Celery brokers, reached over the VPC.
- Cloud Storage with uniform bucket-level access, signed URLs for user downloads, and lifecycle rules for old objects.

## Messaging and scheduling
- Pub/Sub for fan-out events with several consumers. Make consumers idempotent; delivery is at least once.
- Cloud Tasks for targeted HTTP tasks that need rate limits, retries, and scheduling.
- Cloud Scheduler for cron-style jobs.

## Images and builds
- Artifact Registry for container images, tagged with the git commit SHA. Avoid relying on `latest`.
- Cloud Build or GitHub Actions for CI (deployment skill, ci-cd reference).

## Observability
- Log structured JSON to stdout; Cloud Logging parses severity and fields.
- Error Reporting for exceptions, Cloud Monitoring alerts on error rate and latency, and uptime checks for public endpoints.
- Use the same request ID in logs across services.

## Cost
- Budgets with alert thresholds on every project.
- Watch minimum instances, idle Cloud SQL instances, cross-region egress, and log volume.
- Label resources by service and environment so costs can be traced.
