# Ollama Integration Skill

Integrate Ollama LLM capabilities into your Flutter app using the built-in toolkit.

## When to Use This Skill

- Adding AI chat functionality to the app
- Implementing tool-calling agents for task automation
- Creating conversational interfaces with LLMs
- Building AI-powered features with local or remote Ollama
- Developing agentic workflows with custom tools

## Prerequisites

- Ollama installed and running (locally or remote server)
- Network access to Ollama server
- Basic understanding of LLM concepts (optional, the toolkit abstracts most complexity)

## What This Skill Does

This skill helps you integrate the `ollama_toolkit` module into your Flutter app. The toolkit includes:

- **Full Ollama API Client**: Chat, generate, embeddings, model management
- **Model Registry**: Capabilities database for 15+ models (tool calling, vision, thinking)
- **Agent Framework**: LangChain-inspired thinking loops with tool support
- **Configuration Service**: Persist settings with SharedPreferences
- **Memory Management**: Conversation history with sliding window options

## Usage Examples

### Example 1: Basic Chat Interface

**User Prompt:**
```
Use the ollama_toolkit to add a simple chat screen that connects to my local Ollama server 
at http://localhost:11434 and uses the llama3.2 model. Include streaming responses for 
real-time feedback.
```

**What the AI will do:**
1. Import the toolkit: `import 'package:min_flutter_template/ollama_toolkit/ollama_toolkit.dart';`
2. Create an `OllamaClient` instance
3. Build a chat UI with message history
4. Use `chatStream()` for streaming responses
5. Add proper error handling for connection issues

### Example 2: Agent with Custom Tools

**User Prompt:**
```
Create an AI agent using ollama_toolkit that can answer questions and use these tools:
- Calculator for math operations
- Current time checker
- Weather lookup (mock implementation)

Use the llama3.2 model and show the agent's thinking steps in the UI.
```

**What the AI will do:**
1. Create custom tool classes extending `Tool`
2. Set up an `OllamaAgent` with the tools
3. Use `runWithTools()` to process queries
4. Display agent steps (thinking, tool calls, results) in the UI
5. Add a system prompt to guide agent behavior

### Example 3: Configuration Screen

**User Prompt:**
```
Add an Ollama configuration screen where users can:
- Set the base URL
- Test the connection
- Select a default model from available models
- View model capabilities (tool calling, vision, context window)

Save the configuration persistently.
```

**What the AI will do:**
1. Use `OllamaConfigService` for persistence
2. Create a settings screen with form fields
3. Use `listModels()` to fetch available models
4. Display model capabilities from `ModelRegistry`
5. Add connection test button using `testConnection()`

### Example 4: Multi-Turn Conversation with Memory

**User Prompt:**
```
Build a chat interface with conversation memory that:
- Keeps the last 10 messages
- Always remembers the system prompt
- Shows message count in the UI
- Allows clearing conversation history
```

**What the AI will do:**
1. Use `SystemPlusSlidingMemory(windowSize: 10)`
2. Create `OllamaAgent` with the memory
3. Add UI controls for memory management
4. Display current memory state

### Example 5: Model Capability Checker

**User Prompt:**
```
Create a screen that lists all Ollama models and shows their capabilities:
- Tool calling support (🔧)
- Vision support (👁️)
- Thinking mode (🧠)
- Context window size

Allow filtering by capability.
```

**What the AI will do:**
1. Use `ModelRegistry.getAllModelNames()`
2. Get capabilities for each model with `ModelRegistry.getCapabilities()`
3. Implement filtering with `ModelRegistry.findModelsByCapability()`
4. Display with Material Design cards

## Implementation Patterns

### Pattern 1: Simple Client Usage

```dart
final client = OllamaClient(
  baseUrl: 'http://localhost:11434',
  timeout: Duration(seconds: 60),
);

// Non-streaming
final response = await client.chat(
  'llama3.2',
  [OllamaMessage.user('Hello!')],
);

// Streaming
await for (final chunk in client.chatStream('llama3.2', messages)) {
  setState(() {
    responseText += chunk.message.content;
  });
}
```

