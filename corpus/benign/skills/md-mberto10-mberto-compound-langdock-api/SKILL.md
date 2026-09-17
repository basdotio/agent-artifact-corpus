---
name: langdock-api-integration
description: This skill should be used when the user asks to "build with langdock api", "integrate langdock into my app", "use langdock as backend", "call langdock assistant from code", "langdock api client", "embed langdock in application", or needs to build applications that use Langdock APIs as a building block for AI-powered features.
---

# Building with the Langdock API

Use Langdock APIs as building blocks to add AI capabilities to your applications - chatbots, document processing, knowledge retrieval, and more.

## When to Use

- Building a chatbot powered by Langdock assistants
- Adding AI features to an existing application
- Creating backend services that leverage Langdock
- Integrating knowledge folder search into your app
- Building custom UIs on top of Langdock assistants

## Authentication Setup

All Langdock API requests require a Bearer token:

```python
# Python
headers = {
    "Authorization": f"Bearer {LANGDOCK_API_KEY}",
    "Content-Type": "application/json"
}
```

```javascript
// JavaScript/Node.js
const headers = {
  'Authorization': `Bearer ${process.env.LANGDOCK_API_KEY}`,
  'Content-Type': 'application/json'
};
```

**Get API Key:** Langdock Dashboard → Settings → API Keys

---

## Building a Chatbot Backend

### Python Implementation

```python
import os
import requests
from typing import List, Dict, Optional

class LangdockChatbot:
    """Chatbot powered by a Langdock assistant."""

    def __init__(self, assistant_id: str, api_key: Optional[str] = None):
        self.assistant_id = assistant_id
        self.api_key = api_key or os.environ.get("LANGDOCK_API_KEY")
        self.base_url = "https://api.langdock.com/assistant/v1"
        self.conversation_history: List[Dict] = []

    def chat(self, user_message: str) -> str:
        """Send a message and get a response."""
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "assistantId": self.assistant_id,
                "messages": self.conversation_history
            }
        )
        response.raise_for_status()

        assistant_message = response.json()["choices"][0]["message"]["content"]
        self.conversation_history.append({
            "role": "assistant",
            "content": assistant_message
        })

        return assistant_message

    def reset_conversation(self):
        """Clear conversation history."""
        self.conversation_history = []


# Usage
bot = LangdockChatbot(assistant_id="your-assistant-id")
response = bot.chat("What can you help me with?")
print(response)
```

### Node.js/TypeScript Implementation

```typescript
interface Message {
  role: 'user' | 'assistant' | 'tool';
  content: string;
}

class LangdockChatbot {
  private assistantId: string;
  private apiKey: string;
  private baseUrl = 'https://api.langdock.com/assistant/v1';
  private conversationHistory: Message[] = [];

  constructor(assistantId: string, apiKey?: string) {
    this.assistantId = assistantId;
    this.apiKey = apiKey || process.env.LANGDOCK_API_KEY!;
  }

  async chat(userMessage: string): Promise<string> {
    this.conversationHistory.push({
      role: 'user',
      content: userMessage
    });

    const response = await fetch(`${this.baseUrl}/chat/completions`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${this.apiKey}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        assistantId: this.assistantId,
        messages: this.conversationHistory
      })
    });

    if (!response.ok) {
      throw new Error(`API error: ${response.status}`);
    }

    const data = await response.json();
    const assistantMessage = data.choices[0].message.content;

    this.conversationHistory.push({
      role: 'assistant',
      content: assistantMessage
    });

    return assistantMessage;
  }

  resetConversation(): void {
    this.conversationHistory = [];
  }
}

// Usage
const bot = new LangdockChatbot('your-assistant-id');
const response = await bot.chat('Hello!');
```

---

## Building with Temporary Assistants

Create assistants on-the-fly without pre-configuring them in Langdock:

```python
def create_specialist_response(
    user_query: str,
    specialist_type: str,
    instructions: str
) -> str:
    """Create a temporary specialist assistant for a specific task."""

    response = requests.post(
        "https://api.langdock.com/assistant/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {LANGDOCK_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "assistant": {
                "name": f"{specialist_type} Specialist",
                "instructions": instructions,
                "model": "gpt-4o"  # Optional model override
            },
            "messages": [
                {"role": "user", "content": user_query}
            ]
        }
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# Example: Create specialists dynamically
legal_response = create_specialist_response(
    user_query="Review this contract clause...",
    specialist_type="Legal",
    instructions="You are a legal expert. Analyze contracts and identify risks."
)

code_response = create_specialist_response(
    user_query="Optimize this function...",
    specialist_type="Code Review",
    instructions="You are a senior developer. Review code for performance and best practices."
)
```

---

## Building a Knowledge Search Service

Integrate Langdock knowledge folders into your application:

```python
class KnowledgeSearchService:
    """Search service backed by Langdock knowledge folders."""

    def __init__(self, folder_id: str, api_key: str):
        self.folder_id = folder_id
        self.api_key = api_key
        self.base_url = "https://api.langdock.com/v1/knowledge-folders"

    def search(self, query: str, limit: int = 10) -> List[Dict]:
        """Search documents in the knowledge folder."""
        response = requests.post(
            f"{self.base_url}/{self.folder_id}/search",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            },
            json={
                "query": query,
                "limit": limit
            }
        )
        response.raise_for_status()
        return response.json()["results"]

    def upload_document(self, file_path: str) -> Dict:
        """Upload a document to the knowledge folder."""
        with open(file_path, "rb") as f:
            response = requests.post(
                f"{self.base_url}/{self.folder_id}/files",
                headers={"Authorization": f"Bearer {self.api_key}"},
                files={"file": f}
            )
        response.raise_for_status()
        return response.json()

    def list_documents(self) -> List[Dict]:
        """List all documents in the folder."""
        response = requests.get(
            f"{self.base_url}/{self.folder_id}/files",
            headers={"Authorization": f"Bearer {self.api_key}"}
        )
        response.raise_for_status()
        return response.json()["files"]


# Usage: Build a document Q&A system
knowledge = KnowledgeSearchService(
    folder_id="your-folder-id",
    api_key=os.environ["LANGDOCK_API_KEY"]
)

# Search for relevant documents
results = knowledge.search("quarterly revenue projections")

# Use results to augment assistant context
```

