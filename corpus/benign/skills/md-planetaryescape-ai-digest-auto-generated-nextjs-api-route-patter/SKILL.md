---
name: auto-generated-nextjs-api-route-patterns
description: Next.js API route patterns for this project. Runtime config, circuit breakers, demo mode fallback, multiple AWS invocation strategies. Triggers on "api route", "next.js", "route handler", "POST", "GET".
---

# Next.js API Route Patterns

API routes in `frontend/app/api/` with resilience, demo mode, and multiple backend invocation methods.

## Route Handler Exports

Always export runtime and optionally maxDuration:

```typescript
// From frontend/app/api/digest/trigger/route.ts
export const runtime = "nodejs";
export const maxDuration = 60; // seconds, for long-running operations
```

Export named functions for HTTP methods:

```typescript
export async function POST(request: Request) {
  // handler logic
}

export async function GET(request: Request) {
  // handler logic
}
```

## Clerk Auth Pattern (Currently Disabled)

Auth commented out until Clerk configured. Use demo user as fallback:

```typescript
// From frontend/app/api/digest/trigger/route.ts
// Auth temporarily disabled while Clerk is not configured
// const { userId } = await auth();
// if (!userId) {
//   return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
// }
const userId = "demo-user";
```

## Rate Limiting

Check rate limits before expensive operations:

```typescript
// From frontend/app/api/digest/trigger/route.ts
const rateLimitResult = checkRateLimit(userId, "digest-trigger");
if (!rateLimitResult.allowed) {
  return NextResponse.json(
    { error: "Too many requests. Please try again later." },
    {
      status: 429,
      headers: {
        "Retry-After": rateLimitResult.retryAfter?.toString() || "3600",
      },
    }
  );
}
```

Rate limiter tracks by `${userId}:${endpoint}` key. Default: 10 requests/hour.

## Demo Mode Fallback

Return demo data when AWS credentials not configured:

```typescript
// From frontend/app/api/digest/trigger/route.ts
if (!process.env.AWS_ACCESS_KEY_ID || !process.env.AWS_SECRET_ACCESS_KEY) {
  return NextResponse.json({
    success: true,
    message: "Demo mode: Digest generation simulated (AWS credentials not configured)",
    data: {
      demo: true,
      payload,
      generatedAt: new Date().toISOString(),
      estimatedCompletion: new Date(Date.now() + 120000).toISOString(),
    },
    type: "demo",
  });
}
```

For list endpoints, return realistic demo data:

```typescript
// From frontend/app/api/stepfunctions/executions/route.ts
if (!process.env.AWS_ACCESS_KEY_ID || !process.env.AWS_SECRET_ACCESS_KEY) {
  const demoExecutions = [
    {
      executionArn: "arn:aws:states:us-east-1:123456789012:execution:ai-digest-pipeline:demo-execution-1",
      name: "demo-execution-1",
      status: "SUCCEEDED",
      startDate: new Date(Date.now() - 3600000).toISOString(),
      stopDate: new Date(Date.now() - 3000000).toISOString(),
    },
  ];

  return NextResponse.json({
    executions: demoExecutions,
    nextToken: null,
    demo: true,
  });
}
```

## Multiple Invocation Strategies

Three ways to invoke backend, tried in order:

### 1. Step Functions (Orchestrated Pipeline)

```typescript
// From frontend/app/api/digest/trigger/route.ts
if (useStepFunctions) {
  const stateMachineArn =
    process.env.STEP_FUNCTIONS_STATE_MACHINE_ARN ||
    process.env.NEXT_PUBLIC_STEP_FUNCTIONS_STATE_MACHINE_ARN;

  if (!stateMachineArn) {
    return NextResponse.json(
      {
        success: false,
        error: "Step Functions state machine ARN not configured",
        message: "Please configure STEP_FUNCTIONS_STATE_MACHINE_ARN in your environment variables",
        type: "configuration-error",
      },
      { status: 500 }
    );
  }

  const executionName = `digest-${Date.now()}-${userId.slice(-6)}`;

  const command = new StartExecutionCommand({
    stateMachineArn: stateMachineArn,
    name: executionName,
    input: JSON.stringify(payload),
  });

  const sfnClient = getSFNClient();

  const response = await sfnCircuitBreaker.execute(async () => {
    return await sfnClient.send(command);
  });

  return NextResponse.json({
    success: true,
    message: "Step Functions pipeline started",
    executionArn: response.executionArn,
    executionName,
    startDate: response.startDate,
    type: "stepfunctions",
  });
}
```

### 2. Lambda Function URL (Preferred)

```typescript
// From frontend/app/api/digest/trigger/route.ts
const functionUrl = process.env.LAMBDA_RUN_NOW_URL;

if (functionUrl) {
  const response = await httpCircuitBreaker.execute(async () => {
    return await fetch(functionUrl, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    });
  });

  const data = await response.json();

  return NextResponse.json({
    success: response.ok,
    message: data.message || "Digest generation triggered via Function URL",
    data,
    type: "lambda-url",
  });
}
```

### 3. AWS SDK Invocation (Fallback)

