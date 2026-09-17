---
name: Architecture Decision Records
description: Create and maintain Architecture Decision Records (ADRs) in Confluence. Use when documenting technical decisions, architecture choices, technology selections, or when user mentions ADR, architecture decisions, technical choices, or design decisions.
---

# Architecture Decision Records (ADR)

Expert assistance for creating and maintaining Architecture Decision Records in Confluence.

## When to Use This Skill

- Documenting architectural decisions
- Recording technology choices
- Explaining design decisions
- Creating technical decision logs
- User mentions: ADR, architecture, technical decision, design choice

## What Are ADRs?

**Architecture Decision Records** document important architectural decisions made during a project:

### Purpose
- **Record context**: Why the decision was needed
- **Document options**: What alternatives were considered
- **Explain choice**: Why this option was selected
- **Note consequences**: What are the trade-offs

### Benefits
- Historical record of decisions
- Onboarding new team members
- Preventing decision revisitation
- Understanding system evolution
- Avoiding repeated mistakes

## ADR Structure

### Standard Template (Michael Nygard format)

```markdown
# [Number]. [Title]

**Date**: YYYY-MM-DD
**Status**: [Proposed | Accepted | Deprecated | Superseded]
**Decision Makers**: [Names or team]
**Technical Story**: [Optional ticket/issue reference]

## Context

What is the issue we're seeing that is motivating this decision or change?

## Decision

What is the change that we're proposing and/or doing?

## Consequences

What becomes easier or more difficult to do because of this change?

### Positive

- List of positive consequences

### Negative

- List of negative consequences
- Known limitations
- Trade-offs
```

### Example ADR

```markdown
# 001. Use PostgreSQL for Primary Database

**Date**: 2024-01-15
**Status**: Accepted
**Decision Makers**: Engineering Team
**Technical Story**: PROJ-123

## Context

We need to select a database system for our new user management service. The service will:
- Handle up to 1M users initially, growing to 10M
- Require complex queries across multiple tables
- Need ACID compliance for user transactions
- Support full-text search on user profiles
- Integrate with our existing infrastructure

We evaluated several options:
- PostgreSQL
- MySQL
- MongoDB
- DynamoDB

## Decision

We will use PostgreSQL 15 as our primary database.

**Key factors in this decision:**

1. **ACID Compliance**: Strong guarantees for user data integrity
2. **Complex Queries**: Excellent support for JOINs and aggregations
3. **JSON Support**: Native JSONB for flexible schema evolution
4. **Full-Text Search**: Built-in search capabilities with tsvector
5. **Proven at Scale**: Used successfully by similar applications
6. **Team Expertise**: Team has 5+ years PostgreSQL experience
7. **Cost**: Open source with commercial support available

## Consequences

### Positive

- **Data Integrity**: ACID compliance ensures user data consistency
- **Query Flexibility**: Rich SQL support for complex reporting
- **Future-Proof**: JSON support allows schema evolution
- **Performance**: Excellent performance for our workload patterns
- **Ecosystem**: Vast ecosystem of tools and extensions
- **Monitoring**: Mature monitoring and debugging tools
- **Team Velocity**: Team can be productive immediately

### Negative

- **Scaling Complexity**: Horizontal scaling requires additional tooling (Citus)
- **Operational Overhead**: Requires database administration expertise
- **Backup Strategy**: Need to implement robust backup/recovery
- **Cloud Lock-in**: Managed PostgreSQL ties us to cloud provider
- **Migration Cost**: Future migration to different database would be expensive

### Mitigation Strategies

- Use connection pooling (PgBouncer) for connection management
- Implement read replicas for read scaling
- Regular backup testing and disaster recovery drills
- Database versioning with migration tools (Flyway)
- Monitor query performance with pg_stat_statements

### Alternatives Considered

**MySQL**:
- ✅ Similar performance and features
- ❌ Less sophisticated JSON support
- ❌ Team less experienced

**MongoDB**:
- ✅ Excellent horizontal scaling
- ❌ No ACID transactions (at the time)
- ❌ Weak JOIN support for complex queries

**DynamoDB**:
- ✅ Fully managed, auto-scaling
- ❌ Complex query limitations
- ❌ Higher cost at scale
- ❌ AWS lock-in

## Notes

This decision can be revisited if:
- Scale exceeds 50M users
- Query patterns change dramatically
- Team expertise shifts
- Cost becomes prohibitive

## References

- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [Benchmark Results](link-to-internal-benchmarks)
- [Cost Analysis Spreadsheet](link-to-analysis)
```

## ADR Statuses

### Proposed
- Decision is under discussion
- Not yet implemented
- Open for feedback

### Accepted
- Decision has been approved
- Implementation in progress or complete
- Current recommendation

