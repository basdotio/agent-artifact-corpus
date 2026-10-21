# ChatGPT Local MCP Starter for macOS

Run a local FastMCP server from ChatGPT through OpenAI Secure MCP Tunnel.

This starter includes a working Stock OHLC MCP example backed by Alpha Vantage.

```text
ChatGPT
   ↓
OpenAI Secure MCP Tunnel
   ↓
tunnel-client
   ↓
macOS
   ↓
FastMCP
   ↓
Stock OHLC data
```

## Prerequisites

This starter currently supports macOS only. Install the two command-line tools:

```bash
brew install uv
brew install openai/tools/tunnel-client
```

Verify them:

```bash
uv --version
tunnel-client --version
```

The exact supported `tunnel-client` installation command can vary by release. If the Homebrew command changes, follow the current OpenAI tunnel-client documentation.

For the example OHLC tool, create a local `.env` from `.env.example` and add your Alpha Vantage key. The `.env` file is ignored by Git.

## Get an Alpha Vantage API key

The example server uses Alpha Vantage for daily OHLCV data. The Alpha Vantage key is separate from the OpenAI Runtime API Key.

1. Open the [official Alpha Vantage API-key page](https://www.alphavantage.co/support/#api-key).
2. Complete the short form and copy the API key you receive.
3. In the project directory, create your local environment file:

   ```bash
   cp .env.example .env
   ```

4. Edit `.env` and replace the placeholder:

   ```dotenv
   ALPHAVANTAGE_API_KEY=your_alpha_vantage_key
   ```

Keep `.env` on your Mac only. It is ignored by Git; never paste this key into `README.md`, `config.json`, or a commit. Alpha Vantage's [official documentation](https://www.alphavantage.co/documentation/) describes the available stock-data endpoints.

## OpenAI preparation

Before running the bootstrap, create or obtain an OpenAI Secure MCP Tunnel and a Runtime API Key. The normal workflow needs only:

- Tunnel ID
- Runtime API Key

You do not need an OpenAI Admin API key, organization ID, or workspace ID for this starter workflow. Never commit the Runtime API Key to GitHub.

## Quick start

```bash
git clone https://github.com/YOUR_USERNAME/YOUR_REPO.git
cd YOUR_REPO
uv sync
uv run bootstrap.py
```

The bootstrap asks for the two OpenAI values only when they are not already present in the environment:

```text
Enter your OpenAI Tunnel ID:
Enter your OpenAI Runtime API Key:
```

It then detects the repository path, validates the MCP source, configures a local `tunnel-client` profile, runs tunnel diagnostics, and starts the tunnel in the foreground. Keep the Terminal window open.

The tunnel ID must match `tunnel_` followed by 32 lowercase hexadecimal characters, for example:

```text
tunnel_0123456789abcdef0123456789abcdef
```

The generated MCP command uses the absolute repository path automatically, including paths containing spaces. No local path editing is required.

### Environment-variable mode

To avoid the interactive prompts for one session:

```bash
export CONTROL_PLANE_TUNNEL_ID="tunnel_xxx"
export CONTROL_PLANE_API_KEY="runtime-key"
uv run bootstrap.py
```

Do not store the runtime key in the repository, `config.json`, YAML, shell profile, or README.

## Configuration

`config.example.json` contains only non-secret settings:

```json
{
  "profile": "stock-ohlc",
  "entrypoint": "main.py",
  "mcp_name": "Stock OHLC MCP"
}
```

Copy it to `config.json` if you want to customize the profile name, MCP entrypoint, or display name. `config.json` is ignored by Git. The bootstrap uses the official `tunnel-client init` command and does not ask users to edit tunnel-client YAML.

The example server remains runnable locally over stdio:

```bash
uv run python main.py
```

Its existing tool is `get_ohlc(symbol, limit=10)`, returning JSON-serializable daily `date`, `open`, `high`, `low`, `close`, and `volume` data.

## Try it in ChatGPT

After `tunnel-client` is running, open ChatGPT, go to Plugins / Connectors, choose Add an Existing Tunnel, and select the tunnel you configured.

Try:

```text
Use my Stock OHLC MCP to fetch the last 5 days of OHLC data for RELIANCE.NS.
```

```text
Use my Stock OHLC MCP to fetch RELIANCE.NS and TCS.NS and compare their recent price movement.
```

## Troubleshooting

Run these checks in order:

```bash
uv sync
uv run python -m py_compile main.py
uv run python main.py
tunnel-client doctor --profile stock-ohlc --explain
tunnel-client run --profile stock-ohlc
```

Then add the existing tunnel in ChatGPT. Do not debug ChatGPT while `tunnel-client doctor` is failing.

If you see a path-related problem, do not replace the generated path with a hard-coded example such as `/Users/name/project`. The bootstrap detects the absolute repository path itself, including paths with spaces.

If `stock-ohlc` already exists, rerunning the bootstrap refreshes that named profile with the official `tunnel-client init --force` flow. Unrelated profiles are not deleted or changed.

## Security notes

- OpenAI Tunnel IDs are stored as profile configuration; the Runtime API Key is passed by environment reference and held in memory by the bootstrap.
- The bootstrap never puts the Runtime API Key in a command-line argument, repository file, or generated JSON/YAML.
- `.env`, `config.json`, virtual environments, editor files, and macOS metadata are ignored.
- No OpenAI tunnels are created or deleted automatically; the bootstrap configures the local client for a tunnel you already created.
- The project has no telemetry beyond the requests made by `tunnel-client` and the OHLC data provider.

## License

MIT. See [LICENSE](LICENSE).