### Pattern 2: Agent with Tools

```dart
final agent = OllamaAgent(
  client: client,
  model: 'llama3.2',
  systemPrompt: 'You are a helpful assistant with access to tools.',
);

final tools = [
  CalculatorTool(),
  CurrentTimeTool(),
  CustomWeatherTool(),
];

final result = await agent.runWithTools(userQuery, tools);

// Show steps
for (final step in result.steps) {
  print('${step.type}: ${step.content}');
}
```

### Pattern 3: Configuration Persistence

```dart
final config = OllamaConfigService();

// Save
await config.setBaseUrl('http://192.168.1.100:11434');
await config.setDefaultModel('llama3.2');

// Load
final baseUrl = await config.getBaseUrl();
final model = await config.getDefaultModel();

// History
final recentModels = await config.getModelHistory();
```

## Key Toolkit Components

### OllamaClient
- `chat()` / `chatStream()` - Chat with message history
- `generate()` / `generateStream()` - Generate from prompt
- `listModels()` - Get available models
- `embeddings()` - Generate embeddings
- `testConnection()` - Verify server access

### ModelRegistry
- `getCapabilities(model)` - Get model features
- `supportsToolCalling(model)` - Check tool support
- `supportsVision(model)` - Check vision support
- `findModelsByCapability()` - Filter models

### OllamaAgent
- `run(input)` - Process query without tools
- `runWithTools(input, tools)` - Process with tool access
- `clearMemory()` - Reset conversation

### Memory Types
- `ConversationMemory()` - Unlimited history
- `SlidingWindowMemory(windowSize)` - Last N messages
- `SystemPlusSlidingMemory(windowSize)` - System + N messages

## Common Issues and Solutions

### Issue: Connection Refused
**Solution:** Ensure Ollama is running and URL is correct. Use `testConnection()` to verify.

### Issue: Model Not Found
**Solution:** Check available models with `listModels()` or pull model with `pullModel(model)`.

### Issue: Tool Not Called
**Solution:** Verify model supports tool calling with `ModelRegistry.supportsToolCalling(model)`. Use models like llama3.2, qwen2.5, mistral.

### Issue: Out of Memory
**Solution:** Use `SlidingWindowMemory` to limit conversation history. Reduce model size or use smaller variants.

## Supported Models (January 2025)

| Model | Tool Calling | Vision | Thinking | Context |
|-------|-------------|--------|----------|---------|
| llama3.2 | ✅ | ✅ | ❌ | 128k |
| llama3.3 | ✅ | ✅ | ❌ | 128k |
| qwen2.5 | ✅ | ❌ | ❌ | 128k |
| qwen2.5-coder | ✅ | ❌ | ❌ | 128k |
| deepseek-v3 | ✅ | ❌ | ✅ | 128k |
| mistral | ✅ | ❌ | ❌ | 128k |
| mixtral | ✅ | ❌ | ❌ | 128k |
| codestral | ✅ | ❌ | ❌ | 128k |
| pixtral | ✅ | ✅ | ❌ | 128k |
| gemma2 | ✅ | ❌ | ❌ | 128k |
| phi4 | ✅ | ❌ | ❌ | 128k |

## Testing Your Integration

Always test:
1. Connection to Ollama server
2. Model availability
3. Streaming response handling
4. Tool execution (if using agents)
5. Error handling for network issues
6. Configuration persistence

## Related Documentation

- Toolkit README: `lib/ollama_toolkit/README.md`
- Architecture Design: `docs/ARCHITECTURE_OLLAMA_TOOLKIT.md`
- Ollama API Docs: https://docs.ollama.com/

## Quick Start for AI Agents

**Copy-paste this prompt to get started:**

```
I want to integrate Ollama into my Flutter app using the ollama_toolkit.

Create a basic chat screen with:
- Connection to http://localhost:11434
- Model selection dropdown (using ModelRegistry)
- Chat history display
- User input field
- Streaming responses
- Error handling

Use llama3.2 as the default model.
```

This will scaffold a complete working integration that you can then customize.