### Deprecated
- Decision is no longer recommended
- Still in use but should be phased out
- Usually replaced by a newer ADR

### Superseded
- Decision has been replaced
- Reference the new ADR
- Kept for historical context

### Rejected
- Decision was considered but not adopted
- Explains why it was rejected
- Prevents revisiting

## Types of ADRs

### Technology Selection

```markdown
# 005. Use React for Frontend Framework

## Context
Need to select frontend framework for new dashboard application.

Requirements:
- Rich interactive UI
- Real-time updates
- Mobile responsive
- Large community support
- Component reusability

## Decision
Selected React 18 with TypeScript.

## Consequences
[...]
```

### Architecture Pattern

```markdown
# 008. Adopt Microservices Architecture

## Context
Monolithic application becoming difficult to maintain and deploy.

Challenges:
- Long deployment cycles
- Tight coupling
- Difficult to scale independently
- Team coordination overhead

## Decision
Migrate to microservices architecture over 12 months.

## Consequences
[...]
```

### Security Decision

```markdown
# 012. Implement OAuth 2.0 for Authentication

## Context
Need secure, industry-standard authentication.

Requirements:
- Third-party login support
- Token-based authentication
- Refresh token rotation
- Security best practices

## Decision
Implement OAuth 2.0 with PKCE flow.

## Consequences
[...]
```

### Infrastructure Choice

```markdown
# 015. Deploy on AWS Using ECS Fargate

## Context
Need container orchestration solution.

Options evaluated:
- Self-managed Kubernetes
- AWS ECS Fargate
- Google Cloud Run
- Heroku

## Decision
Use AWS ECS Fargate for container deployment.

## Consequences
[...]
```

## ADR Best Practices

### 1. Write When Decision Is Made
- Document as decisions happen
- Don't wait until later
- Capture context while fresh

### 2. Be Specific and Concrete
- Avoid vague language
- Include concrete examples
- Reference metrics and data

### 3. Acknowledge Trade-offs
- Every decision has trade-offs
- Be honest about limitations
- Don't oversell the solution

### 4. Link Related ADRs
- Reference superseded ADRs
- Note related decisions
- Show decision evolution

### 5. Keep It Concise
- Focus on key points
- Link to detailed analysis
- 1-2 pages maximum

### 6. Use Consistent Format
- Same structure for all ADRs
- Predictable organization
- Easy to scan

### 7. Number Sequentially
- 001, 002, 003, etc.
- Never reuse numbers
- Gaps are OK (rejected ADRs)

## ADR Workflow

### 1. Identify Decision Needed
```
Team realizes: "We need to decide on a caching strategy"
```

### 2. Research Options
```
Options:
- Redis
- Memcached
- In-memory (application)
- CDN caching
```

### 3. Draft ADR
```
Create ADR with:
- Context and requirements
- Options evaluated
- Recommendation
- Trade-offs
```

### 4. Review and Discuss
```
Team reviews:
- Technical lead approval
- Security review if needed
- Architecture team input
```

### 5. Accept and Implement
```
- Mark as "Accepted"
- Publish to Confluence
- Implement the decision
- Link from related docs
```

### 6. Maintain Over Time
```
- Update if context changes
- Deprecate if superseded
- Add learnings and updates
```

## Confluence Organization

### ADR Structure in Confluence

```
Architecture Space
├── ADR Index (list of all ADRs)
├── ADR Template
└── Decision Records/
    ├── 001-use-postgresql-for-database.md
    ├── 002-adopt-microservices-architecture.md
    ├── 003-implement-oauth-authentication.md
    ├── 004-use-redis-for-caching.md
    └── ...
```

### ADR Index Page

```markdown
# Architecture Decision Records

## Active Decisions

| Number | Title | Date | Status | Decision Makers |
|--------|-------|------|--------|-----------------|
| 015 | Deploy on AWS ECS Fargate | 2024-01-20 | Accepted | DevOps Team |
| 014 | Use GraphQL for API | 2024-01-18 | Accepted | Backend Team |
| 013 | Implement Feature Flags | 2024-01-15 | Accepted | Engineering |

## Deprecated Decisions

| Number | Title | Date | Status | Superseded By |
|--------|-------|------|--------|---------------|
| 007 | Use MongoDB | 2023-06-10 | Deprecated | ADR-001 |
| 003 | Deploy to Heroku | 2023-03-15 | Deprecated | ADR-015 |

## Rejected Proposals

| Number | Title | Date | Reason |
|--------|-------|------|--------|
| 011 | Use Vue.js | 2023-11-20 | Team lacks expertise |
| 006 | Self-host Kubernetes | 2023-05-10 | Too much operational overhead |

## Categories

### Infrastructure
- ADR-001: Database Selection
- ADR-015: Container Orchestration

### Frontend
- ADR-005: Frontend Framework
- ADR-009: State Management

### Backend
- ADR-012: Authentication Method
- ADR-014: API Design

### Security
- ADR-012: OAuth 2.0 Authentication
- ADR-016: Encryption at Rest
```

