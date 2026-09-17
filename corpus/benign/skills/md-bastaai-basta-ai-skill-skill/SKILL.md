---
name: basta
description: Integration with Basta auction and ecommerce APIs. Use when users want to create auctions, manage sales, handle bidding, or work with auction-related data using Basta's GraphQL APIs (Management API and Client API). Trigger on requests involving auctions, sales, items, bids, bidders, or real-time auction updates.
---

# Basta API Integration

## Overview

Basta is an API-first ecommerce engine for auctions and dynamic pricing. This skill provides workflows for integrating with Basta's two GraphQL APIs to create and manage auctions, handle bidding, and build real-time auction experiences.

## API Architecture

Basta provides two GraphQL APIs with distinct purposes:

**Management API** (`https://management.api.basta.app`)
- Server-side, authenticated operations
- Create and manage sales/auctions
- Configure items, pricing, bid rules
- Generate bidder tokens
- Authentication: `x-account-id` and `x-api-key` headers

**Client API** (`https://client.api.basta.app`)
- Public-facing, client-side operations
- Browse auctions and items
- Place bids (with bidder token)
- Real-time updates via WebSocket subscriptions
- Authentication: Optional JWT bidder tokens

## Core Workflows

Basta provides **two flexible workflows** for managing items and sales:

**Workflow A: Direct Item Creation**
1. Create standalone items with `createItem`
2. Create sale
3. Add existing items to sale with `addItemToSale`
4. Publish sale

**Workflow B: Integrated Creation**
1. Create sale
2. Create items directly in sale with `createItemForSale`
3. Publish sale

### 1. Creating a Sale

Use Management API to create a sale:

```graphql
mutation CreateSale {
  createSale(accountId: "ACCOUNT_ID", input: {
    title: "Auction Title"
    description: "Auction description"
    currency: "USD"
    bidIncrementTable: {
      rules: [
        { lowRange: 0, highRange: 100000, step: 1000 }
      ]
    }
    closingMethod: OVERLAPPING
    closingTimeCountdown: 60000  # milliseconds
  }) {
    id
    status
  }
}
```

### 2a. Creating Standalone Items (Workflow A)

Create reusable items independent of any sale:

```graphql
mutation CreateItem {
  createItem(accountId: "ACCOUNT_ID", input: {
    title: "Item Title"
    description: "Item description"
    startingBid: 1000  # cents
    reserve: 50000     # cents
  }) {
    id
    title
    status
  }
}
```

### 2b. Adding Existing Items to Sale (Workflow A)

Add previously created items to a sale:

```graphql
mutation AddItemToSale {
  addItemToSale(accountId: "ACCOUNT_ID", input: {
    saleId: "SALE_ID"
    itemId: "ITEM_ID"  # From createItem
    allowedBidTypes: [MAX]
    openDate: "2024-02-01T15:00:00Z"
    closingDate: "2024-02-01T16:00:00Z"
  }) {
    id
    status
    dates {
      openDate
      closingStart
      closingEnd
    }
  }
}
```

### 2c. Creating Items Directly in Sale (Workflow B)

Create and add items to a sale in one operation:

```graphql
mutation CreateItemForSale {
  createItemForSale(accountId: "ACCOUNT_ID", input: {
    saleId: "SALE_ID"
    title: "Item Title"
    description: "Item description"
    startingBid: 1000  # cents
    reserve: 50000     # cents
    allowedBidTypes: [MAX]
    openDate: "2024-02-01T15:00:00Z"
    closingDate: "2024-02-01T16:00:00Z"
  }) {
    id
    status
    dates {
      openDate
      closingStart
      closingEnd
    }
  }
}
```

### 3. Publishing the Sale

```graphql
mutation PublishSale {
  publishSale(accountId: "ACCOUNT_ID", input: {
    saleId: "SALE_ID"
  }) {
    id
    status
  }
}
```

### 4. Creating Bidder Tokens

Generate JWT tokens for bidders:

```graphql
mutation CreateBidderToken {
  createBidderToken(accountId: "ACCOUNT_ID", input: {
    metadata: {
      userId: "user-123"
      ttl: 60  # minutes
    }
  }) {
    token
    expiration
  }
}
```

### 5. Placing Bids

Use Client API with bidder token. Basta supports two bid types:

**MaxBid (Proxy Bidding):**
- User sets maximum amount willing to pay
- Auction engine automatically bids incrementally
- Winning amount may be lower than max
- Engine reacts to counter-bids up to max amount

**NormalBid (Direct Bidding):**
- One-time bid at specified amount
- Must align with bid increment table
- Does not react to counter-bids

