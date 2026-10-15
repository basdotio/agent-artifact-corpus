# Remote Serverless MCP Servers

You want to run a remote MCP server, but you don't want to host or pay for a server. Well you're in luck, you can use the Vercel Hobby Tier to run it for free.

This is an adapter library that provides a stateless Python MCP server that runs on [Vercel Functions](https://vercel.com/docs/functions), enabling serverless deployment of MCP tools as edge functions with self-hosting installers. 

## Prerequisites

[Fork](https://github.com/sdiehl/mcp-on-vercel/fork) this repo and [connect it](https://vercel.com/docs/getting-started-with-vercel/template#connect-your-git-provider) to your Vercel account. Once it's deployed get the URL
(`your-domain.vercel.app`).

If you don't have uv installed, install it from astral:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Then, install the MCP server using the self-hosted installer:

```bash
uv run https://your-domain.vercel.app/install.py
```

And we're done. This automatically:

- Configures Claude Desktop and Cursor to use the MCP server
- Uses the bridge script served directly from the server
- No downloads or local files needed

Go to your client and type something stupid like "Use MCP to get the server time" and it should use the remote server.

## Authentication (Optional)

The server supports optional API key authentication to restrict access. To enable authentication:

1. **Server-side**: Set the `MCP_API_KEY` environment variable in your Vercel deployment
2. **Client-side**: The installer will prompt for an API key during setup

You can set the API key in your `vercel.json` file or in the Vercel dashboard:

```json
{
  "env": {
    "MCP_API_KEY": "your-secret-key-here"
  }
}
```

When an API key is configured on the server, all MCP requests must include the key in the `X-API-Key` header. The bridge script automatically handles this when the `MCP_API_KEY` environment variable is set in the client configuration.

## Local Development

```bash
uv sync
vercel dev
```

## Deploy

You just push to Github and it should just work.

Or manually deploy:

```bash
vercel --prod
```
