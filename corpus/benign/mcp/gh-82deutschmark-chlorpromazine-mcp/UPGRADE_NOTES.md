# MCP SDK v1.26.0 Upgrade Notes

## Summary
Successfully upgraded Chlorpromazine MCP Server from SDK v1.12.0 to v1.26.0 to comply with MCP specification 2025-11-25.

## Changes Made

### 1. SDK Version Update
- **From**: `@modelcontextprotocol/sdk@^1.12.0`
- **To**: `@modelcontextprotocol/sdk@^1.26.0`
- **Added**: `zod@^4.3.6` as direct dependency (SDK uses Zod 4)

### 2. Security Fix
- Addresses **GHSA-345p-7cg4-v4c7**: Cross-client response data leak vulnerability

### 3. Breaking API Changes

#### CallToolResult Schema
**Removed deprecated fields:**
- `toolName` - No longer part of the result schema
- `toolRunId` - No longer part of the result schema

**Updated all tool handlers:**
- `src/tools/sober-thinking/handler.ts`
- `src/tools/kill-trip/handler.ts`
- `src/handlers/tools-handler.ts`
- `server.ts` (root file)

#### Tool Input Parameters
**Changed from `params.input` to `params.arguments`:**
```typescript
// Old (v1.12.0)
const args = validateToolInput(validator, params.input);

// New (v1.26.0)
const args = validateToolInput(validator, params.arguments);
```

#### Server Capabilities
**Removed deprecated capability properties:**
```typescript
// Old (v1.12.0)
capabilities: {
  sampling: { createMessage: true },
  tools: { list: true, call: true },
  prompts: { list: true, get: true }
}

// New (v1.26.0)
capabilities: {
  experimental: {},
  tools: {},
  prompts: {}
}
```

#### Message Content Structure
**Changed from single object to array:**
```typescript
// Old (v1.12.0)
if (lastUserMessage.content.type === 'text') {
  const text = lastUserMessage.content.text;
}

// New (v1.26.0)
if (Array.isArray(lastUserMessage.content)) {
  const textContent = lastUserMessage.content.find(c => c.type === 'text');
  if (textContent && textContent.type === 'text') {
    const text = textContent.text;
  }
}
```

#### CreateMessage Parameters
**Removed `model` parameter from request:**
- The `params.model` field no longer exists in `CreateMessageRequestSchema`
- Always use `DEFAULT_ASSISTANT_MODEL` in responses

### 4. Tool Definition Enhancements

**Added `title` field:**
```typescript
const soberThinkingTool = {
  name: 'sober_thinking',
  title: 'Sober Thinking - Reality Check',  // NEW
  description: '...',
  inputSchema: { 
    type: 'object', 
    properties: {}, 
    additionalProperties: false  // UPDATED per spec
  },
  outputSchema: { ... }
};
```

## Files Modified

### Core Server Files
- `package.json` - SDK version bump, added Zod 4
- `server.ts` - Updated capabilities, message handling, tool results
- `src/server.ts` - Updated capabilities

### Handler Files
- `src/handlers/message-handler.ts` - Array-based content handling
- `src/handlers/tools-handler.ts` - Removed deprecated fields

### Tool Implementation Files
- `src/tools/sober-thinking/handler.ts` - Updated params.arguments, removed deprecated fields
- `src/tools/kill-trip/handler.ts` - Updated params.arguments, removed deprecated fields

### Documentation
- `README.md` - Updated SDK version reference
- `CHANGELOG.md` - Added v0.4.0 entry
- `UPGRADE_NOTES.md` - This file

## Testing Required

After deployment, verify:

1. **Tools work correctly:**
   ```bash
   # Test sober_thinking tool
   # Test kill_trip tool
   ```

2. **Message handling works:**
   ```bash
   # Test sampling/createMessage with text content
   ```

3. **Capabilities are properly advertised:**
   ```bash
   # Check initialize response includes tools and prompts capabilities
   ```

## Next Steps

1. Run `npm install` to update dependencies
2. Run `npm run build` to compile TypeScript
3. Test locally before deploying to Smithery.ai
4. Monitor for any runtime issues after deployment

## References

- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25)
- [MCP SDK v1.26.0 Release](https://github.com/modelcontextprotocol/typescript-sdk/releases/tag/v1.26.0)
- [Security Advisory GHSA-345p-7cg4-v4c7](https://github.com/modelcontextprotocol/typescript-sdk/security/advisories/GHSA-345p-7cg4-v4c7)