```graphql
# Headers: { "Authorization": "Bearer BIDDER_TOKEN" }
mutation BidOnItem {
  bidOnItem(
    saleId: "SALE_ID"
    itemId: "ITEM_ID"
    amount: 10000  # cents
    type: MAX       # or NORMAL
  ) {
    __typename
    ... on BidPlacedSuccess {
      amount
      bidStatus
      date
      bidType
    }
    ... on BidPlacedError {
      errorCode
      error
    }
  }
}
```

## Real-time Updates

For live auction experiences, use GraphQL subscriptions over WebSocket:

**Endpoint:** `wss://client.api.basta.app/query`
**Protocol:** graphql-ws

Connect with bidder token in `connection_init` payload:

```json
{
  "type": "connection_init",
  "payload": {
    "token": "BIDDER_TOKEN"
  }
}
```

Subscribe to auction events:

```graphql
subscription {
  auctionUpdates(saleId: "SALE_ID") {
    itemId
    currentBid
    bidCount
    status
  }
}
```

## Webhooks

Basta can notify your application when events occur via webhooks. Configure webhooks in the admin portal settings.

**Webhook Structure:**
```json
{
  "idempotencyKey": "UNIQUE_STRING",
  "actionType": "EVENT_TYPE",
  "data": { }
}
```

**Event Types:**

**BidOnItem** - Sent when a bid is placed:
```json
{
  "bidId": "...",
  "saleId": "...",
  "itemId": "...",
  "userId": "...",
  "amount": 500,
  "maxAmount": 500,
  "saleState": {
    "newLeader": "...",
    "currentBid": 600,
    "currentMaxBid": 600
  },
  "reactiveBids": [...]
}
```

**SaleStatusChanged** - Sent when sale status changes:
```json
{
  "saleId": "...",
  "saleStatus": "OPEN"
}
```

**ItemsStatusChanged** - Sent when item statuses change:
```json
{
  "saleId": "...",
  "itemStatusChanges": [{
    "itemId": "...",
    "itemStatus": "CLOSING",
    "saleState": {...}
  }]
}
```

## Implementation Guidelines

**Workflow Selection:**
- **Use Workflow A (createItem + addItemToSale)** when:
  - Items need to be reused across multiple sales
  - Building an item catalog/inventory system
  - Items are created before sales are scheduled
- **Use Workflow B (createItemForSale)** when:
  - Items are specific to a single sale
  - Creating items and sales in one flow
  - Simpler integration requirements

**Item Reusability:**
- Items created with `createItem` can be added to multiple sales
- Use `removeItemFromSale` to remove items without deleting them
- Update items with `updateItem` to modify across all sales

**Authentication:**
- Store API credentials securely
- Generate bidder tokens server-side only
- Include proper headers in all Management API requests

**Error Handling:**
- Check `__typename` for union return types
- Handle `BidPlacedError` responses
- Implement retry logic for network failures

**Rate Limits:**
- Management API: Use batch operations where possible
- Client API: Cache query results appropriately
- WebSocket: Implement reconnection logic

**Testing:**
- Test in GraphQL Playground: https://management.api.basta.app
- Verify bidder token generation and expiration
- Test WebSocket connections before production
- Test both workflows to understand which fits your use case

## Key Concepts

**Sale:** Container for one or more items being auctioned

**Item:** Individual lot within a sale

**Bid Increments:** Rules defining minimum bid increases

**Closing Method:** OVERLAPPING - items can close at different times

**Closing Time Countdown:** Time extension when bids arrive near closing

**Reserve:** Minimum price for item to sell

**Starting Bid:** Initial bid amount

**Bidder Token:** JWT granting permission to bid on behalf of a user

## Common Pitfalls

**Using the wrong mutation combination:**
- ❌ Wrong: Call `addItemToSale` with an item created via `createItemForSale`
- ✅ Correct: Use `addItemToSale` only with items created via `createItem`

**Missing sale context for item additions:**
- ❌ Wrong: Call `createItemForSale` or `addItemToSale` without a valid `saleId`
- ✅ Correct: Create sale first, then add/create items with the returned `saleId`

**Not understanding item lifecycle:**
- Items created with `createItem` are reusable across sales
- Items created with `createItemForSale` are tied to that specific sale
- Use `removeItemFromSale` to detach items without deletion

**Forgetting to publish:**
- Sales remain in `UNPUBLISHED` status until `publishSale` is called
- Items won't accept bids until the sale is published

## References

For detailed API schemas and examples:
- `references/management_api.md` - Complete Management API reference
- `references/client_api.md` - Complete Client API reference
- `references/webhooks.md` - Comprehensive webhooks guide with implementation examples
- `references/glossary.md` - Basta terminology and concepts
