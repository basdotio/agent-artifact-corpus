---
name: wallbit-skills
description: Integration with the Wallbit public API to query balances, transactions, execute trades, get asset and wallet data. Use when working with Wallbit API, trading endpoints, account balances, stock portfolio, investment operations, or when the user mentions Wallbit.
---

# Wallbit Public API

REST API to integrate Wallbit functionality: query balances, view transaction history, execute trades and more.

## Quick Start

**Base URL**: `https://api.wallbit.io`

**Authentication**: `X-API-Key` header required on all requests.

```bash
curl -H "X-API-Key: YOUR_API_KEY" https://api.wallbit.io/api/public/v1/balance/checking
```

## Endpoints Overview

| Category     | Endpoint                             | Method | Description                   |
| ------------ | ------------------------------------ | ------ | ----------------------------- |
| Balance      | `/api/public/v1/balance/checking`    | GET    | Checking account balance      |
| Balance      | `/api/public/v1/balance/stocks`      | GET    | Investment portfolio          |
| Transactions | `/api/public/v1/transactions`        | GET    | Transaction history           |
| Trades       | `/api/public/v1/trades`              | POST   | Execute buy/sell              |
| Account      | `/api/public/v1/account-details`     | GET    | Bank account details          |
| Wallets      | `/api/public/v1/wallets`             | GET    | Crypto wallet addresses       |
| Assets       | `/api/public/v1/assets`              | GET    | List available assets         |
| Assets       | `/api/public/v1/assets/{symbol}`     | GET    | Specific asset info           |
| Operations   | `/api/public/v1/operations/internal` | POST   | Investment deposit/withdrawal |

## Authentication

### PHP/Laravel

```php
use Illuminate\Support\Facades\Http;

/**
 * Creates an HTTP client configured for the Wallbit API.
 *
 * @return \Illuminate\Http\Client\PendingRequest
 */
function createWallbitClient()
{
    return Http::withHeaders([
        'X-API-Key' => config('services.wallbit.api_key'),
        'Accept' => 'application/json',
    ])->baseUrl('https://api.wallbit.io');
}
```

### JavaScript

```javascript
const wallbitClient = {
  baseUrl: "https://api.wallbit.io",
  apiKey: process.env.WALLBIT_API_KEY,

  async request(endpoint, options = {}) {
    const response = await fetch(`${this.baseUrl}${endpoint}`, {
      ...options,
      headers: {
        "X-API-Key": this.apiKey,
        Accept: "application/json",
        "Content-Type": "application/json",
        ...options.headers,
      },
    });
    return response.json();
  },
};
```

### Python

```python
import requests

class WallbitClient:
    def __init__(self, api_key: str):
        self.base_url = "https://api.wallbit.io"
        self.headers = {
            "X-API-Key": api_key,
            "Accept": "application/json"
        }

    def request(self, method: str, endpoint: str, **kwargs):
        url = f"{self.base_url}{endpoint}"
        response = requests.request(method, url, headers=self.headers, **kwargs)
        response.raise_for_status()
        return response.json()
```

## Error Handling

| Code | Description                          | Action                              |
| ---- | ------------------------------------ | ----------------------------------- |
| 401  | Invalid or missing API Key           | Check X-API-Key header              |
| 403  | Insufficient permissions             | Check API Key permissions           |
| 412  | Incomplete KYC or blocked account    | Complete verification in the app    |
| 422  | Validation error                     | Review sent parameters              |
| 429  | Rate limit exceeded                  | Wait `retry_after` seconds          |

### Error handling example (PHP/Laravel)

```php
/**
 * Executes a Wallbit API request with error handling.
 *
 * @param string $method
 * @param string $endpoint
 * @param array $data
 * @return array
 * @throws \Exception
 */
function wallbitRequest(string $method, string $endpoint, array $data = []): array
{
    $client = createWallbitClient();

    $response = match($method) {
        'GET' => $client->get($endpoint, $data),
        'POST' => $client->post($endpoint, $data),
        default => throw new \Exception("Unsupported method: {$method}")
    };

    if ($response->status() === 429) {
        $retryAfter = $response->json('retry_after', 60);
        throw new \Exception("Rate limit exceeded. Retry in {$retryAfter} seconds.");
    }

    if ($response->status() === 401) {
        throw new \Exception("Invalid or missing API Key.");
    }

    if ($response->status() === 403) {
        $permissions = $response->json('your_permissions', []);
        throw new \Exception("Insufficient permissions. You have: " . implode(', ', $permissions));
    }

    if ($response->status() === 422) {
        $errors = $response->json('errors', []);
        throw new \Exception("Validation error: " . json_encode($errors));
    }

    if (!$response->successful()) {
        throw new \Exception($response->json('message', 'Unknown error'));
    }

    return $response->json('data');
}
```

## Rate Limiting

Response headers:

- `X-RateLimit-Limit`: Requests allowed per minute
- `X-RateLimit-Remaining`: Remaining requests
- `X-RateLimit-Reset`: Unix timestamp of reset
- `Retry-After`: Seconds until retry is allowed (only on 429)

## Code Generation Guidelines

When generating code for this API:

1. **PHP/Laravel**: Use camelCase for functions, include PHPDoc docstrings
2. **Validate parameters** before sending according to OpenAPI spec types
3. **Always handle errors** 401, 403, 422, 429
4. **Do not hardcode API Keys**, use environment variables

### Supported currencies

- Transactions: `USD`, `EUR`, `ARS`, `MXN`, `USDC`, `USDT`, `BOB`, `COP`, `PEN`, `DOP`
- Account Details: `USD`, `EUR` (countries: `US`, `EU`)
- Wallets: `USDT`, `USDC` (networks: `ethereum`, `arbitrum`, `solana`, `polygon`, `tron`)

### Asset Categories

`MOST_POPULAR`, `ETF`, `DIVIDENDS`, `TECHNOLOGY`, `HEALTH`, `CONSUMER_GOODS`, `ENERGY_AND_WATER`, `FINANCE`, `REAL_ESTATE`, `TREASURY_BILLS`, `VIDEOGAMES`, `ARGENTINA_ADR`

### Trade Order Types

- `MARKET`: Market order (executes immediately)
- `LIMIT`: Limit order (requires `limit_price` and `time_in_force`)
- `STOP`: Stop order (requires `stop_price`)
- `STOP_LIMIT`: Stop-limit order (requires `stop_price` and `limit_price`)

## Additional Resources

- For detailed endpoint documentation, see [api-reference.md](api-reference.md)
- For complete code examples, see [examples.md](examples.md)