```typescript
// From frontend/app/api/digest/trigger/route.ts
const command = new InvokeCommand({
  FunctionName: process.env.LAMBDA_DIGEST_FUNCTION_NAME,
  InvocationType: cleanup ? "Event" : "RequestResponse", // async vs sync
  Payload: JSON.stringify(payload),
});

const lambda = getLambdaClient();

const response = await lambdaCircuitBreaker.execute(async () => {
  return await lambda.send(command);
});

if (response.StatusCode === 202) {
  return NextResponse.json({
    success: true,
    message: "Digest generation started (async mode)",
    requestId: response.$metadata.requestId,
    type: "lambda-sdk",
  });
}

const responsePayload = response.Payload
  ? JSON.parse(new TextDecoder().decode(response.Payload))
  : null;

return NextResponse.json({
  success: true,
  message: "Digest generation completed",
  data: responsePayload,
  type: "lambda-sdk",
});
```

## Circuit Breaker Integration

Create circuit breakers at module level, reuse across requests:

```typescript
// From frontend/app/api/digest/trigger/route.ts
const sfnCircuitBreaker = CircuitBreaker.getBreaker("stepfunctions-digest", {
  failureThreshold: 5,
  resetTimeout: 60000,
});

const lambdaCircuitBreaker = CircuitBreaker.getBreaker("lambda-digest", {
  failureThreshold: 5,
  resetTimeout: 60000,
});

const httpCircuitBreaker = CircuitBreaker.getBreaker("lambda-http", {
  failureThreshold: 5,
  resetTimeout: 60000,
});
```

Use singleton pattern via `getBreaker()` - creates on first call, returns existing on subsequent.

Wrap AWS SDK calls:

```typescript
const response = await sfnCircuitBreaker.execute(async () => {
  return await sfnClient.send(command);
});
```

## Input Validation with Zod

Validate query parameters:

```typescript
// From frontend/app/api/stepfunctions/executions/route.ts
import { z } from "zod";

const querySchema = z.object({
  status: z.enum(["RUNNING", "SUCCEEDED", "FAILED", "TIMED_OUT", "ABORTED"]).optional(),
  maxResults: z
    .string()
    .optional()
    .default("10")
    .transform((val) => {
      const num = Number.parseInt(val, 10);
      if (Number.isNaN(num)) {
        return 10;
      }
      return Math.max(1, Math.min(num, 100));
    }),
  nextToken: z.string().optional(),
});

const { searchParams } = new URL(request.url);

const validationResult = querySchema.safeParse({
  status: searchParams.get("status") || undefined,
  maxResults: searchParams.get("maxResults") || "10",
  nextToken: searchParams.get("nextToken") || undefined,
});

if (!validationResult.success) {
  return NextResponse.json(
    { error: "Invalid query parameters", details: validationResult.error.issues },
    { status: 400 }
  );
}

const { status: statusFilter, maxResults, nextToken } = validationResult.data;
```

## Error Sanitization

Always sanitize errors in responses:

```typescript
// From frontend/app/api/digest/trigger/route.ts
import { sanitizeError } from "@/lib/utils/error-handling";

try {
  // route logic
} catch (error) {
  return NextResponse.json(
    {
      error: "Failed to trigger digest generation",
      details: sanitizeError(error), // hides sensitive info in production
    },
    { status: 500 }
  );
}
```

Sanitizer returns generic messages in production, full details in development.

## Response Type Tagging

Tag responses with invocation method:

```typescript
return NextResponse.json({
  success: true,
  message: "...",
  type: "stepfunctions", // or "lambda-url" or "lambda-sdk" or "demo"
});
```

Helps frontend distinguish between real and demo data.

## AWS Client Initialization

Singleton clients with conditional credentials:

```typescript
// From frontend/lib/aws/clients.ts
let sfnClient: SFNClient | null = null;

export function getSFNClient(): SFNClient {
  if (!sfnClient) {
    sfnClient = new SFNClient({
      region: process.env.AWS_REGION || "us-east-1",
      ...(process.env.AWS_ACCESS_KEY_ID && process.env.AWS_SECRET_ACCESS_KEY
        ? {
            credentials: {
              accessKeyId: process.env.AWS_ACCESS_KEY_ID,
              secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
            },
          }
        : {}),
    });
  }
  return sfnClient;
}
```

Pattern: only set credentials if both key and secret present, otherwise let SDK use default provider chain.

## Key Files

- `frontend/app/api/digest/trigger/route.ts` - POST endpoint with 3 invocation strategies
- `frontend/app/api/stepfunctions/executions/route.ts` - GET endpoint with validation
- `frontend/lib/aws/clients.ts` - Singleton AWS clients
- `frontend/lib/circuit-breaker.ts` - Opossum wrapper
- `frontend/lib/rate-limiter.ts` - In-memory rate limiting
- `frontend/lib/utils/error-handling.ts` - Error sanitization

## Avoid

- Don't create new circuit breakers per request (use module-level singletons)
- Don't skip demo mode checks (frontend must work without AWS)
- Don't expose raw AWS errors (always use sanitizeError)
- Don't forget rate limiting on expensive operations
- Don't use relative timeout values (use absolute ms)
- Don't skip input validation on GET endpoints
