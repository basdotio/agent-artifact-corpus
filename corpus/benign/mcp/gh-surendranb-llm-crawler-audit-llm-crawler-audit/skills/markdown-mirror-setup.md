# Markdown Mirroring & Content Negotiation for the Agentic Web

Techniques and architectures to serve native Markdown representations of HTML pages for LLM crawlers, Claude Code, and agentic browsers.

---

## 1. Why Markdown Parity Matters

Modern web pages are heavy with client-side hydration bundles (Next.js, React, Vue), tracking scripts, SVGs, and nested DOM wrappers. When LLMs browse HTML pages:
- **Token Inflation**: A 500-word article can consume 15,000+ tokens of raw HTML.
- **Latency & Parsing Failures**: Complex DOMs frequently cause extraction hallucinations or truncation.
- **Cost**: Processing raw HTML is up to 5x more expensive in LLM inference costs than clean Markdown.

---

## 2. The Three Markdown Delivery Patterns

### Pattern A: HTML Head Alternate Link
Add a discovery tag in the `<head>` of every HTML page pointing to its exact Markdown equivalent:

```html
<link rel="alternate" type="text/markdown" href="https://example.com/posts/agent-architecture.md">
```

### Pattern B: HTTP Link Header
Emit the alternate relation directly in the HTTP response headers:

```http
Link: <https://example.com/posts/agent-architecture.md>; rel="alternate"; type="text/markdown"
Vary: Accept
```

### Pattern C: Content Negotiation (Accept: text/markdown)
Inspect incoming request headers. If the client or agent specifies `Accept: text/markdown`, return clean Markdown with `Content-Type: text/markdown; charset=utf-8`:

```http
GET /posts/agent-architecture HTTP/1.1
Host: example.com
Accept: text/markdown, text/html;q=0.9
```

---

## 3. Implementation Examples

### Cloudflare Worker / Edge Middleware
```javascript
export default {
  async fetch(request, env) {
    const accept = request.headers.get("Accept") || "";
    const url = new URL(request.url);

    if (accept.includes("text/markdown") && !url.pathname.endsWith(".md")) {
      const mdUrl = new URL(`${url.pathname}.md`, url.origin);
      const mdResponse = await fetch(mdUrl);
      if (mdResponse.ok) {
        const headers = new Headers(mdResponse.headers);
        headers.set("Content-Type", "text/markdown; charset=utf-8");
        headers.set("Vary", "Accept");
        return new Response(mdResponse.body, { status: 200, headers });
      }
    }

    const response = await fetch(request);
    const headers = new Headers(response.headers);
    headers.append("Link", `<${url.origin}${url.pathname}.md>; rel="alternate"; type="text/markdown"`);
    headers.set("Vary", "Accept");
    return new Response(response.body, { status: response.status, headers });
  }
};
```

### Next.js Route Handler / Middleware
```typescript
import { NextResponse } from 'next/server';
import type { NextRequest } from 'next/server';

export function middleware(request: NextRequest) {
  const accept = request.headers.get('accept') || '';
  if (accept.includes('text/markdown')) {
    const markdownUrl = new URL(`${request.nextUrl.pathname}.md`, request.url);
    return NextResponse.rewrite(markdownUrl);
  }
}
```

---

## 4. Verification

1. **Verify Link Tag**:
   ```bash
   curl -s https://example.com/page | grep -i 'rel="alternate".*type="text/markdown"'
   ```

2. **Verify Content Negotiation**:
   ```bash
   curl -s -I -H "Accept: text/markdown" https://example.com/page
   ```
   Expected response: `content-type: text/markdown; charset=utf-8` and `vary: Accept`.
