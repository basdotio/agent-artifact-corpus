# lexoffice-mcp

MCP server (built with [FastMCP](https://gofastmcp.com)) for creating invoices in
[Lexware Office](https://developers.lexware.io/docs/#invoices-endpoint) (formerly lexoffice).

## Tools

| Tool | Purpose |
| --- | --- |
| `create_invoice` | Creates an invoice. Drafts by default; `finalize=true` creates an open invoice with a binding number. |
| `find_contacts` | Looks up customers by name, email or customer number to reference them via `contact_id`. |
| `get_invoice` | Returns the full invoice (line items, totals, status). |

`create_invoice` supports one-time addresses or existing contacts, `custom`, `service`, `material` and `text`
line items, net, gross and vat-free tax types, performance dates and periods, payment terms with early
payment discount, and title, introduction and remark texts. It returns the invoice id, number, status,
totals and deep links into Lexware.

The client respects the Lexware limit of 2 requests per second and retries `429` responses. Other errors
are not retried, so a failing request never creates duplicate invoices.

## Example

Ask Claude something like:

> Create a draft invoice for Bike & Ride GmbH, Musterstraße 42, 79112 Freiburg, Germany:
> 8 hours of consulting at 120 EUR net with 19% VAT, payable within 14 days.

Claude calls `create_invoice` with a payload such as:

```json
{
  "invoice": {
    "address": { "name": "Bike & Ride GmbH", "street": "Musterstraße 42", "zip": "79112", "city": "Freiburg", "country_code": "DE" },
    "line_items": [
      { "name": "Consulting", "quantity": 8, "unit_name": "Stunde", "unit_price": 120, "tax_rate_percentage": 19 }
    ],
    "payment_conditions": { "payment_term_label": "Zahlbar innerhalb von 14 Tagen", "payment_term_duration": 14 }
  }
}
```

and gets back the invoice number, totals and a link to open the draft in Lexware.

## Setup

1. Create an API key at <https://app.lexware.de/addons/public-api>.
2. Clone this repository. No install step is needed: `uv run --with` resolves the dependencies
   (`fastmcp`, `httpx`) on the fly when the server starts.

Run the server manually to check it starts:

```bash
LEXWARE_API_KEY=your-api-key uv run --with "fastmcp>=4" --with httpx /absolute/path/to/lexoffice_mcp/main.py
```

## Install into Claude Code

```bash
claude mcp add lexware --scope user \
  -e LEXWARE_API_KEY=your-api-key \
  -- uv run --with "fastmcp>=4" --with httpx /absolute/path/to/lexoffice_mcp/main.py
```

Check the connection with `claude mcp list` or `/mcp` inside Claude Code. The key is stored in plain text in
your Claude Code configuration, so use a key dedicated to this integration and revoke it when no longer needed.

## Install into Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "lexware": {
      "command": "uv",
      "args": ["run", "--with", "fastmcp>=4", "--with", "httpx", "/absolute/path/to/lexoffice_mcp/main.py"],
      "env": { "LEXWARE_API_KEY": "your-api-key" }
    }
  }
}
```

## Configuration

| Variable | Default | Description |
| --- | --- | --- |
| `LEXWARE_API_KEY` | required | Lexware public API key. |
| `LEXWARE_BASE_URL` | `https://api.lexware.io` | API gateway. |
| `LEXWARE_APP_URL` | `https://app.lexware.de` | Used for invoice deep links. |

## Development

```bash
uv sync
uv run pytest
```

Tests run the server in memory against a mocked Lexware API, so no API key is needed.

## License

MIT, see [LICENSE](LICENSE).
