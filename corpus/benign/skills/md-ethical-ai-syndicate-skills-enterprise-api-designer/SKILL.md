---
name: enterprise-api-designer
description: Use when designing APIs for AI services. Use during solution architecture. Produces API specifications, versioning strategy, and integration documentation.
---

# Enterprise API Designer

## Overview

Design enterprise-grade APIs for AI services that are secure, scalable, and maintainable. Create specifications that enable integration while protecting the organization.

**Core principle:** APIs are contracts. Design them for consumers, version them carefully, and secure them properly.

## When to Use

- Exposing AI capability as a service
- Enabling integrations with AI platform
- Standardizing AI service interfaces
- Building internal AI platform

## Output Format

```yaml
api_design:
  service: "[Service name]"
  version: "[API version]"
  date: "[YYYY-MM-DD]"
  
  overview:
    purpose: "[What the API does]"
    consumers: ["[Who will use it]"]
    ai_capability: "[Underlying AI]"
  
  endpoints:
    - endpoint: "[HTTP method] [Path]"
      description: "[What it does]"
      
      request:
        headers:
          - name: "[Header]"
            required: [true | false]
            description: "[Purpose]"
        
        body:
          type: "[JSON schema or description]"
          example: "[Example payload]"
      
      response:
        success:
          code: "[HTTP code]"
          body: "[Response structure]"
        
        errors:
          - code: "[HTTP code]"
            condition: "[When returned]"
            body: "[Error structure]"
      
      rate_limit: "[Limit if applicable]"
      latency_sla: "[Expected response time]"
  
  authentication:
    method: "[OAuth2 | API Key | mTLS | etc.]"
    details: "[Implementation specifics]"
  
  versioning:
    strategy: "[URL | Header | Query param]"
    current: "[Current version]"
    deprecation_policy: "[How versions retired]"
  
  security:
    data_classification: "[What data flows through]"
    encryption: "[In-transit and at-rest]"
    access_control: "[Authorization model]"
    audit: "[Logging requirements]"
  
  operations:
    monitoring: "[Health endpoints, metrics]"
    throttling: "[Rate limiting strategy]"
    error_handling: "[Error codes and retry guidance]"
  
  documentation:
    openapi_spec: "[Link to spec]"
    developer_guide: "[Link to guide]"
    sdks: ["[Available SDKs]"]
```

## API Design Principles

### REST Best Practices
```yaml
rest_principles:
  resources:
    - "Use nouns, not verbs"
    - "Plural for collections (/documents)"
    - "Singular for specific resources (/documents/{id})"
  
  methods:
    - "GET: Read, safe, idempotent"
    - "POST: Create, often for AI predictions"
    - "PUT: Full update, idempotent"
    - "PATCH: Partial update"
    - "DELETE: Remove, idempotent"
  
  responses:
    - "200: Success"
    - "201: Created"
    - "400: Bad request (client error)"
    - "401: Unauthorized"
    - "403: Forbidden"
    - "404: Not found"
    - "429: Rate limited"
    - "500: Server error"
```

### AI Service Patterns
```yaml
ai_patterns:
  synchronous:
    use_when: "Fast inference (<5s)"
    pattern: "POST /predictions"
    response: "Immediate result"
  
  asynchronous:
    use_when: "Long-running inference"
    pattern:
      - "POST /jobs → 202 + job_id"
      - "GET /jobs/{id} → status/result"
  
  batch:
    use_when: "High volume, latency tolerant"
    pattern:
      - "POST /batches → batch_id"
      - "GET /batches/{id}/results"
  
  streaming:
    use_when: "Progressive output (LLM)"
    pattern: "Server-sent events or WebSocket"
```

## Security Design

### Authentication Options
| Method | Use Case | Considerations |
|--------|----------|----------------|
| **API Key** | Simple, internal | Rotate regularly, scope narrowly |
| **OAuth 2.0** | User context, fine-grained | More complex, industry standard |
| **mTLS** | Service-to-service | Certificate management |
| **JWT** | Stateless, claims-based | Token expiry, validation |

### Authorization
```yaml
authorization:
  models:
    - name: "Role-based"
      when: "Distinct user types"
    
    - name: "Scope-based"
      when: "API key with limited permissions"
    
    - name: "Attribute-based"
      when: "Complex rules needed"
  
  implementation:
    - "Validate on every request"
    - "Principle of least privilege"
    - "Log access for audit"
```

## Versioning Strategy

### Options
| Strategy | Format | Pros | Cons |
|----------|--------|------|------|
| **URL path** | /v1/endpoint | Clear, cacheable | URL changes |
| **Header** | Accept-Version: 1 | Clean URLs | Less visible |
| **Query param** | ?version=1 | Simple | Messy |

### Deprecation Policy
```yaml
deprecation:
  notice_period: "6 months minimum"
  communication:
    - "Announce deprecation in changelog"
    - "Add Deprecation header to responses"
    - "Email known consumers"
  
  sunset:
    - "Sunset header with date"
    - "Migration guide provided"
    - "Support during transition"
```

## Error Handling

### Standard Error Format
```yaml
error_format:
  structure:
    error:
      code: "[Error code]"
      message: "[Human-readable message]"
      details: "[Additional context]"
      request_id: "[Correlation ID]"
  
  example:
    error:
      code: "VALIDATION_ERROR"
      message: "Invalid input data"
      details:
        field: "text"
        issue: "exceeds maximum length of 10000"
      request_id: "abc-123-def"
```

### Retry Guidance
```yaml
retry_behavior:
  retryable:
    - "429 Too Many Requests (with Retry-After)"
    - "503 Service Unavailable"
    - "504 Gateway Timeout"
  
  not_retryable:
    - "400 Bad Request"
    - "401 Unauthorized"
    - "403 Forbidden"
```

## Documentation

### OpenAPI Specification
```yaml
openapi_requirements:
  - "Complete endpoint documentation"
  - "Request/response schemas"
  - "Authentication requirements"
  - "Error responses"
  - "Examples for all operations"
```

### Developer Experience
```yaml
developer_experience:
  - "Quick start guide"
  - "Code examples in common languages"
  - "SDKs for major platforms"
  - "Sandbox environment"
  - "Clear error messages"
```

## Checklist

- [ ] Endpoints designed following conventions
- [ ] Authentication method selected
- [ ] Authorization model defined
- [ ] Versioning strategy chosen
- [ ] Error format standardized
- [ ] Rate limiting configured
- [ ] OpenAPI spec created
- [ ] Security review completed
- [ ] Documentation published
