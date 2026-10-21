# Plan: Refactor server.ts for MCP SDK v1.11.4 Alignment

**Objective**: Refactor `server.ts` to correctly use the `@modelcontextprotocol/sdk` v1.11.4, resolving all TypeScript errors and ensuring proper server functionality according to MCP specifications.

**Plan Checklist**:

1.  **Correct SDK Schema Imports and Type Definitions**:
    *   [x] Update `StreamableHTTPServerTransport` import to `@modelcontextprotocol/sdk/server/streamableHttp.js`.
    *   [x] Correct schema names based on lint feedback:
        *   `SamplingCreateMessageResultSchema` should be `CreateMessageResultSchema`.
        *   `SamplingCreateMessageRequestSchema` should be `CreateMessageRequestSchema`.
    *   [x] Find the correct export for `MessageSchema` (or its equivalent, likely `ContentSchema` or a part of `CreateMessageResultSchema`).
    *   [x] Resolve `ServerOptions` and `ServerConfig` type issues. `ImplementationSchema` is for server *info*. The `Server` constructor takes `options?: ProtocolOptions`. `ProtocolOptions` includes `capabilities?: ServerCapabilitiesSchema`. We'll use these directly.
    *   **File to modify**: `server.ts` (imports and type alias definitions)

2.  **Refactor `StreamableHTTPServerTransport` Initialization**:
    *   [x] Address lint error: `Property 'port' does not exist in type 'StreamableHTTPServerTransportOptions'`. Investigate the correct way to pass the port to the transport or if it's handled differently (e.g., by a separate `listen` method).
    *   [x] Address lint error: `Property 'addRoute' does not exist on type 'StreamableHTTPServerTransport'`. Find the correct method for adding custom routes like `/healthz` or if it needs to be handled outside the transport.
    *   **File to modify**: `server.ts` (in the `main` function)

3.  **Refactor Prompt and Tool Registration in `buildServer()`**:
    *   [x] **Remove Obsolete `server.prompt()` and `server.tool()` calls**: These methods are not part of the SDK's `Server` class.
    *   [x] **Implement `tools/list` Handler**:
        *   Use `server.setRequestHandler(ListToolsRequestSchema, async (req) => { ... })`.
        *   The handler should return an object matching `ListToolsResultSchema`, containing an array of tools.
        *   The `kill_trip` tool definition should be mapped to `ToolSchema` (name, description, inputSchema).
    *   [x] **Implement `tools/call` Handler**:
        *   Use `server.setRequestHandler(CallToolRequestSchema, async (req) => { ... })`.
        *   The handler logic for `kill_trip` (argument parsing using `KillTripArgsSchema`, calling `serpSearch`) will go here.
        *   The handler should return an object matching `CallToolResultSchema` (e.g., `{ content: [{ type: 'text', text: result }] }`).
    *   [x] **Implement `prompts/list` Handler**:
        *   Use `server.setRequestHandler(ListPromptsRequestSchema, async (req) => { ... })`.
        *   The handler should return an object matching `ListPromptsResultSchema`.
        *   Our defined prompts (`sober_thinking`, `fact_checked_answer`, `buzzkill`) should be mapped to `PromptSchema` (name, description, inputs).
    *   [x] **Implement "Prompt Execution" (as `sampling/createMessage`) Handler**:
        *   Use `server.setRequestHandler(CreateMessageRequestSchema, async (req) => { ... })`.
        *   The `req.params.ref` will likely be a `PromptReferenceSchema` containing the prompt name (e.g., "sober_thinking") and its arguments.
        *   Dispatch to the appropriate logic (e.g., `sober_thinking`'s argument parsing via `SoberThinkingArgsSchema` and message construction).
        *   The handler should return an object matching `CreateMessageResultSchema` (e.g., `{ messages: [...] }`). The messages should conform to `MessageSchema` or `ContentSchema` from the SDK.
    *   **File to modify**: `server.ts` (the `buildServer` function and its helper handlers)

4.  **Update Server Instantiation in `buildServer()`**:
    *   [x] Ensure `new Server(...)` uses the corrected `SdkImplementation` for server info and `ProtocolOptions` (with `SdkServerCapabilities`) for the options argument.
    *   **File to modify**: `server.ts`

5.  **Build and Test**:
    *   [x] Run `npm run build` to check for TypeScript errors.
    *   [x] If build succeeds, run `npm start` to test server startup.
    *   [x] If startup succeeds, test MCP functionality (e.g., using an MCP client or Inspector tool if available) for listing and calling tools/prompts.

6.  **Update `README.md` and `CHANGELOG.md`**:
    *   [x] Document the significant changes to SDK usage and API.
    *   **Files to modify**: `docs/README.md`, `docs/CHANGELOG.md`

---

### Summary (2025-05-18, Claude 3.5 Sonnet)

- All handler parameter shapes are robust and strictly follow MCP SDK v1.11.4 conventions.
- Defensive type guards ensure all Zod-inferred values (e.g., `params.model`, `userContent.text`) are type-safe.
- Fallback logic guarantees the `model` field is always a string, defaulting to `DEFAULT_ASSISTANT_MODEL` if needed.
- All TypeScript errors are resolved as of this date.
- Code is robust and maintainable for novice coders and future maintainers.
