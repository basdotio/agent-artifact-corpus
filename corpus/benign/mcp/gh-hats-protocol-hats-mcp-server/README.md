# Hats MCP Server Documentation

## Overview

The Hats MCP (Model Context Protocol) Server provides a set of tools for interacting with the Hats Protocol through natural language in Cursor. This server enables AI assistants to understand and interact with the Hats Protocol ecosystem.

## Server Transport Protocols

### StreamableHTTP (Modern Protocol)

StreamableHTTP is the newer, more efficient protocol that supports:

- Bi-directional communication
- Long-running connections
- Automatic session management
- Better error handling
- Native support for streaming responses
- **Not currently supported in Cursor, so we are using SSE for that**

### SSE (Legacy Protocol)

Server-Sent Events (SSE) is currently maintained for backward compatibility. It's needed because:

- Current version of Cursor uses SSE for communication
- It provides a simpler implementation for basic use cases
- It works with existing infrastructure that might not support newer protocols

## Setting Up in Cursor

### Running Locally:

1. Clone the repository
2. Install dependencies:

```bash
pnpm install
```

2. Build the server:

```bash
pnpm build
```

3. Run the server in http mode:

```bash
pnpm start:http
```

4. Configure Cursor to use the local MCP server by adding this to your settings:

```
{
  "mcpServers": {
    "Hats Protocol MCP (Local)": {
      "url": "http://localhost:3001/sse"
    },
     "Hats Protocol MCP (Deployed)": {
      "url": "our-deployment-url.com/sse"
    },
  }
}
```

## Available Tools and Example Prompts

The server provides several tools that can be accessed through natural language prompts in Cursor:

### Currently Active Tools

#### 1. Get Tree Structure (`get_tree`)

**Purpose**: Retrieves a tree on a specific chain.

Example prompts:

- "Please show me tree 1 on Optimism"

#### 2. Get Hat Details (`get_hat_by_id`)

**Purpose**: Retrieves comprehensive information about a specific Hat, including its properties, metadata, and configuration.

Example prompts:

- "What are the details of Hat 0x0000041f00010001000200010000000000000000000000000000000000000000 on Sepolia ?"
- "Tell me more about this specific Hat"

#### 3. Get Wearer Information (`get_wearer`)

**Purpose**: Finds out who currently wears a specific hat, helping track hat assignments and ownership.

Example prompts:

- "Show me the current wearer of this hat"
- "List all wearers of hat ID {x}"
- "Who wears this Hat?"

#### 4. Check Eligibility (`get_eligibility`)

**Purpose**: Evaluates whether an address meets the criteria to wear a particular Hat. Supports ENS.

Example prompts:

- "Is someone.eth eligibile for hat X on chain Y?'
- "What are the eligibility requirements for this hat?"
- "Check if address 0x123... can wear hat 42"

### Work in Progress Tools (Coming Soon)

#### 5. Compare Draft (`compare_draft`) - WIP

**Purpose**: Analyzes differences between a draft hat configuration and its current state, useful for reviewing proposed changes.

Example prompts:

- "What changes are proposed in this draft compared to the current hat?"
- "Show me the differences between the draft and current configuration"
- "Compare the eligibility criteria in this draft with the existing hat"

#### 6. Create Draft (`create_draft`) - WIP

**Purpose**: Initiates a new draft for modifying hat properties, allowing for proposed changes to be reviewed before implementation.

Example prompts:

- "Create a new draft for hat 42 with updated eligibility criteria"
- "Start a draft to modify the admin hat's properties"
- "Make a draft proposal for changing the wearer requirements"

## Chaining Prompts Together

You can chain multiple queries together naturally in your conversation. Here are some examples:

1. Exploring a hat and its wearers:

   ```
   "Can you first show me the tree structure starting from Hat 1 on Optimism, and then tell me who's wearing each of the Hats you find?"
   ```

2. Checking eligibility for multiple hats:

   ```
   "Could you look up Hats X and Y on chain Z, and check if I'm eligible for either of them?"
   ```

3. Complex analysis:

   ```
   "I'd like to understand the Hat structure - can you show me the tree, then for each Hat check who's wearing it and what the eligibility requirements are?"
   ```

4. Draft workflow (once available):
   ```
   "Can you show me the current Hat details for hat X, create a draft with modified eligibility, and then compare the changes?"
   ```

## Best Practices

1. Be specific in your prompts - include Hat IDs when you have them
2. When exploring unknown hats, start with the tree structure to understand the hierarchy
3. Use natural follow-up questions to dig deeper into specific hats
4. Feel free to ask for multiple pieces of information in a single prompt
5. If you're not getting the information you need, try rephrasing your question

## Development Notes

- The server supports both streamableHttp, SSE (soon to be deprecated), and stdio modes
- Debug logging is available for troubleshooting if running locally
- Tool schemas are automatically generated from Zod definitions
- The AI will handle converting your natural language queries into the appropriate tool calls
