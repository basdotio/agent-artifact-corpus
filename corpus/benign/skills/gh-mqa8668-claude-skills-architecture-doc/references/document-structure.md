# The six sections, expanded

Worked against the reference output, `Meshgate Control Plane - Architecture and
Requirements` (11 pages). Each section below states its job, the reader it serves, the
shape it takes, and the failure mode to avoid.

---

## 1. System Architecture

### 1.1 System Overview

**Job:** make the category legible to someone who has not bought into it yet, then say
what this product does about it. **Two paragraphs.** No history, no market sizing, no
"in today's landscape".

Paragraph one names the problem in plain words. Paragraph two names the product's answer
and, if there is one, the structural consequence that makes it different.

> A traditional network trusts whatever is already inside it. Zero Trust does not: every
> peer authenticates, and every path between two peers is allowed or denied explicitly.
>
> Meshgate applies that model over a WireGuard mesh. Once the control plane has authorized
> two peers they connect directly and encrypted, so the control plane never carries their
> traffic. What it carries is identity and policy - it authenticates admins and peers
> against your existing identity provider, coordinates peer discovery and NAT traversal,
> and decides which group may reach which server.

**Failure mode:** three paragraphs of positioning before any fact.

### 1.2 <Product> Architecture

**Job:** the complete component inventory, once, so nothing later has to re-introduce a
name. **Shape:** a short layer description, the archetype-C topology diagram, then a two
column `Component | Role` table.

The table is the canonical description of every component. The Deployment Guide copies
it verbatim. When a role changes, change it here and grep the other documents.

Close with what the product is *not*, if there is a plausible confusion:

> The control plane authenticates against an external OIDC-compliant identity provider
> (Keycloak, Auth0, Zitadel, or similar) - it is not itself an identity
> provider.

**Failure mode:** a component in the diagram that is missing from the table, or named
differently in the two.

### 1.3 Technology Stack

**Job:** answer "what am I actually running" for a security review. **Shape:** one small
`Category | Technology` table per layer - language, protocol, state store, auth. Two
columns, four to six rows. No prose between them beyond the bold layer label.

### 1.4 Deployment Model

**Job:** deployment form (Compose, Helm, RPM) plus the runtime modes, each pointing at
its section 2 subsection. Close with the one architectural property that makes the HA
story simple or hard - stateless sessions, active/passive vs active-active, shared state.

---

## 2. Network Diagram

Section intro, one sentence, establishing that the two models are the same software:

> Two supported topologies. Both run the same containers with the same configuration and
> publish the same ports; they differ only in how many hosts carry the stack and in what
> happens when one of them fails.

### 2.1 Single-instance Model

Lead sentence, then the archetype-A diagram. Say explicitly that the diagram carries the
firewall and DNS answers, so the reader knows not to hunt for a table:

> The zones in the diagram show what is published to the internet and what is not, and
> the strip along the bottom lists every firewall rule and DNS record you need to create.

### 2.2 High-availability Model

Lead sentence positioning it as the thing to grow into, then the archetype-B diagram,
then a bullet per tier explaining its failover. One bullet, one tier, one mechanism.

**Failure mode:** jumping straight from the heading into the image with no lead sentence.

---

## 3. Hardware Requirements

**Job:** the BOM. This is the section procurement prints.

Intro must define both columns and be honest about the floor:

> Two figures per role. Recommended is what <vendor> sizes a production deployment at,
> and what these documents assume. Minimum is the floor that will boot and run correctly,
> suitable for a lab or a proof of concept - it leaves no headroom for relay traffic,
> audit growth, or running an upgrade alongside the current version.

Table shape: `Server role | Qty | Recommended | Minimum | Notes`. The HA table ends with
a bold **Total** row carrying the node count - that number is what gets quoted.

Anything co-located goes in a note card below, not a separate table row, and states the
alternative cost:

> etcd runs as a three-member cluster co-located on the three PostgreSQL nodes, which is
> why the tier is three nodes and not two. An even number of members cannot elect a
> leader. If your standards require etcd on dedicated hosts, add 3 x (2 vCPU, 4 GB RAM,
> 40 GB SSD) for a ten-node total.

Close with the growth driver for disk, so the reader can size their own retention.

**Failure mode:** one sizing column; a node count in the table that disagrees with the
node count in the diagram.

---

## 4. Standard Software List

**Job:** licence and supply-chain review. Columns:
`Software | Version (as deployed) | License | Replaceable | Notes`.

- Drop any column whose value is identical on every row - state it once in the intro
  ("Every component below is open source").
- No empty version cells. If you do not know an exact version, give a floor
  (`2.2 or newer`) or the tag as deployed (`` `lts` image tag ``) - never blank.
- A floating tag is a finding, not a spec. Report it truthfully and recommend pinning:
  "STUN/TURN; pin to a fixed tag or digest if your change control requires it".
- Put the OS in the intro line, not the table, unless the customer mandates a specific
  distro.
- Close with the pinning policy for your own images and why it matters.

---

## 5. Deployment and Verification

### 5.1 Deployment Steps

Four numbered steps, no more - prerequisites, registry login, configure, start. Each one
sentence plus its command inline. Then hand off:

> The full step-by-step runbook, including the `.env` variable reference and
> troubleshooting notes, is in the companion <Product> Deployment Guide.

### 5.2 Verification

Two stages, and each must state what success *looks like*, not what to run:

- **Container health** - the count and state expected, within a stated time, plus the
  one recovery action that is safe.
- **Functional check** - the URL, the login, and the specific screen with the specific
  values on it.

Close with the gate sentence: "Only after both checks pass is <the system> ready to ...".

---

## 6. Use Cases

**Job:** make the abstract concrete. Exactly two scenarios.

Pick them so they differ in *kind*, not in scale: the reference uses one about
**enrolment patterns** (how do I get my existing servers in) and one about **policy
granularity** (how fine can access control get). Each gets its own diagram - archetype E
and archetype D respectively.

Each scenario: a lead paragraph, the pattern bullets, the diagram, then the consequence
paragraph. Always state the default-deny behaviour concretely, with a named example:

> Access is default-deny: a user-group and server pair with no explicit policy between
> them cannot see each other at all, not merely receive a permission error. For example,
> an Office-group user attempting SSH to the Sysadmin-only jump host is rejected before
> authentication - the port simply does not respond.

**Failure mode:** two use cases that are the same scenario at different sizes.

---

## The contents block

Put a flat `**Contents**` list at the top of the markdown, mirroring the numbering
exactly. It renders as a nested list, and the section numbers pick up the list-marker
colour from the style block - which is why that colour is set to `#8A9899` and not the
accent.

## Cross-document invariants

When the set has more than one document, these must be byte-identical across all of them:

- component names and their role descriptions
- port table
- domain table
- image registry host and the pinning policy

Before rendering: `grep -n "<component-name>" *.md` for each component, and read the
matches side by side.
