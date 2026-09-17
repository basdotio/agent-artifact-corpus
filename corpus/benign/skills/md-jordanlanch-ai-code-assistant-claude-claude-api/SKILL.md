# Claude API Integration Skill

**Description:** Expert skill for building applications with Claude API, including best practices for API integration, streaming, prompt engineering, and error handling.

## When to Use This Skill

Use this skill when:
- Implementing Claude API endpoints
- Setting up streaming responses
- Optimizing API calls and token usage
- Implementing error handling and retries
- Working with Claude's message format
- Implementing rate limiting and cost optimization

## Core Capabilities

### 1. API Setup
```typescript
import Anthropic from '@anthropic-ai/sdk';

const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});
```

### 2. Basic Message Creation
```typescript
const message = await anthropic.messages.create({
  model: 'claude-sonnet-4-5-20250929',
  max_tokens: 4096,
  messages: [
    {
      role: 'user',
      content: 'Your prompt here'
    }
  ]
});
```

### 3. Streaming Responses
```typescript
const stream = await anthropic.messages.stream({
  model: 'claude-sonnet-4-5-20250929',
  max_tokens: 4096,
  messages: [{ role: 'user', content: 'Your prompt' }],
});

for await (const chunk of stream) {
  if (chunk.type === 'content_block_delta' &&
      chunk.delta.type === 'text_delta') {
    process.stdout.write(chunk.delta.text);
  }
}
```

### 4. System Prompts
```typescript
const message = await anthropic.messages.create({
  model: 'claude-sonnet-4-5-20250929',
  max_tokens: 4096,
  system: 'You are an expert code assistant...',
  messages: [{ role: 'user', content: 'Help me...' }]
});
```

## Best Practices

### Token Optimization
- Use appropriate max_tokens values
- Monitor token usage with response metadata
- Consider using Claude Haiku for simple tasks
- Use Sonnet 4.5 for complex reasoning

### Error Handling
```typescript
try {
  const message = await anthropic.messages.create({...});
} catch (error) {
  if (error instanceof Anthropic.APIError) {
    console.error('Status:', error.status);
    console.error('Message:', error.message);
  }
  throw error;
}
```

### Rate Limiting
- Implement exponential backoff
- Monitor rate limit headers
- Queue requests appropriately
- Use batch processing when possible

### Prompt Engineering
- Be clear and specific
- Provide examples when needed
- Use structured output formats
- Break complex tasks into steps

## Environment Variables Required

```env
ANTHROPIC_API_KEY=your_api_key_here
```

## Recommended Models

- **claude-sonnet-4-5-20250929**: Best balance of speed and intelligence
- **claude-opus-4-5-20250929**: Maximum capability for complex tasks
- **claude-haiku-3.5**: Fast and cost-effective for simple tasks

## Security Notes

- Never expose API keys in client-side code
- Use environment variables
- Implement API key rotation
- Monitor usage and set billing limits
- Validate user inputs before sending to API
