# Domain-MCP

A simple MCP server that lets AI assistants help you with domain research - checking availability, looking up WHOIS info, finding expired domains, and more.

No API keys needed. Everything works out of the box.

## What it does

- **Check domain availability** - See if a domain is available to register
- **WHOIS lookup** - Get registration info, expiration dates, registrar details
- **DNS records** - Look up A, MX, TXT, and other DNS records
- **SSL certificates** - Check SSL cert info and expiration
- **Find expired domains** - Search for recently expired or deleted domains
- **Domain age** - See how old a domain is
- **Bulk checks** - Check multiple domains at once

## Quick Start

```bash
# Install uv (if you don't have it)
pip install uv

# Clone the repo
git clone https://github.com/yourusername/domain-mcp.git
cd domain-mcp

# Set up and install
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e .

# Run it
python main.py
```

## Using with Claude Desktop

Add this to your Claude Desktop config:

```json
{
  "mcp-servers": {
    "domain-mcp": {
      "command": "python",
      "args": ["/path/to/domain-mcp/main.py", "--transport", "stdio"]
    }
  }
}
```

## Example Usage

Just ask Claude things like:
- "Is mydomain.com available?"
- "Show me WHOIS info for google.com"
- "Find expired domains with 'tech' in the name"
- "What are the DNS records for example.com?"

## How it works

Uses free, public APIs and services:
- RDAP for WHOIS data (no auth needed)
- Cloudflare DNS over HTTPS
- crt.sh for SSL certificates
- Public domain databases

Everything is fetched fresh when you ask - no caching, always current data.

## License

MIT