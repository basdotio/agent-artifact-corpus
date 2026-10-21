# CLAUDE.md

This file provides guidance to you, an LLM agent, on how to effectively contribute to the Chlorpromazine MCP Server project. Your primary goal is to assist in developing a robust, context-aware prompting system for other LLM agents.

## Project Vision & Core Principles

We are building a Model Context Protocol (MCP) server to provide powerful, context-aware tools for LLM agents working within codebases. Our work is guided by these principles:

1.  **Context Awareness**: Tools must provide rich, project-specific context.
2.  **Extensibility**: The system must be easy to extend with new tools and prompts.
3.  **Security**: All operations must be secure and handle sensitive data safely.
4.  **Performance**: Context gathering and processing must be efficient.
5.  **Consistency**: We use standardized interfaces and patterns.

## Commands

*   `npm run dev`: Start the development server with hot-reloading.
*   `npm run build`: Compile TypeScript to JavaScript in `dist/`.
*   `npm start`: Run the compiled server from `dist/`.
*   `npm test`: Run the test suite.
*   `npm run clean`: Remove the `dist/` directory.

## Environment Setup

A `.env` file is required and should contain:

*   `SERPAPI_KEY`: Required for the web search tool. Get from `serpapi.com`.
*   `SITE_FILTER`: Optional. A comma-separated list of domains to prioritize in search results.
*   `PORT`: Optional. The server port, defaults to `3000`.
*   `API_KEY`: Optional. An API key for authenticating requests to the server.

## Architecture Overview

The project uses a modular architecture centered around a Prompt Registry, a Tool System, and various Context Providers.

### 1. Prompt Registry (`src/prompts`)

This is the central hub for all prompt handlers. It enforces a consistent interface, making it easy to discover and use available prompts.

### 2. Tool System (`src/handlers` and `src/services`)

This system provides the core functionality available to the LLM. The tools are the building blocks for the prompts.

*   **`sober-thinking`**: Analyzes project context by reading key files (`package.json`, `README.md`, etc.) to ground the agent.
*   **`buzzkill`**: Provides real-time, context-aware web search results via SerpAPI to answer questions or validate information.

### 3. Context Providers

These are services that gather and supply the context needed by the tools:

*   **Project Context**: File structure, dependencies, and configuration.
*   **Runtime Context**: OS, environment variables, and process info.
*   **Version Control**: Git history, branch status, and diffs (planned).

## Implementation Roadmap

Your work should align with our phased implementation plan.

### Phase 1: Core Infrastructure (Current)

*   [x] Basic prompt registration system (`src/prompts/index.ts`).
*   [x] `sober-thinking` and `buzzkill` tools implemented.
*   [x] File system and web search services (`src/services`).

### Phase 2: Enhanced Tooling (Next)

*   [ ] Implement semantic code search capabilities.
*   [ ] Add a file viewer with syntax highlighting.
*   [ ] Integrate Git operations (view history, status, diffs).
*   [ ] Create a test runner integration.

### Phase 3: Advanced Features (Future)

*   [ ] Context-aware code generation.
*   [ ] Interactive debugging tools.
*   [ ] Performance profiling and security analysis.

Your contributions will help us build a cutting-edge tool that prevents LLM 'hallucinations' and empowers agents to perform complex development tasks with greater accuracy and awareness.