## Templates for Different Decision Types

### Technology Selection Template

```markdown
# [Number]. Select [Technology Type] for [Purpose]

**Date**: YYYY-MM-DD
**Status**: Proposed
**Decision Makers**: [Team]

## Context

### Requirements
- List functional requirements
- List non-functional requirements
- List constraints

### Evaluation Criteria
1. Criterion 1 (weight: X%)
2. Criterion 2 (weight: Y%)
3. Criterion 3 (weight: Z%)

## Options Evaluated

### Option 1: [Technology A]
**Pros**:
- Pro 1
- Pro 2

**Cons**:
- Con 1
- Con 2

**Score**: X/10

### Option 2: [Technology B]
[Same structure]

### Option 3: [Technology C]
[Same structure]

## Decision

Selected [Technology X] because [brief reasoning].

## Consequences

### Implementation Impact
- What changes are needed
- What stays the same

### Performance Impact
- Expected performance characteristics
- Benchmarks if available

### Cost Impact
- Initial costs
- Ongoing costs
- Hidden costs

### Team Impact
- Training needed
- Learning curve
- Hiring implications

### Risk Assessment
| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Risk 1 | High | Medium | Mitigation strategy |
| Risk 2 | Low | High | Mitigation strategy |
```

### Process Change Template

```markdown
# [Number]. Adopt [Process/Practice]

**Date**: YYYY-MM-DD
**Status**: Proposed
**Decision Makers**: [Team]

## Context

### Current State
- How things work now
- Pain points
- Metrics showing problems

### Desired State
- What we want to achieve
- Success metrics
- Expected benefits

## Decision

Adopt [Process/Practice] with the following approach:
1. Step 1
2. Step 2
3. Step 3

## Consequences

### Team Changes
- New roles or responsibilities
- Required training
- Schedule impacts

### Tooling Changes
- New tools needed
- Integration requirements
- Costs

### Rollout Plan
- Phase 1: Pilot (dates)
- Phase 2: Expansion (dates)
- Phase 3: Full adoption (dates)

### Success Metrics
- Metric 1: Target value
- Metric 2: Target value
- Metric 3: Target value
```

## Updating ADRs

### When to Update

**DO update** when:
- Adding lessons learned
- Noting implementation challenges
- Recording actual vs expected consequences
- Adding references or links

**DON'T update** when:
- Decision needs to change → Create new ADR
- Context has changed significantly → Create new ADR
- Original reasoning was wrong → Create new ADR with Supersedes

### Update Format

Add updates section at the end:

```markdown
## Updates

### 2024-03-15: Performance Issues Discovered
After 3 months in production, we discovered that [issue]. We've mitigated this by [solution]. Consider ADR-XXX for future improvements.

### 2024-06-20: Cost Higher Than Expected
Actual monthly cost is $X vs expected $Y because [reason]. Updated cost estimates in budget.
```

## How I'll Help

When creating ADRs, I will:

1. **Identify the decision**:
   - What needs to be decided?
   - Why is it important?
   - Who should be involved?

2. **Research context**:
   - Read related code
   - Review existing docs
   - Find similar decisions

3. **Structure the ADR**:
   - Use appropriate template
   - Fill in all sections
   - Add relevant details

4. **Evaluate options**:
   - List alternatives
   - Analyze trade-offs
   - Provide recommendations

5. **Create in Confluence**:
   - Format as ADF
   - Add to ADR index
   - Link related documents

6. **Maintain over time**:
   - Add updates
   - Track status changes
   - Deprecate when superseded

## Example Interaction

**You**: "We just decided to use Redis for caching. Can you create an ADR?"

**Me**: "I'll create an ADR for the Redis caching decision.

Let me gather some information:
- What were you using before?
- What other options did you consider?
- What were the key factors in choosing Redis?
- Any concerns or trade-offs?

[You provide context]

I'll create ADR-004: Use Redis for Application Caching

**Draft**:
- Context: Need caching to reduce database load (currently 1000 QPS)
- Evaluated: Redis, Memcached, in-memory caching
- Decision: Redis for persistence, pub/sub, and rich data types
- Consequences: Positive (performance, flexibility), Negative (ops overhead, cost)

Should I create this in Confluence? Which space?"

**You**: "Yes, space 456789"

**Me**: [Creates ADR page]
"Created ADR-004 in space 456789!
Link: https://your-domain.atlassian.net/wiki/spaces/456789/pages/...

Also updating the ADR Index to include this new decision."