---

## Building a RAG Pipeline

Combine knowledge search with assistant chat for RAG:

```python
class RAGPipeline:
    """Retrieval-Augmented Generation using Langdock."""

    def __init__(self, assistant_id: str, folder_id: str, api_key: str):
        self.assistant_id = assistant_id
        self.folder_id = folder_id
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

    def query(self, question: str) -> Dict:
        """Answer a question using RAG."""

        # Step 1: Retrieve relevant documents
        search_response = requests.post(
            f"https://api.langdock.com/v1/knowledge-folders/{self.folder_id}/search",
            headers=self.headers,
            json={"query": question, "limit": 5}
        )
        search_response.raise_for_status()
        documents = search_response.json()["results"]

        # Step 2: Build context from retrieved documents
        context = "\n\n".join([
            f"Document: {doc['title']}\n{doc['content']}"
            for doc in documents
        ])

        # Step 3: Query assistant with context
        augmented_prompt = f"""Based on the following documents, answer the question.

Documents:
{context}

Question: {question}

Answer based only on the provided documents. If the answer isn't in the documents, say so."""

        chat_response = requests.post(
            "https://api.langdock.com/assistant/v1/chat/completions",
            headers=self.headers,
            json={
                "assistantId": self.assistant_id,
                "messages": [{"role": "user", "content": augmented_prompt}]
            }
        )
        chat_response.raise_for_status()

        return {
            "answer": chat_response.json()["choices"][0]["message"]["content"],
            "sources": [doc["title"] for doc in documents]
        }


# Usage
rag = RAGPipeline(
    assistant_id="your-assistant-id",
    folder_id="your-folder-id",
    api_key=os.environ["LANGDOCK_API_KEY"]
)

result = rag.query("What were our Q3 results?")
print(f"Answer: {result['answer']}")
print(f"Sources: {result['sources']}")
```

---

## Building a Structured Output Service

Get structured JSON responses for data extraction:

```python
from pydantic import BaseModel
from typing import List

class ExtractedEntity(BaseModel):
    name: str
    type: str
    confidence: float

class ExtractionResult(BaseModel):
    entities: List[ExtractedEntity]
    summary: str

def extract_entities(text: str) -> ExtractionResult:
    """Extract structured data from text using Langdock."""

    response = requests.post(
        "https://api.langdock.com/assistant/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {LANGDOCK_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "assistant": {
                "name": "Entity Extractor",
                "instructions": "Extract named entities from text. Return structured JSON."
            },
            "messages": [{"role": "user", "content": text}],
            "output": {
                "type": "json_schema",
                "json_schema": {
                    "name": "extraction_result",
                    "schema": ExtractionResult.model_json_schema()
                }
            }
        }
    )
    response.raise_for_status()

    result_json = response.json()["choices"][0]["message"]["content"]
    return ExtractionResult.model_validate_json(result_json)


# Usage
result = extract_entities("Apple CEO Tim Cook announced new products in Cupertino.")
for entity in result.entities:
    print(f"{entity.name} ({entity.type}): {entity.confidence}")
```

---

## Error Handling & Retry Logic

Production-ready error handling:

```python
import time
from functools import wraps

class LangdockError(Exception):
    """Base exception for Langdock API errors."""
    pass

class RateLimitError(LangdockError):
    """Rate limit exceeded."""
    pass

def with_retry(max_retries: int = 3, base_delay: float = 1.0):
    """Decorator for retry logic with exponential backoff."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except RateLimitError:
                    if attempt == max_retries - 1:
                        raise
                    delay = base_delay * (2 ** attempt)
                    time.sleep(delay)
            return func(*args, **kwargs)
        return wrapper
    return decorator

@with_retry(max_retries=3)
def call_langdock_api(endpoint: str, payload: dict) -> dict:
    """Make API call with error handling."""
    response = requests.post(
        f"https://api.langdock.com{endpoint}",
        headers={
            "Authorization": f"Bearer {LANGDOCK_API_KEY}",
            "Content-Type": "application/json"
        },
        json=payload
    )

    if response.status_code == 429:
        raise RateLimitError("Rate limit exceeded")
    elif response.status_code == 401:
        raise LangdockError("Invalid API key")
    elif response.status_code >= 500:
        raise LangdockError(f"Server error: {response.status_code}")

    response.raise_for_status()
    return response.json()
```

---

## Rate Limits

| Limit | Value |
|-------|-------|
| Requests per minute | 500 RPM |
| Tokens per minute | 60,000 TPM |

Rate limits are per workspace. Implement backoff when hitting limits.

---

## Live Documentation

For latest API details, fetch documentation:

```
Use WebFetch on:
- https://docs.langdock.com/api-endpoints/api-introduction
- https://docs.langdock.com/api-endpoints/assistant/assistant
- https://docs.langdock.com/api-endpoints/assistant/assistant-models
```
