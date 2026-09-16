# CI/CD Architecture

This document describes how code moves from development to production.

## Pipeline Overview

```mermaid
flowchart LR
    Dev --> PR
    PR --> CI[CI Pipeline]
    CI --> BuildImage
    CI --> RunTests
    BuildImage --> PushRegistry
    RunTests --> Deploy[CD Pipeline]
```

## Details

- Branching strategy:
- CI steps:
- Test strategy:
- Artifact creation:
- Deployment flow:
- GitOps / Automation:
