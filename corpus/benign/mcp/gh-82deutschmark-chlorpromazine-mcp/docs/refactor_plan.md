# Chlorpromazine MCP Server - Comprehensive Refactor Plan

## 📋 **Executive Summary**

This document outlines a comprehensive plan to refactor the Chlorpromazine MCP server, addressing critical security vulnerabilities, architectural issues, and incomplete MCP implementation. The refactor will transform the codebase into a secure, modular, and fully compliant MCP server.

## 🚨 **Critical Issues Identified**

### High Priority
- **Broken Test Suite**: Tests expect REST endpoints but server implements JSON-RPC
- **Incomplete MCP Implementation**: Claims prompts support but no handlers registered
- **Security Vulnerabilities**: No input sanitization, missing rate limiting, API key exposure risk
- **Poor Modularity**: 588-line monolithic server.ts file with mixed concerns

### Medium Priority
- **TypeScript Quality**: Heavy use of `any` types defeats type safety
- **Error Handling**: Inconsistent error propagation and logging
- **Network Security**: No timeouts, CORS, or security headers

## 🏗️ **PHASE 1: Modular Architecture Redesign**

### New Project Structure
```
src/
├── config/
│   ├── constants.ts          # DEFAULT_SITES, server info
│   ├── environment.ts        # Environment variable parsing with validation
│   └── server-config.ts      # MCP server configuration
├── types/
│   ├── mcp-types.ts         # Clean MCP type definitions (reduce `any`)
│   ├── tool-types.ts        # Tool argument/result schemas
│   └── app-types.ts         # Application-specific types
├── services/
│   ├── serpapi.ts           # SerpAPI client with security/rate limiting
│   ├── file-reader.ts       # Secure file reading for sober_thinking
│   └── rate-limiter.ts      # Request rate limiting service
├── tools/
│   ├── kill-trip/
│   │   ├── handler.ts       # Tool implementation
│   │   ├── schema.ts        # Input/output schemas
│   │   └── index.ts         # Exports
│   ├── sober-thinking/
│   │   ├── handler.ts
│   │   ├── schema.ts
│   │   └── index.ts
│   └── index.ts             # Tool registry
├── prompts/
│   ├── sober-thinking.ts    # MCP prompt implementation
│   ├── fact-checked-answer.ts
│   ├── buzzkill.ts
│   └── index.ts             # Prompt registry
├── handlers/
│   ├── message-handler.ts   # sampling/createMessage
│   ├── tools-handler.ts     # tools/list, tools/call
│   ├── prompts-handler.ts   # prompts/list, prompts/get
│   └── index.ts
├── utils/
│   ├── logger.ts            # Structured logging
│   ├── security.ts          # Input sanitization, validation
│   ├── errors.ts            # Custom error classes
│   └── index.ts
└── server.ts                # Orchestration only
```

### Benefits
- **Separation of Concerns**: Each module has single responsibility
- **Testability**: Individual components can be unit tested
- **Maintainability**: Changes localized to specific modules
- **Reusability**: Services can be shared across handlers

## 🔒 **PHASE 2: Security Hardening**

### Critical Security Improvements

#### 1. Input Sanitization & Validation
```typescript
// utils/security.ts
export function sanitizeSearchQuery(query: string): string {
  return query
    .replace(/[^\w\s\-_.]/g, '') // Allow only safe chars
    .slice(0, 200) // Limit length
    .trim();
}

export function validateToolInput<T>(schema: z.ZodSchema<T>, input: unknown): T {
  const result = schema.safeParse(input);
  if (!result.success) {
    throw new SecurityError('Invalid input', result.error.issues);
  }
  return result.data;
}
```

#### 2. Rate Limiting & Timeouts
```typescript
// services/rate-limiter.ts
export class RateLimiter {
  private requests = new Map<string, number[]>();
  
  public checkLimit(identifier: string, maxRequests = 10, windowMs = 60000): boolean {
    // Sliding window rate limiting implementation
    const now = Date.now();
    const windowStart = now - windowMs;
    
    if (!this.requests.has(identifier)) {
      this.requests.set(identifier, []);
    }
    
    const userRequests = this.requests.get(identifier)!;
    const validRequests = userRequests.filter(time => time > windowStart);
    
    if (validRequests.length >= maxRequests) {
      return false;
    }
    
    validRequests.push(now);
    this.requests.set(identifier, validRequests);
    return true;
  }
}

// services/serpapi.ts with timeout
const response = await fetch(url, { 
  signal: AbortSignal.timeout(5000),
  headers: { 'User-Agent': 'ChlorpromazineMCP/0.2.0' }
});
```

#### 3. Secrets Management
```typescript
// config/environment.ts
export const config = {
  serpApiKey: requireEnv('SERPAPI_KEY'),
  port: parseInt(process.env.PORT || '3000'),
  apiKey: process.env.API_KEY || null,
  siteFilter: parseCommaSeparated(process.env.SITE_FILTER),
};

// Mask sensitive data in sober_thinking
function maskEnvValue(line: string): string {
  if (line.includes('KEY') || line.includes('SECRET') || line.includes('TOKEN')) {
    const [key] = line.split('=', 1);
    return `${key}=***`;
  }
  return line;
}
```

### Security Checklist
- [ ] Input sanitization for all user inputs
- [ ] Rate limiting on external API calls
- [ ] Timeout protection on network requests
- [ ] Secrets masking in file operations
- [ ] CORS configuration
- [ ] Security headers implementation
- [ ] Error message sanitization (no stack traces in production)

## 🎯 **PHASE 3: Complete MCP Implementation**

### Fix Missing Prompts

#### 1. Implement Prompt Handlers
```typescript
// handlers/prompts-handler.ts
export function registerPromptHandlers(server: Server) {
  server.setRequestHandler(ListPromptsRequestSchema, async (request) => ({
    prompts: [
      { 
        name: 'sober_thinking', 
        description: 'Ground agent in project reality by reading current files',
        arguments: [
          { name: 'QUESTION_TEXT', description: 'The question to answer', required: true }
        ]
      },
      { 
        name: 'fact_checked_answer', 
        description: 'Verify answer against official documentation',
        arguments: [
          { name: 'USER_QUERY', description: 'Query to fact-check', required: true }
        ]
      },
      { 
        name: 'buzzkill', 
        description: 'Debug systematic issues with structured analysis',
        arguments: [
          { name: 'ISSUE_DESCRIPTION', description: 'Description of the issue', required: true },
          { name: 'RECENT_CHANGES', description: 'Recent changes made', required: false },
          { name: 'EXPECTED_BEHAVIOR', description: 'What should happen', required: false },
          { name: 'ACTUAL_BEHAVIOR', description: 'What actually happens', required: false }
        ]
      }
    ]
  }));

  server.setRequestHandler(GetPromptRequestSchema, async (request) => {
    const { name, arguments: args } = request.params;
    return await promptRegistry.get(name).render(args);
  });
}
```

#### 2. Create Actual Prompts
```typescript
// prompts/sober-thinking.ts
export const soberThinkingPrompt = {
  name: 'sober_thinking',
  render: async (args: { QUESTION_TEXT: string }) => ({
    messages: [{
      role: 'user',
      content: {
        type: 'text',
        text: `Before answering "${args.QUESTION_TEXT}", first read the project files to ground yourself in reality. Use the sober_thinking tool to get current project status, then provide a factual answer based on the actual codebase.

Steps:
1. Call sober_thinking tool to read project files
2. Analyze the current state based on README, .env, and CHANGELOG
3. Answer the question using only verified information from the project files
4. If uncertain, clearly state what information is missing`
      }
    }]
  })
};
```

### MCP Compliance Checklist
- [ ] Implement prompts/list handler
- [ ] Implement prompts/get handler  
- [ ] Create structured prompt definitions
- [ ] Update server capabilities declaration
- [ ] Add prompt argument validation
- [ ] Test all MCP methods with compliant client

## 🧪 **PHASE 4: Test Suite Overhaul**

### Replace REST tests with proper MCP client

```typescript
// test/mcp-client.ts
export class MCPTestClient {
  constructor(private baseUrl: string) {}
  
  async jsonRpcCall(method: string, params: any) {
    const response = await fetch(this.baseUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: Math.random().toString(),
        method,
        params
      })
    });
    
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const result = await response.json();
    if (result.error) {
      throw new Error(`RPC Error: ${result.error.message}`);
    }
    
    return result.result;
  }
  
  async listTools() {
    return this.jsonRpcCall('tools/list', {});
  }
  
  async callTool(name: string, input: any, toolRunId?: string) {
    return this.jsonRpcCall('tools/call', { 
      name, 
      input,
      toolRunId: toolRunId || crypto.randomUUID()
    });
  }
  
  async listPrompts() {
    return this.jsonRpcCall('prompts/list', {});
  }
  
  async getPrompt(name: string, arguments: any) {
    return this.jsonRpcCall('prompts/get', { name, arguments });
  }
  
  async createMessage(messages: any[], model?: string) {
    return this.jsonRpcCall('sampling/createMessage', { messages, model });
  }
}

// test/integration.test.ts
describe('MCP Integration Tests', () => {
  let client: MCPTestClient;
  let server: ChildProcess;
  
  beforeAll(async () => {
    // Start test server
    server = spawn('node', ['dist/server.js'], {
      env: { ...process.env, PORT: TEST_PORT, SERPAPI_KEY: 'test_key' }
    });
    await waitForServer(TEST_PORT);
    client = new MCPTestClient(`http://localhost:${TEST_PORT}`);
  });
  
  afterAll(() => {
    server?.kill();
  });
  
  describe('Tools', () => {
    it('should list tools correctly', async () => {
      const result = await client.listTools();
      expect(result.tools).toHaveLength(2);
      expect(result.tools[0].name).toBe('kill_trip');
      expect(result.tools[1].name).toBe('sober_thinking');
    });
    
    it('should execute kill_trip tool', async () => {
      const result = await client.callTool('kill_trip', { query: 'test query' });
      expect(result.content).toBeDefined();
      expect(result.content[0].type).toBe('text');
    });
    
    it('should execute sober_thinking tool', async () => {
      const result = await client.callTool('sober_thinking', {});
      expect(result.content).toBeDefined();
      expect(result.structuredContent.content).toContain('README.md');
    });
  });
  
  describe('Prompts', () => {
    it('should list prompts correctly', async () => {
      const result = await client.listPrompts();
      expect(result.prompts).toHaveLength(3);
      expect(result.prompts.map(p => p.name)).toContain('sober_thinking');
    });
    
    it('should get sober_thinking prompt', async () => {
      const result = await client.getPrompt('sober_thinking', { 
        QUESTION_TEXT: 'What is this project?' 
      });
      expect(result.messages).toBeDefined();
      expect(result.messages[0].content.text).toContain('sober_thinking tool');
    });
  });
  
  describe('Security', () => {
    it('should sanitize malicious input', async () => {
      const maliciousQuery = '<script>alert("xss")</script>';
      const result = await client.callTool('kill_trip', { query: maliciousQuery });
      expect(result.content[0].text).not.toContain('<script>');
    });
    
    it('should enforce rate limits', async () => {
      // Make rapid requests
      const promises = Array(15).fill(0).map(() => 
        client.callTool('kill_trip', { query: 'test' })
      );
      
      const results = await Promise.allSettled(promises);
      const failures = results.filter(r => r.status === 'rejected');
      expect(failures.length).toBeGreaterThan(0);
    });
  });
});
```

### Test Coverage Goals
- [ ] Unit tests for all modules (>90% coverage)
- [ ] Integration tests for MCP protocol compliance
- [ ] Security tests for input validation and rate limiting
- [ ] Performance tests for concurrent requests
- [ ] Error condition tests for network failures

## 🚀 **PHASE 5: Implementation Roadmap**

### Week 1: Foundation
- [ ] Create new directory structure in `src/`
- [ ] Extract constants to `config/constants.ts`
- [ ] Implement environment validation in `config/environment.ts`
- [ ] Create security utilities in `utils/security.ts`
- [ ] Add structured logging in `utils/logger.ts`
- [ ] Define clean TypeScript types in `types/`

### Week 2: Core Refactor
- [ ] Modularize tool implementations into `tools/`
- [ ] Implement prompt handlers in `prompts/`
- [ ] Add rate limiting service in `services/rate-limiter.ts`
- [ ] Secure SerpAPI client in `services/serpapi.ts`
- [ ] Create MCP handlers in `handlers/`
- [ ] Update main `server.ts` to orchestration only

### Week 3: Testing & Validation
- [ ] Implement MCP test client
- [ ] Rewrite integration tests
- [ ] Add security test suite
- [ ] Add error condition tests
- [ ] Performance testing with concurrent requests
- [ ] Validate MCP protocol compliance

### Week 4: Polish & Deploy
- [ ] Update documentation (README, API docs)
- [ ] Final security audit
- [ ] Deployment testing on Smithery.ai
- [ ] Add monitoring/alerting setup
- [ ] Create migration guide for existing users

## 💡 **Expected Benefits After Refactor**

### Security
✅ **Input Validation**: All inputs sanitized and validated  
✅ **Rate Limiting**: Protection against abuse and DoS  
✅ **Timeout Protection**: Network calls won't hang indefinitely  
✅ **Secrets Security**: Sensitive data properly masked  

### Maintainability
✅ **Modular Design**: Single responsibility principle throughout  
✅ **Type Safety**: Elimination of `any` types  
✅ **Testability**: Each component independently testable  
✅ **Documentation**: Comprehensive inline and API docs  

### Compliance
✅ **Full MCP Implementation**: All advertised capabilities working  
✅ **Protocol Compliance**: Proper JSON-RPC implementation  
✅ **Error Handling**: Consistent error responses  
✅ **Client Compatibility**: Works with all MCP clients  

### Performance
✅ **Efficient Routing**: Optimized request handling  
✅ **Resource Management**: Proper cleanup and limits  
✅ **Monitoring**: Performance metrics and health checks  
✅ **Scalability**: Ready for production deployment  

## 🔄 **Migration Strategy**

### Risk Mitigation
- Each phase can be tested independently
- Gradual rollout with feature flags
- Backward compatibility maintained during transition
- Rollback plan for each phase

### Breaking Changes
- Test suite changes from REST to JSON-RPC (expected)
- Configuration validation may reject invalid env vars
- Tool input validation may reject previously accepted inputs
- API responses will be more consistent but format may change slightly

### Deployment Plan
1. **Development**: Implement on feature branch
2. **Testing**: Comprehensive test suite on staging environment  
3. **Beta**: Limited rollout to test users
4. **Production**: Full rollout with monitoring

## 📚 **References**

- [Model Context Protocol Specification](https://modelcontextprotocol.io/docs)
- [MCP TypeScript SDK Documentation](https://modelcontextprotocol.io/tutorials)
- [Security Best Practices for Node.js](https://nodejs.org/en/docs/guides/security/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)

---

**Created**: 2025-08-19  
**Author**: Claude Code Audit  
**Version**: 1.0  
**Status**: Planning Phase