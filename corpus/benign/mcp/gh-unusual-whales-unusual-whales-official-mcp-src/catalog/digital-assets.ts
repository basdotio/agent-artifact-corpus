import { z } from "zod"
import type { ToolCatalog } from "../engine.js"

const pair = z.string().min(1).max(20).describe("Crypto pair (e.g., BTC-USD, ETH-USD)")

const cryptoCandle = z.enum(["1m", "5m", "10m", "15m", "30m", "1h", "4h", "1d", "1w"])

const blockchain = z.enum([
  "arbitrum", "avalanche", "binance_smart_chain", "bitcoin", "cardano",
  "dogecoin", "ethereum", "fantom", "optimism", "polkadot",
  "polygon", "ripple", "solana", "tron",
])

export const digitalAssetsCatalog: ToolCatalog = {
  id: "uw_crypto",
  summary: `Access UnusualWhales crypto data including prices, OHLC candles, whale trades, and whale transactions across 3 blockchains.

Available commands:
- state: Get current state for a crypto pair with 24h OHLCV data (pair required)
- ohlc: Get OHLC candles for a crypto pair (pair, candle_size required; limit, date optional)
- whales_recent: Get recent large crypto whale trades (limit optional)
- whale_transactions: Get whale transactions across blockchains (limit, blockchain, token_symbol optional)

Supported candle sizes: 1m, 5m, 10m, 15m, 30m, 1h, 4h, 1d, 1w
Supported blockchains: ethereum, bitcoin, solana, polygon, arbitrum, avalanche, binance_smart_chain, cardano, dogecoin, fantom, optimism, polkadot, ripple, tron`,
  commands: [
    { name: "state", route: "/api/crypto/{pair}/state", params: z.object({ pair }) },
    { name: "ohlc", route: "/api/crypto/{pair}/ohlc/{candle_size}", params: z.object({ pair, candle_size: cryptoCandle, limit: z.number().int().min(1).max(500).default(100).optional(), date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/).describe("Date in YYYY-MM-DD format").optional() }) },
    { name: "whales_recent", route: "/api/crypto/whales/recent", params: z.object({ limit: z.number().int().min(1).max(500).default(100).optional() }) },
    { name: "whale_transactions", route: "/api/crypto/whale-transactions", params: z.object({ limit: z.number().int().min(1).max(500).default(100).optional(), blockchain: blockchain.optional(), token_symbol: z.string().describe("Filter by token symbol (e.g., ETH, USDT)").optional() }) },
  ],
}
