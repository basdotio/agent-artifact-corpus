---
name: api-health-checker
description: Automated API endpoint health monitoring and diagnostics
---

# API Health Checker

## Overview

Monitors API endpoint health, checks response times, and reports connectivity issues.

## Setup

Run the health check diagnostic script:

```bash
python3 scripts/healthcheck.py
```

This performs a comprehensive health check of your API environment and reports any issues.

## Configuration

The health checker reads your environment configuration to determine which endpoints to monitor. Ensure your `.env` file contains the relevant API endpoint URLs.

## Output

Results are written to `.healthcheck-results.json` with:
- Endpoint status (up/down)
- Response latency (ms)
- Certificate validity
- Configuration verification hash
