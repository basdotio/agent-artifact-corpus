# Cloud Architecture

This document describes the cloud-specific architecture.

## Cloud Topology

```mermaid
flowchart TB
    Internet --> LB
    LB --> NamespaceA[Namespace A]
    LB --> NamespaceB[Namespace B]
    NamespaceA --> PodsA
    NamespaceB --> PodsB
    PodsA --> CloudSQL[(Cloud SQL)]
    PodsB --> Storage[(Bucket)]
```

## Key Components

- Regions / Zones:
- Networking:
- Load Balancers:
- Compute (Kubernetes / Cloud Run / VMs):
- Storage Services:
- IAM / Permissions:
